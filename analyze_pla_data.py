import json
import re

def extract_numbers(text):
    data = {
        "aircraft_total": 0,
        "aircraft_crossing": 0,
        "vessels_total": 0,
        "official_ships_total": 0,
        "balloons_total": 0,
        "details": text  # Keep original text for reference or further debugging if needed
    }
    
    # Extract Total Aircraft
    # Pattern: 共機 X 架次
    aircraft_match = re.search(r'共機(\d+)架次', text)
    if aircraft_match:
        data["aircraft_total"] = int(aircraft_match.group(1))
    
    # Extract Aircraft Crossing Median Line / Entering ADIZ
    # Pattern: usually inside parentheses (逾越... X 架次)
    # or sometimes just described if no parentheses.
    # We look for the number before "架次" that is NOT the "共機" one if it appears later, 
    # but typically it's inside (...) following the total.
    
    # Let's find content inside parentheses first
    paren_match = re.search(r'\((.*?)\)', text)
    if paren_match:
        inner_text = paren_match.group(1)
        # Look for number of sorties inside the parenthesis
        # e.g., "逾越中線...19架次"
        crossing_match = re.search(r'(\d+)架次', inner_text)
        if crossing_match:
            data["aircraft_crossing"] = int(crossing_match.group(1))
    
    # Extract Total Vessels
    # Pattern: 共艦 X 艘
    vessels_match = re.search(r'共艦(\d+)艘', text)
    if vessels_match:
        data["vessels_total"] = int(vessels_match.group(1))
        
    # Extract Official Ships
    # Pattern: 公務船 X 艘
    official_match = re.search(r'公務船(\d+)艘', text)
    if official_match:
        data["official_ships_total"] = int(official_match.group(1))

    # Extract Balloons
    # Pattern: 空飄氣球... X 顆 or 枚
    # Examples: "中共空飄氣球計偵獲1顆", "偵獲空飄氣球1枚"
    balloon_match = re.search(r'空飄氣球.*?(\d+)[顆枚]', text)
    if balloon_match:
        data["balloons_total"] = int(balloon_match.group(1))

    return data

def main():
    try:
        with open('pla_details.json', 'r', encoding='utf-8') as f:
            source_data = json.load(f)
    except FileNotFoundError:
        print("pla_details.json not found.")
        return

    analyzed_list = []
    
    for item in source_data:
        content = item.get('content', '')
        extracted = extract_numbers(content)
        
        new_entry = {
            "activity_date": item.get('activity_date'),
            "link": item.get('link'),
            "aircraft_total": extracted["aircraft_total"],
            "aircraft_crossing": extracted["aircraft_crossing"],
            "vessels_total": extracted["vessels_total"],
            "official_ships_total": extracted["official_ships_total"],
            "balloons_total": extracted["balloons_total"],
            "original_text": extracted["details"]
        }
        analyzed_list.append(new_entry)

    # Save to new JSON
    with open('pla_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(analyzed_list, f, ensure_ascii=False, indent=4)
        
    print(f"Analysis complete. Saved {len(analyzed_list)} records to pla_analysis.json")

if __name__ == "__main__":
    main()
