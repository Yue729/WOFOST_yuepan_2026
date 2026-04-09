#!/usr/bin/env python3
"""
IRRIGATION SYSTEM - USAGE EXAMPLES

This file demonstrates how the irrigation system works in the WOFOST pipeline.
Run this file to see irrigation data loading and YAML generation.
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

import yaml
import pandas as pd
from main import load_irrigation_data, add_irrigation_to_agro_yaml

# ============================================================================
# EXAMPLE 1: Load Irrigation Data
# ============================================================================

def example_1_load_irrigation_data():
    """Example: Load irrigation flags from crop_registration_extra files"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Loading Irrigation Data")
    print("="*70)
    
    irrigation_data = load_irrigation_data()
    
    print(f"\nTotal records with irrigation info: {len(irrigation_data)}")
    
    # Count irrigated vs non-irrigated
    irrigated = sum(1 for v in irrigation_data.values() if v)
    non_irrigated = len(irrigation_data) - irrigated
    
    print(f"Irrigated fields:     {irrigated}")
    print(f"Non-irrigated fields: {non_irrigated}")
    print(f"Percentage irrigated: {100*irrigated/len(irrigation_data):.1f}%")
    
    # Show first 10 records
    print("\nFirst 10 records:")
    for i, (id_all, is_irrigated) in enumerate(list(irrigation_data.items())[:10]):
        status = "✓ IRRIGATED" if is_irrigated else "  Non-irrigated"
        print(f"  {id_all:15} → {status}")
    
    return irrigation_data


# ============================================================================
# EXAMPLE 2: Create Sample YAML with Irrigation
# ============================================================================

def example_2_create_yaml_with_irrigation():
    """Example: Create sample agro YAML with irrigation StateEvents"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Creating YAML with Irrigation StateEvents")
    print("="*70)
    
    # Sample soil data (typical for loamy soil)
    soil_data = {
        'SM0': 0.48,      # Saturation
        'SMFCF': 0.124,   # Field capacity
        'SMW': 0.055,     # Wilting point (irrigation threshold)
    }
    
    # Sample agro YAML structure
    agro_yaml = {
        "AgroManagement": [
            {
                "2023-05-15": {
                    "CropCalendar": {
                        "crop_start_date": "2023-05-15",
                        "crop_start_type": "sowing",
                        "crop_end_date": "2023-08-30",
                        "crop_end_type": "harvest",
                        "crop_name": "wheat",
                        "variety_name": "Winter_wheat_101",
                        "max_duration": 365
                    },
                    "StateEvents": None,
                    "TimedEvents": {}
                }
            }
        ],
        "Version": "1.0"
    }
    
    print("\n📋 Original YAML (no irrigation):")
    print("StateEvents: null")
    
    # Add irrigation
    agro_irrigated = add_irrigation_to_agro_yaml(
        agro_yaml, 
        field_id="DR01_01", 
        is_irrigated=True, 
        soil_data=soil_data
    )
    
    print("\n✅ Modified YAML (with irrigation StateEvent):")
    print(yaml.dump(agro_irrigated, default_flow_style=False, sort_keys=False))
    
    print("Irrigation Configuration:")
    print(f"  • Trigger threshold (SMW): {soil_data['SMW']} (wilting point)")
    print(f"  • Water amount: 2.0 cm (20 mm)")
    print(f"  • Efficiency: 0.8 (80%)")
    print(f"  • Trigger condition: falling (when SM drops to SMW)")
    
    return agro_irrigated


# ============================================================================
# EXAMPLE 3: Irrigation Logic Explanation
# ============================================================================

def example_3_explain_irrigation_logic():
    """Example: Explain how irrigation logic works"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Irrigation Logic During WOFOST Simulation")
    print("="*70)
    
    print("""
IRRIGATION TRIGGERING MECHANISM:

1. INITIALIZATION (start of season)
   └─ PCSE calculates initial soil moisture (SM)
   └─ Loads irrigation StateEvent with threshold (SMW = 0.055)

2. DAILY SIMULATION LOOP
   ├─ Day N: SM = 0.12 (field capacity) - NO IRRIGATION
   ├─ Day N+1: SM = 0.11 - NO IRRIGATION
   ├─ Day N+2: SM = 0.10 - NO IRRIGATION
   ├─ Day N+3: SM = 0.08 - NO IRRIGATION
   ├─ Day N+4: SM = 0.065 - NO IRRIGATION
   │
   └─ Day N+5: SM = 0.054 ← THRESHOLD CROSSED ✓
      └─ PCSE detects: SM (0.054) < SMW (0.055) with FALLING condition
      └─ Broadcasts IRRIGATE signal
      └─ Water balance adds: 2.0 cm × 0.8 efficiency = 1.6 cm effective
      └─ SM jumps to ~0.09 (increased soil moisture)
      
   ├─ Day N+6: SM = 0.088 - NO IRRIGATION
   ├─ Day N+7: SM = 0.087 - NO IRRIGATION
   └─ ...cycle repeats as crop transpiration reduces SM...

3. KEY DIFFERENCES FROM TIMED IRRIGATION
   
   Timed Irrigation (fixed dates):
   ├─ Irrigation every 7 days (regardless of conditions)
   ├─ May irrigate when soil is wet → wasted water
   ├─ May miss irrigation when soil becomes dry → crop stress
   └─ Not adaptive to weather/rainfall
   
   State-Event Irrigation (soil-based, our system):
   ├─ Irrigation when soil actually reaches wilting point
   ├─ Responds to rainfall → fewer irrigations after rain
   ├─ Avoids over-irrigation → saves water and energy
   ├─ Prevents crop water stress → maintains yields
   └─ Adaptive to weather patterns ✓

4. MULTIPLE IRRIGATIONS PER SEASON
   
   Our system allows unlimited irrigation applications:
   ├─ If SM falls to SMW on Day 20 → Irrigation applied
   ├─ If SM falls to SMW again on Day 35 → Another irrigation
   ├─ Pattern repeats throughout growing season
   ├─ Frequency depends on:
   │  ├─ Rainfall patterns (more rain = fewer irrigations)
   │  ├─ Crop water demand (high demand = more frequent)
   │  ├─ Soil water holding capacity (sandy = more frequent)
   │  └─ SMW value (lower SMW = later irrigation applications)
   └─ Result: Realistic irrigation schedule that varies by year
""")


# ============================================================================
# EXAMPLE 4: Configuration Parameters
# ============================================================================

def example_4_configuration_parameters():
    """Example: Show all configurable parameters"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Irrigation Configuration Parameters")
    print("="*70)
    
    config = {
        "FIXED_PARAMETERS": {
            "water_amount_mm": 20.0,
            "water_amount_cm": 2.0,
            "efficiency": 0.8,
            "efficiency_description": "80% of water becomes available (20% loss to runoff/percolation)",
            "trigger_condition": "falling",
            "trigger_condition_description": "Apply when soil moisture DECREASES to wilting point",
            "event_signal": "irrigate",
            "event_state": "SM",
            "event_state_description": "Soil Moisture",
        },
        "FIELD_SPECIFIC_PARAMETERS": {
            "SMW": "0.04-0.08",
            "SMW_description": "Wilting point from soil data (varies by soil texture)",
            "SM0": "0.40-0.50",
            "SM0_description": "Saturation moisture (varies by soil texture)",
        },
        "WHERE_TO_MODIFY": {
            "water_amount": "add_irrigation_to_agro_yaml() function, line ~510",
            "efficiency": "add_irrigation_to_agro_yaml() function, line ~510",
            "irrigation_yes_no": "crop_registration_extra_*.xlsx, column 'irrigation_main_crop'",
        }
    }
    
    print("\n📊 FIXED PARAMETERS (apply to all fields):")
    for key, value in config["FIXED_PARAMETERS"].items():
        if key.endswith("_description"):
            print(f"     → {value}")
        else:
            print(f"  {key:30} = {value}")
    
    print("\n🌾 FIELD-SPECIFIC PARAMETERS (vary by soil type):")
    for key, value in config["FIELD_SPECIFIC_PARAMETERS"].items():
        if key.endswith("_description"):
            print(f"     → {value}")
        else:
            print(f"  {key:30} = {value}")
    
    print("\n⚙️  HOW TO MODIFY:")
    for setting, location in config["WHERE_TO_MODIFY"].items():
        print(f"  • {setting:25} → {location}")
    
    print("\n💡 ADJUSTMENT SUGGESTIONS:")
    print("""
  To apply MORE water per irrigation:
  ├─ Change: amount: 2.0 → amount: 3.0  (30mm instead of 20mm)
  └─ Effect: Fewer irrigation events, more water per event

  To be MORE conservative with water:
  ├─ Change: efficiency: 0.8 → efficiency: 0.7  (70% effective)
  └─ Effect: Irrigation still triggered at SMW but less water available

  To require MORE soil drying before irrigation:
  ├─ Use crop with lower SMW value (smaller wilting point)
  └─ Effect: Crop experiences more water stress but saves water

  To irrigate MORE FREQUENTLY:
  ├─ This cannot be directly configured
  └─ Increase with: sandy soils (lower SMW), higher-demand crops
""")


# ============================================================================
# EXAMPLE 5: Data Flow Diagram
# ============================================================================

def example_5_data_flow():
    """Example: Show complete data flow"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Complete Data Flow")
    print("="*70)
    
    print("""
WOFOST IRRIGATION PIPELINE - DATA FLOW
═════════════════════════════════════════════════════════════════════

INPUT DATA:
  📊 Desktop/final_data/
  ├── crop_registration_basic_DR01.xlsx     ← Crop, dates, varieties
  └── crop_registration_extra_DR01.xlsx     ← ✓ irrigation_main_crop column
      
STEP 1: Load Irrigation Data
  🔄 load_irrigation_data()
  ├─ Scans crop_registration_extra_*.xlsx files (40 files)
  ├─ Extracts "irrigation_main_crop" column (yes/no)
  └─ Returns: {ID_all: bool, ...}  (e.g., {"DR01_01_2023": True, ...})

STEP 2: Extract Soil Data (required for SMW values)
  🔄 extract_soil_site_data()
  ├─ Input: soil_data.xlsx
  ├─ Calculates Van Genuchten parameters
  ├─ Generates SMW values for each field
  └─ Output: input/soil/soil_DR01_01.yaml
             {SM0: 0.48, SMFCF: 0.124, SMW: 0.055, ...}

STEP 3: Extract Agro Management Data WITH Irrigation
  🔄 extract_agro_management_data(f, output_dir, crops_varieties, 
                                   irrigation_data, soil_output_dir)
  ├─ For each field:
  │  ├─ Check: is_irrigated = irrigation_data[ID_all]
  │  ├─ If TRUE:
  │  │  ├─ Load soil data to get SMW
  │  │  └─ add_irrigation_to_agro_yaml()
  │  │     └─ Adds StateEvent to agro YAML
  │  └─ If FALSE:
  │     └─ Skip irrigation StateEvent
  └─ Output: input/agro/agro_DR01_01.yaml
             {AgroManagement: [...StateEvents: [{irrigate on SM falling}]]}

STEP 4: Run WOFOST Simulations
  🔄 Wofost81_PP model execution
  ├─ Input:
  │  ├─ input/agro/agro_DR01_01.yaml (with irrigation)
  │  ├─ input/soil/soil_DR01_01.yaml (with SMW)
  │  └─ Weather data (NASA Power)
  ├─ During simulation:
  │  ├─ Daily: Calculate soil moisture (SM)
  │  ├─ Check: Does SM fall to SMW?
  │  └─ If YES: Trigger irrigation event
  │             Apply 2.0 cm water (0.8 efficiency)
  └─ Output: Crop/soil state variables over season

RESULT:
  ✓ Irrigation automatically applied during growing season
  ✓ Frequency determined by soil moisture, not fixed calendar
  ✓ Different irrigations for different field/year combinations
  ✓ Realistic simulation of irrigation practices
═════════════════════════════════════════════════════════════════════
""")


# ============================================================================
# RUN ALL EXAMPLES
# ============================================================================

if __name__ == "__main__":
    print("\n" + "🌾 "*10)
    print("WOFOST IRRIGATION SYSTEM - USAGE EXAMPLES")
    print("🌾 "*10)
    
    try:
        # Example 1: Load data
        irrigation_data = example_1_load_irrigation_data()
        
        # Example 2: Create YAML
        example_2_create_yaml_with_irrigation()
        
        # Example 3: Explain logic
        example_3_explain_irrigation_logic()
        
        # Example 4: Configuration
        example_4_configuration_parameters()
        
        # Example 5: Data flow
        example_5_data_flow()
        
        print("\n" + "="*70)
        print("✅ All examples completed successfully!")
        print("="*70)
        print("""
NEXT STEPS:

1. Review the generated YAML files:
   ls -la input/agro/*.yaml
   cat input/agro/agro_DR01_01.yaml

2. Look for irrigation StateEvents:
   grep -A 10 "irrigate" input/agro/*.yaml | head -50

3. Run WOFOST simulations:
   python main.py

4. Check simulation output for irrigation in soil water balance

For more details, see:
  - IRRIGATION_SUMMARY.md (overview)
  - IRRIGATION_IMPLEMENTATION.md (technical details)
""")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
