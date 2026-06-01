import pandas as pd
from openpyxl import load_workbook
import os
from datetime import datetime
from collections import defaultdict
import numpy as np
from openpyxl.styles import PatternFill, Font
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl import Workbook
import re

# All possible target labels in Excel
RAW_STRINGS = [
    "Stride length left front average in cm:",
    "Stride length right front average in cm:",
    "Stride length left hind average in cm:",
    "Stride length right hind average in cm:",
    "Overlap left average in cm:",
    "Overlap Right average in cm:",
    "Stride Width Front(L) average in cm:",
    "Stride Width Front(R) average in cm:",
    "Stride Width Hind(L) average in cm:",
    "Stride Width Hind(R) average in cm:"
]

# Map specific labels to unified output names
RENAME_MAP = {
    "Stride Width Front(L) average in cm:": "Stride Width Front average in cm:",
    "Stride Width Front(R) average in cm:": "Stride Width Front average in cm:",
    "Stride Width Hind(L) average in cm:": "Stride Width Hind average in cm:",
    "Stride Width Hind(R) average in cm:": "Stride Width Hind average in cm:"
}

data_ids = {
    "4023": ("Doente", "Male"),
    "4020": ("Heterozigótico", "Female"),
    "4021": ("Doente", "Female"),
    "4022": ("Heterozigótico", "Female"),
    "4032": ("Heterozigótico", "Female"),
    "4033": ("Heterozigótico", "Female"),
    "4034": ("Heterozigótico", "Male"),
    "4035": ("Heterozigótico", "Male"),
    "4036": ("Doente", "Male"),
    "4037": ("Doente", "Male"),
    "4105": ("Doente", "Female"),
    "4106": ("Heterozigótico", "Female"),
    "4107": ("Heterozigótico", "Female"),
    "4108": ("Heterozigótico", "Female"),
    "4109": ("Doente", "Male"),
    "4110": ("Doente", "Male"),
    "4111": ("Heterozigótico", "Male"),
    "4112": ("Heterozigótico", "Female"),
    "4113": ("Doente", "Female"),
    "4114": ("Heterozigótico", "Female"),
    "4116": ("Doente", "Female"),
    "4120": ("Homozigótico", "Male"),
    "4172": ("Homozigótico", "Female"),
    "4173": ("Doente", "Female"),
    "4174": ("Heterozigótico", "Female"),
    "4175": ("Doente", "Male"),
    "4176": ("Heterozigótico", "Male"),
    "4177": ("Heterozigótico", "Male")
}

def find_table_data(workbook_path):
    # data_only=True is CRITICAL to get the calculated number, not the formula string
    wb = load_workbook(workbook_path, data_only=True)
    result_data = []

    # SAFETY THRESHOLD
    # If a number is > 500, it's 1000x too big (e.g. 4512 -> 4.512)
    THRESHOLD = 500

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        
        # We assume the sheet name itself might be the "Time Tag" (e.g., T4, T5)
        # We pass this down so we can use it as a fallback if the cell text is missing the tag.
        current_sheet_tag = sheet_name 

        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.strip().startswith("Table ID"):
                    
                    # Extract clean Table ID
                    raw_table_id = cell.value.strip().replace("Table ID:", "").strip()
                    
                    table_values = defaultdict(list)
                    table_values["Table ID"].append(raw_table_id)
                    
                    # Store the Sheet Name as a backup "Tag"
                    table_values["Sheet_Source"].append(current_sheet_tag)

                    col_index = cell.column
                    row_index = cell.row

                    for r in range(row_index + 1, ws.max_row + 1):
                        label_cell = ws.cell(row=r, column=col_index)
                        value_cell = ws.cell(row=r, column=col_index + 1)

                        label = label_cell.value
                        value = value_cell.value

                        if label in RAW_STRINGS and isinstance(value, (int, float)):
                            output_label = RENAME_MAP.get(label, label)
                            
                            # --- SMART FIX LOGIC ---
                            # If value is huge (e.g. 4512), divide by 1000
                            if value > THRESHOLD:
                                value = value / 1000.0
                            # -----------------------

                            table_values[output_label].append(value)

                    # Calculate means
                    table_data = {}
                    for key, values in table_values.items():
                        if key in ["Table ID", "Sheet_Source"]:
                            table_data[key] = values[0]
                        else:
                            table_data[key] = float(np.mean(values)) if values else None

                    result_data.append(table_data)

    return result_data

def process_file(input_file):
    
    if not os.path.isfile(input_file):
        raise FileNotFoundError(f"File not found: {input_file}")

    print("Extracting data... (this might take a moment)")
    data = find_table_data(input_file)

    if not data:
        raise ValueError("No 'Table ID' entries found in the provided file.")

    # Step 1: Group by Time Tag (T4, T5, or 4W, 8W)
    w_groups = defaultdict(list)
    
    for entry in data:
        table_id = entry.get("Table ID", "")
        sheet_source = entry.get("Sheet_Source", "Unknown")
        found_tag = None

        # Regex to look for "T4", "T5" OR "4W", "8W"
        # It splits by space or underscore to check parts individually
        parts = re.split(r'[_\s]+', table_id)
        
        for part in parts:
            # Match T + digits (T4, T5) OR digits + W (4W, 8W)
            if re.fullmatch(r"T\d+", part) or re.fullmatch(r"\d+W", part) or re.fullmatch(r"\d+\+\d+W", part):
                found_tag = part
                break
        
        # Fallback: If no tag found in the text, use the Sheet Name
        if not found_tag:
             found_tag = sheet_source

        if found_tag:
            w_groups[found_tag].append(entry)
        else:
            w_groups["Unknown"].append(entry)

    # Step 2: Create output workbook
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = os.path.join(os.path.dirname(input_file), f"MFrame_clean_output_{timestamp}.xlsx")

    wb = Workbook()
    wb.remove(wb.active) # Remove default sheet

    # Setup styles
    white_font = Font(color="FFFFFFFF")

    def get_fill(genotype, sex):
        if (genotype, sex) == ("Sick", "Male"):
            return PatternFill(start_color="FF003366", end_color="FF003366", fill_type="solid"), True
        elif (genotype, sex) == ("Homozygous", "Male"):
            return PatternFill(start_color="FFADD8E6", end_color="FFADD8E6", fill_type="solid"), False
        elif (genotype, sex) == ("Sick", "Female"):
            return PatternFill(start_color="FF8B0000", end_color="FF8B0000", fill_type="solid"), True
        elif (genotype, sex) == ("Homozygous", "Female"):
            return PatternFill(start_color="FFFFC0CB", end_color="FFFFC0CB", fill_type="solid"), False
        elif (genotype, sex) == ("Heterozygous", "Male"):
            return PatternFill(start_color="27F5F5", end_color="27F5F5", fill_type="solid"), False
        elif (genotype, sex) == ("Heterozygous", "Female"):
            return PatternFill(start_color="FFF589C5", end_color="FFF589C5", fill_type="solid"), False
        else:
            return None, False

    # Helper to sort T4, T5 naturally
    def sort_tags(tag):
        # Extract the first number found to sort numerically
        nums = re.findall(r'\d+', tag)
        if nums:
            return int(nums[0])
        return float('inf')

    # Create sheets
    for tag, group_data in sorted(w_groups.items(), key=lambda x: sort_tags(x[0])):
        # Clean up data before DataFrame (remove internal helper key)
        clean_data = []
        for d in group_data:
            d_copy = d.copy()
            d_copy.pop("Sheet_Source", None) # Don't print this helper column
            clean_data.append(d_copy)

        df = pd.DataFrame(clean_data)
        
        # Ensure 'Table ID' is the first column
        cols = ['Table ID'] + [c for c in df.columns if c != 'Table ID']
        df = df[cols]

        ws = wb.create_sheet(title=str(tag))

        for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), start=1):
            for c_idx, value in enumerate(row, start=1):
                cell = ws.cell(row=r_idx, column=c_idx, value=value)
                # Format decimals in output
                if isinstance(value, float):
                    cell.number_format = '0.000'

        # Apply coloring
        headers = list(df.columns)
        try:
            table_id_col_index = headers.index("Table ID") + 1
        except ValueError:
            continue

        for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
            table_id_cell = row[table_id_col_index - 1]
            table_id = str(table_id_cell.value).strip()

            # Find matching ID (e.g. look for "4023" inside "Cage 2301 Animal 4023")
            matched_key = next((k for k in data_ids if k in table_id), None)

            if matched_key:
                genotype, sex = data_ids[matched_key]
                fill, use_white_font = get_fill(genotype, sex)

                for cell in row:
                    if fill:
                        cell.fill = fill
                        if use_white_font:
                            cell.font = white_font

    wb.save(output_file)
    return output_file

if __name__ == "__main__":
    input_file = input("Enter the path to the Excel file: ").strip()
    # Remove quotes if user added them
    input_file = input_file.strip('"').strip("'")
    
    print(f"Input file: {input_file}")
    try:
        output_path = process_file(input_file)
        print(f"✅ Extracted data has been written to: {output_path}")
    except Exception as e:
        print(f"❌ Error: {e}")