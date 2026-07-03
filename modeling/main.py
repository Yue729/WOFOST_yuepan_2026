from typing import Optional
import re
import yaml
import shutil
import pandas as pd
from types import SimpleNamespace
from pathlib import Path
from pcse.base import ParameterProvider
from pcse.input import YAMLCropDataProvider, NASAPowerWeatherDataProvider, YAMLAgroManagementReader
from pcse.models import Wofost73_PP, Wofost73_WLP_CWB
from datetime import datetime, timedelta, date

try:
    # Works when imported as module: `from modeling import main`
    from modeling.soil_param_calculation.pedotransfer_functions import PedotransferFunctionsWosten
    from modeling.soil_param_calculation.van_genuchten import ClassicalSoilWaterBalanceParameterProvider
except ModuleNotFoundError:
    # Works when executed as script: `python modeling/main.py`
    from soil_param_calculation.pedotransfer_functions import PedotransferFunctionsWosten
    from soil_param_calculation.van_genuchten import ClassicalSoilWaterBalanceParameterProvider

CUSTOM_SUGARBEET_FILE = Path(__file__).parent.parent / "input" / "Wofost73_PP_sugarbeet.yaml"

RAW_DATA_PATH = Path(r"/Users/panyue/Desktop/final_data/")
SOIL_DATA_FILE = RAW_DATA_PATH / "3_soil_data/general_soil_characteristics/general_soil_characteristics.xlsx"
CROP_MANAGEMENT_DIR = RAW_DATA_PATH / "1_crop_management_data"
LOCATION_DATA_FILE = RAW_DATA_PATH / "4_other_files/locations_data.xlsx"

GLOBAL_SITE_FILE = Path(__file__).parent.parent.joinpath(Path("input/9_Wofost81_PP_site.yaml"))
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


def _resolve_site_file(field_id: str) -> Path:
    """Resolve site parameter file.

    Preference order:
    1) Legacy global file: input/9_Wofost81_PP_site.yaml
    2) Per-field file   : input/site/site_<field_id>.yaml
    """
    if GLOBAL_SITE_FILE.exists():
        return GLOBAL_SITE_FILE

    field_site_file = Path(__file__).parent.parent / "input" / "site" / f"site_{field_id}.yaml"
    if field_site_file.exists():
        return field_site_file

    raise FileNotFoundError(
        f"No site file found. Checked: {GLOBAL_SITE_FILE} and {field_site_file}"
    )


def extract_agro_management_data(f: Path, output_dir: Path, crops_varieties: dict):
    # Read main crop registration
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

    # ── Load irrigation data from crop_registration_extra.xlsx ──────────────
    extra_file = f.parent / f.name.replace("basic", "extra")
    irrigation_map = {}  # {(ID_field, year): "yes"/"no"}
    if extra_file.exists():
        try:
            df_extra = pd.read_excel(extra_file)
            df_extra.columns = df_extra.columns.astype(str).str.strip()
            if "ID_field" in df_extra.columns and "year" in df_extra.columns and "irrigation_main_crop" in df_extra.columns:
                for _, row in df_extra.iterrows():
                    key = (str(row["ID_field"]).strip(), int(row["year"]))
                    irrigation_map[key] = str(row["irrigation_main_crop"]).strip().lower()
                print(f"  Loaded irrigation data: {len(irrigation_map)} records from {extra_file.name}")
            else:
                print(f"  ⚠ Missing required columns in {extra_file.name}")
        except Exception as e:
            print(f"  ⚠ Could not load irrigation data from {extra_file.name}: {e}")
    else:
        print(f"  ⚠ Irrigation file not found: {extra_file}")

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
                raise ValueError(f"Crop '{normalized_crop_name}' not found in crop data provider.")

            raw_variety = str(row['variety']).strip() if pd.notna(row['variety']) else ''
            variety = resolve_variety(normalized_crop_name, raw_variety)

            # ── Build irrigation events (20mm every 20 days, 0.8 efficiency) ───
            timed_events = None
            irr_key = (str(row["ID_field"]).strip(), int(row["year"]))
            if irrigation_map.get(irr_key) == "yes":
                events_table = []
                current_date = planting_date
                harvest_date = row['date_harvest']
                while current_date <= harvest_date:
                    events_table.append({
                        current_date: {"amount": 20, "efficiency": 0.8}
                    })
                    current_date += timedelta(days=20)
                
                timed_events = [{
                    "event_signal": "irrigate",
                    "name": "Irrigation application table",
                    "comment": "Irrigation scheduled every 20 days, 20mm per event",
                    "events_table": events_table
                }]
                print(f"  Added {len(events_table)} irrigation events for {field_id} year {row['year']}")

            # Campaign entry with date object as key
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
                    },
                    "TimedEvents": timed_events,
                    "StateEvents": None
                }
            }
            agro_management.append(agro_entry)
        
        # Save with custom YAML representer for dates
        output_path = output_dir / f"agro_{field_id}.yaml"
        if output_path.exists():
            raise RuntimeError(f"Output file {output_path} already exists. Please check for duplicates in the input data.")
        
        output_data = {
            "AgroManagement": agro_management,
            "Version": "1.0"
        }
        
        # Custom representer: write date as unquoted YAML timestamp (e.g. 2023-04-18)
        # tag:yaml.org,2002:timestamp ensures PyYAML writes unquoted dates
        # which are then parsed back as datetime.date objects by YAMLAgroManagementReader
        class _AgroDumper(yaml.Dumper):
            def ignore_aliases(self, data):
                return True  # prevent &id001/∗id001 anchors when same date reused

        def _date_representer(dumper, data):
            return dumper.represent_scalar('tag:yaml.org,2002:timestamp', data.isoformat())

        _AgroDumper.add_representer(date, _date_representer)

        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(output_data, f, Dumper=_AgroDumper, sort_keys=False,
                      default_flow_style=False, allow_unicode=True)
        print(f"Wrote {output_path}")


SOIL_COLS = [
    "C",
    "D",
    "S",
    "OM",
    "ID_field"
]

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


def load_irrigation_data() -> dict:
    """Scan the crop registration extra files and return a mapping of irrigation flags.

    Returns a dict keyed by "{ID_field}_{year}" with boolean values True/False.
    Looks for files named like "crop_registration_extra_*.xlsx" under CROP_MANAGEMENT_DIR.
    """
    irrigation = {}
    for f in CROP_MANAGEMENT_DIR.rglob("crop_registration_extra_*.xlsx"):
        try:
            df = pd.read_excel(f)
            df.columns = df.columns.astype(str).str.strip()
            if all(c in df.columns for c in ("ID_field", "year", "irrigation_main_crop")):
                for _, row in df.iterrows():
                    id_field = str(row["ID_field"]).strip()
                    try:
                        year = int(row["year"])
                    except Exception:
                        # fall back to string year-like value
                        year = int(str(row["year"]).strip()) if pd.notna(row["year"]) else None
                    key = f"{id_field}_{year}"
                    val = str(row["irrigation_main_crop"]).strip().lower()
                    irrigation[key] = val in ("yes", "y", "true", "1")
        except Exception as e:
            print(f"  ⚠ Could not read irrigation file {f}: {e}")
    return irrigation


def add_irrigation_to_agro_yaml(agro_yaml: dict, field_id: str, is_irrigated: bool,
                               soil_data: dict = None, water_amount_mm: float = 20.0,
                               efficiency: float = 0.8) -> dict:
    """Add timed irrigation events to an AgroManagement YAML structure.

    For each campaign in `agro_yaml["AgroManagement"]` where there is a CropCalendar,
    and if `is_irrigated` is True, this inserts a `TimedEvents` entry with
    events every 20 days of `water_amount_mm` mm starting from sowing+20 days up to
    harvest-20 days (inclusive where dates allow).

    Returns the modified agro_yaml (modified in-place and also returned).
    """
    from datetime import datetime, date

    def _to_date(d):
        if d is None:
            return None
        if isinstance(d, date) and not isinstance(d, datetime):
            return d
        if isinstance(d, datetime):
            return d.date()
        if isinstance(d, str):
            # accept ISO format
            try:
                return date.fromisoformat(d)
            except Exception:
                try:
                    return datetime.strptime(d, "%Y-%m-%d").date()
                except Exception:
                    return None
        # pandas Timestamp
        try:
            return d.to_pydatetime().date()
        except Exception:
            return None

    ag = agro_yaml.get("AgroManagement") if isinstance(agro_yaml, dict) else None
    if ag is None:
        return agro_yaml

    for campaign in ag:
        # campaign is a dict with single date key
        for start_key, content in list(campaign.items()):
            cal = content.get("CropCalendar") or {}
            sow = _to_date(cal.get("crop_start_date"))
            harvest = _to_date(cal.get("crop_end_date"))
            if not sow or not harvest:
                continue
            if not is_irrigated:
                # ensure TimedEvents remains as is (do not add irrigation)
                continue

            # compute start = sow + 20 days, end = harvest - 20 days
            start_dt = sow + timedelta(days=20)
            end_dt = harvest - timedelta(days=20)
            if start_dt > end_dt:
                # not enough window for timed irrigation; skip
                continue

            events_table = []
            cur = start_dt
            while cur <= end_dt:
                events_table.append({cur: {"amount": water_amount_mm, "efficiency": efficiency}})
                cur = cur + timedelta(days=20)

            timed_events = [{
                "event_signal": "irrigate",
                "name": "Irrigation application table",
                "comment": "Irrigation scheduled every 20 days, 20mm per event",
                "events_table": events_table
            }]

            # Insert or replace TimedEvents
            content["TimedEvents"] = timed_events

    return agro_yaml


from enum import StrEnum

class CropType(StrEnum):
    BARLEY = 'barley'
    CASSAVA = 'cassava'
    CHICKPEA = 'chickpea'
    COTTON = 'cotton'
    COWPEA = 'cowpea'
    FABABEAN = 'fababean'
    GROUNDNUT = 'groundnut'
    MUNGBEAN = 'mungbean'
    PIGEONPEA = 'pigeonpea'
    POTATO = 'potato'
    RAPESEED = 'rapeseed'
    RICE = 'rice'
    SOYBEAN = 'soybean'
    SUGARBEET = 'sugarbeet'
    SUNFLOWER = 'sunflower'
    SWEETPOTATO = 'sweetpotato'
    TOBACCO = 'tobacco'
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
    'winter barley': CropType.WHEAT,   # treated as winter wheat in WOFOST

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
    'spring wheat': CropType.BARLEY,   # treated as spring barley in WOFOST

    # Seed Onion
    'seed onion': CropType.SEED_ONION,
    'seed_onion': CropType.SEED_ONION,
}


def map_crop_name(crop_name: str) -> Optional[CropType]:
    normalized_name = crop_name.strip().lower()
    
    if normalized_name in CROP_NAME_MAPPING:
        return CROP_NAME_MAPPING[normalized_name]
    return None


# Potato varieties that have a direct match in WOFOST 7.3
_POTATO_WOFOST_VARIETIES = {
    'fontane':   'Fontane',
    'festien':   'Festien',
    'innovator': 'Innovator',
    'markies':   'Markies',
}
_POTATO_FALLBACK = 'Fontane' #can be changed

def resolve_variety(crop_type: CropType, raw_variety: str) -> str:
    """Resolve the WOFOST variety name from the crop type and raw field variety string."""

    # Barley (includes spring barley and spring wheat remapped to barley)
    if crop_type == CropType.BARLEY:
        return 'Spring_barley_301'

    # Wheat (includes winter wheat and winter barley remapped to wheat)
    if crop_type == CropType.WHEAT:
        return 'Winter_wheat_101'

    # Sugar beet: always Sugarbeet_601
    if crop_type == CropType.SUGARBEET:
        return 'Sugarbeet_601'

    # Seed onion: always onion_agriadapt
    if crop_type == CropType.SEED_ONION:
        return 'onion_agriadapt'

    # Potato: match field variety if available in WOFOST, else fall back to Fontane
    if crop_type == CropType.POTATO:
        if raw_variety:
            wofost_name = _POTATO_WOFOST_VARIETIES.get(raw_variety.strip().lower())
            if wofost_name:
                return wofost_name
        return _POTATO_FALLBACK
    raise ValueError(f"No variety resolution rule for crop type '{crop_type}'")


def _apply_custom_sugarbeet_params(crop_dict: YAMLCropDataProvider) -> None:
    """Patch all sugarbeet varieties in crop_dict with custom parameters from the local file.

    The custom file is a flat YAML of {param: value}. For every variety under
    the 'sugarbeet' key in crop_dict._store we override any parameter that
    differs from the default, preserving the existing description/units metadata.
    """
    if not CUSTOM_SUGARBEET_FILE.exists():
        return
    custom_params = yaml.safe_load(CUSTOM_SUGARBEET_FILE.read_text())
    sb_store = crop_dict._store.get('sugarbeet', {})
    for variety, variety_params in sb_store.items():
        for param, custom_value in custom_params.items():
            if param in variety_params:
                entry = variety_params[param]
                if isinstance(entry, list) and len(entry) >= 1:
                    entry[0] = custom_value  # preserve description and units
                else:
                    variety_params[param] = custom_value
    print(f"Applied custom sugarbeet parameters from {CUSTOM_SUGARBEET_FILE.name} "
          f"to varieties: {list(sb_store.keys())}")


def run_model(field_id: str, field_to_location_map: dict):
    crop_dict = YAMLCropDataProvider(Wofost73_PP)
    _apply_custom_sugarbeet_params(crop_dict)

    coordinates = field_to_location_map[field_id]
    latitude = coordinates["latitude"]
    longitude = coordinates["longitude"]
    print(f"Running model for field {field_id} at location (lat: {latitude}, long: {longitude})")
    weather_data = NASAPowerWeatherDataProvider(latitude, longitude)

    site_file = _resolve_site_file(field_id)
    with open(site_file, "r") as f:
        site_dict = yaml.safe_load(f.read())

    soil_file = Path(__file__).parent.parent.joinpath(Path(f"input/soil/soil_{field_id}.yaml"))
    with open(soil_file, "r") as f:
        soil_dict = yaml.safe_load(f.read())

    agro_file = Path(__file__).parent.parent.joinpath(Path(f"input/agro/agro_{field_id}.yaml"))
    agro_mgmt = YAMLAgroManagementReader(agro_file)

    # Build a list of (start_date, end_date, crop_name) for campaign-to-row matching.
    # year is taken from crop_end_date so winter crops (sown 2022, harvested 2023) get year=2023.
    campaigns = []  # list of (start_date, end_date, crop_name, harvest_year)
    for campaign in agro_mgmt:
        for start_date, content in campaign.items():
            cal = content.get("CropCalendar") or {}
            crop = cal.get("crop_name", "unknown")
            end_date = cal.get("crop_end_date")
            if end_date is not None:
                harvest_year = end_date.year if hasattr(end_date, 'year') else int(str(end_date)[:4])
            else:
                harvest_year = start_date.year  # fallback
                end_date = start_date  # unknown end
            campaigns.append((start_date, end_date, crop, harvest_year))

    parameters = ParameterProvider(sitedata=site_dict,
                                   soildata=soil_dict,
                                   cropdata=crop_dict)

    # ── Run WOFOST 7.3 PP ───────────────────────────────────────────────────
    wofost_pp = Wofost73_PP(parameters, weather_data, agro_mgmt)
    wofost_pp.run_till_terminate()
    df_pp = pd.DataFrame(wofost_pp.get_output())
    df_pp.insert(0, 'field_id', field_id)
    df_pp.columns = ['field_id'] + [f'PP_{c}' if c != 'day' else c for c in df_pp.columns[1:]]

    # ── Run WOFOST 7.3 WLP_CWB ─────────────────────────────────────────────
    wofost_wlp = Wofost73_WLP_CWB(parameters, weather_data, agro_mgmt)
    wofost_wlp.run_till_terminate()
    df_wlp = pd.DataFrame(wofost_wlp.get_output())
    df_wlp.insert(0, 'field_id', field_id)
    df_wlp.columns = ['field_id'] + [f'WLP_{c}' if c != 'day' else c for c in df_wlp.columns[1:]]

    # Merge on day + field_id
    df = pd.merge(df_pp, df_wlp, on=['field_id', 'day'], how='outer')

    # Add crop_name and year by matching each row's day to its campaign date range.
    # This correctly assigns harvest_year from crop_end_date (not sowing date).
    def _get_campaign_info(day):
        for start_date, end_date, crop, harvest_year in campaigns:
            if start_date <= day.date() <= end_date:
                return crop, harvest_year
        # Fallback: assign to campaign whose end_date is closest after day
        future = [(c, hy) for s, e, c, hy in campaigns if day.date() <= e]
        if future:
            return future[0]
        return 'unknown', day.year

    df['year'] = pd.to_datetime(df['day'])
    df[['crop_name', 'year']] = pd.DataFrame(
        df['year'].apply(_get_campaign_info).tolist(),
        index=df.index
    )

    # Reorder: field_id, day, year, crop_name first
    front_cols = ['field_id', 'day', 'year', 'crop_name']
    other_cols = [c for c in df.columns if c not in front_cols]
    df = df[front_cols + other_cols]

    # Keep only the harvest date row (last simulated day) per year/crop
    df = df.sort_values('day')
    df = df.groupby(['field_id', 'year', 'crop_name'], as_index=False).last()

    return df


def main():

    crop_dict = YAMLCropDataProvider(Wofost73_PP)
    _apply_custom_sugarbeet_params(crop_dict)

    crops_varieties = crop_dict.get_crops_varieties()
    print(crops_varieties[CropType.SUGARBEET])
    print(crops_varieties[CropType.WHEAT])
    print(crops_varieties[CropType.BARLEY])
    print("Extracting agro management data...")

    output_dir = Path(__file__).parent.parent.joinpath(Path("input/agro"))
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for f in CROP_MANAGEMENT_DIR.rglob("crop_registration_basic_*.xlsx"):
        print(f"Processing {f.relative_to(CROP_MANAGEMENT_DIR)}...")
        extract_agro_management_data(f, output_dir, crops_varieties)

    soil_output_dir = Path(__file__).parent.parent.joinpath(Path("input/soil"))
    if soil_output_dir.exists():
        shutil.rmtree(soil_output_dir)
    soil_output_dir.mkdir(parents=True, exist_ok=True)
    print("Copying soil data...")
    extract_soil_site_data(SOIL_DATA_FILE, soil_output_dir)

    field_to_location = get_ID_field_to_location_map()

    fields_from_agro = {"_".join(f.stem.split("_")[1:]) for f in output_dir.glob("agro_*.yaml")}
    fields_from_soil = {"_".join(f.stem.split("_")[1:]) for f in soil_output_dir.glob("soil_*.yaml")}
    fields_from_location = set(field_to_location.keys())
    if not fields_from_agro.issubset(fields_from_soil):
        raise RuntimeError(f"Some fields in soil data are missing from agro data. Soil: {fields_from_soil}, Agro: {fields_from_agro}")

    # Skip fields that have empty AgroManagement (no valid campaigns),
    # because PCSE raises IndexError when initializing agromanagement.
    valid_fields_from_agro = set()
    skipped_empty_agro = []
    for field_id in fields_from_agro:
        agro_file = output_dir / f"agro_{field_id}.yaml"
        try:
            with open(agro_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            campaigns = data.get("AgroManagement") or []
            if isinstance(campaigns, list) and len(campaigns) > 0:
                valid_fields_from_agro.add(field_id)
            else:
                skipped_empty_agro.append(field_id)
        except Exception as e:
            print(f"Skipping field {field_id}: could not read {agro_file.name} ({e})")

    if skipped_empty_agro:
        print(
            f"Skipping {len(skipped_empty_agro)} field(s) with empty AgroManagement: "
            f"{sorted(skipped_empty_agro)}"
        )

    model_runs = []
    exceptions = []
    for field_id in valid_fields_from_agro:
        print(f"Running model for field {field_id}...")
        try:
            df = run_model(field_id, field_to_location)
            model_runs.append(df)
            print(df)
        except Exception as e:
            print(f"Error occurred while running model for field {field_id}: {e}")
            exceptions.append((field_id, e))
    print(f"Model runs completed with {len(exceptions)} exceptions."
          f"Exceptions: {exceptions}")

    if model_runs:
        results_dir = Path(__file__).parent.parent / "output" / "model_results"
        results_dir.mkdir(parents=True, exist_ok=True)

        all_results = pd.concat(model_runs, ignore_index=True)

        # Always include field_id, day, year, crop_name as shared identifier columns
        id_cols = [c for c in ['field_id', 'day', 'year', 'crop_name'] if c in all_results.columns]
        pp_cols  = id_cols + [c for c in all_results.columns if c.startswith('PP_')]
        wlp_cols = id_cols + [c for c in all_results.columns if c.startswith('WLP_')]

        pp_path = results_dir / "WOFOST73_PP_results.xlsx"
        wlp_path = results_dir / "WOFOST73_WLP_CWB_results.xlsx"

        all_results[pp_cols].to_excel(pp_path, index=False)
        all_results[wlp_cols].to_excel(wlp_path, index=False)

        print(f"Saved PP results  → {pp_path}")
        print(f"Saved WLP results → {wlp_path}")



if __name__ == "__main__":
    main()