# REALLOC Parameters Explained

## What They Do

REALLOC parameters control **biomass reallocation** - how the plant moves carbon and nutrients from vegetative parts (leaves, stems) to storage organs (roots, tubers, etc.) during the growing season.

## The 6 Parameters

### 1. **REALLOC_DVS** (Development Stage)
- **Current value:** 3.0
- **Range:** 0.0 to ~2.5 (crop maturity)
- **Meaning:** At what development stage does reallocation START?
  - DVS = 0: Germination
  - DVS = 1: Flowering
  - DVS = 2: Seed/fruit formation
  - DVS = 3: Maturity (post-harvest)
- **For sugarbeet:** 3.0 means reallocation starts after physiological maturity

### 2. **REALLOC_EFFICIENCY** (Transfer Efficiency)
- **Current value:** 1.0 (100%)
- **Range:** 0.0 to 1.0
- **Meaning:** How efficiently does biomass transfer to storage organs?
  - 1.0 = All reallocated biomass goes to storage
  - 0.5 = 50% lost, 50% to storage
  - 0.0 = No reallocation happens
- **For sugarbeet:** 1.0 = Perfect efficiency (no losses in moving sugars to roots)

### 3. **REALLOC_LEAF_FRACTION** (Leaf Reallocation Potential)
- **Current value:** 0.0
- **Range:** 0.0 to 1.0
- **Meaning:** What fraction of leaf biomass CAN be reallocated?
  - 1.0 = All leaf biomass can move to storage
  - 0.5 = Only 50% of leaf biomass available
  - 0.0 = Leaves CANNOT be reallocated (they stay on plant)
- **For sugarbeet:** 0.0 = Leaves stay on plant (not a storage organ)

### 4. **REALLOC_LEAF_RATE** (Daily Leaf Reallocation)
- **Current value:** 0.0
- **Range:** 0.0 to ~0.1 (per day)
- **Meaning:** How fast are leaves reallocated (per day)?
  - Only used if REALLOC_LEAF_FRACTION > 0
  - In kg/m²/day
- **For sugarbeet:** 0.0 = No leaf reallocation (because fraction = 0)

### 5. **REALLOC_STEM_FRACTION** (Stem Reallocation Potential)
- **Current value:** 0.0
- **Range:** 0.0 to 1.0
- **Meaning:** What fraction of stem biomass CAN be reallocated?
  - 1.0 = All stem biomass can move to storage
  - 0.0 = Stems stay on plant
- **For sugarbeet:** 0.0 = Stems stay (not a storage organ)

### 6. **REALLOC_STEM_RATE** (Daily Stem Reallocation)
- **Current value:** 0.0
- **Range:** 0.0 to ~0.1 (per day)
- **Meaning:** How fast are stems reallocated (per day)?
  - Only used if REALLOC_STEM_FRACTION > 0
  - In kg/m²/day
- **For sugarbeet:** 0.0 = No stem reallocation (because fraction = 0)

## Current Configuration Impact

With current values (all 0 except DVS = 3.0):
- ✓ **Leaves stay on plant** throughout growing season
- ✓ **Stems stay on plant** (not moved to roots)
- ✓ **Minimal translocation** to storage roots
- ✓ **Conservative model** - respects natural plant structure

## Scenarios: How to Modify Them

### Scenario 1: Strong Reallocation (Aggressive Storage)
```yaml
REALLOC_DVS: 1.5              # Start earlier (flowering)
REALLOC_EFFICIENCY: 0.95      # 95% efficiency
REALLOC_LEAF_FRACTION: 0.3    # 30% of leaves available
REALLOC_LEAF_RATE: 0.02       # 0.02 kg/m²/day
REALLOC_STEM_FRACTION: 0.2    # 20% of stems available
REALLOC_STEM_RATE: 0.01       # 0.01 kg/m²/day
```
**Effect:** Plant moves more resources to storage roots early, maximizing sugar storage.

### Scenario 2: Minimal Reallocation (Current)
```yaml
REALLOC_DVS: 3.0              # Start after maturity
REALLOC_EFFICIENCY: 1.0       # Perfect efficiency
REALLOC_LEAF_FRACTION: 0.0    # Leaves cannot reallocate
REALLOC_LEAF_RATE: 0.0        # No daily rate
REALLOC_STEM_FRACTION: 0.0    # Stems cannot reallocate
REALLOC_STEM_RATE: 0.0        # No daily rate
```
**Effect:** Plant keeps all leaves/stems. Most realistic for sugarbeet (leaves are harvested separately).

### Scenario 3: Moderate Reallocation
```yaml
REALLOC_DVS: 2.0              # Around grain filling stage
REALLOC_EFFICIENCY: 0.9       # 90% efficiency
REALLOC_LEAF_FRACTION: 0.1    # 10% of leaves available
REALLOC_LEAF_RATE: 0.005      # 0.005 kg/m²/day
REALLOC_STEM_FRACTION: 0.0    # Stems cannot reallocate
REALLOC_STEM_RATE: 0.0        # No stem reallocation
```
**Effect:** Moderate mobilization of leaf reserves to roots, typical for many crops.

## For Your Sugarbeet Model

**Recommendation:** Current settings are appropriate because:
1. **Sugarbeet leaves are harvested separately** - they're not meant to go to storage
2. **Stems are stalks** - not part of the storage root
3. **Storage happens mainly in roots** - not through reallocation from above
4. **DVS = 3.0 is safe** - no reallocation happens anyway

If you want to modify:
- **Increase storage:** Decrease REALLOC_DVS (start earlier)
- **Decrease reallocation:** Keep fractions at 0 (current setup)
- **Fine-tune:** Adjust individual parameters one at a time and compare model outputs

---

## Example: What Gets Reallocated

```
Plant Biomass Structure:
┌─ Leaves (REALLOC_LEAF_FRACTION = 0.0)
│  └─ Cannot go to storage
├─ Stems (REALLOC_STEM_FRACTION = 0.0)
│  └─ Cannot go to storage
└─ Roots (Storage organ)
   └─ Receives reallocated carbon
   └─ Receives nitrogen redistribution
```

With your current settings:
- Leaves: 100% stay as leaves → Later harvested as leaf biomass
- Stems: 100% stay as stems → Plant structural support
- Roots: Only receive new carbon fixed during the season
