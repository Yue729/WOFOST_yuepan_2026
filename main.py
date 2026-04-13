from typing import Optional
import re
from pedotransfer_functions import PedotransferFunctionsWosten
import yaml
import shutil
import pandas as pd
from pedotransfer_functions import PedotransferFunctionsWosten
from van_genuchten import ClassicalSoilWaterBalanceParameterProvider
from types import SimpleNamespace
from pathlib import Path
from pcse.base import ParameterProvider
from pcse.input import YAMLCropDataProvider, NASAPowerWeatherDataProvider
from pcse.models import Wofost73_PP
from pcse.models import Wofost72_WLP_FD
from datetime import datetime




RAW_DATA_PATH = Path(r"/Users/panyue/Desktop/final_data/")
SOIL_DATA_FILE = RAW_DATA_PATH / "3_soil_data/general_soil_characteristics/general_soil_characteristics.xlsx"
CROP_MANAGEMENT_DIR = RAW_DATA_PATH / "1_crop_management_data"
LOCATION_DATA_FILE = RAW_DATA_PATH / "4_other_files/locations_data.xlsx"

GLOBAL_SITE_FILE = Path(__file__).parent.joinpath(Path("input/9_Wofost81_PP_site.yaml"))

MANAGEMENT_COLS = [
    "ID_all",
    "ID_field",
    "ID_farm",
    "year",
    "crop",
    "variety",
    "date_planting",
    "date_harvest"
]


def extract_agro_management_data(f: Path, output_dir: Path, crops_varieties: dict, irrigation_data: dict, soil_dir: Path):
    # `clean column names
    df = pd.read_excel(f)
    df.columns = df.columns.astype(str).str.strip()

    # optional: standardize common variants
    df = df.rename(columns={
        "Yield": "yield",
        "YIELD": "yield",
        "yield ": "yield",
        " date_planting": "date_planting",
        " date_harvest": "date_harvest"
    })

    df = df[MANAGEMENT_COLS].copy()

    # clean dates
    for col in ["date_planting", "date_harvest"]:
        df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
        df[col] = df[col].apply(lambda x: x.date() if pd.notna(x) else None)
    print(df)

    for field_id, group in df.groupby("ID_field"):
        agro_management = []

        for idx, row in group.iterrows():
            if pd.isna(row["crop"]):
                print(f"Skipping row {row} due to missing crop name.")
                continue
            # Use planting date as the key for AgroManagement
            planting_date = row['date_planting']
            if pd.isna(planting_date) or pd.isna(row['date_harvest']):
                print(f"Skipping row {row} due to missing planting date or harvest date.")
                continue


            normalized_crop_name = map_crop_name(row['crop'].lower().strip())

            if normalized_crop_name not in GOOD_CROP_NAMES:
                print(f"Skipping row {row} due to crop name '{normalized_crop_name}' not being in the list of good crop names.")
                continue
            available_varieties = list(crops_varieties.get(normalized_crop_name, []))

            if len(available_varieties) == 0:
                # TODO: fix me what is variety?
                raise ValueError(f"Crop '{normalized_crop_name}' not found in crop data provider.")
            
            if row['variety'] not in available_varieties:
                # Use first available variety if the provided variety is not found
                print(f"Warning: Variety '{row['variety']}' not found for crop '{normalized_crop_name}'. Using '{available_varieties[0]}'.")
                variety = available_varieties[0]
            else:
                variety = row['variety']
            
            agro_entry = {
                planting_date: {
                    "CropCalendar": {
                        "crop_start_date": row['date_planting'],
                        "crop_start_type": "sowing",
                        "crop_end_date": row['date_harvest'],
                        "crop_end_type": "harvest",
                        "crop_name": normalized_crop_name.value,
                        "variety_name": variety,
                        "max_duration": 365,
                        # "ID_field": id_field,
                        # "ID_farm": row["ID_farm"],
                        # "ID_all": row["ID_all"]

                    },
                    "StateEvents": None,
                    "TimedEvents": {}
                }
            }
            agro_management.append(agro_entry)
        
        # Create the final YAML structure
        output_data = {
            "AgroManagement": agro_management,
            "Version": "1.0"
        }

        # Add irrigation StateEvents if field is irrigated
        is_irrigated = irrigation_data.get(row['ID_all'], False) if 'ID_all' in row else False
        if is_irrigated:
            # Load soil data for this field to get SMW
            soil_file = soil_dir / f"soil_{field_id}.yaml"
            if soil_file.exists():
                with open(soil_file, "r") as f:
                    soil_dict = yaml.safe_load(f)
            else:
                soil_dict = {}
            
            output_data = add_irrigation_to_agro_yaml(output_data, field_id, is_irrigated, soil_dict)

        output_path = output_dir / f"agro_{field_id}.yaml"
        if output_path.exists():
            raise RuntimeError(f"Output file {output_path} already exists. Please check for duplicates in the input data.")
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(output_data, f, sort_keys=False, default_flow_style=False)
        print(f"Wrote {output_path}")



SOIL_COLS = [
    "C",
    "D",
    "S",
    "OM",
    "ID_field"
]

def load_irrigation_data():
    """
    Load irrigation data from crop_registration_extra_ files.
    Returns a dictionary mapping ID_all -> irrigation_status ('yes'/'no')
    """
    irrigation_data = {}
    
    for extra_file in CROP_MANAGEMENT_DIR.rglob("crop_registration_extra_*.xlsx"):
        df = pd.read_excel(extra_file)
        
        # Extract irrigation status for each ID_all
        for _, row in df.iterrows():
            id_all = str(row["ID_all"]).strip()
            irrigation_status = str(row["irrigation_main_crop"]).strip().lower()
            irrigation_data[id_all] = irrigation_status == 'yes'
    
    return irrigation_data


def add_irrigation_to_agro_yaml(agro_yaml_data: dict, field_id: str, is_irrigated: bool, soil_data: dict) -> dict:
    """
    Add irrigation StateEvents to agro management YAML data if field is irrigated.
    
    Uses state-based irrigation that applies 20mm water when soil moisture reaches wilting point (SMW).
    
    Parameters:
    -----------
    agro_yaml_data : dict
        The agro management YAML structure
    field_id : str
        The field identifier
    is_irrigated : bool
        Whether the field should be irrigated
    soil_data : dict
        Soil parameters dictionary containing SMW (wilting point)
        
    Returns:
    --------
    dict : Modified agro_yaml_data with irrigation StateEvents added
    """
    if not is_irrigated:
        return agro_yaml_data
    
    # Get wilting point from soil data
    smw = soil_data.get('SMW', 0.05)  # Default to 0.05 if not available
    
    # Create StateEvent for irrigation triggered by soil moisture
    # When SM (soil moisture) falls to SMW (wilting point), apply 20mm irrigation
    # amount in cm = 20mm / 10 = 2.0 cm
    irrigation_event = {
        'event_signal': 'irrigate',
        'event_state': 'SM',
        'zero_condition': 'falling',
        'name': 'Soil moisture driven irrigation scheduling',
        'comment': 'Irrigation applied when soil moisture reaches wilting point (20mm water)',
        'events_table': [
            {smw: {'amount': 2.0, 'efficiency': 0.8}}
        ]
    }
    
    # Add irrigation StateEvent to each campaign in AgroManagement
    if 'AgroManagement' in agro_yaml_data:
        for campaign_entry in agro_yaml_data['AgroManagement']:
            for date_key, campaign_data in campaign_entry.items():
                if isinstance(campaign_data, dict):
                    # Initialize StateEvents list if it doesn't exist
                    if campaign_data.get('StateEvents') is None:
                        campaign_data['StateEvents'] = []
                    elif not isinstance(campaign_data['StateEvents'], list):
                        campaign_data['StateEvents'] = []
                    
                    # Add irrigation StateEvent
                    campaign_data['StateEvents'].append(irrigation_event)
        
        # Add trailing empty campaign after last campaign
        # PCSE requires this when StateEvents are present
        if agro_yaml_data['AgroManagement']:
            last_campaign = agro_yaml_data['AgroManagement'][-1]
            # Get the last campaign's end date
            for date_key, campaign_data in last_campaign.items():
                if isinstance(campaign_data, dict) and 'CropCalendar' in campaign_data:
                    end_date = campaign_data['CropCalendar'].get('crop_end_date')
                    if end_date:
                        # Add trailing empty campaign after the end date
                        trailing_campaign = {
                            end_date: {
                                'CropCalendar': None,
                                'StateEvents': None,
                                'TimedEvents': None
                            }
                        }
                        agro_yaml_data['AgroManagement'].append(trailing_campaign)
                        break
    
    return agro_yaml_data


def extract_soil_site_data(soil_file: Path, output_dir: Path):
    df = pd.read_excel(soil_file)
    df = df.rename(columns={
        "Lutum": "C",
        "Dichtheid": "D",
        "Silt": "S",
        "OS": "OM"
    })

    df = df[SOIL_COLS].copy()
    CRAIRC = 0.04
    RDMSOL = 120
    theta_r = 0.01
    topSoil = True

    print(df)

    required_cols = ["ID_field", "C", "D", "S", "OM"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    for _, row in df.iterrows():
        ID_field = str(row["ID_field"]).strip()
        # For Wösten-style pedotransfer functions, the expected units are usually something like:

        # clay, silt, organic matter in percent
        # bulk density in g/cm³ or kg/dm³, not kg/m³
        C = float(row["C"])
        D = float(row["D"]) / 1000 # -> g/cm^3
        S = float(row["S"])
        OM = float(row["OM"])

        # basic checks
        if C <= 0:
            raise ValueError("C must be > 0")
        if D <= 0:
            raise ValueError("D must be > 0")
        if S <= 0:
            raise ValueError("S must be > 0")
        if OM <= 0:
            OM = 0.01

        if not (0 <= C <= 100):
            raise ValueError(f"Clay % out of range: {C}")
        if not (0 <= S <= 100):
            raise ValueError(f"Silt % out of range: {S}")
        if not (0 <= OM <= 100):
            raise ValueError(f"OM % out of range: {OM}")
        if not (0.8 <= D <= 2.0):
            raise ValueError(f"Bulk density out of range: {D}")
        if C + S > 100:
            raise ValueError(f"Clay + silt exceeds 100: C={C}, S={S}")
        # calculate Van Genuchten parameters
        vg_dict = PedotransferFunctionsWosten(C, D, S, OM, theta_r, topSoil)
        vg = SimpleNamespace(**vg_dict)
        required_vg = ["alpha", "k_sat", "n", "theta_r", "theta_s"]
        missing_vg = [k for k in required_vg if k not in vg_dict]
        if missing_vg:
            raise ValueError(f"Pedotransfer function missing keys: {missing_vg}")

        if not (vg_dict["alpha"] > 0):
            raise ValueError(f"Invalid alpha for field {ID_field}: {vg_dict['alpha']}")
        if not (vg_dict["k_sat"] >= 0):
            raise ValueError(f"Invalid k_sat for field {ID_field}: {vg_dict['k_sat']}")
        if not (vg_dict["n"] > 1):
            raise ValueError(f"Invalid n for field {ID_field}: {vg_dict['n']}")
        if not (0 <= vg_dict["theta_r"] < vg_dict["theta_s"] <= 1):
            raise ValueError(
                f"Invalid theta range for field {ID_field}: "
                f"theta_r={vg_dict['theta_r']}, theta_s={vg_dict['theta_s']}"
            )

        # calculate WOFOST soil parameters
        # TODO: problem is SMCR = p.SMW which is caused by p.SMFCF = p.SM
        soil_dict = ClassicalSoilWaterBalanceParameterProvider(
            vg.alpha,
            vg.k_sat,
            vg.n,
            vg.theta_r,
            vg.theta_s,
            CRAIRC=CRAIRC,
            RDMSOL=RDMSOL
        )

        for name in ["SM0", "SMFCF", "SMW"]:
            if not (0 <= soil_dict[name] <= 1):
                raise ValueError(f"{name} out of range for field {ID_field}: {soil_dict[name]}")

        if not (soil_dict["SM0"] > soil_dict["SMFCF"] > soil_dict["SMW"]):
            raise ValueError(
                f"Invalid moisture ordering for field {ID_field}: "
                f"SM0={soil_dict['SM0']}, SMFCF={soil_dict['SMFCF']}, SMW={soil_dict['SMW']}"
            )

        # prepare one YAML content per field
        yaml_data = {
                key: float(value) if isinstance(value, (int, float)) else value
                for key, value in soil_dict.items()
        }
        # yaml_data["K0"] = 401
        # yaml_data["KSUB"] = 401

        yaml_fp = output_dir / f"soil_{ID_field}.yaml"
        with open(yaml_fp, "w", encoding="utf-8") as f:
            yaml.safe_dump(yaml_data, f, sort_keys=False, allow_unicode=True)

        print(f"Saved: {yaml_fp}")



def parse_dms_string(dms_str):
    """
    Parse DMS string like "52°39'29.2"N" to decimal degrees
    """
    pattern = r"(\d+)°(\d+)'([\d.]+)\"([NSEW])"
    match = re.match(pattern, dms_str.strip())
    
    if match:
        degrees, minutes, seconds, direction = match.groups()
        decimal = float(degrees) + (float(minutes) / 60) + (float(seconds) / 3600)
        
        if direction in ['S', 'W']:
            decimal = -decimal
        
        return decimal
    return None


def get_ID_field_to_location_map() -> dict:
    df = pd.read_excel(LOCATION_DATA_FILE)
    print(df.columns)
    # Placeholder implementation - replace with actual mapping logic
    d = {}
    for _, row in df.iterrows():
        coordinates = row["Coordinates"]
        lat_str, long_str = coordinates.split(" ")
        latitude = parse_dms_string(lat_str)
        longitude = parse_dms_string(long_str)
        d[row["ID_field"]] = {
            "latitude": latitude,
            "longitude": longitude
        }
    return d


from enum import StrEnum

class CropType(StrEnum):
    BARLEY = 'barley'
    POTATO = 'potato'
    SUGARBEET = 'sugarbeet'
    WHEAT = 'wheat'
    SEED_ONION = 'seed_onion'


GOOD_CROP_NAMES = {CropType.POTATO, CropType.BARLEY, CropType.SEED_ONION,
                   CropType.WHEAT,
                   CropType.SUGARBEET}
                   
# Mapping dictionary for common crop name variants
CROP_NAME_MAPPING = {
    # Barley
    'barley': CropType.BARLEY,
    'spring barley': CropType.BARLEY,
    'winter barley': CropType.BARLEY,
    
    
    # Potato
    'potato': CropType.POTATO,
    'ware potato': CropType.POTATO,
    'seed potato': CropType.POTATO,
    'white potato': CropType.POTATO,
    'starch potato': CropType.POTATO,
    
    # Sugarbeet
    'sugarbeet': CropType.SUGARBEET,
    'sugar beet': CropType.SUGARBEET,
    'sugar-beet': CropType.SUGARBEET,
    'beet': CropType.SUGARBEET,
    
    # Wheat
    'wheat': CropType.WHEAT,
    'winter wheat': CropType.WHEAT,
    'spring wheat': CropType.WHEAT,
    
    # Seed Onion
    'seed onion': CropType.SEED_ONION,
    'seed_onion': CropType.SEED_ONION,
}


def map_crop_name(crop_name: str) -> Optional[CropType]:
    normalized_name = crop_name.strip().lower()
    
    if normalized_name in CROP_NAME_MAPPING:
        return CROP_NAME_MAPPING[normalized_name]
    return None



def run_model(field_id: str, field_to_location_map: dict, model_class=Wofost73_PP):
    """
    Run WOFOST model for a given field.
    
    Parameters:
    -----------
    field_id : str
        The field identifier
    field_to_location_map : dict
        Dictionary mapping field IDs to coordinates
    model_class : class
        The WOFOST model class to run (Wofost73_PP or Wofost72_WLP_FD)
        
    Returns:
    --------
    pd.DataFrame : Model output with crop_name added
    """
    crop_dict = YAMLCropDataProvider(model_class)

    coordinates = field_to_location_map[field_id]
    latitude = coordinates["latitude"]
    longitude = coordinates["longitude"]
    model_name = model_class.__name__
    print(f"Running {model_name} for field {field_id} at location (lat: {latitude}, long: {longitude})")
    weather_data = NASAPowerWeatherDataProvider(latitude,
                                            longitude)
    
    with open(GLOBAL_SITE_FILE, "r") as f:
        site_dict = yaml.safe_load(f.read())

    soil_file = Path(__file__).parent.joinpath(Path(f"input/soil/soil_{field_id}.yaml"))
    with open(soil_file, "r") as f:
        soil_dict = yaml.safe_load(f.read())

    agro_file = Path(__file__).parent.joinpath(Path(f"input/agro/agro_{field_id}.yaml"))
    with open(agro_file, "r") as f:
        agro_dict = yaml.safe_load(f.read())

    parameters = ParameterProvider(sitedata=site_dict,
                                   soildata=soil_dict,
                                   cropdata=crop_dict)
    wofost = model_class(parameters, weather_data, agro_dict)

    wofost.run_till_terminate()
    output = wofost.get_output()
    df = pd.DataFrame(output)
    return df



def update_agro_variety_names():
    """
    Update variety names in all agro YAML files based on crop type.
    
    Mapping:
    - wheat -> Winter_wheat_101
    - sugarbeet -> Sugarbeet_601
    - seed_onion -> onion_agriadapt
    - barley -> Spring_barley_301
    """
    variety_mapping = {
        'wheat': 'Winter_wheat_101',
        'sugarbeet': 'Sugarbeet_601',
        'seed_onion': 'onion_agriadapt',
        'barley': 'Spring_barley_301'
    }
    
    agro_dir = Path(__file__).parent.joinpath(Path("input/agro"))
    
    # Process all agro YAML files
    for agro_file in agro_dir.glob("agro_*.yaml"):
        print(f"Processing {agro_file.name}...")
        
        with open(agro_file, "r") as f:
            data = yaml.safe_load(f)
        
        # Update variety names
        if "AgroManagement" in data:
            for entry in data["AgroManagement"]:
                for date_key, date_value in entry.items():
                    if isinstance(date_value, dict) and "CropCalendar" in date_value and date_value["CropCalendar"] is not None:
                        crop_name = date_value["CropCalendar"].get("crop_name", "").lower()
                        
                        if crop_name in variety_mapping:
                            old_variety = date_value["CropCalendar"]["variety_name"]
                            new_variety = variety_mapping[crop_name]
                            date_value["CropCalendar"]["variety_name"] = new_variety
                            print(f"  {crop_name}: {old_variety} -> {new_variety}")
        
        # Write back
        with open(agro_file, "w") as f:
            yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)
        
        print(f"  ✓ Updated {agro_file.name}")
    
    print("\nAll agro files updated!")


def load_agro_data_of_field(field_id: str) -> dict:
    """
    Load agro management data for a specific field from its YAML file.
    
    Parameters:
    -----------
    field_id : str
        The field identifier
        
    Returns:
    --------
    dict : Agro management data for the specified field
    """
    agro_file = Path(__file__).parent.joinpath(Path(f"input/agro/agro_{field_id}.yaml"))
    
    if not agro_file.exists():
        raise FileNotFoundError(f"Agro file not found for field {field_id}: {agro_file}")
    
    with open(agro_file, "r") as f:
        agro_data = yaml.safe_load(f)
    
    return agro_data

def dump_model_results_to_excel(results_dict: dict, output_file: Path):
    if not results_dict:
        print(f"  Warning: No results to export to {output_file.name}. Skipping...")
        return
    
    concat_81_rows = []
    for field_id, df in results_dict.items():
        agro_data = load_agro_data_of_field(field_id)
        end_dates = {}
        for year in agro_data["AgroManagement"]:
            year_key = list(year.keys())[0]
            year_data = year[year_key]
            crop_calendar = year_data.get("CropCalendar")
            if crop_calendar is not None:
                end_dates[crop_calendar["crop_end_date"]] = crop_calendar["crop_name"]
        end_date_rows = df[df["day"].isin(list(end_dates.keys()))]
        end_date_rows["field_id"] = field_id
        for end_date, crop_name in end_dates.items():
            print(f"Mapping end date {end_date} to crop {crop_name} for field {field_id}")
            end_date_rows[end_date_rows["day"] == end_date] = crop_name
        concat_81_rows.append(end_date_rows)
    
    if concat_81_rows:
        pd.concat(concat_81_rows, ignore_index=True).to_excel(output_file, index=False)
        print(f"  ✓ Results saved to {output_file.name}")
        

def main():

    crop_dict = YAMLCropDataProvider(Wofost73_PP)

    crops_varieties = crop_dict.get_crops_varieties()
    print("Sugarbeet varieties:", list(crops_varieties['sugarbeet']))
    print("Wheat varieties:", list(crops_varieties['wheat']))
    print("Barley varieties:", list(crops_varieties['barley']))
    
    # Check what crops are available
    print(f"\nAll available crops: {list(crops_varieties.keys())}")
    
    # Check for onion varieties
    onion_varieties = None
    for crop_name in crops_varieties.keys():
        if 'onion' in crop_name.lower():
            print(f"Found onion crop: {crop_name}")
            onion_varieties = crops_varieties[crop_name]
            print(f"Onion varieties available: {list(onion_varieties)}")
    
    if onion_varieties is None:
        print("WARNING: No onion crop found in crops_varieties!")
    
    print("Loading irrigation data from crop_registration_extra_ files...")
    irrigation_data = load_irrigation_data()
    print(f"Loaded irrigation data for {len(irrigation_data)} records")
    irrigated_count = sum(1 for v in irrigation_data.values() if v)
    print(f"Irrigated fields: {irrigated_count}")
    
    print("Extracting soil data first (needed for irrigation parameters)...")
    soil_output_dir = Path(__file__).parent.joinpath(Path("input/soil"))
    if soil_output_dir.exists():
        shutil.rmtree(soil_output_dir)
    soil_output_dir.mkdir(parents=True, exist_ok=True)
    extract_soil_site_data(SOIL_DATA_FILE, soil_output_dir)
    
    print("Extracting agro management data...")

    output_dir = Path(__file__).parent.joinpath(Path("input/agro"))
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for f in CROP_MANAGEMENT_DIR.rglob("crop_registration_basic_*.xlsx"):
        print(f"Processing {f.relative_to(CROP_MANAGEMENT_DIR)}...")
        extract_agro_management_data(f, output_dir, crops_varieties, irrigation_data, soil_output_dir)

    # Update variety names in agro files
    print("\nUpdating variety names in agro files...")
    update_agro_variety_names()

    field_to_location = get_ID_field_to_location_map()

    fields_from_agro = {"_".join(f.stem.split("_")[1:]) for f in output_dir.glob("agro_*.yaml")}
    fields_from_soil = {"_".join(f.stem.split("_")[1:]) for f in soil_output_dir.glob("soil_*.yaml")}
    fields_from_location = set(field_to_location.keys())
    if not fields_from_agro.issubset(fields_from_soil):
        raise RuntimeError(f"Some fields in soil data are missing from agro data. Soil: {fields_from_soil}, Agro: {fields_from_agro}")

    # Create output directories for model results
    output_excel_dir = Path(__file__).parent.joinpath(Path("output/model_results"))
    output_excel_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize dataframes to collect results from all fields
    wofost81_results = {}
    wofost_wlp_results = {}
    
    exceptions_81 = []
    exceptions_wlp = []
    
    # Run WOFOST73_PP model
    print("\n" + "="*80)
    print("RUNNING WOFOST73_PP MODEL")
    print("="*80)
    for field_id in fields_from_agro:
        print(f"\nRunning WOFOST73_PP for field {field_id}...")
        try:
            df = run_model(field_id, field_to_location, model_class=Wofost73_PP)
            wofost81_results[field_id] = df
            print(f"  ✓ Completed for {field_id}")
        except Exception as e:
            print(f"  ✗ Error for field {field_id}: {e}")
            exceptions_81.append((field_id, str(e)))
    
    # Run Wofost72_WLP_FD model
    print("\n" + "="*80)
    print("RUNNING WOFOST72_WLP_FD MODEL")
    print("="*80)
    for field_id in fields_from_agro:
        print(f"\nRunning Wofost72_WLP_FD for field {field_id}...")
        try:
            df = run_model(field_id, field_to_location, model_class=Wofost72_WLP_FD)
            wofost_wlp_results[field_id] = df
            print(f"  ✓ Completed for {field_id}")
        except Exception as e:
            print(f"  ✗ Error for field {field_id}: {e}")
            exceptions_wlp.append((field_id, str(e)))
    
    # Save results to Excel files
    print("\n" + "="*80)
    print("SAVING RESULTS TO EXCEL")
    print("="*80)

    
    dump_model_results_to_excel(wofost81_results, 
                                output_excel_dir / "WOFOST73_PP_results.xlsx")

    dump_model_results_to_excel(wofost_wlp_results, 
                                output_excel_dir / "Wofost72_WLP_FD_results.xlsx")

    # Print summary
    print("\n" + "="*80)
    print("MODEL EXECUTION SUMMARY")
    print("="*80)
    print(f"\nWOFOST73_PP:")
    print(f"  Successful runs: {len(wofost81_results)}")
    print(f"  Failed runs: {len(exceptions_81)}")
    if exceptions_81:
        print(f"  Failed fields: {[f[0] for f in exceptions_81]}")
    
    print(f"\nWofost72_WLP_FD:")
    print(f"  Successful runs: {len(wofost_wlp_results)}")
    print(f"  Failed runs: {len(exceptions_wlp)}")
    if exceptions_wlp:
        print(f"  Failed fields: {[f[0] for f in exceptions_wlp]}")
    
    print(f"\nResults saved to: {output_excel_dir}")




if __name__ == "__main__":
    main()
