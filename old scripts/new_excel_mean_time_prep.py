import os
import pandas as pd

def main():
    # --- 1. GET USER INPUTS ---
    folder_input = input('Which folder has your filtered xlsx files? ')
    if not os.path.isdir(folder_input):
        print('Invalid path or empty input.')
        return

    folder_output = input('In which folder do you want your output excel file to be? ')
    if folder_output == "":
        print("Not input provided. Defaulting folder output location to folder input.")
        folder_output = folder_input
    elif not os.path.isdir(folder_output):
        print('Invalid path or empty input.')
        return

    experiment_name = input('What experiment are these files from (footprint, beam, swimming, gridwalk)? ')

    # --- 2. FIND FILES ---
    file_paths = [os.path.join(folder_input, f) for f in os.listdir(folder_input) if f.endswith('filtered.xlsx')]
    
    if not file_paths:
        print(f"No files ending with 'filtered.xlsx' found in {folder_input}")
        return

    total_files = len(file_paths)
    
    # --- 3. INITIALIZE CONTAINERS ---
    # We will grab these specific rows from the files
    metrics_to_extract = ['Mean', 'Std', 'Median', 'Min', 'Max']
    data_containers = {m: [] for m in metrics_to_extract}
    data_containers['Time'] = []

    print(f"Processing {total_files} files...")

    # --- 4. LOOP AND EXTRACT ---
    for idx, file in enumerate(file_paths):
        try:
            file_name = os.path.basename(file)
            
            # Extract ID
            parts = file_name.split("_")
            if "out" in parts:
                file_id_split = "_".join(parts[:parts.index("out")])
            else:
                file_id_split = file_name.replace(".xlsx", "")

            # Read the file
            # We treat all data as objects initially to avoid type errors when reading the mixed "Time" column
            df = pd.read_excel(file, sheet_name='Kinematics', header=0)

            # Ensure 'Time' column is string-like so we can search for "Mean", "Std", etc.
            # (We work on a copy to avoid SettingWithCopy warnings)
            df['Time'] = df['Time'].astype(str)

            # --- A. EXTRACT TIME DURATION ---
            # In your script, "Time Duration" is in the 'Time' column, and the value is in the 2nd column (index 1)
            duration_row = df[df['Time'] == 'Time Duration']
            
            if not duration_row.empty:
                # Grab the value from the column immediately following 'Time'
                # usually df.columns[1]
                duration_val = duration_row.iloc[0, 1]
            else:
                duration_val = "N/A"

            data_containers['Time'].append({'Ids': file_id_split, 'Duration': duration_val})

            # --- B. EXTRACT STATISTICS ROWS ---
            for metric in metrics_to_extract:
                # Find the row where the 'Time' column says 'Mean', 'Std', etc.
                stat_row = df[df['Time'] == metric]
                
                if not stat_row.empty:
                    # Convert the row to a dictionary
                    # We drop the 'Time' column from the data since it just says "Mean"
                    row_data = stat_row.drop(columns=['Time']).iloc[0].to_dict()
                    row_data['Ids'] = file_id_split
                    data_containers[metric].append(row_data)
                else:
                    # Handle case where the row is missing
                    print(f"Warning: '{metric}' row missing in {file_name}")

            print(f"Processed {idx + 1}/{total_files}: {file_name}")

        except Exception as e:
            print(f"SKIP - Error processing {os.path.basename(file)}: {e}")

    # --- 5. COMPILE AND WRITE ---
    print("Compiling data...")
    
    has_data = any(len(v) > 0 for v in data_containers.values())
    
    if has_data:
        # Construct output filename
        list_path_directories = os.path.normpath(file_paths[0]).split(os.path.sep)
        p3 = list_path_directories[-3] if len(list_path_directories) > 2 else "Output"
        p2 = list_path_directories[-2] if len(list_path_directories) > 1 else "Data"
        
        output_filename = f'{experiment_name.upper()}_Descriptive_Statistics_{p3}_{p2}.xlsx'
        output_full_path = os.path.join(folder_output, output_filename)

        with pd.ExcelWriter(output_full_path, engine='openpyxl') as writer:
            for sheet_name, data_list in data_containers.items():
                if data_list:
                    df_sheet = pd.DataFrame(data_list)
                    
                    # Reorder columns: Ids first
                    if 'Ids' in df_sheet.columns:
                        cols = ['Ids'] + [c for c in df_sheet.columns if c != 'Ids']
                        df_sheet = df_sheet[cols]
                    
                    # Optional: Clean up formatting (convert numbers back to float if they got stuck as strings)
                    # This ensures Excel treats them as numbers
                    for col in df_sheet.columns:
                        if col != 'Ids':
                            df_sheet[col] = pd.to_numeric(df_sheet[col], errors='ignore')

                    df_sheet.to_excel(writer, sheet_name=sheet_name, index=False)
        
        print(f"DONE. Successfully saved to: {output_full_path}")
    else:
        print("ERROR: No valid data extracted.")

if __name__ == '__main__':
    try:
        print("Ctrl+C to terminate function at anytime.")
        main()
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")