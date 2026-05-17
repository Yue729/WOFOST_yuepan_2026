# Quick Start: Using Custom Crop Parameters

## What Changed?

Your `main.py` now automatically uses custom crop parameters from your `input/` directory instead of (or in addition to) PCSE's bundled parameters.

## File You Already Have

✅ `input/Wofost73_PP_sugarbeet.yaml` - Your custom sugarbeet parameters for WOFOST73_PP

## How to Use

### Option 1: Use Existing Setup (Recommended for Now)
Just run your model as before:
```bash
python3 main.py
```

**What happens:**
- Fields with **sugarbeet** → Use `input/Wofost73_PP_sugarbeet.yaml` (your custom file)
- Fields with **other crops** → Use PCSE's bundled parameters
- Fields with **sugarbeet + WLP model** → Use PCSE bundled (no custom WLP file yet)

### Option 2: Add Custom Parameters for Other Crops

For example, to use custom wheat parameters:

1. **Create** `input/Wofost73_PP_wheat.yaml`
   - Copy parameters from PCSE's bundled wheat YAML
   - Modify values as needed

2. **Run** `python3 main.py`
   - Both sugarbeet and wheat fields now use custom parameters

## Create Custom Parameters Template

To extract PCSE's default parameters for customization:

```python
from pcse.input import YAMLCropDataProvider
from pcse.models import Wofost73_PP
import yaml

# Get default PCSE parameters
provider = YAMLCropDataProvider(Wofost73_PP)
wheat_params = provider.get_crop('wheat')

# Save as template
with open('input/Wofost73_PP_wheat.yaml', 'w') as f:
    yaml.safe_dump(wheat_params, f)

print("Created input/Wofost73_PP_wheat.yaml")
```

Then edit the file to customize parameter values.

## File Naming Convention

| Use Case | File Path |
|----------|-----------|
| Sugarbeet (WOFOST73_PP) | `input/Wofost73_PP_sugarbeet.yaml` |
| Sugarbeet (WOFOST73_WLP) | `input/Wofost73_WLP_sugarbeet.yaml` |
| Wheat (WOFOST73_PP) | `input/Wofost73_PP_wheat.yaml` |
| Wheat (WOFOST73_WLP) | `input/Wofost73_WLP_wheat.yaml` |
| Potato (WOFOST73_PP) | `input/Wofost73_PP_potato.yaml` |
| Barley (WOFOST73_PP) | `input/Wofost73_PP_barley.yaml` |

**Pattern:** `input/Wofost73_<MODEL>_<CROP>.yaml`

## Console Output Example

When running with custom parameters, you'll see:
```
Running WOFOST73_PP for field DR01_03...
    Loaded custom crop parameters from: Wofost73_PP_sugarbeet.yaml
  Using custom crop parameters for: sugarbeet
  ✓ Completed for DR01_03
```

## Verification

To verify which parameters are being used for sugarbeet:

```bash
# Check if your custom file exists
ls -l input/Wofost73_PP_sugarbeet.yaml

# Check which agro files have sugarbeet
grep -l "crop_name: sugarbeet" input/agro/agro_*.yaml
```

## Troubleshooting

### "KeyError: 'sugarbeet'" when running model
- The custom YAML file is missing required parameters
- Solution: Ensure all required crop parameters are in the YAML

### Custom parameters not being loaded
- Check file naming: Should be `Wofost73_PP_sugarbeet.yaml` (exact case)
- Check location: Should be in `input/` directory
- Check format: Should be valid YAML

### To fall back to PCSE defaults temporarily
- Simply rename or move your custom YAML file
- Example: `mv input/Wofost73_PP_sugarbeet.yaml input/Wofost73_PP_sugarbeet.yaml.bak`

## More Information

See `CUSTOM_CROP_PARAMETERS.md` for complete documentation.
