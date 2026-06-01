import fitz  # PyMuPDF
import os

def render_images_from_folder(source_folder, target_folder, dpi=300):
    # Create output folder if it doesn't exist
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    files = [f for f in os.listdir(source_folder) if f.lower().endswith(".pdf")]
    print(f"Found {len(files)} PDF files. Starting rendering at {dpi} DPI...")

    for filename in files:
        pdf_path = os.path.join(source_folder, filename)
        
        try:
            doc = fitz.open(pdf_path)
            page = doc[0]  # Assuming 1 page per file
            
            # --- THE MAGIC PART ---
            # We set the 'matrix' to control resolution (DPI).
            # Default PDF is 72 DPI. To get 300 DPI, we zoom in by 300/72 ≈ 4.16
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            
            # get_pixmap renders the page (stitches all tiles together)
            pix = page.get_pixmap(matrix=mat)
            
            # Save as PNG (Lossless) to prevent quality loss
            image_name = f"{os.path.splitext(filename)[0]}.png"
            save_path = os.path.join(target_folder, image_name)
            
            pix.save(save_path)
            
            print(f"[OK] Stitched & Saved: {image_name} ({pix.width}x{pix.height} px)")

        except Exception as e:
            print(f"[X] Error processing '{filename}': {e}")
            
    print("\n--- Batch Processing Complete ---")

# --- CONFIGURE HERE ---
source_folder = input("Where are your pdf files: ")
target_folder = source_folder

# 300 DPI is standard print quality. 
# If you need it sharper, change to 600 (file size will be much larger).
render_images_from_folder(source_folder, target_folder, dpi=300)