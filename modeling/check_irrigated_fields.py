"""
Check which fields have irrigation scheduled in their agro YAML files.
"""

import yaml
from pathlib import Path
from collections import defaultdict

# Configuration
AGRO_DIR = Path(__file__).resolve().parent / "input" / "agro"

def check_irrigated_fields():
    """
    Scan all agro YAML files and identify which fields have irrigation events.
    """
    
    print("="*80)
    print("CHECKING IRRIGATED FIELDS FROM AGRO YAML FILES")
    print("="*80)
    
    if not AGRO_DIR.exists():
        print(f"\nERROR: Agro directory not found: {AGRO_DIR}")
        return None
    
    agro_files = sorted(AGRO_DIR.glob("agro_*.yaml"))
    print(f"\nFound {len(agro_files)} agro files\n")
    
    irrigated_fields = {}
    non_irrigated_fields = {}
    
    for agro_file in agro_files:
        field_id = agro_file.stem.replace("agro_", "")
        
        try:
            with open(agro_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data or "AgroManagement" not in data:
                print(f"  ⚠ {field_id}: Invalid structure")
                continue
            
            agro_management = data["AgroManagement"]
            
            # Check for irrigation events
            has_irrigation = False
            irrigation_events = []
            
            for entry in agro_management:
                for date_key, campaign_data in entry.items():
                    if campaign_data is None:
                        continue
                    
                    # Check TimedEvents for irrigation
                    timed_events = campaign_data.get("TimedEvents", [])
                    if timed_events:
                        for event in timed_events:
                            if event.get("event_signal") == "irrigate":
                                has_irrigation = True
                                events_table = event.get("events_table", [])
                                irrigation_events.append({
                                    "date_key": date_key,
                                    "event_signal": event.get("event_signal"),
                                    "num_events": len(events_table),
                                    "comment": event.get("comment", "")
                                })
            
            if has_irrigation:
                irrigated_fields[field_id] = irrigation_events
                print(f"  ✓ {field_id}: IRRIGATED ({len(irrigation_events)} campaigns)")
                for irr_event in irrigation_events:
                    print(f"      - {irr_event['date_key']}: {irr_event['num_events']} irrigation events")
                    if irr_event['comment']:
                        print(f"        Comment: {irr_event['comment']}")
            else:
                non_irrigated_fields[field_id] = True
                print(f"  - {field_id}: Not irrigated")
        
        except Exception as e:
            print(f"  ✗ {field_id}: ERROR - {str(e)}")
    
    print("\n" + "="*80)
    print("IRRIGATION SUMMARY")
    print("="*80)
    
    total_fields = len(agro_files)
    irrigated_count = len(irrigated_fields)
    non_irrigated_count = len(non_irrigated_fields)
    
    print(f"\nTotal fields: {total_fields}")
    print(f"Irrigated fields: {irrigated_count} ({irrigated_count/total_fields*100:.1f}%)")
    print(f"Non-irrigated fields: {non_irrigated_count} ({non_irrigated_count/total_fields*100:.1f}%)")
    
    if irrigated_fields:
        print(f"\nIrrigated fields list:")
        for field_id in sorted(irrigated_fields.keys()):
            print(f"  - {field_id}")
    
    if non_irrigated_fields:
        print(f"\nNon-irrigated fields list:")
        for field_id in sorted(non_irrigated_fields.keys()):
            print(f"  - {field_id}")
    
    # Save results to files
    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save irrigated fields list
    irrigated_list_file = output_dir / "irrigated_fields.txt"
    with open(irrigated_list_file, 'w') as f:
        f.write("IRRIGATED FIELDS\n")
        f.write("="*80 + "\n\n")
        for field_id in sorted(irrigated_fields.keys()):
            f.write(f"{field_id}\n")
    print(f"\n✓ Irrigated fields list saved: {irrigated_list_file}")
    
    # Save non-irrigated fields list
    non_irrigated_list_file = output_dir / "non_irrigated_fields.txt"
    with open(non_irrigated_list_file, 'w') as f:
        f.write("NON-IRRIGATED FIELDS\n")
        f.write("="*80 + "\n\n")
        for field_id in sorted(non_irrigated_fields.keys()):
            f.write(f"{field_id}\n")
    print(f"✓ Non-irrigated fields list saved: {non_irrigated_list_file}")
    
    # Save detailed irrigation report
    detailed_file = output_dir / "irrigation_details.txt"
    with open(detailed_file, 'w') as f:
        f.write("DETAILED IRRIGATION REPORT\n")
        f.write("="*80 + "\n\n")
        
        f.write(f"Total fields: {total_fields}\n")
        f.write(f"Irrigated fields: {irrigated_count} ({irrigated_count/total_fields*100:.1f}%)\n")
        f.write(f"Non-irrigated fields: {non_irrigated_count} ({non_irrigated_count/total_fields*100:.1f}%)\n\n")
        
        f.write("IRRIGATED FIELDS WITH DETAILS:\n")
        f.write("-"*80 + "\n\n")
        for field_id in sorted(irrigated_fields.keys()):
            f.write(f"\nField: {field_id}\n")
            for i, irr_event in enumerate(irrigated_fields[field_id], 1):
                f.write(f"  Campaign {i}:\n")
                f.write(f"    Date key: {irr_event['date_key']}\n")
                f.write(f"    Event signal: {irr_event['event_signal']}\n")
                f.write(f"    Number of irrigation events: {irr_event['num_events']}\n")
                if irr_event['comment']:
                    f.write(f"    Comment: {irr_event['comment']}\n")
    
    print(f"✓ Detailed irrigation report saved: {detailed_file}")
    
    print("\n" + "="*80)
    
    return {
        "irrigated": irrigated_fields,
        "non_irrigated": non_irrigated_fields,
        "summary": {
            "total": total_fields,
            "irrigated_count": irrigated_count,
            "non_irrigated_count": non_irrigated_count
        }
    }


if __name__ == "__main__":
    results = check_irrigated_fields()
