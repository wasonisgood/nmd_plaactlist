import requests
from bs4 import BeautifulSoup
import csv
import json
import concurrent.futures
import urllib3
from datetime import datetime, timedelta
import re
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

def scrape_detail(row):
    url = row['link']
    publish_date_str = row['date'] # YYYY-MM-DD
    
    try:
        publish_date = datetime.strptime(publish_date_str, '%Y-%m-%d')
        # Activity date is the day before the publish date
        activity_date = publish_date - timedelta(days=1)
        activity_date_str = activity_date.strftime('%Y-%m-%d')

        response = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract content from <div class="maincontent">
        content_div = soup.find('div', class_='maincontent')
        
        if content_div:
            # Get all text, but try to find the "Activity Dynamic" part
            # Based on the sample: 
            # <p>二、活動動態：<br />迄0600時止...</p>
            
            full_text = content_div.get_text(separator='\n', strip=True)
            
            # Try to extract specifically the text after "活動動態"
            # Regex to find "Activity Dynamic" or similar headers
            # Pattern: matches "Activity Dynamic:" or "2. Activity Dynamic:" etc.
            # Then captures everything until the end or next section if any.
            
            # Simple approach: just save the full text for now, but user asked for "Activity Dynamic Text"
            # Let's try to be smarter.
            
            # The sample shows:
            # 一、日期：...
            # 二、活動動態：...
            
            activity_text = ""
            lines = full_text.split('\n')
            capture = False
            captured_lines = []
            
            for line in lines:
                if "活動動態" in line:
                    capture = True
                    # Remove the header itself if it's on the same line
                    # e.g. "二、活動動態：迄0600時止..." -> "迄0600時止..."
                    # But often it might be "二、活動動態：" then newline.
                    
                    # Split by colon if exists
                    if "：" in line:
                        parts = line.split("：", 1)
                        if len(parts) > 1 and parts[1].strip():
                            captured_lines.append(parts[1].strip())
                    elif ":" in line:
                         parts = line.split(":", 1)
                         if len(parts) > 1 and parts[1].strip():
                            captured_lines.append(parts[1].strip())
                    continue
                
                if capture:
                    # You might want to stop if you hit another section "三、" or similar, 
                    # but usually this is the main part.
                    # Images are often at the end.
                    if line.strip() == "":
                        continue
                    captured_lines.append(line.strip())
            
            if captured_lines:
                activity_text = "\n".join(captured_lines)
            else:
                # Fallback: if regex didn't work (maybe different format), take the whole text
                # but maybe strip the "Date:" part if possible.
                activity_text = full_text

            return {
                "publish_date": publish_date_str,
                "activity_date": activity_date_str,
                "title": row['title'],
                "link": url,
                "content": activity_text
            }
        else:
            print(f"Warning: No content found for {url}")
            return {
                "publish_date": publish_date_str,
                "activity_date": activity_date_str,
                "title": row['title'],
                "link": url,
                "content": "Content not found"
            }

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

def main():
    # Read CSV
    try:
        with open('pla_activity.csv', 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except FileNotFoundError:
        print("pla_activity.csv not found. Please run the list scraper first.")
        return

    print(f"Found {len(rows)} items to scrape.")
    
    results = []
    
    # Multi-threading
    # Adjust max_workers as needed. 10 is usually safe for scraping without being too aggressive.
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_row = {executor.submit(scrape_detail, row): row for row in rows}
        
        completed = 0
        for future in concurrent.futures.as_completed(future_to_row):
            data = future.result()
            if data:
                results.append(data)
            
            completed += 1
            if completed % 10 == 0:
                print(f"Progress: {completed}/{len(rows)}")

    # Sort results by activity date (descending)
    results.sort(key=lambda x: x['activity_date'], reverse=True)

    # Save to JSON
    with open('pla_details.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
        
    print(f"Scraping complete. Saved {len(results)} details to pla_details.json")

if __name__ == "__main__":
    main()
