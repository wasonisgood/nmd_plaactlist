import json
import requests
import datetime
import os
from datetime import timedelta

SUPABASE_URL = "https://abjxpbtcseagrfwcehbo.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFianhwYnRjc2VhZ3Jmd2NlaGJvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY4Mzc0NzUsImV4cCI6MjA4MjQxMzQ3NX0.IMLgS1jTBS82J0BER2I_CROCJn_7DtMoPIbyRCSpC9s"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation" 
}

def migrate():
    input_file = "archive/merged_pla_data.json"
    if not os.path.exists(input_file):
        input_file = "merged_pla_data.json"

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find {input_file}")
        return

    print(f"Loaded {len(data)} records. Starting migration...")

    success_count = 0
    
    for index, item in enumerate(data):
        # Ensure dates
        if 'publish_date' not in item and 'activity_date' in item:
            try:
                act_dt = datetime.datetime.strptime(item['activity_date'], '%Y-%m-%d')
                pub_dt = act_dt + timedelta(days=1)
                item['publish_date'] = pub_dt.strftime('%Y-%m-%d')
            except:
                item['publish_date'] = None

        main_record = {
            "activity_date": item.get('activity_date'),
            "publish_date": item.get('publish_date'),
            "link": item.get('link'),
            "aircraft_total": item.get('aircraft_total', 0),
            "aircraft_crossing": item.get('aircraft_crossing', 0),
            "vessels_total": item.get('vessels_total', 0),
            "official_ships_total": item.get('official_ships_total', 0),
            "balloons_total": item.get('balloons_total', 0),
            "original_text": item.get('original_text', ""),
            "image_file": item.get('image_file')
        }

        try:
            # 1. Insert Main Record
            url_main = f"{SUPABASE_URL}/rest/v1/pla_activity"
            resp_main = requests.post(url_main, headers=HEADERS, json=main_record)
            
            if resp_main.status_code not in [200, 201]:
                # 409 usually means duplicate key (date exists), try to skip or log
                if resp_main.status_code == 409:
                    print(f"Skipping duplicate date: {item.get('activity_date')}")
                else:
                    print(f"Failed to insert main {item.get('activity_date')}: {resp_main.text}")
                continue
            
            # 2. Get the new ID from response to create relationship
            inserted_data = resp_main.json()
            if not inserted_data:
                continue
                
            activity_id = inserted_data[0]['id']
            
            # 3. Prepare Linked Events (With Date and Link for easier querying)
            events = item.get('events', [])
            if events:
                event_records = []
                for evt in events:
                    event_records.append({
                        "activity_id": activity_id,         # The Relationship Key
                        "activity_date": item.get('activity_date'), # Redundant but useful
                        "link": item.get('link'),           # Redundant but useful
                        "time_range": evt.get('time'),
                        "aircraft_type": evt.get('aircraft_type'),
                        "count": evt.get('count', 0),
                        "details": evt.get('details', [])
                    })
                
                # 4. Insert Events
                url_events = f"{SUPABASE_URL}/rest/v1/pla_flight_events"
                resp_events = requests.post(url_events, headers=HEADERS, json=event_records)
                
                if resp_events.status_code not in [200, 201]:
                    print(f"  Warning: Events failed for {item.get('activity_date')}: {resp_events.text}")
            
            success_count += 1
            if success_count % 10 == 0:
                print(f"Processed {success_count} records...")

        except Exception as e:
            print(f"Exception at record {index}: {e}")

    print(f"Migration complete. Uploaded {success_count} records.")

if __name__ == "__main__":
    migrate()
