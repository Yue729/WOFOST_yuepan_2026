"""
Merge all crop_registration_basic_*.xlsx files from field-specific folders
into a single combined Excel/CSV file, then combine with WOFOST model outputs
(PP and WLP yields) based on field_id and year.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime


RAW_DATA_PATH = Path("/Users/panyue/Desktop/final_data")
CROP_MANAGEMENT_DIR = RAW_DATA_PATH / "1_crop_management_data"
MEASURED_DATA_PATH = RAW_DATA_PATH / "2_yield_data" / "yield_data_2025"

# WOFOST model outputs
PROJECT_ROOT = Path(__file__).resolve().parent
PP_RESULTS_FILE = PROJECT_ROOT / "output" / "model_results" / "WOFOST73_PP_results.xlsx"
WLP_RESULTS_FILE = PROJECT_ROOT / "output" / "model_results" / "WOFOST73_WLP_CWB_results.xlsx"

OUTPUT_EXCEL = RAW_DATA_PATH / "combined_crop_records.xlsx"
OUTPUT_CSV = RAW_DATA_PATH / "combined_crop_records.csv"

# Output with WOFOST yields
OUTPUT_COMBINED_EXCEL = RAW_DATA_PATH / "combined_crop_records_with_wofost.xlsx"
OUTPUT_COMBINED_CSV = RAW_DATA_PATH / "combined_crop_records_with_wofost.csv"


EXPECTED_COLUMNS = [
    "ID_all",
    "ID_farm", 
    "ID_field",
    "year",
    "crop",
    "variety",
    "yield",
    "date_planting",
    "date_harvest"
]

def merge_crop_registration_files():
    """
    Merge all crop_registration_basic_*.xlsx files from field folders
    into a single DataFrame.
    """
    
    print("="*80)
    print("MERGING CROP REGISTRATION FILES FROM ALL FIELDS")
    print("="*80)
    print(f"\nSearching in: {CROP_MANAGEMENT_DIR}\n")
    
    # Find all crop_registration_basic_*.xlsx files recursively
    crop_files = list(CROP_MANAGEMENT_DIR.rglob("crop_registration_basic_*.xlsx"))
    print(f"Found {len(crop_files)} crop registration files\n")
    
    if not crop_files:
        print("ERROR: No crop_registration_basic_*.xlsx files found!")
        return None
    
    all_data = []
    failed_files = []
    
    for crop_file in sorted(crop_files):
        relative_path = crop_file.relative_to(CROP_MANAGEMENT_DIR)
        field_folder = crop_file.parent.name
        
        try:
        
            df = pd.read_excel(crop_file)
            
           
            df.columns = df.columns.astype(str).str.strip()
            
        
            missing_cols = [col for col in EXPECTED_COLUMNS if col not in df.columns]
            if missing_cols:
                print(f"  ⚠ {relative_path}: Missing columns {missing_cols}")
                # Continue anyway and select available columns
                available_cols = [col for col in EXPECTED_COLUMNS if col in df.columns]
                df = df[available_cols]
            else:
                df = df[EXPECTED_COLUMNS]
            
            # Remove rows with all NaN values
            df = df.dropna(how='all')
            
            # Remove rows where ID_field is NaN
            if "ID_field" in df.columns:
                df = df.dropna(subset=["ID_field"])
            
            if len(df) > 0:
                all_data.append(df)
                print(f"  ✓ {relative_path}: {len(df)} records")
            else:
                print(f"  - {relative_path}: 0 records (skipped)")
                
        except Exception as e:
            print(f"  ✗ {relative_path}: ERROR - {str(e)}")
            failed_files.append((relative_path, str(e)))
    
    if not all_data:
        print("\nERROR: No data was successfully read from any files!")
        return None
    
    # Combine all dataframes
    print(f"\nCombining {len(all_data)} files...")
    combined_df = pd.concat(all_data, ignore_index=True)
    
    print(f"\n" + "="*80)
    print("MERGE SUMMARY")
    print("="*80)
    print(f"Total files processed: {len(crop_files)}")
    print(f"Files successfully read: {len(all_data)}")
    print(f"Files with errors: {len(failed_files)}")
    print(f"\nTotal records in combined file: {len(combined_df)}")
    
    # Show data types and sample
    print(f"\nColumns in combined file:")
    for col in combined_df.columns:
        print(f"  - {col}: {combined_df[col].dtype}")
    
    print(f"\nSample data (first 5 rows):")
    print(combined_df.head())
    
    print(f"\nData summary:")
    print(f"  Unique ID_fields: {combined_df['ID_field'].nunique() if 'ID_field' in combined_df.columns else 'N/A'}")
    print(f"  Unique ID_farms: {combined_df['ID_farm'].nunique() if 'ID_farm' in combined_df.columns else 'N/A'}")
    print(f"  Year range: {combined_df['year'].min() if 'year' in combined_df.columns else 'N/A'} - {combined_df['year'].max() if 'year' in combined_df.columns else 'N/A'}")
    print(f"  Unique crops: {combined_df['crop'].nunique() if 'crop' in combined_df.columns else 'N/A'}")
    
    if len(combined_df) > 0:
        print(f"\n  Crop distribution:")
        if 'crop' in combined_df.columns:
            crop_counts = combined_df['crop'].value_counts()
            for crop, count in crop_counts.items():
                print(f"    - {crop}: {count}")
    
    # Save to Excel
    print(f"\nSaving to {OUTPUT_EXCEL.name}...")
    combined_df.to_excel(OUTPUT_EXCEL, index=False, engine='openpyxl')
    print(f"  ✓ Saved: {OUTPUT_EXCEL}")
    
    # Save to CSV
    print(f"\nSaving to {OUTPUT_CSV.name}...")
    combined_df.to_csv(OUTPUT_CSV, index=False)
    print(f"  ✓ Saved: {OUTPUT_CSV}")
    
    if failed_files:
        print(f"\n⚠ Files with errors:")
        for file_path, error in failed_files:
            print(f"  - {file_path}: {error}")
    
    print("\n" + "="*80)
    print("MERGE COMPLETE")
    print("="*80)
    
    return combined_df


def extract_wofost_yields():
    """
    Extract estimated yields from WOFOST PP and WLP results.
    Returns a DataFrame with field_id, year, crop_name, PP_yield, and WLP_yield.
    """
    
    print("\n" + "="*80)
    print("EXTRACTING WOFOST YIELDS")
    print("="*80)
    
    yields_data = []
    
    # Extract PP yields
    if PP_RESULTS_FILE.exists():
        print(f"\nReading PP results: {PP_RESULTS_FILE.name}")
        pp_df = pd.read_excel(PP_RESULTS_FILE)
        
        # Extract year from day column
        pp_df['year'] = pd.to_datetime(pp_df['day'], errors='coerce').dt.year
        
        # Get end-of-season yields (PP_TWSO in kg/ha, convert to t/ha by dividing by 1000)
        # Group by field_id and year, take the last (harvest) record
        pp_harvest = pp_df.sort_values('day').groupby(['field_id', 'year']).tail(1)[['field_id', 'year', 'crop_name', 'PP_TWSO']].copy()
        pp_harvest['PP_TWSO'] = pp_harvest['PP_TWSO'] / 1000.0  # Convert kg/ha to t/ha
        pp_harvest = pp_harvest.rename(columns={'PP_TWSO': 'PP_yield_t_ha'})
        
        print(f"  ✓ Extracted PP yields: {len(pp_harvest)} records")
        yields_data.append(pp_harvest)
    else:
        print(f"  ⚠ PP results file not found: {PP_RESULTS_FILE}")
    
    # Extract WLP yields
    if WLP_RESULTS_FILE.exists():
        print(f"\nReading WLP results: {WLP_RESULTS_FILE.name}")
        wlp_df = pd.read_excel(WLP_RESULTS_FILE)
        
        # Extract year from day column
        wlp_df['year'] = pd.to_datetime(wlp_df['day'], errors='coerce').dt.year
        
        # Get end-of-season yields (WLP_TWSO in kg/ha, convert to t/ha by dividing by 1000)
        # Group by field_id and year, take the last (harvest) record
        wlp_harvest = wlp_df.sort_values('day').groupby(['field_id', 'year']).tail(1)[['field_id', 'year', 'crop_name', 'WLP_TWSO']].copy()
        wlp_harvest['WLP_TWSO'] = wlp_harvest['WLP_TWSO'] / 1000.0  # Convert kg/ha to t/ha
        wlp_harvest = wlp_harvest.rename(columns={'WLP_TWSO': 'WLP_yield_t_ha'})
        
        print(f"  ✓ Extracted WLP yields: {len(wlp_harvest)} records")
        yields_data.append(wlp_harvest)
    else:
        print(f"  ⚠ WLP results file not found: {WLP_RESULTS_FILE}")
    
    if not yields_data:
        print("\nERROR: No WOFOST results files found!")
        return None
    
    # Merge PP and WLP yields
    if len(yields_data) == 2:
        combined_yields = yields_data[0].merge(yields_data[1], on=['field_id', 'year', 'crop_name'], how='outer')
    else:
        combined_yields = yields_data[0]
    
    print(f"\n  Combined WOFOST yields: {len(combined_yields)} records")
    return combined_yields


def combine_crop_records_with_wofost(crop_df, wofost_yields_df):
    """
    Combine crop records with WOFOST estimated yields.
    Match by field_id and year.
    Keep only rows with both PP and WLP data.
    """
    
    print("\n" + "="*80)
    print("COMBINING CROP RECORDS WITH WOFOST YIELDS")
    print("="*80)
    
    print(f"\nCrop records before merge: {len(crop_df)}")
    print(f"WOFOST yields available: {len(wofost_yields_df)}")
    
    # Rename field_id in wofost_yields to match crop records
    wofost_yields_df = wofost_yields_df.rename(columns={'field_id': 'ID_field'})
    
    # Merge on ID_field and year
    merged_df = crop_df.merge(
        wofost_yields_df,
        on=['ID_field', 'year'],
        how='left'
    )
    
    print(f"\nMerged records (before filtering): {len(merged_df)}")
    print(f"Records with PP yield: {merged_df['PP_yield_t_ha'].notna().sum()}")
    print(f"Records with WLP yield: {merged_df['WLP_yield_t_ha'].notna().sum()}")
    print(f"Records with both PP and WLP: {((merged_df['PP_yield_t_ha'].notna()) & (merged_df['WLP_yield_t_ha'].notna())).sum()}")
    
    # Keep only rows with both PP and WLP data
    filtered_df = merged_df[
        (merged_df['PP_yield_t_ha'].notna()) & 
        (merged_df['WLP_yield_t_ha'].notna())
    ].copy()
    
    print(f"\nFiltered records (with both PP and WLP): {len(filtered_df)}")
    print(f"Records removed: {len(merged_df) - len(filtered_df)}")
    
    # Calculate yield gaps
    filtered_df['actual_yield'] = filtered_df['yield']  # Measured yield
    filtered_df['gap_to_pp'] = (filtered_df['PP_yield_t_ha'] - filtered_df['actual_yield']).clip(lower=0)
    filtered_df['gap_to_wlp'] = (filtered_df['WLP_yield_t_ha'] - filtered_df['actual_yield']).clip(lower=0)
    filtered_df['water_limited_gap'] = (filtered_df['PP_yield_t_ha'] - filtered_df['WLP_yield_t_ha']).clip(lower=0)
    
    print(f"\nYield Gap Statistics:")
    print(f"  Average actual yield: {filtered_df['actual_yield'].mean():.2f} t/ha")
    print(f"  Average PP yield: {filtered_df['PP_yield_t_ha'].mean():.2f} t/ha")
    print(f"  Average WLP yield: {filtered_df['WLP_yield_t_ha'].mean():.2f} t/ha")
    print(f"  Average gap to PP: {filtered_df['gap_to_pp'].mean():.2f} t/ha")
    print(f"  Average water-limited gap: {filtered_df['water_limited_gap'].mean():.2f} t/ha")
    
    return filtered_df


if __name__ == "__main__":
    combined_df = merge_crop_registration_files()
    
    if combined_df is not None:
        # Extract WOFOST yields
        wofost_yields = extract_wofost_yields()
        
        if wofost_yields is not None:
            # Combine with WOFOST yields
            final_df = combine_crop_records_with_wofost(combined_df, wofost_yields)
            
            # Save combined file with WOFOST yields
            print(f"\n" + "="*80)
            print("SAVING COMBINED FILE WITH WOFOST YIELDS")
            print("="*80)
            
            print(f"\nSaving to {OUTPUT_COMBINED_EXCEL.name}...")
            final_df.to_excel(OUTPUT_COMBINED_EXCEL, index=False, engine='openpyxl')
            print(f"  ✓ Saved: {OUTPUT_COMBINED_EXCEL}")
            
            print(f"\nSaving to {OUTPUT_COMBINED_CSV.name}...")
            final_df.to_csv(OUTPUT_COMBINED_CSV, index=False)
            print(f"  ✓ Saved: {OUTPUT_COMBINED_CSV}")
            
            print(f"\n" + "="*80)
            print("COMBINATION COMPLETE")
            print("="*80)
