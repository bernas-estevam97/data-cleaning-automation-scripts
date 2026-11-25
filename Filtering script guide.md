# Gait Kinematics Filtering: User Guide

## About this guide

This guide describes the filtering algorithm applied to gait tracking data: what each step does, why it is needed, and how to interpret the results.

**In short:** the filtering algorithm takes each tracked session (`*_out_processed.xlsx`), keeps only the part of the video where the mouse is fully visible and walking, removes positions that the tracking software got wrong, recalculates every measurement from the cleaned positions, and saves the results with summary statistics in a new file (`*_filtered.xlsx`). Anything unusual is noted in a log file (see "Understanding the log file").

---

## Before you start: choosing the settings

When the filtering algorithm starts, it asks for a few settings. **Use the same settings for every file you plan to compare**, because several results (for example, the trial duration) depend on them.

| Setting | What it means | Recommended |
|---|---|---|
| Starting point | The body part whose appearance marks the start of the trial: tail tip, tail center, tail base or both hind paws | Tail tip |
| Species | Mouse (*Mus*) or spiny mouse (*Acomys*). Also sets species-specific limits (Steps 4 and 8) | As applicable |
| Test | Groundwalk (footprint), gridwalk, beam walk or swimming | As applicable |
| Old or new settings | Which version of the recording setup was used | As applicable |
| Height cutoff | Whether height measurements stop once the hind paw passes the middle of the walkway | Yes |
| Floor reference | How the floor level is found: measured in each session (*auto*) or a fixed value (*fixed*) | Auto |
| Swing speed threshold | Paw speed above which the paw counts as moving (in the air) | Default for the selected test |
| Keep positions sheet | Whether the raw positions are copied into the output file | Your choice |

---

## Step by step: what the filtering algorithm does

### Step 1: Find when the trial starts

**What happens:** the trial starts at the moment the chosen starting point (by default the tail tip) first appears in the video. A body part counts as having appeared once it has moved at least 5 mm from its initial position.

**Why:** the videos are not all cut at the same moment. They usually begin when about half of the tail is visible. Because the tail tip is the last body part to come into view, its appearance is the first moment when the whole mouse is visible and tracked. Before that, the tracking software reports a fixed placeholder position for the tail tip, so the moment that position starts changing is the moment the tail tip appears.

The 5 mm margin matters when a recording starts before the animal has entered the walkway, as in the *Acomys* recordings. The placeholder position can then drift by about 1 mm before the animal enters, and this small drift must not be mistaken for the tail tip appearing.

> **Keep the starting point the same for all files.** An earlier starting point (for example, tail center) gives longer trial durations than the tail tip.

### Step 2: Find when the trial ends

**What happens:** the trial ends at the moment the mouse's nose leaves the camera's field of view. This is detected as the first moment the nose reaches its exit position, or the moment the tracking software stops following it near the exit, whichever happens first.

**Why:** after the nose has left the frame, the tracking software often continues to report estimated positions for it. If these were treated as real, the trial would appear longer than it was and every measurement would include invalid data. This occurred in approximately one in five footprint and gridwalk sessions and in most beam walk sessions, adding up to 4 seconds of invalid data per session.

During this period, the tracked positions describe physically impossible behaviour: the body appears to shrink to a few millimetres long, its nose moves at over 6 m/s, and its nose ends up behind its hind paws. Left in the data, these positions produce paw accelerations of up to 300 m/s², far beyond what a mouse can achieve.

**Notes:**

- On the beam, the nose is often briefly lost *in the middle* of the crossing (for example, when the beam hides it). These short losses do **not** end the trial; only losses close to the exit do.
- Occasionally, the nose position jumps on the very last frames of a recording, after the nose has already stopped at the exit. Such a glitch is ignored, so it cannot shift the end of the trial.

### Step 3: Remove "frozen" positions

**What happens:** whenever a body part's position stays *exactly* the same from one video frame to the next, that frame is treated as missing for that body part.

**Why:** when the tracking software loses sight of a body part, it does not leave a gap. Instead, it keeps repeating the last position it saw. These repeated values look like real data but are not. In one representative session, the paws "froze" one by one in the last half second of the trial. As a result, step width and step length repeated the same value for up to 50 frames, which distorted the averages and especially the variability (CV) of those measurements.

A real body part, even a paw resting on the floor, always moves very slightly between frames. An exactly repeated position is therefore a reliable sign of lost tracking.

### Step 4: Remove physically impossible positions

**What happens:** each video frame is checked against what a walking mouse can physically do. A frame is removed if:

- the nose is behind one of the hind paws;
- a hind paw is more than 1 cm ahead of the front paw on the same side; or
- the distance from nose to tail base is much shorter or longer than usual for that mouse (below 70% or above 130% of its typical body length).

In addition, two checks are applied to individual body parts:

- **Jumps:** if a body part moves more than 3 cm between two consecutive frames (one hundredth of a second), that position is removed. For *Acomys* the limit is 4 cm, because their real, fast steps reach about 3.1 cm per frame.
- **Jitter spikes:** if a body part jumps more than 8 mm away from its path and returns on the very next frame, that single position is removed. The tail is excluded from this check, because it can genuinely whip this fast.

**Why:** besides freezing, the tracking software sometimes swaps labels (for example, it confuses a front paw with a hind paw) or jumps a marker onto the wrong body part. These errors produce impossible body shapes and movements. When a frame fails a body check, the whole frame is removed, because it is impossible to know which body part was mislabelled.

Jitter spikes are common on the beam, where the paws are partly hidden: a paw marker briefly jumps 1–2 cm off and straight back. A single spike of this kind produces an acceleration above 100 m/s², which no mouse paw reaches.

**How the limits were chosen:** in footprint sessions, which are the most reliably tracked, normal walking never came close to failing these checks. Body length stayed between 80% and 122% of normal, the hind paws were never ahead of the front paws, no paw moved more than 2.5 cm between frames, and no paw showed a jitter spike above 6 mm. The tracking errors, by contrast, produced body lengths as short as 1% of normal, jumps of up to 6.5 cm and spikes of up to 2 cm.

> **Warning in the log: "CHECK THIS VIDEO".** This warning appears when the nose is probably tracked incorrectly throughout the session, which is detected in two ways: more than 20% of the trial fails the body checks, or the nose ends the recording behind the point where it started while the paws move forward. Since the nose also determines the end of the trial, that session's results are not reliable. Re-track the video or exclude the session.

### Step 5: Recalculate all measurements from the cleaned positions

**What happens:** every measurement (heights, step width and length, joint angles, paw speeds and accelerations) is recalculated from the cleaned positions from Steps 3 and 4. The values in the original *Kinematics* sheet are not used.

**Why:** the program that created the original *Kinematics* sheet applied an automatic "outlier" correction to every measurement. Because a paw spends most of its time resting on the floor, that correction treated every fast paw movement as an error and smoothed it away. As a result, paw speeds in the original sheet are about **10 times too low**, and the highest points of toe clearance and step length are cut off. Recalculating from the positions, which were never affected by that correction, restores the real values.

**Things to know:**

- Nose height and tail tip height are always measured from the left-side camera, so every session measures them the same way (the original files were inconsistent).
- If a measurement cannot be recalculated, it is copied from the original sheet and the log says so ("Kept from Kinematics sheet"). Treat those columns with caution, because they have not been cleaned.

### Step 6: Limit height measurements to the first half of the walkway

**What happens:** if the height cutoff is switched on, height, toe clearance and paw drag measurements are kept only until the left hind toe reaches the middle of the walkway.

**Why:** height measurements are considered reliable only in that part of the walkway.

**Special case:** occasionally, the hind paw passes the middle of the walkway *before* the tail tip comes into view (Step 1). No part of the trial would then be left for height measurements. In that case, heights are measured from the moment the hind paws start moving until they reach the middle. All other measurements and the trial duration are unaffected. The log reports this, and the output file shows exactly which time range the heights came from (see "Height Window" in Step 10).

> **For your methods section:** "When the hind paw reached the height cutoff before the tail tip came into view (n = X sessions), heights were measured from the start of hind paw movement up to the cutoff; all other measurements used the standard trial window." Count X from the log.

### Step 7: Measure heights relative to the floor

**What happens:** heights are converted into distances above the floor.

**Why:** the cameras record positions in their own coordinates, not relative to the floor, and one side camera records the image upside down. To express heights as "how high above the floor", the floor level must be known.

- **Auto (recommended):** the floor level is measured in each session, from the hind toe at the moments it rests on the ground. This automatically corrects for small differences in camera position between sessions.
- **Fixed:** a predefined floor value is used for each species, test and setup.

### Step 8: Keep paw speed and acceleration only while the paw is moving

**What happens:** for each paw, speed and acceleration values are kept only while that paw is in the air (moving faster than the swing speed threshold). Values recorded while the paw rests on the ground are left empty.

**Why:** the paw speed and acceleration results are meant to describe the step itself. A paw on the ground only shows tiny tracking noise, which would pull the averages down.

| Test | Default threshold | Reason |
|---|---|---|
| Groundwalk and gridwalk | 0.1 m/s | Resting paws (about 0.02 m/s) and moving paws (about 0.5–0.6 m/s) are clearly separated; 0.1 m/s sits between them |
| Beam walk | 0.03 m/s | Paws grip and slide slowly on the beam, so only tracking noise is removed |

These defaults currently apply to both species. The *Acomys* values are provisional: resting *Acomys* paws show more tracking noise and their steps are faster, so a slightly higher threshold may suit them better once more *Acomys* sessions have been tested.

> **This is the main reason the speed and acceleration columns contain gaps.** Roughly half of every paw's frames are resting frames, so this is expected.

### Step 9: Add quality-control measures

**What happens:** three quality indicators are added to each session's results:

| Indicator | What it shows | Good value |
|---|---|---|
| Tracked Frames (%) | Share of the trial in which all four paws were tracked correctly | Close to 100 |
| Hind Ahead of Front (%) | Share of the trial in which a hind paw appeared ahead of a front paw (a sign of label swaps) | Close to 0 |
| Step Length SD | Variability of step length; a value near zero suggests the front and hind paw markers were assigned to the same paw | Clearly above 0 |

If all four paws are tracked in less than 70% of the trial, the log shows a **"Low tracking"** message. The session is still processed, but its paw-based results rest on fewer frames than usual. This mainly occurs on the beam, where the beam itself hides the paws.

### Step 10: Calculate summary statistics and save the results

**What happens:** the filtering algorithm creates a new file, `*_filtered.xlsx`, containing:

- **Positions (used):** the original tracked positions, unchanged (optional).
- **Kinematics:** the frame-by-frame measurements, followed by:
  1. **Time Duration:** the length of the trial, from Step 1 to Step 2.
  2. **Summary statistics** for each measurement: Mean, Std, Median, Min, Max, Max_Normalized_Mean and CV (coefficient of variation).
  3. **Height Window:** the start and end time of the period used for height measurements.

Empty cells are ignored in the statistics, so each measurement is summarised using only its valid values.

---

## Understanding the log file

Each run creates its own log file in the output folder, named after the input folder and the date and time of the run, for example `error_log_Beam_2026-11-25_14-03-12.txt`. Processing several batches into the same output folder therefore keeps a separate log for each batch; no log is ever overwritten. The top of each log records the input folder, the output folder and the settings used.

The log lists every session and any messages about it. A session marked **WARNING** has still been processed; the message explains what was removed or changed.

| Message | What it means | What to do |
|---|---|---|
| Nose left the frame or stopped being tracked at… | False tracking after the nose left was removed (Step 2) | No action required. For very large cuts, the video can be reviewed to confirm. |
| Start marker appeared … after the height cutoff | Heights were measured with the special rule in Step 6 | Count these sessions for your methods section |
| Placeholder (frozen) positions removed… | Frozen positions were removed (Step 3) | No action required |
| Implausible positions removed… | Impossible positions, jumps or jitter spikes were removed (Step 4) | No action required, unless a large part of the trial is affected |
| **CHECK THIS VIDEO** | The nose tracking is unreliable in this session (Step 4) | Re-track the video or exclude the session |
| Low tracking… | All four paws were tracked in less than 70% of the trial (Step 9) | Interpret paw-based results with care; consider reviewing the video |
| Floor not estimated… | Heights could not be converted to height above the floor (Step 7) | Read the reason given and check the hind toe tracking |
| No fixed floor constant… | No predefined floor value exists for this combination of settings | Use the *auto* floor reference |
| Kept from Kinematics sheet… | Some measurements were copied without cleaning (Step 5) | Use those measurements with caution |
| …no data in… | A measurement was empty in the original file | No action required |
| Mean of empty slice | A measurement had no valid values in this trial | Usually explained by one of the messages above |

---

## Testing and validation

The filtering algorithm was tested on 805 sessions: 114 footprint, 349 gridwalk and 342 beam walk. All sessions were processed with the tail tip as starting point, new settings, height cutoff on, automatic floor reference and the default swing speed threshold.

| | Footprint | Gridwalk | Beam walk |
|---|---|---|---|
| Sessions processed | 114 | 349 | 342 |
| Sessions that failed to process | 0 | 0 | 0 |
| Sessions where false tracking was removed at the end | 21 | 90 | 264 |
| Sessions with frames removed by the body checks | 0 | 14 | 290 (median 1.4% of the trial) |
| Sessions with jitter spikes removed | 25 | 84 | 320 |
| Highest paw acceleration (m/s²) | 84 | 163 | 175 |
| Sessions flagged "CHECK THIS VIDEO" | 0 | 2 | 1 |
| Sessions with "Low tracking" | 0 | 0 | 21 |
| Typical trial duration (s) | 1.5 | 1.8 | 4.1 |

Without the filtering, paw accelerations of up to 300 m/s² appeared in the results, far beyond what a mouse can achieve.

---

## Limitations

- **The limits were set using this dataset.** They assume the same recording setup (100 frames per second, the same camera position, and animals walking in the same direction). If the setup changes, the limits should be checked again. *Acomys* settings are based on only 9 groundwalk sessions so far and will be reviewed as more data becomes available.
- **Beam and gridwalk tracking is less steady.** Even after jitter spikes are removed, a small number of unrealistically high acceleration values (100–175 m/s²) remain: about 220 frames across 105 of the 342 beam sessions, and about 20 frames across 14 gridwalk sessions. Averages and medians are hardly affected, but the **Max** values are. For these tests, report the mean or median acceleration rather than the maximum.
- **Removing a whole frame is conservative by design.** When a frame fails a body check, correctly tracked body parts in that frame are removed too.
- **The nose determines the end of the trial.** If the nose is poorly tracked, the end may be wrong. The "CHECK THIS VIDEO" warning exists for this, but only the video can confirm it.

---

## Checklist for each processing run

1. Choose the settings and use **the same settings for every file** you will compare.
2. Remove any existing `*_filtered.xlsx` files from the output folder if you want those sessions processed again. The filtering algorithm skips any session that already has a filtered file.
3. Run the filtering algorithm.
4. Open the log file of the run (`error_log_<input folder>_<date and time>.txt`) and:
   - re-track or exclude any session flagged **CHECK THIS VIDEO**;
   - count the sessions that used the special height rule (Step 6) for your methods section;
   - look at any session with a low **Tracked Frames (%)**.
5. Review a sample of flagged videos to confirm that the removed data matches what is visible in the recording.

---

## Appendix: adjustable limits (for the person maintaining the filtering algorithm)

These values are set at the beginning of the filtering algorithm's code. Change them only if the recording setup changes or a check proves too strict or too lenient.

| Setting name | Default | Used in |
|---|---|---|
| `START_MOVE_TOL` | 0.005 m | Step 1 (how far the starting point must move to count as appearing) |
| `SWING_SPEED_BY_SPECIES` | 0.1 m/s (groundwalk, gridwalk); 0.03 m/s (beam), for both species (*Acomys* provisional) | Step 8 |
| `FLOOR_PCT` | 10 | Step 7 (how the resting toe position is chosen) |
| `FROZEN_MIN_REPEATS` | 1 | Step 3 |
| `NOSE_EXIT_TOL` | 0.001 m | Step 2 (how close to the exit counts as "reached") |
| `NOSE_HOLD_FRAMES` | 5 frames | Step 2 (how long the nose must be lost) |
| `NOSE_EXIT_ZONE` | 0.02 m | Step 2 (how close to the exit a loss must be) |
| `MAX_JUMP_BY_SPECIES` | 0.03 m per frame (*Mus*); 0.04 m per frame (*Acomys*) | Step 4 (assumes 100 frames per second) |
| `HIND_AHEAD_TOL` | 0.01 m | Step 4 |
| `BODY_LENGTH_RANGE` | 70–130% | Step 4 |
| `MAX_BAD_FRACTION` | 20% | Step 4 ("CHECK THIS VIDEO" warning) |
| `SPIKE_MAX_M` | 0.008 m | Step 4 (jitter spikes) |
| `MIN_TRACKED_PCT` | 70% | Step 9 ("Low tracking" message) |