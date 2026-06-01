import fitz  # PyMuPDF
import os

def render_at_highest_resolution(source_folder, target_folder):
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    files = [f for f in os.listdir(source_folder) if f.lower().endswith(".pdf")]
    print(f"Found {len(files)} PDF files...")

    for filename in files:
        pdf_path = os.path.join(source_folder, filename)
        
        try:
            doc = fitz.open(pdf_path)
            page = doc[0]  
            
            image_list = page.get_images(full=True)
            
            if not image_list:
                print(f"[!] No images found in '{filename}'. Skipping.")
                continue

            # --- SEARCH FOR THE HIGHEST RESOLUTION FRAGMENT ---
            max_zoom_factor = 0
            detected_dpi = 0

            for img in image_list:
                xref = img[0]
                
                # 1. Get RAW pixel dimensions
                try:
                    base_image = doc.extract_image(xref)
                    raw_width_px = base_image["width"]
                except:
                    continue # Skip if image data is corrupt

                # 2. Get physical size on page
                image_rects = page.get_image_rects(xref)
                if not image_rects:
                    continue # Image is in file but not displayed on page

                rect_width_points = image_rects[0].width
                
                # Avoid division by zero
                if rect_width_points <= 0:
                    continue

                # 3. Calculate Zoom Factor for this specific fragment
                # (Raw Pixels / Point Width) is the scale factor needed to match native res
                current_zoom = raw_width_px / rect_width_points
                
                # Keep the highest one found
                if current_zoom > max_zoom_factor:
                    max_zoom_factor = current_zoom
                    detected_dpi = int(current_zoom * 72)

            # --- VALIDATION ---
            if max_zoom_factor == 0:
                print(f"[!] Could not calculate resolution for '{filename}'. Defaulting to 300 DPI.")
                max_zoom_factor = 300 / 72
                detected_dpi = 300
            
            print(f"    Processing: {filename} @ {detected_dpi} DPI")

            # --- RENDER ---
            # We use the highest zoom factor found to ensure the best quality tile is sharp
            mat = fitz.Matrix(max_zoom_factor, max_zoom_factor)
            pix = page.get_pixmap(matrix=mat)
            
            image_name = f"{os.path.splitext(filename)[0]}.png"
            save_path = os.path.join(target_folder, image_name)
            
            pix.save(save_path)
            print(f"[OK] Saved: {image_name}")

        except Exception as e:
            print(f"[X] Error processing '{filename}': {e}")
            
    print("\n--- Batch Processing Complete ---")

# --- CONFIGURE HERE ---
# input() allows you to paste the path when running
source_folder = input("Where are your pdf files (paste path): ").strip().strip('"')    
target_folder = source_folder

render_at_highest_resolution(source_folder, target_folder)