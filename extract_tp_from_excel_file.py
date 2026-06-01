import pandas as pd
import logging
import os

# Set up logging for professional execution tracking
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def extract_timepoints(input_file, id_column_name, early_out, late_out):
    logging.info(f"Loading data from {input_file} (This may take a moment for large files)...")

    # Ensure input file exists before running
    if not os.path.exists(input_file):
        logging.error(f"File '{input_file}' not found. Please check the path and try again.")
        return

    try:
        # Read all sheets into a dictionary { 'SheetName': DataFrame }
        all_sheets = pd.read_excel(input_file, sheet_name=None)
    except Exception as e:
        logging.error(f"Failed to read the Excel file. Error: {e}")
        return

    # Prepare regex patterns. 
    # (?<!\d) is a negative lookbehind. It tells Python: "Match '4W', but ONLY if there is NO digit immediately before it." 
    # This prevents the critical bug of '4W' triggering a false positive match on '44W'.
    early_pattern = r'(?<!\d)(4W|8W|12W|16W)'
    late_pattern = r'(?<!\d)(40W|44W|48W|52W)'

    early_data_found = False
    late_data_found = False

    # Initialize Excel writers to maintain separate sheets in the output files
    with pd.ExcelWriter(early_out, engine='openpyxl') as writer_early, \
         pd.ExcelWriter(late_out, engine='openpyxl') as writer_late:

        for sheet_name, df in all_sheets.items():
            logging.info(f"Scanning sheet: '{sheet_name}'")

            # Clean column names by removing hidden leading/trailing spaces
            df.columns = df.columns.astype(str).str.strip()

            if id_column_name not in df.columns:
                logging.warning(f"  -> Column '{id_column_name}' not found in '{sheet_name}'. Skipping sheet.")
                continue

            # Clean ID column: convert to string and handle empty values (NaNs) gracefully
            id_series = df[id_column_name].fillna('').astype(str)

            # Create boolean masks to filter the data (case-insensitive)
            early_mask = id_series.str.contains(early_pattern, case=False, regex=True)
            late_mask = id_series.str.contains(late_pattern, case=False, regex=True)

            # Apply masks to slice the dataframe
            early_df = df[early_mask]
            late_df = df[late_mask]

            # Write to the respective output files ONLY if matching data exists in this sheet
            if not early_df.empty:
                early_df.to_excel(writer_early, sheet_name=sheet_name, index=False)
                early_data_found = True
                logging.info(f"  -> Extracted {len(early_df)} Early timepoints.")

            if not late_df.empty:
                late_df.to_excel(writer_late, sheet_name=sheet_name, index=False)
                late_data_found = True
                logging.info(f"  -> Extracted {len(late_df)} Late timepoints.")

    # --- Post-Processing Cleanup ---
    # Pandas creates an empty file even if no sheets were written. We delete empty files to avoid confusion.
    if not early_data_found:
        if os.path.exists(early_out):
            os.remove(early_out)
        logging.warning(f"No Early timepoints were found across any sheets. '{early_out}' was aborted.")
    else:
        logging.info(f"SUCCESS! Saved to '{early_out}'.")

    if not late_data_found:
        if os.path.exists(late_out):
            os.remove(late_out)
        logging.warning(f"No Late timepoints were found across any sheets. '{late_out}' was aborted.")
    else:
        logging.info(f"SUCCESS! Saved to '{late_out}'.")


if __name__ == "__main__":
    print("\n--- Excel Timepoint Extractor ---")
    
    # 1. Collect inputs from the user
    user_input_file = input('Where is your Excel file located? (Please provide the full path, e.g., C:/path/to/your/file.xlsx):\n> ').strip() 
    user_test_name = input('\nWhat is the name of your test? (Used to name the output files, e.g., "Gridwalk"):\n> ').strip()           
    user_id_column = input('\nWhat is the name of the column that contains the timepoint identifiers? (e.g., "Ids"):\n> ').strip()

    # 2. Generate output filenames dynamically
    out_file_early = f"Early_Timepoints_{user_test_name}.xlsx"
    out_file_late = f"Late_Timepoints_{user_test_name}.xlsx"
    
    print("\n--- Starting Extraction ---")
    
    # 3. Pass the user's inputs directly into the function
    extract_timepoints(
        input_file=user_input_file, 
        id_column_name=user_id_column, 
        early_out=out_file_early, 
        late_out=out_file_late
    )