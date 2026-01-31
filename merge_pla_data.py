import json

def merge_data():
    file_analysis = 'pla_analysis.json'
    file_ocr = 'ocr_cleaned.json'
    output_file = 'merged_pla_data.json'

    # Load data
    try:
        with open(file_analysis, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        with open(file_ocr, 'r', encoding='utf-8') as f:
            ocr_data = json.load(f)
    except FileNotFoundError as e:
        print(f"Error loading files: {e}")
        return

    # Create a lookup dictionary for OCR data based on date
    # ocr_cleaned.json uses 'date', pla_analysis.json uses 'activity_date'
    ocr_map = {item['date']: item for item in ocr_data}

    merged_list = []

    for entry in analysis_data:
        date_key = entry.get('activity_date')
        
        # Create a new merged entry starting with the analysis data
        merged_entry = entry.copy()
        
        # Find corresponding OCR details
        if date_key in ocr_map:
            ocr_entry = ocr_map[date_key]
            
            # Get events and remove 'raw_lines'
            clean_events = []
            if 'events' in ocr_entry:
                for event in ocr_entry['events']:
                    # Create a copy of event to modify
                    clean_event = event.copy()
                    if 'raw_lines' in clean_event:
                        del clean_event['raw_lines']
                    clean_events.append(clean_event)
            
            merged_entry['events'] = clean_events
            # Optionally carry over the file name if useful
            if 'file' in ocr_entry:
                merged_entry['image_file'] = ocr_entry['file']
        else:
            merged_entry['events'] = []
            merged_entry['image_file'] = None

        merged_list.append(merged_entry)

    # Save merged data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_list, f, ensure_ascii=False, indent=4)

    print(f"Merge complete. Saved {len(merged_list)} records to {output_file}.")

if __name__ == "__main__":
    merge_data()
