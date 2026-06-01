import os
import pandas as pd
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
import sys
import traceback
import datetime
import warnings

# --- WORKER FUNCTION ---
def filter_excel_by_column(file_info_tuple, choice, animal_choice, experiment, old_or_new):
    index, file_path, total_files = file_info_tuple
    file_name = os.path.basename(file_path)
    
    # Initialize a list to hold any warnings that pop up
    captured_warnings = []

    choice_map = {
        "0": '/Feature/Tail/Tip_X',
        "1": '/Feature/Tail/Center_X',
        "2": '/Feature/Tail/Base_X',
        "3": ['/Feature/Paw/Hind/Left_X', '/Feature/Paw/Hind/Right_X']
    }
    
    subtraction_map = {
        ("0", "groundwalk", "old"): 0.524,
        ("1", "groundwalk", "old"): 0.524,
        ("0", "groundwalk", "new"): 0.502,
        ("0", "beamwalk", "old"): 0.44,
        ("1", "beamwalk", "old"): 0.444,
        ("0", "beamwalk", "new"): 0.43,
        ("0", "gridwalk", "old"): 0.507,
        ("0", "gridwalk", "new"): 0.486,
        ("1", "gridwalk", "old"): 0.504,
        ("0", "swimming", "old"): 0.567
    }

    offset_map = {
        ("0", "groundwalk", "old"): 0,
        ("1", "groundwalk", "old"): 0,
        ("0", "groundwalk", "new"): 0,
        ("0", "beamwalk", "old"): 0,
        ("1", "beamwalk", "old"): 0,
        ("0", "beamwalk", "new"): 0,
        ("0", "gridwalk", "old"): 0,
        ("0", "gridwalk", "new"): 0,
        ("1", "gridwalk", "old"): 0,
        ("0", "swimming", "old"): 0
    }

    column_targets = choice_map.get(choice)
    if not column_targets:
         # Return: (Success, FileName, Message, WarningsList)
         return (False, file_name, f"[ERROR] Invalid choice '{choice}'.", [])

    try:
        # Context manager to catch RuntimeWarnings (like 'Mean of empty slice')
        with warnings.catch_warnings(record=True) as w_log:
            warnings.simplefilter("always") # Cause all warnings to be caught
            
            with pd.ExcelFile(file_path) as xls:
                df_raw = pd.read_excel(xls, sheet_name='Positions (used)')
                df_kin = pd.read_excel(xls, sheet_name='Kinematics')

            # --- 1. Find Start/End Indices with Static-Value Skipping ---
            threshold = 0.00001
            
            df_raw_clean = df_raw.dropna(how='all').reset_index(drop=True)
            df_kin_clean = df_kin.dropna(how='all').reset_index(drop=True)

            if isinstance(column_targets, list):
                first_vals = df_raw_clean[column_targets].iloc[0]
                change_mask = ((df_raw_clean[column_targets] - first_vals).abs() > threshold).any(axis=1)
                movement_indices = df_raw_clean.index[change_mask]
                start_index = movement_indices[0] if not movement_indices.empty else 0
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

            # 2. Filter Kinematics
            df_kin_filtered = df_kin_clean.iloc[start_index : last_index + 1].copy()

            # 3. Apply Subtraction & Inversion
            target_indices = [5, 6, 9, 11, 13, 15, 16, 17]
            target_indices_offset = [5,6,7,8,9,10,11,12,13,14,15,16,17,18]
            current_combo = (animal_choice, experiment, old_or_new)
            
            value_to_subtract = subtraction_map.get(current_combo)
            value_to_subtract_offset = offset_map.get(current_combo)

            if value_to_subtract_offset is not None:
                df_kin_filtered.iloc[:, target_indices_offset] = df_kin_filtered.iloc[:, target_indices_offset] - value_to_subtract_offset

            if value_to_subtract is not None:
                df_kin_filtered.iloc[:, target_indices] = value_to_subtract - df_kin_filtered.iloc[:, target_indices]

            cols_to_replace_zero = df_kin_filtered.columns[26:50]
            df_kin_filtered[cols_to_replace_zero] = df_kin_filtered[cols_to_replace_zero].replace(0, pd.NA)

            # 4. Hind Paw Timestamp Logic
            hind_paw_col = '/Feature/Paw/Tao/Hind/Left_X'
            if hind_paw_col in df_raw.columns and 'Time' in df_raw.columns:
                hind_reach = df_raw[df_raw[hind_paw_col] >= -0.016]
                if not hind_reach.empty:
                    hind_timestamp = df_raw.loc[hind_reach.index[0], "Time"]
                    cols_F_to_S = df_kin_filtered.columns[5:19]
                    mask_time = df_kin_filtered['Time'] > hind_timestamp
                    df_kin_filtered.loc[mask_time, cols_F_to_S] = pd.NA

            # 5. Statistics and Saving
            time_series = df_kin_filtered['Time'].dropna()
            time_duration = (time_series.iloc[-1] - time_series.iloc[0]) if not time_series.empty else 0
            numeric_cols = df_kin_filtered.columns[1:] 
            
            # This line typically causes "Mean of empty slice" if data is missing
            stats_block = df_kin_filtered[numeric_cols].agg(['mean', 'std', 'median', 'min', 'max'])
            
            stats_block.index = stats_block.index.str.title()
            stats_output = stats_block.reset_index()
            stats_output.columns = [df_kin_filtered.columns[0]] + list(numeric_cols)

            duration_df = pd.DataFrame([[pd.NA] * len(df_kin_filtered.columns)], columns=df_kin_filtered.columns)
            duration_df.iloc[0, 0] = 'Time Duration'
            duration_df.iloc[0, 1] = time_duration

            output_file = os.path.splitext(file_path)[0] + '_filtered.xlsx'
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df_raw.to_excel(writer, sheet_name='Positions (used)', index=False)
                df_kin_filtered.to_excel(writer, sheet_name='Kinematics', index=False)
                start_row = len(df_kin_filtered) + 2
                duration_df.to_excel(writer, sheet_name='Kinematics', startrow=start_row, index=False, header=False)
                stats_output.to_excel(writer, sheet_name='Kinematics', startrow=start_row + 1, index=False, header=False)

            # EXTRACT WARNINGS FROM CONTEXT MANAGER
            for w in w_log:
                captured_warnings.append(f"{w.category.__name__}: {str(w.message)}")

        # Return Success + Warnings
        return (True, file_name, f"Processed file {index + 1} of {total_files}: {file_name}", captured_warnings)

    except Exception as e:
        error_msg = f"{e}\n{traceback.format_exc()}"
        return (False, file_name, error_msg, [])

# --- MAIN EXECUTION ---
def main():
    while True:
        folder_input = input('\nWhich folder has your .xlsx files? ').strip()
        if os.path.isdir(folder_input):
            break
        print("[!] Invalid folder path. Please try again.")

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

    file_paths = [os.path.join(folder_input, f) for f in os.listdir(folder_input) if f.lower().endswith('.xlsx') and not f.startswith('~$')]
    
    if not file_paths:
        print("[!] No Excel files found.")
        return

    total_files = len(file_paths)
    indexed_files = [(i, f, total_files) for i, f in enumerate(file_paths)]
    num_processes = os.cpu_count() or 4
    
    # --- LOG FILE SETUP ---
    log_file_path = os.path.join(folder_input, "error_log.txt")
    print(f"\n[INFO] Processing {total_files} files... Logging to: {log_file_path}")
    
    start_time = time.perf_counter()
    
    failed_files = []
    files_with_warnings = []

    # Open log file with UTF-8
    with open(log_file_path, 'w', encoding='utf-8') as log_file:
        log_file.write(f"--- Processing Started at {datetime.datetime.now()} ---\n")
        log_file.write(f"Parameters: Choice={choice}, Animal={animal_choice}, Exp={experiment}, Set={old_or_new}\n")
        log_file.write("-" * 50 + "\n")

        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            futures = [executor.submit(filter_excel_by_column, item, choice, animal_choice, experiment, old_or_new) for item in indexed_files]
            
            for future in as_completed(futures):
                # Unpack the 4 items now
                success, fname, message, warnings_list = future.result()
                
                if success:
                    if warnings_list:
                        # Success but with warnings
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
        
        if failed_files:
            summary_msg += f"\n[FAIL] {len(failed_files)} files FAILED:\n"
            for f, err in failed_files:
                summary_msg += f"   - {f}: {err}\n"
        
        if files_with_warnings:
             summary_msg += f"\n[WARN] {len(files_with_warnings)} files had WARNINGS (check log):\n"
             for f in files_with_warnings:
                 summary_msg += f"   - {f}\n"

        if not failed_files and not files_with_warnings:
            summary_msg += "\n[OK] All files processed perfectly (no errors, no warnings).\n"
        
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