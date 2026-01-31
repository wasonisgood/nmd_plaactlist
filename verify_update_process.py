import json
import os
import subprocess
import sys

def verify_process():
    db_file = 'merged_pla_data.json'
    backup_file = 'latest_backup.json'
    updater_script = 'update_pla_data.py'

    # 1. Load DB
    if not os.path.exists(db_file):
        print(f"Error: {db_file} not found.")
        return

    with open(db_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not data:
        print("Database is empty.")
        return

    # 2. Extract & Backup Latest Record
    # Assuming sorted by date desc, so index 0 is newest
    latest_record = data[0]
    date_to_remove = latest_record.get('publish_date')
    if not date_to_remove:
         # Fallback to activity date for logging
         date_to_remove = latest_record.get('activity_date')
    
    print(f"Removing latest record: {date_to_remove} (Activity: {latest_record['activity_date']})")
    
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(latest_record, f, ensure_ascii=False, indent=4)

    # 3. Simulate "Old" DB
    old_data = data[1:]
    with open(db_file, 'w', encoding='utf-8') as f:
        json.dump(old_data, f, ensure_ascii=False, indent=4)
    
    print(f"Database rolled back. New count: {len(old_data)}")

    # 4. Run Updater
    print(f"Running {updater_script}...")
    try:
        subprocess.check_call([sys.executable, updater_script])
    except subprocess.CalledProcessError as e:
        print(f"Updater script failed: {e}")
        # Restore backup just in case
        restore_db(data, db_file)
        return

    # 5. Verify Result
    print("Verifying update result...")
    with open(db_file, 'r', encoding='utf-8') as f:
        new_data = json.load(f)

    new_latest = new_data[0]
    
    # Check if we got the record back
    # Compare activity_date
    if new_latest['activity_date'] != latest_record['activity_date']:
        print("FAIL: The latest record was not re-added.")
        print(f"Expected Activity: {latest_record['activity_date']}, Got: {new_latest['activity_date']}")
    else:
        # Compare content
        # We exclude 'image_file' comparison strictly because download might result in same content but different logic if filename handling changed? 
        # Actually filename logic is consistent.
        # But let's check key fields.
        
        match = True
        mismatches = []
        
        fields_to_check = ['activity_date', 'aircraft_total', 'vessels_total', 'original_text']
        
        for field in fields_to_check:
            if new_latest.get(field) != latest_record.get(field):
                match = False
                mismatches.append(f"{field}: Original={latest_record.get(field)} | New={new_latest.get(field)}")

        # Check events count
        if len(new_latest.get('events', [])) != len(latest_record.get('events', [])):
             match = False
             mismatches.append(f"Events Count: Original={len(latest_record.get('events', []))} | New={len(new_latest.get('events', []))}")

        if match:
            print("SUCCESS: The record was successfully re-acquired and matches the original.")
        else:
            print("WARNING: The record was re-acquired but has differences:")
            for m in mismatches:
                print(f"  - {m}")

def restore_db(full_data, path):
    print("Restoring original database...")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(full_data, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    verify_process()
