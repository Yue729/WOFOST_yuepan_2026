#!/usr/bin/env python3
"""
Script to update irrigation scheme from wilting point detection to
fixed-interval irrigation (every 15 days, 20mm) from crop start date to 09-30.
"""

import yaml
from pathlib import Path
from datetime import datetime, timedelta


def generate_timed_irrigation_events(crop_start_date, end_date_str):
    """
    Generate timed irrigation events every 15 days from crop_start_date to 09-30.
    
    Parameters:
    - crop_start_date: datetime object or string (YYYY-MM-DD)
    - end_date_str: string or datetime object for the end date (09-30 of the year)
    
    Returns:
    - List of irrigation event dictionaries for TimedEvents
    """
    
    if isinstance(crop_start_date, str):
        crop_start_date = datetime.strptime(crop_start_date, "%Y-%m-%d").date()
    elif isinstance(crop_start_date, datetime):
        crop_start_date = crop_start_date.date()
    
    # Parse end date (should be 09-30 of the crop start year)
    year = crop_start_date.year
    cutoff_date = datetime(year, 9, 30).date()
    
    # Generate irrigation dates every 15 days
    irrigation_dates = []
    current_date = crop_start_date
    
    while current_date <= cutoff_date:
        irrigation_dates.append(current_date)
        current_date += timedelta(days=15)
    
    # Create TimedEvents structure
    timed_events = []
    for irrig_date in irrigation_dates:
        event = {
            str(irrig_date): {
                "event_signal": "irrigate",
                "amount": 20.0,
                "efficiency": 0.8
            }
        }
        timed_events.append(event)
    
    return timed_events


def update_agro_yaml_irrigation(file_path):
    """
    Update a single agro YAML file with the new irrigation scheme.
    """
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    if not data or "AgroManagement" not in data:
        print(f"Skipped {file_path.name}: Invalid structure")
        return False
    
    agro_management = data["AgroManagement"]
    changes_made = 0
    
    for entry in agro_management:
        for date_key, campaign_data in entry.items():
            # Skip empty campaigns (those with null values)
            if campaign_data is None:
                continue
            
            crop_calendar = campaign_data.get("CropCalendar")
            if crop_calendar is None:
                continue
            
            crop_start_date = crop_calendar.get("crop_start_date")
            
            # Generate new timed irrigation events
            new_timed_events = generate_timed_irrigation_events(
                crop_start_date,
                "09-30"
            )
            
            # Update the campaign with new irrigation scheme
            campaign_data["StateEvents"] = None  # Remove state-based events
            campaign_data["TimedEvents"] = new_timed_events  # Add timed events
            
            changes_made += 1
    
    # Save the updated YAML file
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)
    
    if changes_made > 0:
        print(f"✓ Updated {file_path.name}: {changes_made} campaigns modified")
        return True
    else:
        print(f"- Skipped {file_path.name}: No campaigns to modify")
        return False


def main():
    """Main function to update all agro YAML files."""
    
    agro_dir = Path("/Users/panyue/PycharmProjects/wofost_example_test/input/agro")
    
    print("="*80)
    print("UPDATING IRRIGATION SCHEME IN AGRO YAML FILES")
    print("="*80)
    print("Scheme: Fixed-interval irrigation every 15 days, 20mm")
    print("Period: Crop start date to 09-30 of the year\n")
    
    updated_count = 0
    skipped_count = 0
    
    for yaml_file in sorted(agro_dir.glob("agro_*.yaml")):
        try:
            if update_agro_yaml_irrigation(yaml_file):
                updated_count += 1
            else:
                skipped_count += 1
        except Exception as e:
            print(f"✗ Error processing {yaml_file.name}: {e}")
            skipped_count += 1
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Updated files: {updated_count}")
    print(f"Skipped files: {skipped_count}")
    print(f"Total files processed: {updated_count + skipped_count}")


if __name__ == "__main__":
    main()
