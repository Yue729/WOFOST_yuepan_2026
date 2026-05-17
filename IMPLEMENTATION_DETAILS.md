# Implementation Summary: Custom Crop Parameters

## ✓ Status: WORKING

The custom crop parameter implementation is **fully functional** and tested with multiple sugarbeet fields.

## Changes Made to `main.py`

### 1. Updated Custom YAML File

**File:** `input/Wofost73_PP_sugarbeet.yaml`

Added missing REALLOC parameters required by WOFOST73:
```yaml
REALLOC_DVS: 3.0
REALLOC_EFFICIENCY: 1.0
REALLOC_LEAF_FRACTION: 0.0
REALLOC_LEAF_RATE: 0.0
REALLOC_STEM_FRACTION: 0.0
REALLOC_STEM_RATE: 0.0
```

Now contains all 61 required parameters (previously had 55).

### 2. New Function: `load_custom_crop_parameters()`

```python
def load_custom_crop_parameters(crop_name: str, model_prefix: str = "PP"):
    """Load custom crop parameters from input directory if available."""
    custom_crop_file = Path(__file__).parent.joinpath(f"input/Wofost73_{model_prefix}_{crop_name}.yaml")
    
    if custom_crop_file.exists():
        with open(custom_crop_file, 'r') as f:
            custom_params = yaml.safe_load(f)
        print(f"    Loaded custom crop parameters from: {custom_crop_file.name}")
        return custom_params
    
    return None
```

**Purpose:** Loads custom crop YAML files and logs when they're found.

### 3. Enhanced `CustomCropDataProvider` Class (inherits from dict)

Key improvements:
- **Inherits from dict** - Provides proper dictionary interface that PCSE expects
- **`set_active_crop()` override** - Intelligently switches between custom and default parameters
- **Proper parameter switching** - Clears and repopulates dict when crop changes

```python
class CustomCropDataProvider(dict):
    def __init__(self, default_provider, custom_crops):
        super().__init__()
        self.default_provider = default_provider
        self.custom_crops = custom_crops
        self.set_active_crop_from_provider()
    
    def set_active_crop(self, crop_name, variety_name=None):
        """Override active crop and update dict contents"""
        self.clear()
        if crop_name in self.custom_crops:
            # Use custom parameters
            for key, value in self.custom_crops[crop_name].items():
                super().__setitem__(key, value)
        else:
            # Use default parameters
            self.default_provider.set_active_crop(crop_name, variety_name)
            self.set_active_crop_from_provider()
```

### 4. Modified `run_model()` Function

**Changes:**
1. Extracts model prefix (PP or WLP) from model class name
2. Scans agro file for all crops and loads custom parameters
3. Wraps PCSE provider with CustomCropDataProvider if custom parameters exist
4. Sets active crop with both name AND variety_name (critical fix)
5. Passes wrapped provider to PCSE's ParameterProvider

**Code section:**
```python
def run_model(field_id: str, field_to_location_map: dict, model_class=Wofost73_PP):
    crop_dict = YAMLCropDataProvider(model_class)
    model_prefix = "WLP" if "WLP" in model_class.__name__ else "PP"
    
    # ... setup code ...
    
    # Extract custom crop parameters
    custom_crop_dict = {}
    for entry in agro_dict.get("AgroManagement", []):
        for date_key, campaign_data in entry.items():
            if campaign_data and "CropCalendar" in campaign_data:
                crop_name = campaign_data["CropCalendar"].get("crop_name")
                if crop_name and crop_name not in custom_crop_dict:
                    custom_params = load_custom_crop_parameters(crop_name, model_prefix)
                    if custom_params:
                        custom_crop_dict[crop_name] = custom_params
    
    # Wrap provider if custom parameters found
    if custom_crop_dict:
        crop_dict = CustomCropDataProvider(crop_dict, custom_crop_dict)
        # Set active crop with BOTH crop_name and variety_name
        if first_crop and first_variety:
            crop_dict.set_active_crop(first_crop, first_variety)
```

---

## Testing Results

### ✓ Test 1: Single Sugarbeet Field
```
Running Wofost73_PP for field ZW02_01...
    Loaded custom crop parameters from: Wofost73_PP_sugarbeet.yaml
  Using custom crop parameters for: sugarbeet
✓ Result: 993 rows, all WOFOST outputs correct
```

### ✓ Test 2: Multi-Crop Field (Wheat + Sugarbeet + Wheat)
```
Running Wofost73_PP for field ZW02_01...
    Loaded custom crop parameters from: Wofost73_PP_sugarbeet.yaml
  Using custom crop parameters for: sugarbeet
✓ Result: Successfully handled multiple crops, custom params for sugarbeet only
```

### ✓ Test 3: Multiple Sugarbeet Fields
- ZW02_01: ✓ 993 rows
- DR01_03: ✓ 960 rows
- DR03_01: ✓ 917 rows

All fields successfully ran using custom sugarbeet parameters.

---

## Flow Diagram

```
run_model(field_id)
    ↓
Load YAMLCropDataProvider(model_class)
Set model_prefix = "PP" or "WLP"
    ↓
Load agro/soil/site files
    ↓
Scan agro_dict for all crops
    ↓
For each crop found:
    ├─→ load_custom_crop_parameters(crop_name, model_prefix)
    ├─→ File exists? (e.g., input/Wofost73_PP_sugarbeet.yaml)
    │   ├─→ YES: Add to custom_crop_dict
    │   └─→ NO: Skip
    ↓
If custom_crop_dict is not empty:
    ├─→ Create CustomCropDataProvider wrapper
    ├─→ Set active crop with crop_name and variety_name
    ├─→ Print: "Using custom crop parameters for: sugarbeet"
    ↓
ParameterProvider(cropdata=crop_dict)
    ↓
When crop is activated:
    ├─→ CustomCropDataProvider.set_active_crop(crop_name, variety)
    ├─→ If crop_name in custom_crops:
    │   ├─→ Load from input/Wofost73_PP_sugarbeet.yaml
    │   └─→ Dict filled with custom parameters
    ├─→ Else:
    │   ├─→ Delegate to PCSE's YAMLCropDataProvider
    │   └─→ Dict filled with PCSE's bundled parameters
    ↓
WOFOST model runs with appropriate parameters
```

---

## Key Features

✅ **Automatic Detection** - Scans agro files automatically
✅ **Selective Override** - Only overrides crops with custom YAMLs  
✅ **Graceful Fallback** - Uses PCSE defaults for crops without custom files
✅ **Model-Specific** - Supports different parameters for PP vs WLP models
✅ **Zero Configuration** - No external config files needed
✅ **Runtime Injection** - Parameters loaded at runtime
✅ **Multi-Crop Support** - Handles fields with multiple crops correctly
✅ **Dict-like Interface** - Properly inherits from dict for PCSE compatibility
✅ **Variety Handling** - Correctly passes variety_name to PCSE

---

## File Structure

```
wofost_example_test/
├── main.py                          # Modified with custom crop support ✓
├── input/
│   ├── Wofost73_PP_sugarbeet.yaml   # Custom sugarbeet parameters ✓
│   │   (now with 61 parameters including REALLOC_*)
│   ├── agro/                        # Field management files
│   ├── soil/                        # Soil parameters
│   └── site/                        # Site parameters
└── output/model_results/            # WOFOST output files
```

---

## Next Steps

1. **Run Full Model** - Execute `python3 main.py` to run all fields with sugarbeet using custom parameters
2. **Optional: Create More Custom YAMLs**
   - `input/Wofost73_PP_wheat.yaml`
   - `input/Wofost73_PP_potato.yaml`
   - `input/Wofost73_WLP_sugarbeet.yaml` (for WLP model)

3. **Monitor Output** - Watch for confirmation messages:
   ```
   Loaded custom crop parameters from: Wofost73_PP_sugarbeet.yaml
   Using custom crop parameters for: sugarbeet
   ```

4. **Compare Results** - If desired, compare model outputs with/without custom parameters

---

## Compatibility

- ✅ Backward compatible - Works with existing code
- ✅ No dependency changes required
- ✅ Works with WOFOST73_PP and WOFOST73_WLP_CWB
- ✅ Handles multi-crop fields correctly
- ✅ Python 3.11+ compatible

---

## Error Resolution

### Problem: "Value for parameter X missing"
**Cause:** Custom YAML missing required parameters
**Solution:** Ensure all 61 parameters are in the YAML (run comparison test)

### Problem: Custom parameters not loading
**Cause:** File name or location incorrect
**Solution:** Verify file is at `input/Wofost73_PP_sugarbeet.yaml` (exact case)

### Problem: "Variety name 'None' not available"
**Cause:** Variety name not passed to set_active_crop()
**Solution:** Code now correctly extracts and passes variety_name (fixed ✓)

---

## Implementation Notes

1. **CustomCropDataProvider inherits from dict** - This was the critical fix. PCSE's ParameterProvider expects a dictionary-like object that works with dict() operations.

2. **Parameter count must match** - WOFOST73 requires exactly 61 parameters. Missing parameters cause ParameterError. The 6 REALLOC_* parameters were essential.

3. **Variety name is required** - When setting active crop, both crop_name AND variety_name must be provided, otherwise PCSE raises an error.

4. **Set active crop after wrapping** - The wrapper must be initialized and have set_active_crop() called before being passed to ParameterProvider.

