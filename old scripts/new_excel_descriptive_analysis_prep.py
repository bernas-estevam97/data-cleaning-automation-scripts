import os
import pandas as pd
#import time
#from multiprocessing import Pool
#from pathlib import Path
#from concurrent.futures import ProcessPoolExecutor, as_completed

pd.set_option('future.no_silent_downcasting', True)

def create_new_excel_mean_time(idx, file, total_files, output_folder, experiment):
    list_path_directories = os.path.normpath(file).split(os.path.sep)
    
    # Read the specific sheet
    try:
        df_filtered = pd.read_excel(file, sheet_name='Kinematics', header=None)
    except Exception as e:
        return f"Error reading {os.path.basename(file)}: {e}"

    file_id = os.path.basename(file)
    parts = file_id.split("_")
    file_id_split = "_".join(parts[:parts.index("out")]) if "out" in parts else file_id

    # 1. Extract the Header Row (usually contains "Time", "Step Width", etc.)
    # We assume the first row (index 0) is the header.
    header_row_raw = df_filtered.iloc[0]
    df_header = pd.DataFrame(header_row_raw).T
    df_header.insert(0, "Ids", "Ids") # Add "Ids" label to the start

    # 2. Define the statistics rows we want to find and their corresponding Sheet Names
    # Keys are the keywords to search for in the first column, Values are the Output Sheet Names
    stats_to_extract = {
        "Mean": "Mean",
        "Std": "Std", 
        "Median": "Median",
        "Min": "Min", 
        "Max": "Max"
    }

    # Construct Output File Path
    # Using the same naming convention as your original code
    output_filename = f'{experiment.upper()}_descriptive_statistics_{list_path_directories[-3]}_{list_path_directories[-2]}.xlsx'
    output_path = os.path.join(output_folder, output_filename)

    # 3. Write to Excel
    # Use 'w' (write) mode for the first file to create/overwrite, 'a' (append) for others
    mode = 'w' if idx == 0 else 'a'
    # 'overlay' allows writing to existing sheets without clearing them (crucial for 'a' mode)
    if_sheet_exists = None if idx == 0 else 'overlay'

    with pd.ExcelWriter(output_path, engine='openpyxl', mode=mode, if_sheet_exists=if_sheet_exists) as writer:
        
        for keyword, sheet_name in stats_to_extract.items():
            # Search for the row where the first column contains the keyword (case-insensitive)
            # We convert to string first to handle any potential non-string types
            mask = df_filtered.iloc[:, 0].astype(str).str.contains(keyword, case=False, na=False)
            found_rows = df_filtered[mask]

            if not found_rows.empty:
                # Take the last occurrence found (assuming summary stats are at the bottom)
                stat_values = found_rows.iloc[-1]
                df_stat_values = pd.DataFrame(stat_values).T
                
                # Insert the File ID at the beginning
                df_stat_values.insert(0, "Ids", file_id_split)

                # Write Header (only for the first file)
                if idx == 0:
                    df_header.to_excel(writer, sheet_name=sheet_name, startrow=0, index=False, header=False)

                # Write Data Row
                # startrow = idx + 1 ensures we append row by row (Row 0 is header)
                df_stat_values.to_excel(writer, sheet_name=sheet_name, startrow=idx + 1, index=False, header=False)
            else:
                # Optional: Print warning if a specific stat row is missing in this file
                # print(f"Warning: '{keyword}' row not found in {file_id}")
                pass

    return f"Added info to Excel from file {idx + 1} of {total_files}: {os.path.basename(file)} info added"

def main():
    # Get folder path input from user
    folder_input = input('Which folder has your filtered xlsx files? ')
    if os.path.isdir(folder_input):
        print('Folder selected: ', folder_input)
    elif folder_input == "":
        print("You didn't input any path.")
        return
    else:
        print('Invalid path input.')
        return
    
    folder_output = input('In which folder do you want your excel file to be at: ')

    if os.path.isdir(folder_output):
        print('File destination: ', folder_output)
    elif folder_output == "":
        print("No input. Saving to same folder as your filtered excel files")
        folder_output = folder_input
    else:
        print('Invalid path input.')
        return
        
    experiment_name = input('What experiment are these files from (footprint, beam, swimming, gridwalk)? ')
    
    # Get the list of files in the folder (filtering only filtered xlsx files)
    file_paths = [os.path.join(folder_input, str(p)) for p in os.listdir(folder_input) if p.endswith('filtered.xlsx')]
    if not file_paths:
       print(f"No files found in the folder '{folder_input}'.")
       return
    
    total_files = len(file_paths)

    for idx, file in enumerate(file_paths):
        result = create_new_excel_mean_time(idx, file, total_files, folder_output, experiment_name)
        print(result)

if __name__ == '__main__':
    main()