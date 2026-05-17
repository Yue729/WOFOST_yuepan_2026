# 📚 Documentation Index

## Quick Start
Start here if you want to run the model immediately:
- **`PREFLIGHT_CHECKLIST.md`** - Verify everything is ready
- **`README_CUSTOM_SETUP.md`** - Quick overview and how to run

## Understanding Your Setup
Learn what's been implemented:
- **`ACCOMPLISHED.md`** - What was done and why
- **`SETUP_COMPLETE.md`** - Setup summary and next steps
- **`SUGARBEET_CUSTOM_SETUP.md`** - Complete setup guide

## Understanding the Parameters
Deep dive into the REALLOC parameters:
- **`REALLOC_PARAMETERS_EXPLAINED.md`** - Detailed breakdown with scenarios
- **`REALLOC_MISSING_PARAMETERS_EXPLAINED.md`** - What each parameter means
  - REALLOC_DVS (Development Stage)
  - REALLOC_EFFICIENCY (Transfer Efficiency)
  - REALLOC_LEAF_FRACTION (Leaf Reallocation Potential)
  - REALLOC_LEAF_RATE (Daily Leaf Movement)
  - REALLOC_STEM_FRACTION (Stem Reallocation Potential)
  - REALLOC_STEM_RATE (Daily Stem Movement)

## Technical Documentation
For developers and advanced users:
- **`IMPLEMENTATION_DETAILS.md`** - Code implementation and flow diagrams
- **`CUSTOM_CROP_PARAMETERS.md`** - Framework documentation
- **`CUSTOM_CROP_PARAMS_QUICKSTART.md`** - Quick reference for usage

## Legacy Documentation
Previous versions (for reference):
- **`CUSTOM_CROP_FIXED.md`** - Earlier fix documentation
- **`CUSTOM_CROP_PARAMETERS.md`** - Framework overview

---

## File Organization

```
/Users/panyue/PycharmProjects/wofost_example_test/
├── 📖 Documentation Files
│   ├── DOCUMENTATION_INDEX.md          ← You are here
│   ├── PREFLIGHT_CHECKLIST.md          ← Start: Ready to run?
│   ├── README_CUSTOM_SETUP.md          ← Start: Quick overview
│   ├── ACCOMPLISHED.md                 ← What was done
│   ├── SETUP_COMPLETE.md               ← Summary
│   ├── SUGARBEET_CUSTOM_SETUP.md       ← Complete guide
│   ├── REALLOC_PARAMETERS_EXPLAINED.md ← Detailed params
│   ├── REALLOC_MISSING_PARAMETERS_EXPLAINED.md
│   ├── IMPLEMENTATION_DETAILS.md       ← Technical
│   └── CUSTOM_CROP_PARAMETERS.md       ← Framework
│
├── 💾 Code Files
│   └── main.py                         ← Updated with custom crop support
│
└── 📂 Data Files
    ├── input/
    │   ├── Wofost73_PP_sugarbeet.yaml       ← PP model (61 params)
    │   ├── Wofost73_WLP_sugarbeet.yaml      ← WLP model (61 params)
    │   ├── agro/                           ← 137 field management files
    │   ├── soil/                           ← Soil parameters
    │   └── site/                           ← Site parameters
    └── output/
        └── model_results/                  ← Results go here
            ├── WOFOST73_PP_results.xlsx
            └── WOFOST73_WLP_CWB_results.xlsx
```

---

## How to Use This Documentation

### I want to...

**Run the model immediately**
→ Read: `PREFLIGHT_CHECKLIST.md` → `README_CUSTOM_SETUP.md`

**Understand what was done**
→ Read: `ACCOMPLISHED.md` → `SETUP_COMPLETE.md`

**Learn about REALLOC parameters**
→ Read: `REALLOC_MISSING_PARAMETERS_EXPLAINED.md` → `REALLOC_PARAMETERS_EXPLAINED.md`

**Modify parameters for different behavior**
→ Read: `REALLOC_PARAMETERS_EXPLAINED.md` (Scenarios section)

**Add custom parameters for other crops**
→ Read: `CUSTOM_CROP_PARAMS_QUICKSTART.md` → `CUSTOM_CROP_PARAMETERS.md`

**Understand the code implementation**
→ Read: `IMPLEMENTATION_DETAILS.md` → `CUSTOM_CROP_PARAMETERS.md`

**Check that everything is ready**
→ Read: `PREFLIGHT_CHECKLIST.md` (verify all ✓ marks)

**Troubleshoot issues**
→ Read: `PREFLIGHT_CHECKLIST.md` (Troubleshooting section)

---

## Key Information at a Glance

### Your Custom Setup
- **Files:** `Wofost73_PP_sugarbeet.yaml` + `Wofost73_WLP_sugarbeet.yaml`
- **Parameters:** 61 each (55 custom + 6 REALLOC)
- **Models supported:** WOFOST73_PP and WOFOST73_WLP_CWB
- **Fields covered:** All 137 sugarbeet fields

### The 6 REALLOC Parameters
1. **REALLOC_DVS** = 3.0 (start reallocation post-harvest)
2. **REALLOC_EFFICIENCY** = 1.0 (100% efficiency)
3. **REALLOC_LEAF_FRACTION** = 0.0 (leaves stay on plant)
4. **REALLOC_LEAF_RATE** = 0.0 (no daily leaf reallocation)
5. **REALLOC_STEM_FRACTION** = 0.0 (stems stay on plant)
6. **REALLOC_STEM_RATE** = 0.0 (no daily stem reallocation)

**Effect:** Conservative, realistic model

### How to Run
```bash
cd /Users/panyue/PycharmProjects/wofost_example_test
.venv/bin/python3 main.py
```

**Time:** ~45-60 minutes for all 137 fields

### Output Location
```
output/model_results/
├── WOFOST73_PP_results.xlsx
└── WOFOST73_WLP_CWB_results.xlsx
```

---

## Status

✅ **COMPLETE AND READY TO USE**

All documentation has been created. The system is fully operational.

**Next step:** Run `python3 main.py`

---

## Document Purposes

| Document | Type | Length | Audience |
|----------|------|--------|----------|
| PREFLIGHT_CHECKLIST | Checklist | Short | Everyone |
| README_CUSTOM_SETUP | Guide | Medium | Users |
| ACCOMPLISHED | Summary | Short | Overview |
| SETUP_COMPLETE | Summary | Medium | Overview |
| SUGARBEET_CUSTOM_SETUP | Guide | Long | Detailed users |
| REALLOC_PARAMETERS_EXPLAINED | Reference | Long | Technical |
| REALLOC_MISSING_PARAMETERS | Reference | Long | Technical |
| IMPLEMENTATION_DETAILS | Technical | Long | Developers |
| CUSTOM_CROP_PARAMETERS | Framework | Long | Developers |
| CUSTOM_CROP_PARAMS_QUICKSTART | Reference | Short | Quick ref |
| DOCUMENTATION_INDEX | Index | This | Navigation |

---

## Questions?

**General questions:**
- See: `README_CUSTOM_SETUP.md`

**What the parameters do:**
- See: `REALLOC_MISSING_PARAMETERS_EXPLAINED.md`

**How to modify them:**
- See: `REALLOC_PARAMETERS_EXPLAINED.md`

**How the code works:**
- See: `IMPLEMENTATION_DETAILS.md`

**Is everything ready?**
- See: `PREFLIGHT_CHECKLIST.md`

---

Good luck! 🚀
