# v2 of optimized_excel_filtering.py: name-based columns, per-session floor, swing threshold, QC columns.
import os
import re
import time
import importlib.util
import traceback
import datetime
import warnings
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
from concurrent.futures import ProcessPoolExecutor, as_completed

# --- GLOBALS ---
CHOICE_MAP = {
    "0": '/Feature/Tail/Tip_X',
    "1": '/Feature/Tail/Center_X',
    "2": '/Feature/Tail/Base_X',
    "3": ['/Feature/Paw/Hind/Left_X', '/Feature/Paw/Hind/Right_X']
}

SUBTRACTION_MAP = {
    ("0", "groundwalk", "old"): 0.522,
    ("1", "groundwalk", "old"): 0.525,
    ("0", "groundwalk", "new"): 0.502,
    ("1", "groundwalk", "new"): 0.519,
    ("0", "beamwalk", "old"): 0.445,
    ("1", "beamwalk", "old"): 0.445,
    ("0", "beamwalk", "new"): 0.43,
    ("1", "beamwalk", "new"): 0.44,
    ("0", "gridwalk", "old"): 0.496,
    ("0", "gridwalk", "new"): 0.483,
    ("1", "gridwalk", "old"): 0.504,
    ("1", "gridwalk", "new"): 0.498,
    ("0", "swimming", "old"): 0.566,
    ("0", "swimming", "new"): 0.568,
}

OFFSET_MAP = {
    ("0", "groundwalk", "old"): 0,
    ("1", "groundwalk", "old"): 0,
    ("0", "groundwalk", "new"): 0,
    ("0", "beamwalk", "old"): 0,
    ("1", "beamwalk", "old"): 0,
    ("0", "beamwalk", "new"): 0,
    ("0", "gridwalk", "old"): 0,
    ("0", "gridwalk", "new"): 0,
    ("1", "gridwalk", "old"): 0,
    ("0", "swimming", "old"): 0.029,
    ("0", "swimming", "new"): 0.036,
}

# --- v2 SETTINGS ---
SWING_SPEED_DEFAULT = 0.1    # m/s; paw speed above this = swing. 0 keeps every frame (stance included)
# Per-experiment defaults, from v2 (Savitzky-Golay) paw speed histograms on 15 SCA2-Q129 sessions per test:
# groundwalk/gridwalk speeds are bimodal (jitter ~0.02, swing ~0.5-0.6) with the valley at 0.08-0.126 -> 0.1.
# beamwalk has one broad peak (~0.06-0.1, slow gripping/sliding), no valley -> 0.03 only removes jitter.
# swimming not measured -> SWING_SPEED_DEFAULT.
SWING_SPEED_BY_EXPERIMENT = {"groundwalk": 0.1, "gridwalk": 0.1, "beamwalk": 0.03}
FLOOR_PCT = 10               # floor = 10th percentile of left hind toe Y (90th in the upside-down right view)
FROZEN_MIN_REPEATS = 1      # a marker whose X and Y repeat EXACTLY for this many frames is a tracker placeholder
                             # (real smoothed positions always change a little, even on a resting paw)
# Implausible-position checks (v2). Real paw moves in a clean session: <= ~18 mm/frame; tracking jumps: 40-65 mm.
NOSE_EXIT_TOL = 0.001        # m; the window ends at the first frame the nose is this close to its exit (final) X
MAX_JUMP_M = 0.03            # m per frame (3 m/s at 100 fps); a measured marker moving more than this = tracking jump
HIND_AHEAD_TOL = 0.01        # m; hind paw more than this ahead of the front paw on the same side = label swap
BODY_LENGTH_RANGE = (0.7, 1.3)  # nose-tail base distance allowed, as a fraction of the session median

# --- Kinematics rebuilt from 'Positions (used)' ---
# The calculations_*.py scripts run remove_outliers() (median/MAD z-score) on every metric before saving the
# Kinematics sheet. Paws rest for most frames, so the median is the resting value and every swing peak gets
# flagged and spline-filled: paw speeds come out ~10x too low and toe-clearance / step-length peaks are cut.
# 'Positions (used)' holds the smoothed positions those metrics came from, untouched by that step, so v2
# recomputes each metric from it with the same formulas. Columns with no formula here are kept from the sheet.
_P = '/Feature/'
Y_METRICS = {  # column: (marker, take abs)
    'Toe Clearance Forepaw (Right)': ('Paw/Tao/Front/Right', True), 'Toe Clearance Hindpaw (Right)': ('Paw/Tao/Hind/Right', True),
    'Toe Clearance Forepaw (Left)': ('Paw/Tao/Front/Left', False), 'Toe Clearance Hindpaw (Left)': ('Paw/Tao/Hind/Left', False),
    'Iliac Crest Height (Right)': ('PSIS/Right', True), 'Iliac Crest Height (Left)': ('PSIS/Left', False),
    'Hip Height (Right)': ('Hip/Right', True), 'Hip Height (Left)': ('Hip/Left', False),
    'Tail Base Height (Right)': ('Tail/Base/RightView', True), 'Tail Base Height (Left)': ('Tail/Base/LeftView', False),
    # Saved sheets are mixed (most use RightView, some LeftView: e.g. Footprint weeks 36-40, ~55% of Beam).
    # v2 always uses LeftView, as the calculations scripts do, so every session measures the same thing.
    'Nose Height': ('Head/Nose/LeftView', True), 'Tail Tip Height': ('Tail/Tip/LeftView', True),
    'Shoulder Height (Right)': ('Shoulder/Upper/Right', False), 'Shoulder Height (Left)': ('Shoulder/Upper/Left', False),
    'Front Paw Drag (Right)': ('Paw/Tao/Front/Right', True), 'Front Paw Drag (Left)': ('Paw/Tao/Front/Left', True),
    'Hind Paw Drag (Right)': ('Paw/Tao/Hind/Right', True), 'Hind Paw Drag (Left)': ('Paw/Tao/Hind/Left', True),
    'Head Rotation': ('Head/Jaw', False),
}
DIST_METRICS = {
    'Step Width (Hind)': ('Paw/Hind/Left', 'Paw/Hind/Right'), 'Step Width (Front)': ('Paw/Front/Left', 'Paw/Front/Right'),
    'Step Length (Left)': ('Paw/Front/Left', 'Paw/Hind/Left'), 'Step Length (Right)': ('Paw/Front/Right', 'Paw/Hind/Right'),
    'Protraction/Retraction (Right)': ('Paw/Tao/Hind/Right', 'PSIS/Right'),
    'Protraction/Retraction (Left)': ('Paw/Tao/Hind/Left', 'PSIS/Left'),
}
ANGLE_METRICS = {  # angle at the middle marker
    **{f'Hip Angle ({s})': ('PSIS/' + s, 'Hip/' + s, 'Knee/' + s) for s in ('Right', 'Left')},
    **{f'Knee Angle ({s})': ('Hip/' + s, 'Knee/' + s, 'Ankle/' + s) for s in ('Right', 'Left')},
    **{f'Ankle Angle ({s})': ('Knee/' + s, 'Ankle/' + s, f'Paw/Tao/Hind/{s}') for s in ('Right', 'Left')},
    **{f'Shoulder Angle ({s})': (f'Shoulder/Upper/{s}', f'Shoulder/Lower/{s}', 'Elbow/' + s) for s in ('Right', 'Left')},
    **{f'Elbow Angle ({s})': (f'Shoulder/Lower/{s}', 'Elbow/' + s, 'Wrist/' + s) for s in ('Right', 'Left')},
    **{f'Wrist Angle ({s})': ('Elbow/' + s, 'Wrist/' + s, f'Paw/Tao/Front/{s}') for s in ('Right', 'Left')},
    'Tail Angle (Side View)': ('Tail/Base/LeftView', 'Tail/Center/LeftView', 'Tail/Tip/LeftView'),
}
PAW_KIN = re.compile(r'^(Front|Hind) (Left|Right)(?: Paw)? (Vx|Vy|Speed|Ax|Ay|\|Acc\|) \(')


def _xy(pos, marker):
    x, y = _P + marker + '_X', _P + marker + '_Y'
    return (pos[x], pos[y]) if x in pos and y in pos else (None, None)


def _savgol(s, deriv, dt):
    """Savitzky-Golay derivative (window 5, order 2, as the calculations scripts smooth); NaN stays NaN."""
    if s.notna().sum() < 5:
        return pd.Series(np.nan, index=s.index)
    filled = s.interpolate(limit_direction='both')
    return pd.Series(savgol_filter(filled, 5, 2, deriv=deriv, delta=dt), index=s.index).where(s.notna())


def kinematics_from_positions(pos, kin):
    """Rebuild every Kinematics column that has a known formula from the position sheet (see note above).
    Returns (dataframe in the sheet's column order, list of columns kept from the sheet)."""
    out = pd.DataFrame({'Time': pos['Time']}, index=pos.index)
    dt = pos['Time'].diff().median()
    sheet = kin.set_index(kin['Time'].round(6)) if 'Time' in kin else None
    kept = []
    for col in kin.columns:
        if col == 'Time':
            continue
        val = None
        if col in Y_METRICS:
            x, y = _xy(pos, Y_METRICS[col][0])
            val = None if y is None else (y.abs() if Y_METRICS[col][1] else y)
        elif col in DIST_METRICS:
            (x1, y1), (x2, y2) = (_xy(pos, m) for m in DIST_METRICS[col])
            val = None if x1 is None or x2 is None else np.hypot(x1 - x2, y1 - y2)
        elif col in ANGLE_METRICS:
            pts = [_xy(pos, m) for m in ANGLE_METRICS[col]]
            if all(p[0] is not None for p in pts):
                (x1, y1), (x2, y2), (x3, y3) = pts
                ax_, ay_, bx, by = x1 - x2, y1 - y2, x3 - x2, y3 - y2
                norm = np.hypot(ax_, ay_) * np.hypot(bx, by)
                cos = ((ax_ * bx + ay_ * by) / norm.where(norm > 1e-24)).clip(-1, 1)
                val = np.degrees(np.arccos(cos))
        elif (m := PAW_KIN.match(col)) and dt > 0:
            x, y = _xy(pos, f'Paw/{m[1]}/{m[2]}')
            if x is not None:
                kind = m[3]
                d = 2 if kind in ('Ax', 'Ay', '|Acc|') else 1
                gx, gy = _savgol(x, d, dt), _savgol(y, d, dt)
                val = {'Vx': gx, 'Ax': gx, 'Vy': gy, 'Ay': gy}.get(kind, np.hypot(gx, gy))
        if val is None:
            kept.append(col)
            val = sheet[col].reindex(pos['Time'].round(6)).to_numpy() if sheet is not None else np.nan
        out[col] = val
    return out, kept


def height_columns(df):
    """Height / clearance / drag columns split by view. Upside-down (right) view values are raw Y coordinates
    around 0.5 m; normal (left) view values are already near 0. Name-based, so column order does not matter."""
    cols = [c for c in df.columns if isinstance(c, str) and ('Height' in c or 'Clearance' in c or 'Drag' in c)]
    means = {c: df[c].mean() for c in cols}
    right = [c for c in cols if pd.notna(means[c]) and means[c] > 0.3]
    left = [c for c in cols if c not in right]
    return right, left


def session_floors(raw_win):
    """Floor Y of each side view from the hind toe while it is on the ground (it rests there for most of
    the stance phase). The right view is upside down: its floor is the LARGEST Y."""
    r, l = '/Feature/Paw/Tao/Hind/Right_Y', '/Feature/Paw/Tao/Hind/Left_Y'
    floor_r = raw_win[r].abs().quantile(1 - FLOOR_PCT / 100) if r in raw_win and raw_win[r].notna().any() else None
    floor_l = raw_win[l].quantile(FLOOR_PCT / 100) if l in raw_win and raw_win[l].notna().any() else None
    return floor_r, floor_l


def measured_markers():
    """Markers used by at least one rebuilt measurement (only these are reported in the placeholder warning)."""
    used = {m for m, _ in Y_METRICS.values()}
    used |= {m for pair in DIST_METRICS.values() for m in pair}
    used |= {m for trio in ANGLE_METRICS.values() for m in trio}
    used |= {f'Paw/{fh}/{side}' for fh in ('Front', 'Hind') for side in ('Left', 'Right')}
    return used


def mask_placeholders(pos, min_repeats=FROZEN_MIN_REPEATS):
    """(v2) Tracker placeholders -> NaN. When a marker is lost, its position is held at the last value (or at a
    fixed value before it was first seen), so X and Y repeat exactly. Every repeated frame is set to NaN; the
    first frame of a hold is the last real position and is kept, unless the hold starts at frame 0.
    Returns (masked copy, {marker: boolean Series of masked frames})."""
    out = pos.copy()
    held_by_marker = {}
    for x in [c for c in pos.columns if isinstance(c, str) and c.endswith('_X')]:
        y = x[:-2] + '_Y'
        if y not in pos.columns:
            continue
        same = (pos[x].diff().abs() <= 1e-12) & (pos[y].diff().abs() <= 1e-12)
        run_id = (~same).cumsum()                                # a real frame followed by its repeats
        run_len = same.groupby(run_id).transform('sum')         # number of repeats in that hold
        held = same & (run_len >= min_repeats)
        if len(pos) > 1 and run_len.iloc[0] >= min_repeats:     # held from the first frame: nothing real
            held |= run_id == run_id.iloc[0]
        if held.any():
            out.loc[held, [x, y]] = np.nan
            held_by_marker[x[len(_P):-2]] = held
    return out, held_by_marker


def mask_implausible(pos, last_index):
    """(v2) Positions a walking mouse cannot produce -> NaN (run after mask_placeholders).
    1. Body checks in the ventral view -> the WHOLE frame (we cannot tell which marker is wrong):
       nose behind a hind paw; hind paw more than HIND_AHEAD_TOL ahead of the front paw on the same side;
       nose-tail base length outside BODY_LENGTH_RANGE x the session median.
    2. Jump: a measured marker moving more than MAX_JUMP_M in one frame -> that marker, that frame.
    A check is skipped in frames where its markers are missing. Returns (masked copy, bad frames, {marker: jumps})."""
    out = pos.copy()
    bad = pd.Series(False, index=pos.index)
    nx, ny = _xy(pos, 'Head/Nose')
    if nx is not None:
        nose = nx.iloc[:last_index + 1].dropna()
        direction = np.sign(nose.iloc[-1] - nose.iloc[0]) if len(nose) > 1 and nose.iloc[-1] != nose.iloc[0] else 1.0
        for side in ('Left', 'Right'):
            hx, fx = _xy(pos, 'Paw/Hind/' + side)[0], _xy(pos, 'Paw/Front/' + side)[0]
            if hx is not None:
                bad |= direction * (hx - nx) > 0                    # nose behind a hind paw
                if fx is not None:
                    bad |= direction * (hx - fx) > HIND_AHEAD_TOL   # hind paw well ahead of the front paw
        bx, by = _xy(pos, 'Tail/Base')
        if bx is not None:
            length = np.hypot(nx - bx, ny - by)
            med = length.iloc[:last_index + 1].median()
            if pd.notna(med) and med > 0:
                bad |= (length < BODY_LENGTH_RANGE[0] * med) | (length > BODY_LENGTH_RANGE[1] * med)
    marker_cols = [c for c in out.columns if isinstance(c, str) and c.startswith(_P) and c[-2:] in ('_X', '_Y')]
    out.loc[bad, marker_cols] = np.nan
    jumps = {}  # after the body checks, so a jump does not hide the frame from them
    for m in sorted(measured_markers() | {'Head/Nose', 'Tail/Base'}):
        x, y = _xy(pos, m)
        if x is None:
            continue
        jump = (np.hypot(x.diff(), y.diff()) > MAX_JUMP_M) & ~bad
        if jump.any():
            out.loc[jump, [_P + m + '_X', _P + m + '_Y']] = np.nan
            jumps[m] = jump
    return out, bad, jumps


def paw_kinematic_columns(df):
    """{'Front Right': [its Vx, Vy, Speed, Ax, Ay, |Acc| columns], ...}"""
    out = {}
    for c in df.columns:
        if isinstance(c, str) and c.endswith(" Speed (m/s)"):
            paw = c[:-len(" Speed (m/s)")]
            out[paw] = [k for k in df.columns if isinstance(k, str) and k.startswith(paw + " ") and "(m/s" in k]
    return out


def qc_values(raw_win, kin, swap_win=None):
    """Per-session tracking checks.
    - Tracked frames: % of window frames where all four paws have a position.
    - Step Length SD: ~0 means front and hind markers move as one (tracker locked both on one paw).
    - Hind ahead of front: % of frames where the hind paw is ahead of the front paw on the same side
      (label swaps; should be near 0)."""
    paws = [f'/Feature/Paw/{fh}/{side}_X' for fh in ('Front', 'Hind') for side in ('Left', 'Right')]
    qc = {}
    if all(p in raw_win for p in paws):
        qc['QC Tracked Frames (%)'] = 100 * raw_win[paws].notna().all(axis=1).mean()
        nose = raw_win['/Feature/Head/Nose_X'].dropna() if '/Feature/Head/Nose_X' in raw_win else pd.Series(dtype=float)
        direction = np.sign(nose.iloc[-1] - nose.iloc[0]) if len(nose) > 1 else 1.0
        sw = raw_win if swap_win is None else swap_win  # positions before the body checks removed the swaps
        lead = [direction * (sw[f'/Feature/Paw/Hind/{s}_X'] - sw[f'/Feature/Paw/Front/{s}_X'])
                for s in ('Left', 'Right')]
        ahead = [(d > 0)[d.notna()] for d in lead]  # only frames where both paws have a real position
        qc['QC Hind Ahead of Front (%)'] = 100 * pd.concat(ahead).mean()
    for side in ('Left', 'Right'):
        c = f'Step Length ({side})'
        if c in kin:
            qc[f'QC Step Length SD ({side}) (m)'] = kin[c].std()
    return qc


# --- WORKER FUNCTION ---
def filter_excel_by_column(file_info_tuple, choice, animal_choice, experiment, old_or_new, output_folder, height_cutoff,
                           floor_mode="auto", swing_speed=SWING_SPEED_DEFAULT):
    index, file_path, total_files = file_info_tuple
    file_name = os.path.basename(file_path)
    captured_warnings = []

    column_targets = CHOICE_MAP.get(choice)
    if not column_targets:
         return (False, file_name, f"[ERROR] Invalid choice '{choice}'.", [], False)

    # --- 1. Determine Output Path and Check if it Exists ---
    output_file = os.path.join(output_folder, os.path.splitext(file_name)[0] + '_filtered.xlsx')

    if os.path.exists(output_file):
        return (True, file_name, f"Skipped file {index + 1} of {total_files}: {file_name} (Already exists)", [], True)

    try:
        with warnings.catch_warnings(record=True) as w_log:
            warnings.simplefilter("always") 
            
            with pd.ExcelFile(file_path, engine='calamine') as xls:
                df_raw = pd.read_excel(xls, sheet_name='Positions (used)')
                df_kin = pd.read_excel(xls, sheet_name='Kinematics')

            # --- 2. Find Start/End Indices ---
            threshold = 0.00001
            df_raw_clean = df_raw.dropna(how='all').reset_index(drop=True)
            df_kin_clean = df_kin.dropna(how='all').reset_index(drop=True)

            if isinstance(column_targets, list):
                first_vals = df_raw_clean[column_targets].iloc[0]
                change_mask = ((df_raw_clean[column_targets] - first_vals).abs() > threshold).any(axis=1)
                movement_indices = df_raw_clean.index[change_mask]
            else:
                first_val = df_raw_clean[column_targets].iloc[0]
                movement_indices = df_raw_clean.index[(df_raw_clean[column_targets] - first_val).abs() > threshold]
            
            start_index = movement_indices[0] if not movement_indices.empty else 0

            nose_col = '/Feature/Head/Nose_X'
            if nose_col in df_raw_clean.columns:
                final_static_val = df_raw_clean[nose_col].iloc[-1]
                end_movement_indices = df_raw_clean.index[(df_raw_clean[nose_col] - final_static_val).abs() > threshold]
                last_index = end_movement_indices[-1] if not end_movement_indices.empty else len(df_raw_clean) - 1
            else:
                last_index = len(df_raw_clean) - 1

            # (v2) End = FIRST frame the nose reaches its exit position. After the nose leaves the frame the tracker
            #      can keep inventing nose positions, which the "last change" rule above counts as movement.
            if nose_col in df_raw_clean.columns:
                at_exit = df_raw_clean.index[(df_raw_clean[nose_col] - final_static_val).abs() <= NOSE_EXIT_TOL]
                at_exit = at_exit[at_exit >= start_index]
                if not at_exit.empty and at_exit[0] < last_index:
                    t_exit, t_last = df_raw_clean.loc[at_exit[0], 'Time'], df_raw_clean.loc[last_index, 'Time']
                    if t_last - t_exit > 0.05:
                        captured_warnings.append(
                            f"Nose reached its exit position at {t_exit:.2f}s but kept 'moving' until {t_last:.2f}s "
                            f"(tracking after the nose left): window ends at {t_exit:.2f}s.")
                    last_index = at_exit[0]

            # 3. Kinematics rebuilt from positions (v2), then cut to the movement window
            for col in df_kin_clean.columns:
                if col != 'Time':
                    df_kin_clean[col] = pd.to_numeric(df_kin_clean[col], errors='coerce').astype(float)
            raw_win = df_raw_clean.iloc[start_index : last_index + 1]
            # (v2) Placeholder positions -> NaN for every measurement, floor and QC. Start/end and height cutoff
            #      detection keep the raw values (the start rule relies on the tail tip's placeholder).
            pos_holds, held = mask_placeholders(df_raw_clean)
            pos_real, implausible, jumps = mask_implausible(pos_holds, last_index)
            raw_win_real = pos_real.iloc[start_index : last_index + 1]
            df_kin_full, kept = kinematics_from_positions(pos_real, df_kin_clean)
            if kept:
                captured_warnings.append(f"Kept from Kinematics sheet (no formula / markers missing): {', '.join(kept)}")
            df_kin_filtered = df_kin_full.iloc[start_index : last_index + 1].copy()

            # Height cutoff time: heights are only kept before the hind paw reaches this X
            hind_timestamp = None
            if height_cutoff == "yes":
                hind_paw_col = '/Feature/Paw/Tao/Hind/Left_X'
                if hind_paw_col in df_raw_clean.columns and 'Time' in df_raw_clean.columns:
                    threshold_val = 0 if old_or_new == "new" else -0.016
                    hind_reach = df_raw_clean[df_raw_clean[hind_paw_col] >= threshold_val]
                    if not hind_reach.empty:
                        hind_timestamp = df_raw_clean.loc[hind_reach.index[0], "Time"]

            # 3b. (v2) Start marker appeared only AFTER the height cutoff (e.g. tail tip came into view after the
            #     hind paw passed the cutoff X): no frame of the window is before the cutoff. Height columns only
            #     need paw/hip/PSIS markers, so they are taken from the frames between the hind paws' first
            #     movement and the cutoff. Time duration and every other column keep the start-marker window.
            height_start = start_index
            if hind_timestamp is not None and 'Time' in df_raw_clean.columns \
                    and hind_timestamp < df_raw_clean.loc[start_index, 'Time']:
                paws = CHOICE_MAP["3"]
                paw_start = 0
                if all(p in df_raw_clean.columns for p in paws):
                    moved = ((df_raw_clean[paws] - df_raw_clean[paws].iloc[0]).abs() > threshold).any(axis=1)
                    paw_start = df_raw_clean.index[moved][0] if moved.any() else 0
                if paw_start < start_index:
                    height_start = paw_start
                    df_kin_filtered = df_kin_full.iloc[height_start : last_index + 1].copy()
                    captured_warnings.append(
                        f"Start marker appeared at {df_raw_clean.loc[start_index, 'Time']:.2f}s, after the height cutoff "
                        f"({hind_timestamp:.2f}s): heights taken from hind paw movement start "
                        f"({df_raw_clean.loc[height_start, 'Time']:.2f}s) to the cutoff; other columns and "
                        f"Time Duration still use the start-marker window.")

            # (v2) Report placeholders inside the frames that are measured (markers used by a measurement only)
            first_frame = min(start_index, height_start)
            used = measured_markers()
            in_win = {m: h.iloc[first_frame : last_index + 1] for m, h in held.items() if m in used}
            in_win = {m: h for m, h in in_win.items() if h.any()}
            if in_win:
                captured_warnings.append("Placeholder (frozen) positions removed from measurements: " + "; ".join(
                    f"{m} {int(h.sum())} frames, first at {df_raw_clean.loc[h.idxmax(), 'Time']:.2f}s"
                    for m, h in sorted(in_win.items())))
            bad_win = implausible.iloc[first_frame : last_index + 1]
            jumps_win = {m: j.iloc[first_frame : last_index + 1] for m, j in jumps.items()}
            jumps_win = {m: j for m, j in jumps_win.items() if j.any()}
            if bad_win.any() or jumps_win:
                parts = []
                if bad_win.any():
                    parts.append(f"{int(bad_win.sum())} frames failed the body checks (whole frame removed), first at "
                                 f"{df_raw_clean.loc[bad_win.idxmax(), 'Time']:.2f}s")
                parts += [f"{m} jump in {int(j.sum())} frames, first at {df_raw_clean.loc[j.idxmax(), 'Time']:.2f}s"
                          for m, j in sorted(jumps_win.items())]
                captured_warnings.append("Implausible positions removed from measurements: " + "; ".join(parts))

            # 4. Heights relative to the floor (v2: columns picked by NAME, not position)
            info = []
            right_cols, left_cols = height_columns(df_kin_filtered)
            if height_start < start_index:  # rows before the window start carry heights only (see 3b)
                other_cols = [c for c in df_kin_filtered.columns if c != 'Time' and c not in right_cols + left_cols]
                df_kin_filtered.loc[df_kin_filtered.index < start_index, other_cols] = np.nan
                info.append(f"heights from {df_raw_clean.loc[height_start, 'Time']:.2f}s")
            raw_heights = pos_real.iloc[height_start : last_index + 1]
            if floor_mode == "auto":
                # Floor from the same frames the heights are kept for (before the height cutoff)
                height_win = raw_heights if hind_timestamp is None else raw_heights[raw_heights['Time'] <= hind_timestamp]
                floor_r, floor_l = session_floors(height_win)
                if right_cols and floor_r is not None:
                    df_kin_filtered[right_cols] = floor_r - df_kin_filtered[right_cols]
                if left_cols and floor_l is not None:
                    df_kin_filtered[left_cols] = df_kin_filtered[left_cols] - floor_l
                if (right_cols and floor_r is None) or (left_cols and floor_l is None):
                    toe_cols = ('/Feature/Paw/Tao/Hind/Right_Y', '/Feature/Paw/Tao/Hind/Left_Y')
                    if not all(c in raw_win for c in toe_cols):
                        reason = "hind toe columns missing"
                    elif height_win.empty and hind_timestamp is not None and not raw_win.empty:
                        reason = (f"height cutoff ({hind_timestamp:.2f}s) is before the movement window starts "
                                  f"({raw_win['Time'].iloc[0]:.2f}s), so no frames are left for the floor and all "
                                  f"height columns are blanked; check the tracking of the start marker")
                    elif height_win.empty:
                        reason = "movement window is empty"
                    else:
                        reason = "hind toe has no tracked positions in the window"
                    captured_warnings.append(f"Floor not estimated ({reason}); heights left as is.")
                info.append(f"floor R={floor_r if floor_r is None else round(floor_r, 4)} "
                            f"L={floor_l if floor_l is None else round(floor_l, 4)}")
            else:  # fixed: original SUBTRACTION_MAP / OFFSET_MAP values
                combo = (animal_choice, experiment, old_or_new)
                value_to_subtract, value_to_add_offset = SUBTRACTION_MAP.get(combo), OFFSET_MAP.get(combo)
                if value_to_add_offset:
                    df_kin_filtered[right_cols + left_cols] += value_to_add_offset
                if value_to_subtract is not None and right_cols:
                    df_kin_filtered[right_cols] = value_to_subtract - df_kin_filtered[right_cols]
            info.append(f"upside-down view columns: {len(right_cols)}")

            # 5a. Paw speed / acceleration: keep swing frames only (v2: explicit speed threshold instead of
            #     "== 0", which stops working on Savitzky-Golay derivatives)
            for paw, cols in paw_kinematic_columns(df_kin_filtered).items():
                all_zero = [c for c in cols if (df_kin_filtered[c].fillna(0) == 0).all()]
                if all_zero:  # columns zeroed by the old outlier filter carry no data
                    df_kin_filtered[all_zero] = np.nan
                    captured_warnings.append(f"{paw}: no data in {', '.join(all_zero)}")
                if swing_speed > 0:
                    stance = ~(df_kin_filtered[f"{paw} Speed (m/s)"] > swing_speed)
                    df_kin_filtered.loc[stance, cols] = np.nan

            # 5b. Hind Paw Timestamp Logic (height columns only, by name)
            if hind_timestamp is not None:
                mask_time = df_kin_filtered['Time'] > hind_timestamp
                df_kin_filtered.loc[mask_time, right_cols + left_cols] = np.nan

            # 5c. Quality-control columns (constant per session, so they reach the merged file as measurements)
            for name, value in qc_values(raw_win_real, df_kin_filtered, pos_holds.iloc[start_index : last_index + 1]).items():
                df_kin_filtered[name] = value

            # 6. Statistics and Saving
            time_series = raw_win['Time'].dropna() if 'Time' in raw_win.columns else pd.Series(dtype=float)
            time_duration = (time_series.iloc[-1] - time_series.iloc[0]) if not time_series.empty else 0

            # Height Window: first and last time (s) of the frames the height columns were taken from
            height_times = df_raw_clean['Time'].iloc[height_start : last_index + 1] if 'Time' in df_raw_clean.columns else pd.Series(dtype=float)
            if hind_timestamp is not None:
                height_times = height_times[height_times <= hind_timestamp]
            height_window = (height_times.iloc[0], height_times.iloc[-1]) if not height_times.empty else (np.nan, np.nan)
            stats_cols = [col for col in df_kin_filtered.columns if col != 'Time']
            
            # --- CUSTOM STATISTIC: max_norm_mean (Safe against empty slices) ---
            def max_norm_mean(col):
                clean_col = col.dropna()
                if clean_col.empty:
                    return np.nan
                max_val = clean_col.max()
                if pd.isna(max_val) or max_val == 0:
                    return np.nan
                return (clean_col / max_val).mean()

            # --- CUSTOM STATISTIC: coef_var (Safe against empty slices) ---
            def coef_var(col):
                clean_col = col.dropna()
                if clean_col.empty:
                    return np.nan
                mean_val = clean_col.mean()
                if pd.isna(mean_val) or mean_val == 0:
                    return np.nan
                return clean_col.std() / mean_val
            
            # Add coef_var to the aggregation list
            stats_block = df_kin_filtered[stats_cols].agg(['mean', 'std', 'median', 'min', 'max', max_norm_mean, coef_var])
            
            # Formatting the index, preserving the exact wording for custom stats
            formatted_index = []
            for idx in stats_block.index:
                if idx == 'max_norm_mean':
                    formatted_index.append('Max_Normalized_Mean')
                elif idx == 'coef_var':
                    formatted_index.append('CV')
                else:
                    formatted_index.append(str(idx).title())
            stats_block.index = formatted_index
            
            stats_output = stats_block.reset_index()
            stats_output.columns = [df_kin_filtered.columns[0]] + list(stats_cols)

            row_data = [np.nan] * len(df_kin_filtered.columns)
            row_data[0] = 'Time Duration'
            if len(row_data) > 1:
                row_data[1] = time_duration
            duration_df = pd.DataFrame([row_data], columns=df_kin_filtered.columns)

            hw_row = [np.nan] * len(df_kin_filtered.columns)
            hw_row[0] = 'Height Window (start, end s)'
            if len(hw_row) > 2:
                hw_row[1], hw_row[2] = height_window
            height_window_df = pd.DataFrame([hw_row], columns=df_kin_filtered.columns)

            engine = 'xlsxwriter' if importlib.util.find_spec('xlsxwriter') else 'openpyxl'
            with pd.ExcelWriter(output_file, engine=engine) as writer:
                df_raw.to_excel(writer, sheet_name='Positions (used)', index=False)
                df_kin_filtered.to_excel(writer, sheet_name='Kinematics', index=False)
                start_row = len(df_kin_filtered) + 2
                duration_df.to_excel(writer, sheet_name='Kinematics', startrow=start_row, index=False, header=False)
                stats_output.to_excel(writer, sheet_name='Kinematics', startrow=start_row + 1, index=False, header=False)
                height_window_df.to_excel(writer, sheet_name='Kinematics', startrow=start_row + 1 + len(stats_output),
                                          index=False, header=False)

            for w in w_log:
                captured_warnings.append(f"{w.category.__name__}: {str(w.message)}")

        return (True, file_name, f"Processed file {index + 1} of {total_files}: {file_name} (" + "; ".join(info) + ")", captured_warnings, False)

    except Exception as e:
        error_msg = f"{e}\n{traceback.format_exc()}"
        return (False, file_name, error_msg, [], False)


# --- MAIN EXECUTION ---
def main():
    # Streamlined Folder Validation
    while True:
        folder_input = input('\nWhich folder has your .xlsx files? ').strip()
        folder_output = input('\nWhich folder you wish to place your filtered files (if empty it will be the same as the input folder)? ').strip()
        
        if not folder_output:
            folder_output = folder_input
            
        if os.path.isdir(folder_input) and os.path.isdir(folder_output):
            print(f'\nInput folder: {os.path.basename(os.path.normpath(folder_input))}          Output folder: {os.path.basename(os.path.normpath(folder_output))}')
            break
            
        print("\n[!] Invalid folder path. Check your input and output folder paths and please try again.")
        

    def get_valid_input(prompt, valid_options, error_msg):
        while True:
            val = input(prompt).strip().lower()
            if val in valid_options:
                return val
            print(f"[!] {error_msg}")

    print("\n0 - Tail Tip | 1 - Tail Center | 2 - Tail Base | 3 - Both Paws")
    choice = get_valid_input("Cutoff starts where (0-3)? ", ["0", "1", "2", "3"], "Choose 0, 1, 2, or 3.")
    animal_choice = get_valid_input("Animal species (0: Mus, 1: Acomys): ", ["0", "1"], "Choose 0 or 1.")
    experiment = get_valid_input("Experiment type: ", ["groundwalk", "gridwalk", "beamwalk", "swimming"], "Invalid experiment.")
    old_or_new = get_valid_input("Old or New settings? ", ["old", "new"], "Choose 'old' or 'new'.")
    height_cutoff = get_valid_input("Apply hind paw height cutoff? (yes/no): ", ["yes", "no"], "Choose 'yes' or 'no'.")
    floor_mode = get_valid_input("Floor reference - auto (measured per session) or fixed (old/new constants)? ",
                                 ["auto", "fixed"], "Choose 'auto' or 'fixed'.")
    default_swing = SWING_SPEED_BY_EXPERIMENT.get(experiment, SWING_SPEED_DEFAULT)
    while True:
        sw = input(f"Paw swing speed threshold in m/s (Enter = {default_swing} for {experiment}, 0 = keep stance frames): ").strip()
        try:
            swing_speed = float(sw) if sw else default_swing
            if swing_speed >= 0:
                break
        except ValueError:
            pass
        print("[!] Enter a number >= 0.")

    file_paths = [os.path.join(folder_input, f) for f in os.listdir(folder_input) 
                  if f.lower().endswith('.xlsx') and not f.startswith('~$') and not f.endswith('_filtered.xlsx')]
    
    if not file_paths:
        print("[!] No valid Excel files found to process.")
        return
        
    total_files = len(file_paths)
    indexed_files = [(i, f, total_files) for i, f in enumerate(file_paths)]

    # Dynamic CPU Allocation
    total_cores = os.cpu_count() or 4
    num_processes = total_cores - 4 if total_cores > 8 else total_cores
    num_processes = max(1, num_processes)
    
    # --- LOG FILE SETUP ---
    log_file_path = os.path.join(folder_output, "error_log.txt")
    print(f"\n[INFO] Checking {total_files} files using {num_processes} processes... Logging to: {log_file_path}")
    
    start_time = time.perf_counter()
    failed_files, files_with_warnings, skipped_files = [], [], []

    with open(log_file_path, 'w', encoding='utf-8') as log_file:
        log_file.write(f"--- Processing Started at {datetime.datetime.now()} ---\n")
        log_file.write(f"Parameters: Choice={choice}, Animal={animal_choice}, Exp={experiment}, Set={old_or_new}, Floor={floor_mode}, Swing={swing_speed} m/s\n")
        log_file.write("-" * 50 + "\n")

        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            futures = [executor.submit(filter_excel_by_column, item, choice, animal_choice, experiment, old_or_new, folder_output, height_cutoff, floor_mode, swing_speed) for item in indexed_files]
            
            for future in as_completed(futures):
                success, fname, message, warnings_list, is_skipped = future.result()
                
                if success:
                    if is_skipped:
                        print(message)
                        log_file.write(f"[SKIPPED] {fname}\n")
                        skipped_files.append(fname)
                    elif warnings_list:
                        print(f"[WARN] {fname}: Processed with warnings.")
                        log_file.write(f"[WARNING] {fname}\n")
                        for w in warnings_list:
                            log_file.write(f"    - {w}\n")
                        files_with_warnings.append(fname)
                    else:
                        print(message)
                        log_file.write(f"[SUCCESS] {fname}\n")
                else:
                    error_short = message.split('\n')[0]
                    print(f"[ERROR] File '{fname}': {error_short}")
                    log_file.write(f"\n[ERROR] File: {fname}\n{message}\n{'-'*30}\n")
                    failed_files.append((fname, error_short))

        # --- FINAL SUMMARY ---
        duration = round(time.perf_counter() - start_time, 2)
        end_msg = f"\n[DONE] Finished in {duration} seconds.\n"
        
        summary_msg = f"\nTotal Files Checked: {total_files}\n"
        summary_msg += f"Processed Successfully: {total_files - len(skipped_files) - len(failed_files)}\n"
        summary_msg += f"Skipped (Already Existed): {len(skipped_files)}\n"

        if failed_files:
            summary_msg += f"\n[FAIL] {len(failed_files)} files FAILED:\n" + "".join([f"   - {f}: {err}\n" for f, err in failed_files])
        
        if files_with_warnings:
             summary_msg += f"\n[WARN] {len(files_with_warnings)} files had WARNINGS (check log):\n" + "".join([f"   - {f}\n" for f in files_with_warnings])

        if not failed_files and not files_with_warnings:
            summary_msg += "\n[OK] Processing completed without errors or warnings.\n"
        
        summary_msg += f"\nFull details saved to: '{os.path.basename(log_file_path)}'\n"

        print(end_msg + summary_msg)
        log_file.write(end_msg + summary_msg)

if __name__ == '__main__':
    try:
        print("Ctrl+C to terminate function at anytime.")
        main()
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")