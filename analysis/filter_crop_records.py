"""
Filter combined crop records to keep only specified crops:
- Potato (any type: Ware, Seed, Starch)
- Barley (any type: Winter, Spring)
- Onion (any type: Seed, Sets)
- Beet (any type: Sugar Beet)
- Wheat (any type: Winter, Spring)

This filters based on the "crop" column name, case-insensitive.
"""

import pandas as pd
from pathlib import Path

# Configuration
RAW_DATA_PATH = Path("/Users/panyue/Desktop/final_data")
INPUT_FILE = RAW_DATA_PATH / "combined_crop_records.xlsx"
OUTPUT_EXCEL = RAW_DATA_PATH / "combined_crop_records_filtered.xlsx"
OUTPUT_CSV = RAW_DATA_PATH / "combined_crop_records_filtered.csv"

# Keywords to search for in crop names (case-insensitive)
CROP_KEYWORDS = ["potato", "barley", "onion", "beet", "wheat"]

def filter_crop_records():
    """
    Filter combined crop records to keep only specified crops.
    """
    
    print("="*80)
    print("FILTERING CROP RECORDS")
    print("="*80)
    print(f"\nReading from: {INPUT_FILE.name}\n")
    
    # Read the combined file
    try:
        combined_df = pd.read_excel(INPUT_FILE)
    except FileNotFoundError:
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        return None
    
    print(f"Total records before filtering: {len(combined_df)}")
    
    # Show original crop distribution
    print(f"\nOriginal crop distribution:")
    if 'crop' in combined_df.columns:
        original_crops = combined_df['crop'].value_counts()
        for crop, count in original_crops.items():
            print(f"  - {crop}: {count}")
    
    # Create a mask for rows containing any of the keywords
    if 'crop' not in combined_df.columns:
        print("ERROR: 'crop' column not found in the dataframe!")
        return None
    
    # Convert crop names to lowercase for matching
    crop_lower = combined_df['crop'].str.lower()
    
    # Create mask for each keyword
    mask = crop_lower.str.contains('|'.join(CROP_KEYWORDS), case=False, na=False)
    
    # Filter the dataframe
    filtered_df = combined_df[mask].copy()
    
    print(f"\nFiltering for crops containing: {', '.join(CROP_KEYWORDS)}")
    print(f"(Case-insensitive, matches any part of crop name)")
    
    # Reset index
    filtered_df = filtered_df.reset_index(drop=True)
    
    print(f"\nTotal records after filtering: {len(filtered_df)}")
    print(f"Records removed: {len(combined_df) - len(filtered_df)}")
    
    # Show filtered crop distribution
    print(f"\nFiltered crop distribution:")
    if 'crop' in filtered_df.columns:
        filtered_crops = filtered_df['crop'].value_counts()
        for crop, count in filtered_crops.items():
            print(f"  - {crop}: {count}")
    
    print(f"\n" + "="*80)
    print("DATA SUMMARY - FILTERED")
    print("="*80)
    
    print(f"\nColumns in filtered file:")
    for col in filtered_df.columns:
        print(f"  - {col}: {filtered_df[col].dtype}")
    
    print(f"\nSample data (first 5 rows):")
    print(filtered_df.head())
    
    print(f"\nData summary:")
    print(f"  Unique ID_fields: {filtered_df['ID_field'].nunique() if 'ID_field' in filtered_df.columns else 'N/A'}")
    print(f"  Unique ID_farms: {filtered_df['ID_farm'].nunique() if 'ID_farm' in filtered_df.columns else 'N/A'}")
    print(f"  Year range: {filtered_df['year'].min() if 'year' in filtered_df.columns else 'N/A'} - {filtered_df['year'].max() if 'year' in filtered_df.columns else 'N/A'}")
    print(f"  Unique crops: {filtered_df['crop'].nunique() if 'crop' in filtered_df.columns else 'N/A'}")
    
    # Save to Excel
    print(f"\nSaving to {OUTPUT_EXCEL.name}...")
    filtered_df.to_excel(OUTPUT_EXCEL, index=False, engine='openpyxl')
    print(f"  ✓ Saved: {OUTPUT_EXCEL}")
    
    # Save to CSV
    print(f"\nSaving to {OUTPUT_CSV.name}...")
    filtered_df.to_csv(OUTPUT_CSV, index=False)
    print(f"  ✓ Saved: {OUTPUT_CSV}")
    
    print(f"\n" + "="*80)
    print("FILTERING COMPLETE")
    print("="*80)
    
    return filtered_df

if __name__ == "__main__":
    filtered_df = filter_crop_records()
