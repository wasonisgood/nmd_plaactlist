import os
import json
import glob
import concurrent.futures
import sys
try:
    from PIL import Image
    import pytesseract
except ImportError:
    print("Please install libraries: pip install pytesseract Pillow")
    sys.exit(1)

# Configuration for Tesseract path on Windows (Common locations)
# Users might need to install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
possible_paths = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    r'C:\Users\wason\AppData\Local\Tesseract-OCR\tesseract.exe'
]

tesseract_cmd = None
for path in possible_paths:
    if os.path.exists(path):
        tesseract_cmd = path
        break

if tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
else:
    # Hope it's in PATH
    pass

def process_image(img_path):
    try:
        filename = os.path.basename(img_path)
        date_str = os.path.splitext(filename)[0]
        
        with Image.open(img_path) as img:
            width, height = img.size
            
            # Crop Area: Adjusted to skip the title (approx top 16%)
            # Focus on the left table
            left = 0
            top = height * 0.16  # Skip title and date info
            right = width * 0.45 
            bottom = height * 0.50 # Extend slightly to capture more rows
            
            cropped_img = img.crop((left, top, right, bottom))
            
            # Convert to grayscale for better OCR
            cropped_img = cropped_img.convert('L')
            
            # Perform OCR
            # Try to use Chinese Traditional + English
            try:
                text = pytesseract.image_to_string(cropped_img, lang='chi_tra+eng')
            except pytesseract.TesseractError:
                # Fallback to English only if chi_tra is missing
                try:
                    text = pytesseract.image_to_string(cropped_img, lang='eng')
                except Exception as e:
                    return {"date": date_str, "error": str(e)}

            # Simple parsing of the text to clean it up
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            return {
                "date": date_str,
                "file": filename,
                "raw_text": lines
            }
            
    except Exception as e:
        return {"date": date_str, "error": str(e)}

def main():
    image_dir = "images"
    output_file = "ocr_results.json"
    
    # Get list of images
    image_files = glob.glob(os.path.join(image_dir, "*.jpg")) + \
                  glob.glob(os.path.join(image_dir, "*.png")) + \
                  glob.glob(os.path.join(image_dir, "*.JPG")) + \
                  glob.glob(os.path.join(image_dir, "*.PNG"))
    
    print(f"Found {len(image_files)} images to process.")
    
    results = []
    
    # Check if tesseract is available effectively
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        print("Error: Tesseract OCR binary not found.")
        print("Please install Tesseract OCR from https://github.com/UB-Mannheim/tesseract/wiki")
        print("And ensure it is in your PATH or update the script with the installation path.")
        # We will still try to run, maybe some workers will fail or all will fail.
        # But actually if get_version fails, image_to_string will fail too.
        # Let's stop here to be clear.
        return

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future_to_img = {executor.submit(process_image, img_path): img_path for img_path in image_files}
        
        for future in concurrent.futures.as_completed(future_to_img):
            data = future.result()
            if data:
                results.append(data)
                
    # Sort by date
    results.sort(key=lambda x: x.get('date', ''))
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
        
    print(f"OCR complete. Saved results for {len(results)} images to {output_file}.")

if __name__ == "__main__":
    main()
