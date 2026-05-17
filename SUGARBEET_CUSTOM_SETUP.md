# ✓ COMPLETE: Custom Sugarbeet Parameters for PP and WLP

## Setup Summary

Your custom sugarbeet YAML files are now ready for **both WOFOST73_PP and WOFOST73_WLP_CWB models**.

## Files Configuration

| File | Parameters | Status |
|------|-----------|--------|
| `input/Wofost73_PP_sugarbeet.yaml` | 61 (55 custom + 6 REALLOC) | ✓ Ready |
| `input/Wofost73_WLP_sugarbeet.yaml` | 61 (55 custom + 6 REALLOC) | ✓ Ready |

## What Each Parameter Does

### Original 55 Custom Parameters
Your custom crop parameters covering:
- Maximum LAI (AMAXTB)
- CO2 response tables (CO2AMAXTB, CO2EFFTB, CO2TRATB)
- Crop coefficients (CVL, CVO, CVR, CVS)
- Development and timing (DTSMTB, DVSEND, TSUM1, TSUM2)
- Light and nitrogen response (FLTB, FOTB, SLATB)
- Root depth and water uptake (RDI, RDMCR, RRI)
- Temperature response (TMNFTB, TMPFTB)
- And many others optimized for your sugarbeet varieties

### 6 Required REALLOC Parameters (Biomass Reallocation)

| Parameter | Value | Meaning |
|-----------|-------|---------|
| **REALLOC_DVS** | 3.0 | Development stage when reallocation starts (late season) |
| **REALLOC_EFFICIENCY** | 1.0 | 100% efficiency of biomass movement to storage organs |
| **REALLOC_LEAF_FRACTION** | 0.0 | Leaves cannot be reallocated |
| **REALLOC_LEAF_RATE** | 0.0 | No daily leaf reallocation rate |
| **REALLOC_STEM_FRACTION** | 0.0 | Stems cannot be reallocated |
| **REALLOC_STEM_RATE** | 0.0 | No daily stem reallocation rate |

**Why these matter for sugarbeet:** These control how much biomass moves from leaves/stems to the sugar storage roots. The current settings (all 0 except DVS) mean minimal reallocation - your plant keeps its leaves and stems throughout the season.

## Verified Tests

✓ Both models successfully ran with custom parameters:

```
Field ZW02_01 (sugarbeet + wheat):
  ✓ WOFOST73_PP: 993 rows
  ✓ WOFOST73_WLP_CWB: 993 rows

Field DR01_03 (sugarbeet):
  ✓ WOFOST73_PP: 960 rows
  ✓ WOFOST73_WLP_CWB: 960 rows
```

Console output confirms custom loading:
```
Loaded custom crop parameters from: Wofost73_PP_sugarbeet.yaml
Using custom crop parameters for: sugarbeet
```

## Running the Full Model

To generate WOFOST results with custom sugarbeet parameters for all fields:

```bash
cd /Users/panyue/PycharmProjects/wofost_example_test
.venv/bin/python3 main.py
```

This will:
1. ✓ Generate soil/site/agro files
2. ✓ Run WOFOST73_PP using custom sugarbeet parameters
3. ✓ Run WOFOST73_WLP_CWB using custom sugarbeet parameters
4. ✓ Export to `output/model_results/WOFOST73_PP_results.xlsx` and `WOFOST73_WLP_CWB_results.xlsx`

## File Status

```
input/
├── Wofost73_PP_sugarbeet.yaml      ✓ 61 parameters (55 custom + 6 REALLOC)
├── Wofost73_WLP_sugarbeet.yaml     ✓ 61 parameters (55 custom + 6 REALLOC)
└── agro/
    ├── agro_ZW02_01.yaml           ✓ Uses custom PP sugarbeet
    ├── agro_DR01_03.yaml           ✓ Uses custom PP sugarbeet
    └── ... (all sugarbeet fields)
```

## How It Works

1. **At runtime**, `main.py` scans each field's agro file for crops
2. **For sugarbeet fields**, it loads `Wofost73_PP_sugarbeet.yaml` or `Wofost73_WLP_sugarbeet.yaml`
3. **For other crops** (wheat, potato, barley, onion), it uses PCSE's bundled defaults
4. **CustomCropDataProvider** wrapper injects your parameters into the model
5. **WOFOST runs** with your custom sugarbeet parameters

## Customization Options

### Modify Existing Parameters
Edit either YAML file to adjust sugarbeet parameters:
- Increase/decrease maximum LAI (AMAXTB)
- Adjust development timing (TSUM1, TSUM2)
- Change root depth (RDMCR)
- etc.

Run `main.py` again - changes take effect immediately.

### Add Custom Parameters for Other Crops
Create `input/Wofost73_PP_wheat.yaml` or `input/Wofost73_WLP_potato.yaml` following the same structure.

### Modify REALLOC for Different Crop Behavior
Adjust the 6 REALLOC parameters to change how biomass reallocates to storage organs:
- Increase `REALLOC_*_FRACTION` (0-1) to allow more reallocation
- Adjust `REALLOC_*_RATE` to control daily reallocation speed
- Change `REALLOC_DVS` to control when reallocation starts

## Important Notes

⚠️ **REALLOC parameters are required:**
- WOFOST73_PP and WOFOST73_WLP_CWB both need all 6 REALLOC parameters
- Cannot use 55-parameter files alone
- Must include REALLOC_DVS through REALLOC_STEM_RATE

✓ **Both models use identical files:**
- Same 61 parameters for PP and WLP
- You can have different values for PP vs WLP if needed
- Currently both use the same custom sugarbeet file

✓ **Backwards compatible:**
- Other crops automatically fall back to PCSE defaults
- No changes to soil/site/agro generation logic
- Purely additive - only overrides specific crops

---

**Status: ✓ COMPLETE AND TESTED**

Ready to run full model with custom sugarbeet parameters for both PP and WLP!
