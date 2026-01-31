import os
import json
import re
import time
import requests
import urllib3
import base64
import concurrent.futures
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from PIL import Image

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

BASE_URL = "https://www.mnd.gov.tw"
LIST_URL_TEMPLATE = "https://www.mnd.gov.tw/news/plaactlist/{}"
IMAGE_DIR = "images"

SUPABASE_URL = "https://abjxpbtcseagrfwcehbo.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFianhwYnRjc2VhZ3Jmd2NlaGJvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY4Mzc0NzUsImV4cCI6MjA4MjQxMzQ3NX0.IMLgS1jTBS82J0BER2I_CROCJn_7DtMoPIbyRCSpC9s"

SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# Tesseract Configuration
try:
    import pytesseract
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
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

# --- Helper Functions ---
def roc_to_ad(roc_date_str):
    try:
        parts = roc_date_str.strip().split('.')
        year = int(parts[0]) + 1911
        month = int(parts[1])
        day = int(parts[2])
        return datetime(year, month, day).strftime('%Y-%m-%d')
    except ValueError:
        return None

def get_activity_date(publish_date_str):
    try:
        pub_date = datetime.strptime(publish_date_str, '%Y-%m-%d')
        act_date = pub_date - timedelta(days=1)
        return act_date.strftime('%Y-%m-%d')
    except:
        return publish_date_str

def analyze_text_content(text):
    data = {"aircraft_total": 0, "aircraft_crossing": 0, "vessels_total": 0, "official_ships_total": 0, "balloons_total": 0}
    match = re.search(r'共機(\d+)架次', text)
    if match: data["aircraft_total"] = int(match.group(1))
    paren_match = re.search(r'\((.*?)\)', text)
    if paren_match:
        inner = paren_match.group(1)
        crossing = re.search(r'(\d+)架次', inner)
        if crossing: data["aircraft_crossing"] = int(crossing.group(1))
    match = re.search(r'共艦(\d+)艘', text)
    if match: data["vessels_total"] = int(match.group(1))
    match = re.search(r'公務船(\d+)艘', text)
    if match: data["official_ships_total"] = int(match.group(1))
    match = re.search(r'空飄氣球.*?(\d+)[顆枚]', text)
    if match: data["balloons_total"] = int(match.group(1))
    return data

def parse_ocr_lines(raw_lines):
    events = []
    current_event = None
    for line in raw_lines:
        line = line.strip()
        if not line or line.lower() in ['activities', 'no', 'content', '內容']: continue
        time_match = re.search(r'(\d{4})\s*[-~]\s*(\d{4})', line)
        if time_match:
            if current_event: events.append(current_event)
            current_event = {"time": f"{time_match.group(1)}-{time_match.group(2)}", "aircraft_type": "Unknown", "count": 0, "details": []}
            continue
        if current_event:
            line_lower = line.lower()
            types = []
            if 'fighter' in line_lower or '主戰' in line: types.append('主戰機 (Fighter)')
            if 'support' in line_lower or '輔戰' in line: types.append('輔戰機 (Support)')
            if 'uav' in line_lower or '無人' in line: types.append('無人機 (UAV)')
            if 'helicopter' in line_lower or '直升' in line: types.append('直升機 (Helicopter)')
            if 'bomber' in line_lower or '轟炸' in line: types.append('轟炸機 (Bomber)')
            for t in types:
                if current_event['aircraft_type'] == "Unknown": current_event['aircraft_type'] = t
                elif t not in current_event['aircraft_type']: current_event['aircraft_type'] += f", {t}"
            clean_line = re.sub(r'[^\w\s\(\)]', '', line)
            count_match = re.search(r'(\d+)\s*(?:架次|架|sorties|sortie)', line)
            if not count_match: count_match = re.search(r'(?:計|of)\s*(\d+)', line)
            if count_match and current_event['count'] == 0: current_event['count'] = int(count_match.group(1))
            if '中線' in line or 'median line' in line_lower:
                if "逾越中線 (Crossed Median Line)" not in current_event['details']: current_event['details'].append("逾越中線 (Crossed Median Line)")
            if '西南' in line or 'sw' in line_lower or 'southwest' in line_lower:
                 if "進入西南空域 (Entered SW ADIZ)" not in current_event['details']: current_event['details'].append("進入西南空域 (Entered SW ADIZ)")
            if '東部' in line or 'east' in line_lower:
                 if "進入東部空域 (Entered East ADIZ)" not in current_event['details']: current_event['details'].append("進入東部空域 (Entered East ADIZ)")
            if '北部' in line or 'north' in line_lower:
                 if "進入北部空域 (Entered North ADIZ)" not in current_event['details']: current_event['details'].append("進入北部空域 (Entered North ADIZ)")
    if current_event: events.append(current_event)
    return events

def process_image(url, date_str):
    img_filename = None
    ocr_events = []
    if not url: return None, []
    try:
        img_data = None
        ext = ".jpg"
        if url.startswith('data:image'):
            try:
                header, encoded = url.split(',', 1)
                if "png" in header: ext = ".png"
                img_data = base64.b64decode(encoded)
            except: pass
        else:
            if not url.startswith('http'): url = BASE_URL + ('/' + url if not url.startswith('/') else url)
            try:
                resp = requests.get(url, headers=HEADERS, timeout=15, verify=False)
                if resp.status_code == 200:
                    img_data = resp.content
                    if url.lower().endswith('.png'): ext = ".png"
            except: pass
        if not img_data: return None, []
        img_filename = f"{date_str}{ext}"
        img_path = os.path.join(IMAGE_DIR, img_filename)
        with open(img_path, 'wb') as f: f.write(img_data)
        if TESSERACT_AVAILABLE:
            try:
                with Image.open(img_path) as img:
                    width, height = img.size
                    crop_img = img.crop((0, height * 0.16, width * 0.45, height * 0.50))
                    crop_img = crop_img.convert('L') 
                    try: text = pytesseract.image_to_string(crop_img, lang='chi_tra+eng')
                    except: text = pytesseract.image_to_string(crop_img, lang='eng')
                    raw_lines = [l.strip() for l in text.split('\n') if l.strip()]
                    ocr_events = parse_ocr_lines(raw_lines)
            except Exception as e: print(f"OCR Error: {e}")
        return img_filename, ocr_events
    except Exception as e: return None, []

def process_new_item(item):
    link = item['link']
    date_str = item['date'] 
    try:
        resp = requests.get(link, headers=HEADERS, timeout=10, verify=False)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
    except: return None
    content_div = soup.find('div', class_='maincontent')
    raw_text = content_div.get_text(separator='\n', strip=True) if content_div else ""
    lines = raw_text.split('\n')
    activity_text_lines = []
    capture = False
    for line in lines:
        if "活動動態" in line:
            capture = True
            if "：" in line:
                parts = line.split("：", 1)
                if len(parts) > 1 and parts[1].strip(): activity_text_lines.append(parts[1].strip())
            elif ":" in line:
                parts = line.split(":", 1)
                if len(parts) > 1 and parts[1].strip(): activity_text_lines.append(parts[1].strip())
            continue
        if capture and line.strip(): activity_text_lines.append(line.strip())
    final_text = "\n".join(activity_text_lines) if activity_text_lines else raw_text
    stats = analyze_text_content(final_text)
    img_url = None
    if content_div:
        images = content_div.find_all('img')
        for img in images:
            src = img.get('src')
            if src and ('jpg' in src.lower() or 'png' in src.lower() or 'data:image' in src):
                img_url = src
                break
    act_date = get_activity_date(date_str)
    img_filename, events = process_image(img_url, act_date)
    record = {
        "activity_date": act_date,
        "publish_date": date_str,
        "link": link,
        "aircraft_total": stats["aircraft_total"],
        "aircraft_crossing": stats["aircraft_crossing"],
        "vessels_total": stats["vessels_total"],
        "official_ships_total": stats["official_ships_total"],
        "balloons_total": stats["balloons_total"],
        "original_text": final_text,
        "events": events,
        "image_file": img_filename
    }
    print(f"Processed: {act_date} - {stats['aircraft_total']} Aircraft")
    return record

# --- Supabase Logic ---
def get_existing_dates():
    try:
        url = f"{SUPABASE_URL}/rest/v1/pla_activity?select=publish_date"
        resp = requests.get(url, headers=SUPABASE_HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {item['publish_date'] for item in data if item.get('publish_date')}
        else: return set()
    except: return set()

def insert_relational_record(record):
    main_payload = {
        "activity_date": record['activity_date'],
        "publish_date": record['publish_date'],
        "link": record['link'],
        "aircraft_total": record['aircraft_total'],
        "aircraft_crossing": record['aircraft_crossing'],
        "vessels_total": record['vessels_total'],
        "official_ships_total": record['official_ships_total'],
        "balloons_total": record['balloons_total'],
        "original_text": record['original_text'],
        "image_file": record['image_file']
    }
    try:
        url_main = f"{SUPABASE_URL}/rest/v1/pla_activity"
        resp = requests.post(url_main, headers=SUPABASE_HEADERS, json=main_payload)
        
        if resp.status_code not in [200, 201]:
            print(f"Error inserting {record['activity_date']}: {resp.text}")
            return

        inserted_data = resp.json()
        if not inserted_data: return
        activity_id = inserted_data[0]['id']

        events = record.get('events', [])
        if events:
            event_payloads = []
            for evt in events:
                event_payloads.append({
                    "activity_id": activity_id,
                    "activity_date": record['activity_date'], # Redundancy
                    "link": record['link'],                   # Redundancy
                    "time_range": evt.get('time'),
                    "aircraft_type": evt.get('aircraft_type'),
                    "count": evt.get('count', 0),
                    "details": evt.get('details', [])
                })
            
            url_events = f"{SUPABASE_URL}/rest/v1/pla_flight_events"
            requests.post(url_events, headers=SUPABASE_HEADERS, json=event_payloads)
            
        print(f"Successfully uploaded: {record['activity_date']}")
    except Exception as e: print(f"Exception during upload: {e}")

# --- Main ---
def update_database():
    print("=== Starting PLA Activity Update (Relational V2) ===")
    existing_dates = get_existing_dates()
    print(f"Loaded {len(existing_dates)} records from Supabase.")

    new_items_to_process = []
    page = 1
    stop_scraping = False

    while not stop_scraping:
        url = LIST_URL_TEMPLATE.format(page)
        print(f"Scanning page {page}...")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10, verify=False)
            if resp.status_code != 200: break
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.find_all('a', class_='news_list')
            if not items: break
            
            for item in items:
                date_tag = item.find('h5', class_='date')
                if not date_tag: continue
                roc_date = date_tag.get_text(strip=True)
                ad_date = roc_to_ad(roc_date)
                if not ad_date: continue
                if ad_date in existing_dates:
                    stop_scraping = True
                    continue 
                link = item.get('href')
                if link and not link.startswith('http'): link = BASE_URL + '/' + link.lstrip('/')
                new_items_to_process.append({'date': ad_date, 'link': link})
        except Exception as e: print(f"Error scanning list: {e}")
        break
        if stop_scraping: break
        page += 1
        time.sleep(1)

    if not new_items_to_process:
        print("No new updates found.")
        return

    print(f"Found {len(new_items_to_process)} new updates. Processing...")
    
    new_records = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_new_item, item): item for item in new_items_to_process}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: new_records.append(res)

    if new_records:
        new_records.sort(key=lambda x: x['activity_date'], reverse=False)
        for rec in new_records:
            insert_relational_record(rec)
    else:
        print("No valid records extracted.")

if __name__ == "__main__":
    update_database()