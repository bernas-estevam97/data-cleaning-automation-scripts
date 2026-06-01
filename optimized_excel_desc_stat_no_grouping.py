import os
import pandas as pd
from multiprocessing import Pool, cpu_count

pd.set_option('future.no_silent_downcasting', True)

def extract_data_from_excel(file_path):
    """
    WORKER FUNCTION (Runs in parallel)
    Opens a single Excel file, extracts the needed rows, and returns a dictionary.
    """
    try:
        df_filtered = pd.read_excel(file_path, sheet_name='Kinematics', header=None)
    except Exception as e:
        return {'error': f"Error reading {os.path.basename(file_path)}: {e}"}

    file_id = os.path.basename(file_path)
    parts = file_id.split("_")
    # Keeps the full name including trial number, just removes the "out..." suffix
    trial_id = "_".join(parts[:parts.index("out")]) if "out" in parts else file_id

    # 1. Extract the Header Row
    header_row_raw = df_filtered.iloc[0]
    header_stats = ["Ids"] + header_row_raw.iloc[1:].tolist()

    # 2. Extract Statistics
    stats_to_extract = {
        "Mean": "Mean", "Std": "Std", "Median": "Median", 
        "Min": "Min", "Max": "Max"
    }
    extracted_stats = {}
    
    for keyword, sheet_name in stats_to_extract.items():
        mask = df_filtered.iloc[:, 0].astype(str).str.contains(keyword, case=False, na=False)
        found_rows = df_filtered[mask]

        if not found_rows.empty:
            stat_values = found_rows.iloc[-1]
            # Attach the unique trial_id to the row
            stat_data = [trial_id] + stat_values.iloc[1:].tolist()
            extracted_stats[sheet_name] = stat_data

    # 3. Extract Time Duration
    duration_val = None
    mask_duration = df_filtered.iloc[:, 0].astype(str).str.contains("Duration", case=False, na=False)
    found_duration_rows = df_filtered[mask_duration]
    
    if not found_duration_rows.empty:
        duration_values = found_duration_rows.iloc[-1]
        duration_val = duration_values.iloc[1]

    return {
        'error': None,
        'file_path': file_path,
        'trial_id': trial_id,
        'header_stats': header_stats,
        'extracted_stats': extracted_stats,
        'duration_val': duration_val
    }

def main():
    # --- GET INPUTS ---
    folder_input = input('Which folder has your filtered xlsx files? ')
    if not os.path.isdir(folder_input):
        print('Invalid path input.')
        return
    
    folder_output = input('In which folder do you want your excel file to be at: ')
    if folder_output == "":
        print("No input. Saving to same folder as your filtered excel files")
        folder_output = folder_input
    elif not os.path.isdir(folder_output):
        print('Invalid path input.')
        return
        
    experiment_name = input('What experiment are these files from (footprint, beam, swimming, gridwalk)? ')
    
    # Get the list of target files
    file_paths = sorted([os.path.join(folder_input, p) for p in os.listdir(folder_input) if p.endswith('filtered.xlsx')]) #Sorted
    if not file_paths:
       print(f"No files found in the folder '{folder_input}'.")
       return
    
    total_files = len(file_paths)
    print(f"\nFound {total_files} files. Starting parallel data extraction...")

    # --- PHASE 1: READ MULTIPLE FILES IN PARALLEL ---
    num_cores = max(1, cpu_count() - 4) 
    
    with Pool(processes=num_cores) as pool:
        results = pool.map(extract_data_from_excel, file_paths)

    print("Data extraction complete! Compiling to Excel...\n")

    # --- PHASE 2: WRITE DIRECTLY TO EXCEL (NO AVERAGING) ---
    compiled_stats = {sheet: [] for sheet in ["Mean", "Std", "Median", "Min", "Max"]}
    compiled_durations = []
    master_header = None

    for res in results:
        if res['error']:
            print(res['error'])
            continue
        
        if master_header is None and res['header_stats']:
            master_header = res['header_stats']

        for sheet_name, row_data in res['extracted_stats'].items():
            compiled_stats[sheet_name].append(row_data)

        if res['duration_val'] is not None:
            compiled_durations.append([res['trial_id'], res['duration_val']])

    sample_path_split = os.path.normpath(file_paths[0]).split(os.path.sep)
    dir_part_1 = sample_path_split[-3] if len(sample_path_split) >= 3 else "folder"
    dir_part_2 = sample_path_split[-2] if len(sample_path_split) >= 2 else "output"
    
    output_filename = f'{experiment_name.upper()}_descriptive_statistics_{dir_part_1}_{dir_part_2}.xlsx'
    output_path = os.path.join(folder_output, output_filename)

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        
        # 1. Write the stat sheets
        for sheet_name, rows in compiled_stats.items():
            if rows: 
                df = pd.DataFrame(rows, columns=master_header)
                # Removed the grouping and mean logic; just write the raw dataframe
                df.to_excel(writer, sheet_name=sheet_name, index=False)

        # 2. Write the Time Duration sheet
        if compiled_durations:
            df_duration = pd.DataFrame(compiled_durations, columns=["Ids", "Time Duration"])
            # Removed the grouping and mean logic
            df_duration.to_excel(writer, sheet_name="Time Duration", index=False)

    print(f"Success! Data for all individual trials saved to: {output_filename}")

if __name__ == '__main__':
    print('Ctrl+C to terminate program at any time.\n')
    try:
        main()
    except KeyboardInterrupt:
        print('\nProgram terminated by user. Exiting function...')