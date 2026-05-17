# The 6 Missing REALLOC Parameters - Complete Explanation

## Question: What are the missing parameters? What do they stand for?

## Answer: The 6 REALLOC Parameters

REALLOC is short for **REALLOCation** - the process of moving biomass (carbon, nitrogen) from one plant part to another during grain/fruit/root filling.

### Parameter Breakdown

```
REALLOC_DVS
├─ Stands for: REALLOCation at Development Stage
├─ Current value: 3.0
├─ Range: 0.0 (germination) to 2.0+ (maturity)
└─ Meaning: At what growth stage does biomass reallocation START?
    └─ 0 = Never
    └─ 1.0 = Flowering stage
    └─ 2.0 = Grain/fruit filling
    └─ 3.0 = Post-maturity (very late)
```

```
REALLOC_EFFICIENCY
├─ Stands for: Efficiency of REALLOCation transfer
├─ Current value: 1.0
├─ Range: 0.0 to 1.0
└─ Meaning: How much of reallocated biomass actually reaches storage?
    └─ 0.0 = 0% efficiency (no reallocation works)
    └─ 0.5 = 50% efficiency (half lost, half stored)
    └─ 1.0 = 100% efficiency (perfect transfer)
```

```
REALLOC_LEAF_FRACTION
├─ Stands for: Fraction of LEAF biomass available for REALLOCation
├─ Current value: 0.0
├─ Range: 0.0 to 1.0
└─ Meaning: What % of leaf mass can be moved to storage organs?
    └─ 0.0 = Leaves CANNOT be reallocated (stay on plant)
    └─ 0.5 = 50% of leaf biomass available for relocation
    └─ 1.0 = 100% of leaves could be reallocated
```

```
REALLOC_LEAF_RATE
├─ Stands for: Rate of LEAF REALLOCation per day
├─ Current value: 0.0
├─ Range: 0.0 to ~0.1 kg/m²/day
└─ Meaning: How fast do leaves reallocate? (only if REALLOC_LEAF_FRACTION > 0)
    └─ Units: kg dry matter per m² per day
    └─ 0.0 = No daily reallocation
    └─ 0.05 = 50g/m² of leaf biomass moves per day
```

```
REALLOC_STEM_FRACTION
├─ Stands for: Fraction of STEM biomass available for REALLOCation
├─ Current value: 0.0
├─ Range: 0.0 to 1.0
└─ Meaning: What % of stem mass can be moved to storage organs?
    └─ 0.0 = Stems CANNOT be reallocated (stay as structural support)
    └─ 0.5 = 50% of stem biomass available
    └─ 1.0 = 100% of stems could be reallocated
```

```
REALLOC_STEM_RATE
├─ Stands for: Rate of STEM REALLOCation per day
├─ Current value: 0.0
├─ Range: 0.0 to ~0.1 kg/m²/day
└─ Meaning: How fast do stems reallocate? (only if REALLOC_STEM_FRACTION > 0)
    └─ Units: kg dry matter per m² per day
    └─ 0.0 = No daily reallocation
    └─ 0.03 = 30g/m² of stem biomass moves per day
```

## Why These Matter

### Plant Physiology
During growth, plants prioritize:
1. **Early growth**: Build leaves and stems (photosynthesis apparatus)
2. **Reproduction**: Develop grains, fruits, or storage organs
3. **Filling**: Move reserves FROM leaves/stems TO storage organs

REALLOC parameters control step 3.

### Example: Wheat
```
Timeline:
├─ DVS 0-1: Build leaves/stems
├─ DVS 1-1.5: Flower
├─ DVS 1.5-2.0: Grain filling (REALLOC starts)
│  └─ REALLOC_DVS might be 1.5 (start at flowering)
│  └─ Leaves and stems start losing weight
│  └─ Grains get heavier
└─ DVS 2.0+: Maturity (reallocation ends)
```

### Example: Sugarbeet (Current)
```
Timeline:
├─ DVS 0-2: Build leaves/stems AND storage roots
├─ DVS 2-3: Late season (continued growth)
└─ DVS 3+: Maturity (REALLOC_DVS=3.0, NO reallocation)
   └─ Leaves stay on plant (harvested separately)
   └─ Stems stay (structural support)
   └─ Roots receive new sugars (not reallocated)
```

## Your Current Configuration

```
REALLOC_DVS: 3.0
├─ Reallocation starts AFTER normal harvest
├─ Effectively: NO reallocation during growing season
└─ Result: Conservative model

REALLOC_EFFICIENCY: 1.0
├─ 100% efficiency (theoretical maximum)
├─ Safe assumption
└─ Only matters if other parameters allow reallocation

REALLOC_LEAF_FRACTION: 0.0
├─ Leaves CANNOT be reallocated
├─ Realistic for sugarbeet (separate leaf harvest)
└─ Leaves stay photosynthesizing

REALLOC_LEAF_RATE: 0.0
├─ Ignored (because REALLOC_LEAF_FRACTION = 0)
└─ No daily leaf reallocation

REALLOC_STEM_FRACTION: 0.0
├─ Stems CANNOT be reallocated
├─ Realistic (stems are structural)
└─ Plant keeps structural support

REALLOC_STEM_RATE: 0.0
├─ Ignored (because REALLOC_STEM_FRACTION = 0)
└─ No daily stem reallocation
```

## Effect on Model Simulation

With these settings:
- ✓ Leaves remain on plant throughout season
- ✓ Leaves continue photosynthesizing until harvest
- ✓ Stems provide structural support
- ✓ Storage roots receive newly fixed carbon (not reallocated reserves)
- ✓ Result: Realistic sugarbeet growth simulation

## If You Wanted to Change It

### To promote MORE storage (aggressive):
```yaml
REALLOC_DVS: 1.5           # Start at flowering
REALLOC_LEAF_FRACTION: 0.2 # 20% of leaves available
REALLOC_LEAF_RATE: 0.01    # 10g/m² per day
REALLOC_STEM_FRACTION: 0.1 # 10% of stems available
REALLOC_STEM_RATE: 0.005   # 5g/m² per day
```
→ Result: More reserves go to storage roots, less to leaves/stems

### To keep it conservative (current):
```yaml
REALLOC_DVS: 3.0           # Never during normal season
REALLOC_LEAF_FRACTION: 0.0 # Leaves cannot move
REALLOC_STEM_FRACTION: 0.0 # Stems cannot move
```
→ Result: Minimal reallocation, very realistic

## Why You Need Them

WOFOST73 requires these 6 parameters because:
1. They're part of the standard WOFOST model structure
2. They control how biomass is partitioned
3. All crops go through reallocation phases
4. Without them, the model is incomplete

Even if you set them all to 0 (no reallocation), WOFOST still needs the parameters to be present and defined.

## Summary Table

| Parameter | Your Value | What It Means |
|-----------|-----------|---------------|
| REALLOC_DVS | 3.0 | Start reallocation after harvest (doesn't happen) |
| REALLOC_EFFICIENCY | 1.0 | 100% transfer efficiency (theoretical) |
| REALLOC_LEAF_FRACTION | 0.0 | Leaves stay (not reallocated) |
| REALLOC_LEAF_RATE | 0.0 | No daily leaf reallocation |
| REALLOC_STEM_FRACTION | 0.0 | Stems stay (not reallocated) |
| REALLOC_STEM_RATE | 0.0 | No daily stem reallocation |
| **Net Effect** | — | **Minimal reallocation = Conservative model** |

---

**Bottom line:** These 6 parameters control biomass movement during storage organ filling. Your settings keep them at minimum/zero, which is appropriate for sugarbeet where leaves and stems are part of the harvest, not just source organs for storage.
