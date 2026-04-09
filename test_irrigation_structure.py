"""
Test script to verify irrigation YAML structure is correctly created
"""
import yaml
import pandas as pd
from pathlib import Path

# Test the irrigation functions
extra_files = list(Path("/Users/panyue/Desktop/final_data/1_crop_management_data").rglob("crop_registration_extra_*.xlsx"))
basic_files = list(Path("/Users/panyue/Desktop/final_data/1_crop_management_data").rglob("crop_registration_basic_*.xlsx"))

print(f"Found {len(extra_files)} extra files")
print(f"Found {len(basic_files)} basic files")

# Load first extra file to see structure
if extra_files:
    extra_df = pd.read_excel(extra_files[0])
    print("\nExtra file columns:", extra_df.columns.tolist())
    print("\nFirst 5 rows:")
    print(extra_df[['ID_all', 'ID_field', 'irrigation_main_crop']].head())
    
    # Count irrigated vs non-irrigated
    irrigated = (extra_df['irrigation_main_crop'] == 'yes').sum()
    non_irrigated = (extra_df['irrigation_main_crop'] == 'no').sum()
    print(f"\nIrrigated: {irrigated}, Non-irrigated: {non_irrigated}")

# Load first basic file
if basic_files:
    basic_df = pd.read_excel(basic_files[0])
    print("\n\nBasic file columns:", basic_df.columns.tolist())
    print("First 5 rows:")
    print(basic_df[['ID_all', 'ID_field', 'crop']].head())

# Create example YAML with irrigation
example_yaml = {
    "AgroManagement": [
        {
            "2023-05-01": {
                "CropCalendar": {
                    "crop_name": "wheat",
                    "variety_name": "Winter_wheat_101",
                    "crop_start_date": "2023-05-01",
                    "crop_start_type": "sowing",
                    "crop_end_date": "2023-08-15",
                    "crop_end_type": "harvest",
                    "max_duration": 365
                },
                "TimedEvents": {},
                "StateEvents": [
                    {
                        "event_signal": "irrigate",
                        "event_state": "SM",
                        "zero_condition": "falling",
                        "name": "Soil moisture driven irrigation scheduling",
                        "comment": "Irrigation applied when soil moisture reaches wilting point (20mm water)",
                        "events_table": [
                            {
                                0.05: {"amount": 2.0, "efficiency": 0.8}
                            }
                        ]
                    }
                ]
            }
        }
    ],
    "Version": "1.0"
}

print("\n\nExample YAML with irrigation StateEvent:")
print(yaml.dump(example_yaml, default_flow_style=False, sort_keys=False))

print("\n✓ Irrigation structure test complete!")
