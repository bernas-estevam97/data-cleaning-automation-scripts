import fitz  # PyMuPDF
import os

def inspect_pdf_resolution(pdf_path):
    doc = fitz.open(pdf_path)
    page = doc[0]  # Check first page
    
    image_list = page.get_images(full=True)
    
    print(f"--- INSPECTING: {os.path.basename(pdf_path)} ---")
    print(f"Total image objects found: {len(image_list)}")
    print(f"{'Img ID':<8} | {'Raw Pixels':<12} | {'On-Page Size (pts)':<20} | {'Calculated DPI':<15}")
    print("-" * 65)

    detected_dpis = []

    for i, img in enumerate(image_list):
        xref = img[0]
        
        # 1. Get raw image dimensions (The actual file stored inside)
        base_image = doc.extract_image(xref)
        raw_w = base_image["width"]
        raw_h = base_image["height"]
        
        # 2. Get displayed dimensions (How big it looks on the page)
        # Note: Rects are measured in "points" (1/72 inch)
        image_rects = page.get_image_rects(xref)
        
        if not image_rects:
            continue # Image exists but isn't displayed on this page
            
        rect = image_rects[0]
        rect_w = rect.width
        rect_h = rect.height
        
        # 3. Calculate DPI
        # Formula: (Pixels / Points) * 72
        if rect_w > 0:
            dpi_x = (raw_w / rect_w) * 72
            dpi_y = (raw_h / rect_h) * 72
            avg_dpi = int((dpi_x + dpi_y) / 2)
            
            detected_dpis.append(avg_dpi)
            
            # Only print the first 10 to avoid spamming console if there are 200 tiles
            if i < 10:
                print(f"#{i:<7} | {raw_w}x{raw_h:<7} | {rect_w:.1f}x{rect_h:.1f} pts      | {avg_dpi} DPI")
    
    if len(image_list) > 10:
        print(f"... (and {len(image_list) - 10} more fragments)")
        
    if detected_dpis:
        max_dpi = max(detected_dpis)
        print("-" * 65)
        print(f"HIGHEST DPI FOUND: {max_dpi}")
        print(f"MOST COMMON DPI:   {max(set(detected_dpis), key=detected_dpis.count)}")
    else:
        print("No visible images found to calculate DPI.")

# --- CHANGE THIS FILE PATH TO TEST ---
input_here = input("Which is the pdf you want to check: ")

inspect_pdf_resolution(input_here)