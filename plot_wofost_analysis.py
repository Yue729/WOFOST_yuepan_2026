import os
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAW_DATA_PATH = Path("/Users/panyue/Desktop/final_data/")
MODEL_RESULTS_DIR = Path(__file__).parent / "output" / "model_results"
PP_RESULTS_FILE  = MODEL_RESULTS_DIR / "WOFOST73_PP_results.xlsx"
WLP_RESULTS_FILE = MODEL_RESULTS_DIR / "WOFOST73_WLP_CWB_results.xlsx"
OLD_INPUT_FILE   = RAW_DATA_PATH / "wofost_results_analysis.xlsx"
plot_dir = RAW_DATA_PATH / "2_yield_data" / "yield_plots_wofost_analysis"
yield_dir = RAW_DATA_PATH / "2_yield_data" / "yield_data_2025"

# Create plot directory
plot_dir.mkdir(parents=True, exist_ok=True)

# ── Load actual (converted) yield from old analysis file ─────────────────────
old = pd.read_excel(OLD_INPUT_FILE, sheet_name='Sheet2')
old['ID_field'] = old['ID_field'].astype(str).str.strip()
# Keep actual yield + crop name from field records
actual_df = old[['ID_field', 'year', 'crop', 'converted_yield']].copy()
actual_df = actual_df.rename(columns={'crop': 'crop_name_field'})

# ── Load new PP results, convert TWSO kg/ha → t/ha ───────────────────────────
pp_raw = pd.read_excel(PP_RESULTS_FILE)[['field_id', 'day', 'crop_name', 'PP_TWSO']].copy()
pp_raw = pp_raw.rename(columns={'field_id': 'ID_field', 'crop_name': 'crop_name_pp'})
pp_raw['PP_yield_t_ha'] = pp_raw['PP_TWSO'] / 1000.0
pp_raw['ID_field'] = pp_raw['ID_field'].astype(str).str.strip()
# Use harvest year (day column) not sowing year
pp_raw['year'] = pd.to_datetime(pp_raw['day']).dt.year

# ── Load new WLP results, convert TWSO kg/ha → t/ha ──────────────────────────
wlp_raw = pd.read_excel(WLP_RESULTS_FILE)[['field_id', 'day', 'crop_name', 'WLP_TWSO']].copy()
wlp_raw = wlp_raw.rename(columns={'field_id': 'ID_field', 'crop_name': 'crop_name_wlp'})
wlp_raw['WLP_yield_t_ha'] = wlp_raw['WLP_TWSO'] / 1000.0
wlp_raw['ID_field'] = wlp_raw['ID_field'].astype(str).str.strip()
# Use harvest year (day column) not sowing year
wlp_raw['year'] = pd.to_datetime(wlp_raw['day']).dt.year

# ── Merge all three on ID_field + year ───────────────────────────────────────
df = actual_df.merge(pp_raw[['ID_field', 'year', 'crop_name_pp', 'PP_yield_t_ha']],
                     on=['ID_field', 'year'], how='outer')
df = df.merge(wlp_raw[['ID_field', 'year', 'crop_name_wlp', 'WLP_yield_t_ha']],
              on=['ID_field', 'year'], how='outer')

# ── Combine crop names from all sources ──────────────────────────────────────
# Priority: field record crop name > PP model crop name > WLP model crop name
df['crop_name'] = (df['crop_name_field']
                   .combine_first(df['crop_name_pp'])
                   .combine_first(df['crop_name_wlp']))

# ── Recalculate yield gaps: PP/WLP - actual ───────────────────────────────────
df['gap_to_pp']  = df['PP_yield_t_ha']  - df['converted_yield']
df['gap_to_wlp'] = df['WLP_yield_t_ha'] - df['converted_yield']

print(f"Loaded data: {df.shape[0]} rows")
print(f"Crops: {df['crop_name'].unique()}")
print(f"Years: {sorted(df['year'].dropna().astype(int).unique())}")

# ── Filter to study period 2023–2025 only ────────────────────────────────────
df = df[df['year'].between(2023, 2025)].copy()
print(f"After year filter (2023–2025): {df.shape[0]} rows")

# Normalize crop names for grouping
crop_groups = {
    'sugarbeet': 'sugarbeet',
    'potato': 'potato',
    'starch potato': 'potato',
    'ware potato': 'potato',
    'barley': 'cereal_barley',
    'spring barley': 'cereal_barley',
    'winter barley': 'cereal_barley',
    'wheat': 'cereal_wheat',
    'spring wheat': 'cereal_wheat',
    'winter wheat': 'cereal_wheat',
    'seed_onion': 'onion',
    'seed onion': 'onion',
    'onion': 'onion',
}

df['crop_group'] = df['crop_name'].str.strip().str.lower().map(crop_groups)
df = df[df['crop_group'].notna()].copy()
print(f"After crop group filter: {df.shape[0]} rows ({df['crop_group'].nunique()} crop groups)")

# ── Load 2025 dry weight data (field-level) for sugarbeet, onion, potato ──────
dry_weight_files = {
    'sugarbeet': 'yield_sugar_beet_2025.xlsx',
    'onion':     'yield_onion_2025.xlsx',
    'potato':    'yield_potato_2025.xlsx',
}
dw_data = {}  # {crop_group: DataFrame with ID_field, dw_mean, dw_std}
for crop_group, fname in dry_weight_files.items():
    fpath = yield_dir / fname
    if fpath.exists():
        raw = pd.read_excel(fpath)[['ID_field', 'dry weight', 'standard deviation']].copy()
        raw = raw.rename(columns={'dry weight': 'dw_mean', 'standard deviation': 'dw_std'})
        dw_data[crop_group] = raw
        print(f"Loaded dry weight for {crop_group}: {len(raw)} records")
    else:
        print(f"  ⚠ Not found: {fpath}")

# ── Load 2025 grain yield for wheat and barley ───────────────────────────────
cereal_fpath = yield_dir / 'yield_cereal_2025.xlsx'
if cereal_fpath.exists():
    cereal_raw = pd.read_excel(cereal_fpath)
    grain_cols = [c for c in cereal_raw.columns if 'Dry matter yield grain' in c and c.startswith('P')]
    cereal_raw['dw_mean'] = cereal_raw[grain_cols].mean(axis=1)
    cereal_raw['dw_std']  = cereal_raw[grain_cols].std(axis=1)
    cereal_raw['crop_lower'] = cereal_raw['Crop'].str.strip().str.lower()
    for crop_group, keyword in [('cereal_barley', 'barley'), ('cereal_wheat', 'wheat')]:
        subset = cereal_raw[cereal_raw['crop_lower'].str.contains(keyword)][['ID_field', 'dw_mean', 'dw_std']].copy()
        if not subset.empty:
            dw_data[crop_group] = subset
            print(f"Loaded grain yield for {crop_group}: {len(subset)} records")
else:
    print(f"  ⚠ Not found: {cereal_fpath}")

def _configure_axes(axes_list, x, field_labels):
    """Apply common x-axis settings to a list of axes."""
    for ax in axes_list:
        ax.set_xticks(x)
        ax.set_xticklabels(field_labels, rotation=55, ha='right')
        ax.tick_params(axis='x', labelsize=9, pad=6)
        ax.margins(x=0.02)
        ax.grid(axis='y', alpha=0.25)
        ax.set_axisbelow(True)


def _overlay_dw(ax_abs, ax_rel, dw_df, fields, pp_yield, color, label):
    """Overlay measured dry weight (absolute + relative) on the given axes."""
    dw_vals, dw_errs, dw_xpos = [], [], []
    dw_pct_vals, dw_pct_errs = [], []
    for xi, (field, pp_val) in enumerate(zip(fields, pp_yield)):
        row = dw_df[dw_df['ID_field'] == field]
        if not row.empty and pp_val > 0:
            dw_mean = row['dw_mean'].values[0]
            dw_std  = row['dw_std'].values[0]
            dw_vals.append(dw_mean)
            dw_errs.append(dw_std if not np.isnan(dw_std) else 0)
            dw_xpos.append(xi)
            dw_pct_vals.append(dw_mean / pp_val * 100)
            dw_pct_errs.append(dw_std / pp_val * 100 if not np.isnan(dw_std) else 0)
    if dw_xpos:
        kw = dict(fmt='D', color=color, markersize=8, capsize=5, linewidth=2,
                  linestyle='none', markeredgewidth=2, zorder=10)
        ax_abs.errorbar(dw_xpos, dw_vals, yerr=dw_errs, label=label, **kw)
        ax_rel.errorbar(dw_xpos, dw_pct_vals, yerr=dw_pct_errs, label=label, **kw)


# Group by crop and year
for crop_group in sorted(df['crop_group'].dropna().unique()):
    crop_data = df[df['crop_group'] == crop_group]

    for year in sorted(crop_data['year'].unique()):
        year_data = crop_data[crop_data['year'] == year].copy()

        if year_data.empty:
            continue

        print(f"\nProcessing {crop_group} - {year}: {len(year_data)} records")

        # Sort by field for consistent X-axis ordering
        year_data = year_data.sort_values('ID_field').reset_index(drop=True)
        year_data['field_label'] = year_data['ID_field'].astype(str)

        x = np.arange(len(year_data))
        actual    = year_data['converted_yield'].to_numpy(dtype=float)
        wlp_yield = year_data['WLP_yield_t_ha'].to_numpy(dtype=float)
        pp_yield  = year_data['PP_yield_t_ha'].to_numpy(dtype=float)

        denom      = np.where(pp_yield > 0, pp_yield, np.nan)
        actual_pct = actual    / denom * 100
        wlp_pct    = wlp_yield / denom * 100
        pp_pct     = np.full_like(pp_yield, 100.0)

        colors = {'wlp': '#FFD700', 'pp': '#4169E1'}
        width  = max(14, len(year_data) * 0.7)

        # ── All crops: 1×2 layout ────────────────────────────────────────────
        fig, axes = plt.subplots(1, 2, figsize=(width, 7), constrained_layout=True)

        axes[0].bar(x, pp_yield,  width=0.6, color=colors['pp'],  edgecolor='#333333', label='PP yield (TWSO)',  alpha=0.7)
        axes[0].bar(x, wlp_yield, width=0.6, color=colors['wlp'], edgecolor='#333333', label='WLP yield (TWSO)', alpha=0.9)
        axes[0].plot(x, actual, linestyle=':', linewidth=2.5, marker='o', markersize=5,
                     color='#D32F2F', label='Actual yield', zorder=4)
        axes[0].set_ylabel('Yield (t ha$^{-1}$)')
        axes[0].set_title('Absolute yield')

        axes[1].bar(x, pp_pct,  width=0.6, color=colors['pp'],  edgecolor='#333333', label='PP yield (100%)', alpha=0.7)
        axes[1].bar(x, wlp_pct, width=0.6, color=colors['wlp'], edgecolor='#333333', label='WLP yield',       alpha=0.9)
        axes[1].plot(x, actual_pct, linestyle=':', linewidth=2.5, marker='o', markersize=5,
                     color='#D32F2F', label='Actual yield', zorder=4)
        axes[1].set_ylabel('Share of PP yield (%)')
        axes[1].set_ylim(0, 120)
        axes[1].set_title('Relative to PP')

        # Measured dry weight / grain yield overlay (2025 only)
        if year == 2025 and crop_group in dw_data:
            dw_label = 'Measured grain yield' if 'cereal' in crop_group else 'Measured dry weight'
            _overlay_dw(axes[0], axes[1], dw_data[crop_group],
                        year_data['ID_field'], pp_yield,
                        '#1a7a1a', dw_label)

        _configure_axes(axes, x, year_data['field_label'])

        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc='outside lower center', ncol=4, frameon=False)

        # Title and save
        pretty_crop = crop_group.replace('_', ' ').title()
        fig.suptitle(f'{pretty_crop} {year}: actual vs WLP vs PP', fontsize=14)

        safe_crop = crop_group.lower().replace(' ', '_')
        plot_path = plot_dir / f"{safe_crop}_{year}_yield_comparison.png"
        fig.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close(fig)

        print(f"  ✓ Saved: {plot_path.name}")

print(f"\n✓ All plots saved to: {plot_dir}")
