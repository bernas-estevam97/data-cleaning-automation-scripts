import os
import re
import pandas as pd
from multiprocessing import Pool, cpu_count

pd.set_option('future.no_silent_downcasting', True)

def extract_data_from_excel(file_path):
    """
    WORKER FUNCTION (Runs in parallel)
    Opens a single Excel file, extracts the needed rows, parses tags, and returns a dictionary.
    """
    try:
        df_filtered = pd.read_excel(file_path, sheet_name='Kinematics', header=None)
    except Exception as e:
        return {'error': f"Error reading {os.path.basename(file_path)}: {e}"}

    file_id = os.path.basename(file_path)
    parts = file_id.split("_")
    file_id_split = "_".join(parts[:parts.index("out")]) if "out" in parts else file_id

    # 1. Apply the trial number removal first (your existing logic)
    cleaned_id_str = re.sub(r'_\d{1,2}(?=_)', '', file_id_split, count=1)

    # 2. Extract Tags (Timepoint, Test, Group, Gender)
    # Initialize defaults in case a file is missing a tag
    timepoint = "Unknown"
    test_performed = "Unknown"
    group = "Unknown"
    gender = "Unknown"
    
    clean_parts = []
    
    for p in cleaned_id_str.split("_"):
        p_upper = p.upper()
        
        # Check Timepoint (e.g., 4W, 12W)
        time_match = re.match(r'^(\d{1,2})W$', p_upper)
        if time_match:
            weeks = int(time_match.group(1))
            timepoint = weeks // 4  # Maps 4W -> 1, 8W -> 2, 12W -> 3, etc.
            continue
            
        # Check Test
        if p_upper in ['FOOTPRINT', 'BEAM', 'GRIDWALK']:
            test_performed = p_upper
            continue
            
        # Check Group
        if p_upper in ['WT', 'TG']:
            group = p_upper
            continue
            
        # Check Gender
        if p_upper in ['M', 'F']:
            gender = p_upper
            continue
            
        # If it's not a tag, it belongs to the base ID
        clean_parts.append(p)
        
    # Reassemble the base ID without the tags
    base_id = "_".join(clean_parts)

    # 3. Format Headers with the new columns
    header_row_raw = df_filtered.iloc[0]
    # Adding Experimental Group - Gender - Test - Timepoint right after Ids
    tag_headers = ["Experimental Group", "Gender", "Test", "Timepoint"]
    header_stats = ["Ids"] + tag_headers + header_row_raw.iloc[1:].tolist()

    # 4. Extract Statistics
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
            # Attach base_id and tags, then the values
            stat_data = [base_id, group, gender, test_performed, timepoint] + stat_values.iloc[1:].tolist()
            extracted_stats[sheet_name] = stat_data

    # 5. Extract Time Duration
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
        'base_id': base_id,
        'group': group,
        'gender': gender,
        'test_performed': test_performed,
        'timepoint': timepoint,
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
        
    initial_filename = input('What is the name of your project that includes all these tests and ids (this will be the start of the name of the output file)? ')
    
    # Get the list of target files
    file_paths = sorted([os.path.join(folder_input, p) for p in os.listdir(folder_input) if p.endswith('filtered.xlsx')])
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
            # Match the new categorical column structure for durations as well
            compiled_durations.append([
                res['base_id'], res['group'], res['gender'], 
                res['test_performed'], res['timepoint'], res['duration_val']
            ])

    output_filename = f'{initial_filename}_descriptive_statistics.xlsx'
    output_path = os.path.join(folder_output, output_filename)

    # Columns we don't want to convert to numeric/calculate means for
    categorical_cols = ["Ids", "Experimental Group", "Gender", "Test", "Timepoint"]

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        
        # 1. Write the stat sheets
        for sheet_name, rows in compiled_stats.items():
            if rows: 
                df = pd.DataFrame(rows, columns=master_header)
                
                # Convert measurement columns to numeric
                numeric_cols = df.columns.drop(categorical_cols)
                df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)
                
                # Group by ID AND the new tags so they don't get erased, calculate mean across trials
                df_grouped = df.groupby(categorical_cols, as_index=False, dropna=False)[numeric_cols].mean()
                
                df_grouped.to_excel(writer, sheet_name=sheet_name, index=False)

        # 2. Write the Time Duration sheet
        if compiled_durations:
            duration_headers = categorical_cols + ["Time Duration"]
            df_duration = pd.DataFrame(compiled_durations, columns=duration_headers)
            
            df_duration['Time Duration'] = pd.to_numeric(df_duration['Time Duration'])
            # Group by ID and tags to calculate mean duration
            df_duration_grouped = df_duration.groupby(categorical_cols, as_index=False, dropna=False).mean()
            
            df_duration_grouped.to_excel(writer, sheet_name="Time Duration", index=False)

    print(f"Success! Data averaged across trials and saved to: {output_filename}")

if __name__ == '__main__':
    print('Ctrl+C to terminate program at any time.\n')
    try:
        main()
    except KeyboardInterrupt:
        print('\nProgram terminated by user. Exiting function...')