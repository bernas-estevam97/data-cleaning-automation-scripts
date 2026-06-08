import os
import re
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
    file_id_split = "_".join(parts[:parts.index("out")]) if "out" in parts else file_id

    # NEW: Remove trailing trial numbers (e.g., "_01", "_02") to get the base subject ID
    # This looks for an underscore followed by digits at the end of the string
    #base_id = re.sub(r'_\d+$', '', file_id_split) THIS WORKS FOR MY FILE NAMES NOT FOR INES
    # Removes a 1 or 2-digit number surrounded by underscores from the string
    base_id = re.sub(r'_\d{1,2}(?=_)', '', file_id_split, count=1) # THIS WORKS FOR INES FILENAMES

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
            # Take values from index 1 onwards to drop label column, attach base_id
            stat_data = [base_id] + stat_values.iloc[1:].tolist()
            extracted_stats[sheet_name] = stat_data

    # 3. Extract Time Duration
    duration_val = None
    mask_duration = df_filtered.iloc[:, 0].astype(str).str.contains("Duration", case=False, na=False)
    found_duration_rows = df_filtered[mask_duration]
    
    if not found_duration_rows.empty:
        duration_values = found_duration_rows.iloc[-1]
        duration_val = duration_values.iloc[1]

    # Return all extracted data for this file
    return {
        'error': None,
        'file_path': file_path,
        'base_id': base_id,  # Using the cleaned ID
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

    print("Data extraction complete! Grouping trials and calculating means...\n")

    # --- PHASE 2: WRITE SEQUENTIALLY TO ONE EXCEL FILE ---
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
            compiled_durations.append([res['base_id'], res['duration_val']])

    sample_path_split = os.path.normpath(file_paths[0]).split(os.path.sep)
    #dir_part_1 = sample_path_split[-3] if len(sample_path_split) >= 3 else "folder"
    #dir_part_2 = sample_path_split[-2] if len(sample_path_split) >= 2 else "output"
    
    #output_filename = f'{experiment_name.upper()}_descriptive_statistics_{dir_part_1}_{dir_part_2}.xlsx'
    output_filename = f'{experiment_name.upper()}_descriptive_statistics.xlsx'
    output_path = os.path.join(folder_output, output_filename)

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        
        # 1. Write the stat sheets
        for sheet_name, rows in compiled_stats.items():
            if rows: 
                df = pd.DataFrame(rows, columns=master_header)
                
                # NEW: Convert columns to numeric, then group by ID and calculate the mean
                numeric_cols = df.columns.drop('Ids')
                df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)
                df_grouped = df.groupby('Ids', as_index=False)[numeric_cols].mean()
                
                df_grouped.to_excel(writer, sheet_name=sheet_name, index=False)

        # 2. Write the Time Duration sheet
        if compiled_durations:
            df_duration = pd.DataFrame(compiled_durations, columns=["Ids", "Time Duration"])
            
            # NEW: Convert duration to numeric and group by ID to get the mean
            df_duration['Time Duration'] = pd.to_numeric(df_duration['Time Duration'])
            df_duration_grouped = df_duration.groupby('Ids', as_index=False).mean()
            
            df_duration_grouped.to_excel(writer, sheet_name="Time Duration", index=False)

    print(f"Success! Data averaged across trials and saved to: {output_filename}")

if __name__ == '__main__':
    print('Ctrl+C to terminate program at any time.\n')
    try:
        main()
    except KeyboardInterrupt:
        print('\nProgram terminated by user. Exiting function...')