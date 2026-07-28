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
        df_filtered = pd.read_excel(file_path, sheet_name='Kinematics', header=None, engine='openpyxl')
    except Exception as e:
        return {'error': f"Error reading {os.path.basename(file_path)}: {e}"}

    file_id = os.path.basename(file_path)
    parts = file_id.split("_")
    file_id_split = "_".join(parts[:parts.index("out")]) if "out" in parts else file_id
    
    # Removes a 1 or 2-digit number surrounded by underscores from the string.
    # NOTE: \d{1,2} natively captures 01, 02, 03 as well as 1, 2, 3.
    base_id = re.sub(r'_\d{1,2}(?=_|\.|$)', '', file_id_split, count=1)

    # 1. Extract the Header Row
    header_row_raw = df_filtered.iloc[0]
    header_stats = ["Ids"] + header_row_raw.iloc[1:].tolist()

    first_col = df_filtered.iloc[:, 0].astype(str).str.lower().str.strip()

    # 2. Extract Statistics
    stats_to_extract = {
        "mean": "Mean", 
        "std": "Std", 
        "median": "Median", 
        "min": "Min", 
        "max": "Max",
        "max_normalized_mean": "Max_Normalized_Mean",
        "cv": "CV"
    }
    extracted_stats = {}
    
    for search_term, sheet_name in stats_to_extract.items():
        mask = first_col == search_term
        found_rows = df_filtered[mask]

        if not found_rows.empty:
            stat_values = found_rows.iloc[-1]
            # ONLY extract the numeric data here. The ID will be prepended in Phase 2 based on user choice.
            stat_data = stat_values.iloc[1:].tolist()
            extracted_stats[sheet_name] = stat_data

    # 3. Extract Time Duration
    duration_val = None
    mask_duration = first_col.str.contains("duration", na=False)
    found_duration_rows = df_filtered[mask_duration]
    
    if not found_duration_rows.empty:
        duration_values = found_duration_rows.iloc[-1]
        duration_val = duration_values.iloc[1]

    return {
        'error': None,
        'file_path': file_path,
        'original_id': file_id_split, # Keeping the unstripped ID just in case
        'base_id': base_id,           # Keeping the stripped ID for grouping
        'header_stats': header_stats,
        'extracted_stats': extracted_stats,
        'duration_val': duration_val
    }

def main():
    # --- GET INPUTS ---
    folder_input = input('Which folder has your filtered xlsx files? ').strip()
    if not os.path.isdir(folder_input):
        print('Invalid path input.')
        return
    
    folder_output = input('In which folder do you want your excel file to be at: ').strip()
    if folder_output == "":
        print("No input. Saving to same folder as your filtered excel files.")
        folder_output = folder_input
    elif not os.path.isdir(folder_output):
        print('Invalid path input.')
        return
        
    experiment_name = input('What experiment are these files from (footprint, beam, swimming, gridwalk)? ').strip()
    
    # GROUPING PROMPT AND WARNING
    print("\n--- GROUPING CONFIGURATION ---")
    print("WARNING: To successfully group trials into a mean, your data files MUST have the exact same base name followed by different trial numbers (e.g., _1, _2, _3 or _01, _02, _03).")
    group_choice = input("Do you want to group the means according to the detected IDs? (y/n): ").strip().lower()
    should_group = group_choice == 'y'
    
    # Get the list of target files
    file_paths = sorted([os.path.join(folder_input, p) for p in os.listdir(folder_input) if p.endswith('filtered.xlsx')])
    
    if not file_paths:
       print(f"No '*filtered.xlsx' files found in '{folder_input}'.")
       return
    
    total_files = len(file_paths)
    print(f"\nFound {total_files} files. Starting parallel data extraction...")

    # --- PHASE 1: READ MULTIPLE FILES IN PARALLEL ---
    num_cores = max(1, cpu_count() - 2) 
    
    with Pool(processes=num_cores) as pool:
        results = pool.map(extract_data_from_excel, file_paths)

    if should_group:
        print("Data extraction complete! Grouping trials and calculating means...\n")
    else:
        print("Data extraction complete! Compiling data without grouping...\n")

    # --- PHASE 2: WRITE SEQUENTIALLY TO ONE EXCEL FILE ---
    compiled_stats = {sheet: [] for sheet in ["Mean", "Std", "Median", "Min", "Max", "Max_Normalized_Mean", "CV"]}
    compiled_durations = []
    master_header = None

    for res in results:
        if res['error']:
            print(res['error'])
            continue
        
        if master_header is None and res.get('header_stats'):
            master_header = res['header_stats']

        # Choose which ID to use based on the user's input
        current_id = res['base_id'] if should_group else res['original_id']

        for sheet_name, row_data in res['extracted_stats'].items():
            # Prepend the chosen ID to the row's numeric data
            compiled_stats[sheet_name].append([current_id] + row_data)

        if res['duration_val'] is not None:
            compiled_durations.append([current_id, res['duration_val']])

    output_filename = f'{experiment_name.upper()}_descriptive_statistics.xlsx'
    output_path = os.path.join(folder_output, output_filename)

    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        
        # 1. Write the stat sheets
        for sheet_name, rows in compiled_stats.items():
            if rows: 
                df = pd.DataFrame(rows, columns=master_header)
                numeric_cols = df.columns.drop('Ids')
                
                df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
                
                # Apply grouping conditionally
                if should_group:
                    df_final = df.groupby('Ids', as_index=False)[numeric_cols].mean()
                else:
                    df_final = df
                    
                df_final.to_excel(writer, sheet_name=sheet_name, index=False)

        # 2. Write the Time Duration sheet
        if compiled_durations:
            df_duration = pd.DataFrame(compiled_durations, columns=["Ids", "Time Duration"])
            df_duration['Time Duration'] = pd.to_numeric(df_duration['Time Duration'], errors='coerce')
            
            # Apply grouping conditionally
            if should_group:
                df_duration_final = df_duration.groupby('Ids', as_index=False).mean()
            else:
                df_duration_final = df_duration
                
            df_duration_final.to_excel(writer, sheet_name="Time Duration", index=False)

    print(f"Success! Data saved to: {output_path}")

if __name__ == '__main__':
    print('Ctrl+C to terminate program at any time.\n')
    try:
        main()
    except KeyboardInterrupt:
        print('\nProgram terminated by user. Exiting function...')