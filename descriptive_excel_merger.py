import os
import pandas as pd
import re

def alphanumeric_key(s):
    """Splits string into text and digits for natural sorting (e.g., ID2 comes before ID10)"""
    return tuple(int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', str(s)))

def main():
    print("--- Excel File Merger ---")
    
    file1_path = input("Enter the path for the FIRST excel file: ").strip("'\" ")
    if not os.path.isfile(file1_path):
        print("Invalid file path for the first file.")
        return

    file2_path = input("Enter the path for the SECOND excel file: ").strip("'\" ")
    if not os.path.isfile(file2_path):
        print("Invalid file path for the second file.")
        return

    output_path = input("Enter the path/name for the OUTPUT merged excel file (e.g., merged.xlsx): ").strip("'\" ")
    if not output_path.endswith('.xlsx'):
        output_path += '.xlsx'

    print("\nReading files and merging sheets...")

    try:
        dict1 = pd.read_excel(file1_path, sheet_name=None)
        dict2 = pd.read_excel(file2_path, sheet_name=None)
    except Exception as e:
        print(f"Error reading the Excel files: {e}")
        return

    all_sheets = set(dict1.keys()).union(set(dict2.keys()))

    try:
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for sheet in all_sheets:
                df1 = dict1.get(sheet, pd.DataFrame())
                df2 = dict2.get(sheet, pd.DataFrame())

                # Concatenate the two DataFrames
                merged_df = pd.concat([df1, df2], ignore_index=True)

                # Sort by the FIRST column if the sheet isn't empty
                if not merged_df.empty:
                    first_col = merged_df.columns[0]
                    merged_df = merged_df.sort_values(
                        by=first_col, 
                        key=lambda col: col.map(alphanumeric_key),
                        ignore_index=True
                    )

                merged_df.to_excel(writer, sheet_name=sheet, index=False)
                
        print(f"\nSuccess! Files have been merged and saved to: {output_path}")

    except Exception as e:
        print(f"Error saving the merged file: {e}")

if __name__ == '__main__':
    print('Ctrl+C to terminate program at any time.\n')
    try:
        main()
    except KeyboardInterrupt:
        print('\nProgram terminated by user. Exiting...')