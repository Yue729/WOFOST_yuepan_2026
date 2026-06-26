"""
Combine all crop_registration_extra_*.xlsx files from each farm folder
into a single Excel file with all records.

Output: /Users/panyue/Desktop/final_data/1_crop_management_data/crop_registration_extra_combined.xlsx
"""

from pathlib import Path
import pandas as pd

CROP_MANAGEMENT_DIR = Path("/Users/panyue/Desktop/final_data/1_crop_management_data")
OUTPUT_FILE = CROP_MANAGEMENT_DIR / "crop_registration_extra_combined.xlsx"


def main():
    files = sorted(CROP_MANAGEMENT_DIR.rglob("crop_registration_extra_*.xlsx"))
    print(f"Found {len(files)} crop_registration_extra files.")

    frames = []
    for f in files:
        farm_id = f.stem.replace("crop_registration_extra_", "")
        try:
            df = pd.read_excel(f)
            df.columns = df.columns.astype(str).str.strip()
            df.insert(0, "source_farm", farm_id)
            frames.append(df)
            print(f"  ✓ {f.relative_to(CROP_MANAGEMENT_DIR)}  ({len(df)} rows)")
        except Exception as e:
            print(f"  ✗ {f.name}: {e}")

    if not frames:
        print("No files loaded. Exiting.")
        return

    combined = pd.concat(frames, ignore_index=True)
    print(f"\nTotal rows combined: {len(combined)}")
    print(f"Columns: {combined.columns.tolist()}")

    # Sort by farm then field then year for readability
    sort_cols = [c for c in ["ID_farm", "ID_field", "year"] if c in combined.columns]
    if sort_cols:
        combined = combined.sort_values(sort_cols).reset_index(drop=True)

    combined.to_excel(OUTPUT_FILE, index=False)
    print(f"\n✓ Saved combined file: {OUTPUT_FILE}")
    print(f"  {len(combined)} rows × {len(combined.columns)} columns")


if __name__ == "__main__":
    main()
