#!/usr/bin/env python3
"""
Test script to verify irrigation data integration
"""
import yaml
from pathlib import Path

# Run a subset of the main extraction to test irrigation integration
if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    
    from main import extract_agro_management_data, YAMLCropDataProvider
    from pcse.models import Wofost81_PP
    
    # Setup
    output_dir = Path(__file__).parent / "test_output"
    output_dir.mkdir(exist_ok=True)
    
    # Load crop varieties
    crop_dict = YAMLCropDataProvider(Wofost81_PP)
    crops_varieties = crop_dict.get_crops_varieties()
    
    # Test with DR01 files
    basic_file = Path("/Users/panyue/Desktop/final_data/1_crop_management_data/DR01/crop_registration_basic_DR01.xlsx")
    extra_file = Path("/Users/panyue/Desktop/final_data/1_crop_management_data/DR01/crop_registration_extra_DR01.xlsx")
    
    print(f"Testing with:")
    print(f"  Basic: {basic_file.name}")
    print(f"  Extra: {extra_file.name}")
    print()
    
    # Extract with irrigation data
    extract_agro_management_data(basic_file, extra_file, output_dir, crops_varieties)
    
    # Display generated files
    print("\n" + "="*60)
    print("Generated YAML files with irrigation metadata:")
    print("="*60)
    
    for yaml_file in sorted(output_dir.glob("agro_*.yaml")):
        print(f"\n--- {yaml_file.name} ---")
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
        
        # Show AgroManagement entries
        if "AgroManagement" in data:
            for entry in data["AgroManagement"]:
                for date_key, date_value in entry.items():
                    if isinstance(date_value, dict):
                        crop_name = date_value.get("CropCalendar", {}).get("crop_name", "N/A")
                        irrigation = date_value.get("metadata", {}).get("irrigation", False)
                        id_all = date_value.get("metadata", {}).get("ID_all", "N/A")
                        print(f"  {date_key}: {crop_name:<15} | Irrigation: {str(irrigation):<5} | ID: {id_all}")
    
    print("\n✓ Test completed successfully!")
