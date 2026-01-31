import requests
from bs4 import BeautifulSoup
import time
import random
import csv
import sys
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://www.mnd.gov.tw"
LIST_URL_TEMPLATE = "https://www.mnd.gov.tw/news/plaactlist/{}"
TARGET_DATE = datetime(2025, 5, 20)  # 114.05.20

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
}

def roc_to_ad(roc_date_str):
    """Converts ROC date string (e.g., '115.01.31') to datetime object."""
    try:
        parts = roc_date_str.strip().split('.')
        year = int(parts[0]) + 1911
        month = int(parts[1])
        day = int(parts[2])
        return datetime(year, month, day)
    except ValueError:
        return None

def scrape():
    page = 1
    results = []
    stop_scraping = False

    print(f"Start scraping... Target date: {TARGET_DATE.strftime('%Y-%m-%d')}")

    while not stop_scraping:
        url = LIST_URL_TEMPLATE.format(page)
        print(f"Fetching page {page}: {url}")
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=10, verify=False)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            break

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the list container
        # Based on list.html: <a href="..." class="news_list">...</a>
        items = soup.find_all('a', class_='news_list')
        
        if not items:
            print("No items found on this page. Ending.")
            break

        print(f"Found {len(items)} items on page {page}.")
        
        for item in items:
            # Extract Date
            date_tag = item.find('h5', class_='date')
            if not date_tag:
                continue
                
            date_str = date_tag.get_text(strip=True)
            ad_date = roc_to_ad(date_str)
            
            if not ad_date:
                print(f"Skipping invalid date format: {date_str}")
                continue

            # Check stopping condition
            if ad_date < TARGET_DATE:
                print(f"Reached date {ad_date.strftime('%Y-%m-%d')} which is older than target. Stopping.")
                stop_scraping = True
                break
            
            # Extract Link
            link = item.get('href')
            if link and not link.startswith('http'):
                full_link = BASE_URL + '/' + link.lstrip('/')
            else:
                full_link = link

            # Extract Title (optional but good for verification)
            title_tag = item.find('h4', class_='title')
            title = title_tag.get_text(strip=True) if title_tag else "No Title"

            print(f"  Captured: {ad_date.strftime('%Y-%m-%d')} - {title}")
            
            results.append({
                'date': ad_date.strftime('%Y-%m-%d'),
                'roc_date': date_str,
                'title': title,
                'link': full_link
            })

        if stop_scraping:
            break
            
        page += 1
        
        # Anti-scraping delay
        delay = random.uniform(1, 3)
        print(f"Sleeping for {delay:.2f} seconds...")
        time.sleep(delay)

    # Save to CSV
    csv_filename = 'pla_activity.csv'
    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'roc_date', 'title', 'link'])
        writer.writeheader()
        writer.writerows(results)
    
    print(f"Scraping complete. Saved {len(results)} records to {csv_filename}.")

if __name__ == "__main__":
    scrape()
