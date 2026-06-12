import os
import pandas as pd
import re

# Dictionary mapping groundwalk naming convention to gridwalk naming convention
groundwalk_to_gridwalk_map = {
    # Front Right Paw
    'Front Right Vx (m/s)': 'Front Right Paw Vx (m/s)',
    'Front Right Vy (m/s)': 'Front Right Paw Vy (m/s)',
    'Front Right Speed (m/s)': 'Front Right Paw Speed (m/s)',
    'Front Right Ax (m/s^2)': 'Front Right Paw Ax (m/s^2)',
    'Front Right Ay (m/s^2)': 'Front Right Paw Ay (m/s^2)',
    'Front Right |Acc| (m/s^2)': 'Front Right Paw |Acc| (m/s^2)',

    # Front Left Paw
    'Front Left Vx (m/s)': 'Front Left Paw Vx (m/s)',
    'Front Left Vy (m/s)': 'Front Left Paw Vy (m/s)',
    'Front Left Speed (m/s)': 'Front Left Paw Speed (m/s)',
    'Front Left Ax (m/s^2)': 'Front Left Paw Ax (m/s^2)',
    'Front Left Ay (m/s^2)': 'Front Left Paw Ay (m/s^2)',
    'Front Left |Acc| (m/s^2)': 'Front Left Paw |Acc| (m/s^2)',

    # Hind Right Paw
    'Hind Right Vx (m/s)': 'Hind Right Paw Vx (m/s)',
    'Hind Right Vy (m/s)': 'Hind Right Paw Vy (m/s)',
    'Hind Right Speed (m/s)': 'Hind Right Paw Speed (m/s)',
    'Hind Right Ax (m/s^2)': 'Hind Right Paw Ax (m/s^2)',
    'Hind Right Ay (m/s^2)': 'Hind Right Paw Ay (m/s^2)',
    'Hind Right |Acc| (m/s^2)': 'Hind Right Paw |Acc| (m/s^2)',

    # Hind Left Paw
    'Hind Left Vx (m/s)': 'Hind Left Paw Vx (m/s)',
    'Hind Left Vy (m/s)': 'Hind Left Paw Vy (m/s)',
    'Hind Left Speed (m/s)': 'Hind Left Paw Speed (m/s)',
    'Hind Left Ax (m/s^2)': 'Hind Left Paw Ax (m/s^2)',
    'Hind Left Ay (m/s^2)': 'Hind Left Paw Ay (m/s^2)',
    'Hind Left |Acc| (m/s^2)': 'Hind Left Paw |Acc| (m/s^2)'
}

def alphanumeric_key(s):
    """Splits string into text and digits for natural sorting (e.g., ID2 comes before ID10)"""
    return tuple(int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', str(s)))

def main():
    print("--- Excel File Merger ---")
    
    # 1. Gather an unlimited number of file paths dynamically
    file_paths = []
    while True:
        file_num = len(file_paths) + 1
        prompt = f"Enter the path for Excel file #{file_num} (or press Enter if you are done adding files): "
        path = input(prompt).strip("'\" ")
        
        if not path:
            if len(file_paths) < 2:
                print("You need at least two files to merge. Please add another file.")
                continue
            else:
                break  # User is done entering files
                
        if not os.path.isfile(path):
            print(f"Invalid file path: {path}. Please try again.")
            continue
            
        file_paths.append(path)

    output_path = input("\nEnter the path/name for the OUTPUT merged excel file (e.g., merged.xlsx): ").strip("'\" ")
    if not output_path.endswith('.xlsx'):
        output_path += '.xlsx'

    print("\nReading files, standardizing columns, and merging sheets...")

    # 2. Read all files into a list of dictionaries and apply the renaming map
    dicts = []
    for path in file_paths:
        try:
            # Read all sheets from the Excel file
            excel_data = pd.read_excel(path, sheet_name=None)
            
            # Iterate through each sheet and rename columns if they exist in the map
            for sheet_name, df in excel_data.items():
                df.rename(columns=groundwalk_to_gridwalk_map, inplace=True)
                
            dicts.append(excel_data)
        except Exception as e:
            print(f"Error reading file '{path}': {e}")
            return

    # 3. Get all unique sheet names across all provided files
    all_sheets = set()
    for d in dicts:
        all_sheets.update(d.keys())

    try:
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for sheet in all_sheets:
                # Gather dataframes for this specific sheet from all files
                dfs = []
                for d in dicts:
                    if sheet in d:
                        dfs.append(d[sheet])
                
                if not dfs:
                    continue

                # 4. Concatenate all DataFrames. 
                # Because we renamed them above, the groundwalk and gridwalk columns will align perfectly.
                merged_df = pd.concat(dfs, ignore_index=True)

                # Sort by the FIRST column if the sheet isn't empty
                if not merged_df.empty:
                    first_col = merged_df.columns[0]
                    merged_df = merged_df.sort_values(
                        by=first_col, 
                        key=lambda col: col.map(alphanumeric_key),
                        ignore_index=True
                    )

                merged_df.to_excel(writer, sheet_name=sheet, index=False)
                
        print(f"\nSuccess! {len(file_paths)} files have been merged and saved to: {output_path}")

    except Exception as e:
        print(f"Error saving the merged file: {e}")

if __name__ == '__main__':
    print('Ctrl+C to terminate program at any time.\n')
    try:
        main()
    except KeyboardInterrupt:
        print('\nProgram terminated by user. Exiting...')