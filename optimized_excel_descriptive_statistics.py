import os
import re
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from tqdm import tqdm

def extract_data_from_excel(file_path):
    """
    WORKER FUNCTION (Runs in parallel)
    Opens a single Excel file, extracts the needed rows, and returns a dictionary.
    Does NOT perform file I/O operations on log files to prevent Windows locking deadlocks.
    """
    filename = os.path.basename(file_path)
    start_time_str = datetime.now().strftime('%H:%M:%S')

    try:
        # Fast Rust-based parser 'calamine' with fallback to 'openpyxl'
        try:
            df_filtered = pd.read_excel(file_path, sheet_name='Kinematics', header=None, engine='calamine')
        except Exception:
            df_filtered = pd.read_excel(file_path, sheet_name='Kinematics', header=None, engine='openpyxl')
    except Exception as e:
        error_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ERROR reading {filename}: {e}\n"
        return {
            'error': error_msg,
            'filename': filename,
            'log_entry': error_msg
        }

    file_id = filename
    parts = file_id.split("_")
    file_id_split = "_".join(parts[:parts.index("out")]) if "out" in parts else file_id

    # Removes a 1 or 2-digit number surrounded by underscores from the string
    base_id = re.sub(r'_\d{1,2}(?=_|\.|$)', '', file_id_split, count=1)

    # 1. Extract Header Row
    header_row_raw = df_filtered.iloc[0]
    header_stats = ["Ids"] + header_row_raw.iloc[1:].tolist()

    # 2. Single-pass column scan for matching row labels
    first_col = df_filtered.iloc[:, 0].astype(str).str.lower().str.strip()
    
    label_to_idx = {}
    duration_idx = None
    for idx, val in enumerate(first_col):
        label_to_idx[val] = idx
        if "duration" in val:
            duration_idx = idx

    # Extract Statistics
    stats_to_extract = {
        "mean": "Mean", 
        "std": "Std", 
        "median": "Median", 
        "min": "Min", 
        "max": "Max",
        "max_normalized_mean": "Max_Normalized_Mean"
    }
    extracted_stats = {}
    
    for search_term, sheet_name in stats_to_extract.items():
        if search_term in label_to_idx:
            row_idx = label_to_idx[search_term]
            stat_values = df_filtered.iloc[row_idx]
            extracted_stats[sheet_name] = [base_id] + stat_values.iloc[1:].tolist()

    # 3. Extract Time Duration
    duration_val = None
    if duration_idx is not None:
        duration_val = df_filtered.iloc[duration_idx, 1]

    end_time_str = datetime.now().strftime('%H:%M:%S')
    log_entry = (
        f"[{start_time_str}] STARTED: {filename}\n"
        f"[{end_time_str}] FINISHED: {filename}\n"
    )

    return {
        'error': None,
        'filename': filename,
        'file_path': file_path,
        'base_id': base_id,
        'header_stats': header_stats,
        'extracted_stats': extracted_stats,
        'duration_val': duration_val,
        'log_entry': log_entry
    }

def main():
    # --- GET INPUTS ---
    folder_input = input('Which folder has your filtered xlsx files? ').strip().strip('"\'')
    if not os.path.isdir(folder_input):
        print('Invalid path input.')
        return
    
    folder_output = input('In which folder do you want your excel file to be at: ').strip().strip('"\'')
    if folder_output == "":
        print("No input. Saving to same folder as your filtered excel files.")
        folder_output = folder_input
    elif not os.path.isdir(folder_output):
        print('Invalid path input.')
        return
        
    experiment_name = input('What experiment are these files from (footprint, beam, swimming, gridwalk)? ').strip()
    
    # Initialize the log file
    log_file_path = os.path.join(folder_input, "debug_log.txt")
    with open(log_file_path, "w", encoding="utf-8") as f_log:
        f_log.write(f"--- STARTING DATA EXTRACTION AT {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")

    # Get the list of target files, IGNORING the ~$ ghost files
    file_paths = sorted([
        os.path.join(folder_input, p) for p in os.listdir(folder_input) 
        if p.endswith('filtered.xlsx') and not p.startswith('~$')
    ])
    
    if not file_paths:
        print(f"No '*filtered.xlsx' files found in '{folder_input}'.")
        return
    
    total_files = len(file_paths)
    print(f"\nFound {total_files} files. Starting parallel data extraction...")
    print(f"Tracking progress in: {log_file_path}")

    # --- PHASE 1: READ MULTIPLE FILES IN PARALLEL ---
    num_cores = max(1, (os.cpu_count() or 4) - 1)
    results = []

    with ProcessPoolExecutor(max_workers=num_cores) as executor:
        # Submit tasks to process pool
        future_to_file = {executor.submit(extract_data_from_excel, fp): fp for fp in file_paths}
        
        # Open log file in main process to append logs safely without file locking collisions
        with open(log_file_path, "a", encoding="utf-8") as f_log:
            with tqdm(total=total_files, desc="Extracting Excel files", unit="file") as pbar:
                for future in as_completed(future_to_file):
                    res = future.result()
                    results.append(res)
                    
                    # Write worker log entry sequentially from main process
                    if res.get('log_entry'):
                        f_log.write(res['log_entry'])
                        f_log.flush()
                        
                    pbar.update(1)

    print("\nData extraction complete! Grouping trials and calculating means...\n")

    # --- PHASE 2: WRITE SEQUENTIALLY TO ONE EXCEL FILE ---
    compiled_stats = {sheet: [] for sheet in ["Mean", "Std", "Median", "Min", "Max", "Max_Normalized_Mean"]}
    compiled_durations = []
    master_header = None

    for res in results:
        if res['error']:
            print(res['error'].strip())
            continue
        
        if master_header is None and res.get('header_stats'):
            master_header = res['header_stats']

        for sheet_name, row_data in res['extracted_stats'].items():
            compiled_stats[sheet_name].append(row_data)

        if res['duration_val'] is not None:
            compiled_durations.append([res['base_id'], res['duration_val']])

    output_filename = f'{experiment_name.upper()}_descriptive_statistics.xlsx'
    output_path = os.path.join(folder_output, output_filename)

    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        
        # 1. Write the stat sheets
        for sheet_name, rows in compiled_stats.items():
            if rows: 
                df = pd.DataFrame(rows, columns=master_header)
                numeric_cols = df.columns.drop('Ids')
                
                df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
                
                df_grouped = df.groupby('Ids', as_index=False)[numeric_cols].mean()
                df_grouped.to_excel(writer, sheet_name=sheet_name, index=False)

        # 2. Write the Time Duration sheet
        if compiled_durations:
            df_duration = pd.DataFrame(compiled_durations, columns=["Ids", "Time Duration"])
            
            df_duration['Time Duration'] = pd.to_numeric(df_duration['Time Duration'], errors='coerce')
            df_duration_grouped = df_duration.groupby('Ids', as_index=False).mean()
            
            df_duration_grouped.to_excel(writer, sheet_name="Time Duration", index=False)

    print(f"Success! Data averaged across trials and saved to: {output_path}")

if __name__ == '__main__':
    print('Ctrl+C to terminate program at any time.\n')
    try:
        main()
    except KeyboardInterrupt:
        print('\nProgram terminated by user. Exiting function...')