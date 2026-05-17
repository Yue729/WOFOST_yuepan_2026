# Custom Crop Parameters Implementation

## Overview
The `main.py` has been updated to support custom crop parameters from your local `input/` directory. This allows you to override PCSE's bundled crop parameters with your own customized values.

## How It Works

### 1. **Automatic Detection**
When `run_model()` is executed for a field:
- It reads the agro YAML file to identify which crops are grown
- For each crop, it checks if a custom parameter file exists in `input/`

### 2. **File Naming Convention**
Custom crop parameters should follow this naming pattern:
```
input/Wofost73_<MODEL>_<CROP>.yaml
```

**Examples:**
- `input/Wofost73_PP_sugarbeet.yaml` → Used for WOFOST73_PP model with sugarbeet
- `input/Wofost73_WLP_sugarbeet.yaml` → Used for WOFOST73_WLP_CWB model with sugarbeet
- `input/Wofost73_PP_wheat.yaml` → Used for WOFOST73_PP model with wheat
- `input/Wofost73_WLP_potato.yaml` → Used for WOFOST73_WLP_CWB model with potato

### 3. **Fallback Mechanism**
- **If custom file exists**: Uses your custom crop parameters from `input/`
- **If custom file doesn't exist**: Falls back to PCSE's bundled parameters

### 4. **Priority**
Custom parameters take **priority** over PCSE's bundled parameters when both exist.

## Current Setup

### Available Custom Parameters
- ✅ `input/Wofost73_PP_sugarbeet.yaml` - Custom sugarbeet parameters for WOFOST73_PP

### Fields Using Custom Parameters
When running the model, sugarbeet fields will automatically use your custom parameters:
```
input/agro/agro_DR01_03.yaml    (sugarbeet)
input/agro/agro_DR03_01.yaml    (sugarbeet)
input/agro/agro_DR03_02.yaml    (sugarbeet)
input/agro/agro_DR03_03.yaml    (sugarbeet)
... and more
```

## Implementation Details

### New Functions Added

**`load_custom_crop_parameters(crop_name, model_prefix="PP")`**
- Loads custom crop YAML from `input/Wofost73_{model_prefix}_{crop_name}.yaml`
- Returns custom parameters dict if file exists, None otherwise
- Prints confirmation when custom file is loaded

**`CustomCropDataProvider` (wrapper class)**
- Wraps PCSE's YAMLCropDataProvider
- Returns custom parameters when available
- Falls back to PCSE defaults for other crops

### Modified Functions

**`run_model()`**
- Determines model prefix (PP or WLP) from model class name
- Scans agro file for all crops grown in the field
- Creates CustomCropDataProvider wrapper if any custom parameters are found
- Passes wrapped provider to PCSE's ParameterProvider

## Example Output

When running the model with sugarbeet fields, you should see:
```
Running WOFOST73_PP for field DR01_03...
    Loaded custom crop parameters from: Wofost73_PP_sugarbeet.yaml
  Using custom crop parameters for: sugarbeet
  ✓ Completed for DR01_03
```

## Adding More Custom Crops

To add custom parameters for other crops:

1. **Create custom YAML file** (e.g., `input/Wofost73_PP_wheat.yaml`)
   - Copy the structure from PCSE's bundled YAML
   - Modify parameters as needed

2. **Place in `input/` directory**
   - Follow naming convention: `Wofost73_<MODEL>_<CROP>.yaml`

3. **Run main.py**
   - The implementation automatically detects and uses the custom file

## Testing

To verify custom parameters are being used:

1. Run `main.py` with sugarbeet fields present
2. Watch for confirmation messages in the console:
   - `Loaded custom crop parameters from: Wofost73_PP_sugarbeet.yaml`
   - `Using custom crop parameters for: sugarbeet`

3. Compare results with/without custom parameters to verify the impact

## Notes

- Custom parameters are **field-specific and crop-specific**
- If a field grows both sugarbeet and wheat, sugarbeet uses custom params (if available) while wheat uses PCSE defaults (unless custom wheat params exist)
- Different custom YAMLs can be used for different models (e.g., PP vs WLP)
- The custom parameters are loaded at runtime, no model recompilation needed
