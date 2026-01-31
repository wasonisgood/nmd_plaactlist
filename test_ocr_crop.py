import os
import json
import glob
import sys
from PIL import Image
import pytesseract

# Configuration for Tesseract path
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
    print(f"Using Tesseract at: {tesseract_cmd}")
else:
    print("Warning: Tesseract binary not found in common paths. Trying default 'tesseract' command.")

def test_crop_and_ocr(sample_count=5):
    image_dir = "images"
    test_dir = "test_crops"
    
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
        
    image_files = glob.glob(os.path.join(image_dir, "*.jpg")) + \
                  glob.glob(os.path.join(image_dir, "*.png"))
    
    samples = image_files[:sample_count]
    results = []

    print(f"Testing OCR on {len(samples)} samples...")

    for img_path in samples:
        filename = os.path.basename(img_path)
        date_str = os.path.splitext(filename)[0]
        
        try:
            with Image.open(img_path) as img:
                width, height = img.size
                
                # Crop Area: Left 50%, Top 40%
                left = 0
                top = 0
                right = width * 0.45  # Slightly adjusted to focus on the table
                bottom = height * 0.40
                
                cropped_img = img.crop((left, top, right, bottom))
                
                # Save crop for user verification
                crop_filename = f"crop_{filename}"
                crop_path = os.path.join(test_dir, crop_filename)
                cropped_img.save(crop_path)
                
                # OCR process
                # Try chi_tra first
                try:
                    text = pytesseract.image_to_string(cropped_img, lang='chi_tra+eng')
                except Exception:
                    text = pytesseract.image_to_string(cropped_img, lang='eng')
                
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                
                print(f"\n--- Result for {filename} ---")
                print(f"Cropped image saved to: {crop_path}")
                print("Extracted Text:")
                for l in lines[:10]: # Print first 10 lines
                    print(f"  {l}")
                
                results.append({
                    "date": date_str,
                    "ocr_lines": lines
                })
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    with open("test_ocr_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    test_crop_and_ocr()
