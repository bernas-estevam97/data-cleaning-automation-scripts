import os
import time
import sys
import traceback
import datetime
import warnings
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed

# --- GLOBALS (Moved outside worker to save initialization time) ---
CHOICE_MAP = {
    "0": '/Feature/Tail/Tip_X',
    "1": '/Feature/Tail/Center_X',
    "2": '/Feature/Tail/Base_X',
    "3": ['/Feature/Paw/Hind/Left_X', '/Feature/Paw/Hind/Right_X']
}

SUBTRACTION_MAP = {
    ("0", "groundwalk", "old"): 0.522, #updated from ---> 0.524
    ("1", "groundwalk", "old"): 0.525,
    ("0", "groundwalk", "new"): 0.502,
    ("1", "groundwalk", "new"): 0.519,
    ("0", "beamwalk", "old"): 0.445, #updated from ---> 0.44
    ("1", "beamwalk", "old"): 0.445,
    ("0", "beamwalk", "new"): 0.43,
    ("1", "beamwalk", "new"): 0.44,
    ("0", "gridwalk", "old"): 0.496, #updated from ---> 0.507
    ("0", "gridwalk", "new"): 0.483, #update from ---> 0.486
    ("1", "gridwalk", "old"): 0.504,
    ("1", "gridwalk", "new"): 0.498,
    ("0", "swimming", "old"): 0.566, #value takes offset into account
    ("0", "swimming", "new"): 0.568, #value takes offset into account
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

# --- WORKER FUNCTION ---
def filter_excel_by_column(file_info_tuple, choice, animal_choice, experiment, old_or_new, output_folder):
    index, file_path, total_files = file_info_tuple
    file_name = os.path.basename(file_path)
    captured_warnings = []

    column_targets = CHOICE_MAP.get(choice)
    if not column_targets:
         return (False, file_name, f"[ERROR] Invalid choice '{choice}'.", [], False)

    # --- 1. Determine Output Path and Check if it Exists ---
    if output_folder == '':
        output_file = os.path.splitext(file_path)[0] + '_filtered.xlsx'
    else:
        output_file = os.path.join(output_folder, os.path.splitext(file_name)[0] + '_filtered.xlsx')

    if os.path.exists(output_file):
        # Return early without reading data to save time. Added a 5th tuple item 'True' for 'is_skipped'
        return (True, file_name, f"Skipped file {index + 1} of {total_files}: {file_name} (Already exists)", [], True)

    try:
        with warnings.catch_warnings(record=True) as w_log:
            warnings.simplefilter("always") 
            
            # OPTIMIZATION: Use calamine for vastly faster reads
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

            # 3. Filter Kinematics
            df_kin_filtered = df_kin_clean.iloc[start_index : last_index + 1].copy()

            # 4. Apply Subtraction & Inversion
            if experiment == "gridwalk":
                target_indices = [5, 6, 9, 11, 13, 21, 23]
            else:
                target_indices = [5, 6, 9, 11, 13, 17]

            #target_indices = [5, 6, 9, 11, 13, 17]

            # --- NEW DYNAMIC INDEX LOGIC ---
            # Check Nose Height (index 15) and Tail Tip Height (index 16) GRIDWALK HAS DIFFERENT INDEXES FOR NOSE HEIGHT AND TAIL HEIGHT
            if experiment == "gridwalk":
                if df_kin_filtered.iloc[:, 15].mean() > 0.3:
                    target_indices.append(15)
                if df_kin_filtered.iloc[:, 19].mean() > 0.3:
                    target_indices.append(19)
                if df_kin_filtered.iloc[:, 20].mean() > 0.3:
                    target_indices.append(20)
            else:
                if df_kin_filtered.iloc[:, 15].mean() > 0.3:
                    target_indices.append(15)
                if df_kin_filtered.iloc[:, 16].mean() > 0.3:
                    target_indices.append(16)
            # -------------------------------
            
            target_indices_offset = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
            current_combo = (animal_choice, experiment, old_or_new)
            
            value_to_subtract = SUBTRACTION_MAP.get(current_combo)
            value_to_add_offset = OFFSET_MAP.get(current_combo)

            if value_to_add_offset is not None:
                df_kin_filtered.iloc[:, target_indices_offset] += value_to_add_offset

            if value_to_subtract is not None:
                df_kin_filtered.iloc[:, target_indices] = value_to_subtract - df_kin_filtered.iloc[:, target_indices]

            # OPTIMIZATION: Numpy masking is faster than .replace()
            cols_to_replace_zero = df_kin_filtered.columns[26:50]
            # Replace 0 with np.nan (faster math, still exports as empty cell in Excel)
            for col in cols_to_replace_zero:
                df_kin_filtered[col] = np.where(df_kin_filtered[col] == 0, np.nan, df_kin_filtered[col])

            # 5. Hind Paw Timestamp Logic
            setup_info = CHOICE_MAP.get(old_or_new)
            hind_paw_col = '/Feature/Paw/Tao/Hind/Left_X'
            if setup_info == "new":
                if hind_paw_col in df_raw.columns and 'Time' in df_raw.columns:
                    hind_reach = df_raw[df_raw[hind_paw_col] >= 0]
                    if not hind_reach.empty:
                        hind_timestamp = df_raw.loc[hind_reach.index[0], "Time"]
                        cols_F_to_S = df_kin_filtered.columns[5:19]
                        mask_time = df_kin_filtered['Time'] > hind_timestamp
                        df_kin_filtered.loc[mask_time, cols_F_to_S] = np.nan
            else:
                if hind_paw_col in df_raw.columns and 'Time' in df_raw.columns:
                    hind_reach = df_raw[df_raw[hind_paw_col] >= -0.016]
                    if not hind_reach.empty:
                        hind_timestamp = df_raw.loc[hind_reach.index[0], "Time"]
                        cols_F_to_S = df_kin_filtered.columns[5:19]
                        mask_time = df_kin_filtered['Time'] > hind_timestamp
                        df_kin_filtered.loc[mask_time, cols_F_to_S] = np.nan

            # 6. Statistics and Saving
            time_series = df_kin_filtered['Time'].dropna()
            time_duration = (time_series.iloc[-1] - time_series.iloc[0]) if not time_series.empty else 0
            numeric_cols = df_kin_filtered.columns[1:] 
            
            stats_block = df_kin_filtered[numeric_cols].agg(['mean', 'std', 'median', 'min', 'max'])
            stats_block.index = stats_block.index.str.title()
            stats_output = stats_block.reset_index()
            stats_output.columns = [df_kin_filtered.columns[0]] + list(numeric_cols)

            row_data = [np.nan] * len(df_kin_filtered.columns)
            # Insert our string and numeric values
            row_data[0] = 'Time Duration'
            row_data[1] = time_duration
            # Convert directly to DataFrame
            duration_df = pd.DataFrame([row_data], columns=df_kin_filtered.columns)

            # OPTIMIZATION: Use xlsxwriter for much faster creation of new files
            with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
                df_raw.to_excel(writer, sheet_name='Positions (used)', index=False)
                df_kin_filtered.to_excel(writer, sheet_name='Kinematics', index=False)
                start_row = len(df_kin_filtered) + 2
                duration_df.to_excel(writer, sheet_name='Kinematics', startrow=start_row, index=False, header=False)
                stats_output.to_excel(writer, sheet_name='Kinematics', startrow=start_row + 1, index=False, header=False)

            for w in w_log:
                captured_warnings.append(f"{w.category.__name__}: {str(w.message)}")

        # Return Success (is_skipped = False)
        return (True, file_name, f"Processed file {index + 1} of {total_files}: {file_name}", captured_warnings, False)

    except Exception as e:
        error_msg = f"{e}\n{traceback.format_exc()}"
        # Return Failure (is_skipped = False)
        return (False, file_name, error_msg, [], False)


# --- MAIN EXECUTION ---
def main():
    while True:
        folder_input = input('\nWhich folder has your .xlsx files? ').strip()
        folder_output = input('\nWhich folder you wish to place your filtered files (if empty it will be the same as the input folder)? ').strip()
        if os.path.isdir(folder_input) and folder_output=='':
            print(f'\nInput folder: {os.path.basename(os.path.normpath(folder_input))}          Output folder: {os.path.basename(os.path.normpath(folder_input))}')
            break
        elif os.path.isdir(folder_input) and os.path.isdir(folder_output):
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

    # Added check to ignore files that end in _filtered.xlsx
    file_paths = [os.path.join(folder_input, f) for f in os.listdir(folder_input) 
                  if f.lower().endswith('.xlsx') and not f.startswith('~$') and not f.endswith('_filtered.xlsx')]
    
    if not file_paths:
        print("[!] No valid Excel files found to process.")
        return
    total_files = len(file_paths)
    indexed_files = [(i, f, total_files) for i, f in enumerate(file_paths)]

    # ------------------------ CPU MULTIPROCESSING OPTIONS ------------------------#

    # Use a "capped" approach:
    # 1. Get total count (defaulting to 4 if None)
    # 2. Try to subtract 4, but don't let it go below 1.
    # 3. Ensure we never exceed the actual physical core count.
    #total_cores = os.cpu_count() or 4
    #num_processes = max(1, min(total_cores, total_cores - 4))

    #The "Power User" Logic:
    total_cores = os.cpu_count() or 4
    # If we have lots of cores, reserve some; if we have few, use them all.
    num_processes = total_cores - 4 if total_cores > 8 else total_cores
    # Ensure we never try to run 0 or negative processes
    num_processes = max(1, num_processes)


    
    # --- LOG FILE SETUP ---
    log_file_path = os.path.join(folder_input if folder_output == "" else folder_output, "error_log.txt")
    print(f"\n[INFO] Checking {total_files} files... Logging to: {log_file_path}")
    
    start_time = time.perf_counter()
    
    failed_files = []
    files_with_warnings = []
    skipped_files = []

    # Open log file with UTF-8
    with open(log_file_path, 'w', encoding='utf-8') as log_file:
        log_file.write(f"--- Processing Started at {datetime.datetime.now()} ---\n")
        log_file.write(f"Parameters: Choice={choice}, Animal={animal_choice}, Exp={experiment}, Set={old_or_new}\n")
        log_file.write("-" * 50 + "\n")

        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            futures = [executor.submit(filter_excel_by_column, item, choice, animal_choice, experiment, old_or_new, folder_output) for item in indexed_files]
            
            for future in as_completed(futures):
                # Unpack the 5 items now
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
                        # Clean success
                        print(message)
                        log_file.write(f"[SUCCESS] {fname}\n")
                else:
                    # Error
                    error_short = message.split('\n')[0]
                    console_msg = f"[ERROR] File '{fname}': {error_short}"
                    print(console_msg)
                    
                    log_file.write(f"\n[ERROR] File: {fname}\n{message}\n{'-'*30}\n")
                    failed_files.append((fname, error_short))

        # --- FINAL SUMMARY ---
        duration = round(time.perf_counter() - start_time, 2)
        end_msg = f"\n[DONE] Finished in {duration} seconds.\n"
        
        summary_msg = ""
        
        processed_count = total_files - len(skipped_files) - len(failed_files)
        summary_msg += f"\nTotal Files Checked: {total_files}\n"
        summary_msg += f"Processed Successfully: {processed_count}\n"
        summary_msg += f"Skipped (Already Existed): {len(skipped_files)}\n"

        if failed_files:
            summary_msg += f"\n[FAIL] {len(failed_files)} files FAILED:\n"
            for f, err in failed_files:
                summary_msg += f"   - {f}: {err}\n"
        
        if files_with_warnings:
             summary_msg += f"\n[WARN] {len(files_with_warnings)} files had WARNINGS (check log):\n"
             for f in files_with_warnings:
                 summary_msg += f"   - {f}\n"

        if not failed_files and not files_with_warnings:
            summary_msg += "\n[OK] Processing completed without errors or warnings.\n"
        
        summary_msg += f"\nFull details saved to: '{os.path.basename(log_file_path)}'\n"

        print(end_msg)
        print(summary_msg)
        
        log_file.write(end_msg)
        log_file.write(summary_msg)

if __name__ == '__main__':
    try:
        print("Ctrl+C to terminate function at anytime.")
        main()
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")