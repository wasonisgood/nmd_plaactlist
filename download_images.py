import os
import json
import requests
from bs4 import BeautifulSoup
import concurrent.futures
import urllib3
import base64

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

BASE_URL = "https://www.mnd.gov.tw"
OUTPUT_DIR = "images"

def download_image(activity):
    url = activity['link']
    date_str = activity['activity_date']
    
    try:
        # Check if already downloaded to skip
        # Need to check extensions, so maybe skip if any file with that date exists
        for ext in ['.jpg', '.JPG', '.png', '.PNG', '.jpeg']:
             if os.path.exists(os.path.join(OUTPUT_DIR, f"{date_str}{ext}")):
                 return

        # Fetch the page content
        response = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the image in the main content
        content_div = soup.find('div', class_='maincontent')
        
        img_src = None
        if content_div:
            images = content_div.find_all('img')
            for img in images:
                src = img.get('src')
                if not src:
                    continue
                
                # Check for data URI or likely image files
                if src.startswith('data:image'):
                    img_src = src
                    break
                elif 'jpg' in src.lower() or 'png' in src.lower() or 'jpeg' in src.lower():
                    img_src = src
                    break
        
        if not img_src:
            print(f"No image found for {date_str} ({url})")
            return

        # Handle Data URI
        if img_src.startswith('data:image'):
            try:
                # Format: data:image/png;base64,.....
                header, encoded = img_src.split(',', 1)
                
                # Determine extension from header
                ext = ".jpg" # Default
                if "png" in header:
                    ext = ".png"
                elif "jpeg" in header or "jpg" in header:
                    ext = ".jpg"
                elif "gif" in header:
                    ext = ".gif"
                
                img_data = base64.b64decode(encoded)
                
                filename = f"{date_str}{ext}"
                filepath = os.path.join(OUTPUT_DIR, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(img_data)
                
                print(f"Saved (Base64): {filename}")
                return
            except Exception as e:
                print(f"Error decoding base64 for {date_str}: {e}")
                return

        # Handle Normal URL
        if not img_src.startswith('http'):
            if img_src.startswith('/'):
                 img_src = BASE_URL + img_src
            else:
                 img_src = BASE_URL + '/' + img_src

        # Determine file extension
        ext = os.path.splitext(img_src)[1]
        if not ext:
            ext = ".jpg"
            
        filename = f"{date_str}{ext}"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        # Download the image
        img_response = requests.get(img_src, headers=HEADERS, timeout=20, verify=False)
        img_response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            f.write(img_response.content)
            
        print(f"Downloaded: {filename}")

    except Exception as e:
        print(f"Error processing {date_str}: {e}")

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    try:
        with open('pla_details.json', 'r', encoding='utf-8') as f:
            activities = json.load(f)
    except FileNotFoundError:
        print("pla_details.json not found.")
        return

    print(f"Found {len(activities)} activities. Starting image download...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(download_image, activities)

    print("Download process complete.")

if __name__ == "__main__":
    main()
