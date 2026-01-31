import json
import re

def parse_time(text):
    # Matches 0810-1245, 0810 - 1245, allowing for some noise at the end
    match = re.search(r'(\d{4})\s*[-~]\s*(\d{4})', text)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    return None

def parse_count(text):
    # Try to find numbers followed by specific keywords
    # Chinese: 5架次, 計5架
    # English: 5 sorties, 1 sortie
    
    # Clean noise like '5}' -> '5'
    clean_text = re.sub(r'[^\w\s\(\)]', '', text)
    
    match = re.search(r'(\d+)\s*(?:架次|架|sorties|sortie)', text)
    if match:
        return int(match.group(1))
    
    # Sometimes OCR puts number at end: 主戰機計5
    match_end = re.search(r'(?:計|of)\s*(\d+)', text)
    if match_end:
        return int(match_end.group(1))
        
    return None

def detect_aircraft_type(text):
    text = text.lower()
    if 'fighter' in text or '主戰' in text:
        return '主戰機 (Fighter)'
    if 'support' in text or '輔戰' in text:
        return '輔戰機 (Support)'
    if 'uav' in text or '無人' in text:
        return '無人機 (UAV)'
    if 'helicopter' in text or '直升' in text:
        return '直升機 (Helicopter)'
    if 'bomber' in text or '轟炸' in text:
        return '轟炸機 (Bomber)'
    return None

def detect_activity_details(text):
    details = []
    if '中線' in text or 'median line' in text.lower():
        details.append("逾越中線 (Crossed Median Line)")
    if '西南' in text or 'sw' in text.lower() or 'southwest' in text.lower():
        details.append("進入西南空域 (Entered SW ADIZ)")
    if '東部' in text or 'east' in text.lower():
        details.append("進入東部空域 (Entered East ADIZ)")
    if '北部' in text or 'north' in text.lower():
        details.append("進入北部空域 (Entered North ADIZ)")
    return details

def clean_ocr_data():
    input_file = 'ocr_results.json'
    output_file = 'ocr_cleaned.json'
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except FileNotFoundError:
        print(f"{input_file} not found.")
        return

    cleaned_data = []

    for entry in raw_data:
        date = entry.get('date')
        file = entry.get('file')
        raw_lines = entry.get('raw_text', [])
        
        events = []
        current_event = None
        
        for line in raw_lines:
            line = line.strip()
            if not line:
                continue
                
            # Skip table headers
            if line.lower() in ['activities', 'no', 'content', '內容']:
                continue

            # Check if line is a time range (Start of new event)
            time_range = parse_time(line)
            if time_range:
                # Save previous event if exists
                if current_event:
                    events.append(current_event)
                
                # Start new event
                current_event = {
                    "time": time_range,
                    "aircraft_type": "Unknown",
                    "count": 0,
                    "details": [],
                    "raw_lines": [line] # Keep track of lines used for this event
                }
                continue
            
            # If we are inside an event, analyze the line
            if current_event:
                current_event['raw_lines'].append(line)
                
                # Aircraft Type
                ac_type = detect_aircraft_type(line)
                if ac_type:
                    # If we already have a type (e.g., Fighter), and find another (e.g., UAV), append it
                    if current_event['aircraft_type'] == "Unknown":
                        current_event['aircraft_type'] = ac_type
                    elif ac_type not in current_event['aircraft_type']:
                        current_event['aircraft_type'] += f", {ac_type}"
                
                # Count
                count = parse_count(line)
                if count is not None:
                    # Only update if current is 0 or find a larger number which usually implies the total for that group
                    if current_event['count'] == 0:
                        current_event['count'] = count
                    else:
                        # Sometimes lines repeat counts "5 sorties", "5架次". Don't sum, just take max or keep logic simple.
                        # Usually the first number found after Type is reliable.
                        pass
                        
                # Details
                dets = detect_activity_details(line)
                for d in dets:
                    if d not in current_event['details']:
                        current_event['details'].append(d)

        # Append the last event
        if current_event:
            events.append(current_event)
            
        cleaned_data.append({
            "date": date,
            "file": file,
            "total_events": len(events),
            "events": events
        })

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=4)
        
    print(f"Cleaning complete. Processed {len(cleaned_data)} records into {output_file}.")

if __name__ == "__main__":
    clean_ocr_data()
