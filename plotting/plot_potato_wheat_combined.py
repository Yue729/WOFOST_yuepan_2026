"""
Create combined plots for potato and wheat showing all years (2023-2025) together
"""
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

# Create plot directory
plot_dir.mkdir(parents=True, exist_ok=True)

# ── Load actual (converted) yield from old analysis file ─────────────────────
old = pd.read_excel(OLD_INPUT_FILE, sheet_name='Sheet2')
old['ID_field'] = old['ID_field'].astype(str).str.strip()
actual_df = old[['ID_field', 'year', 'crop', 'converted_yield']].copy()
actual_df = actual_df.rename(columns={'crop': 'crop_name_field'})

# ── Load new PP results, convert TWSO kg/ha → t/ha ───────────────────────────
pp_raw = pd.read_excel(PP_RESULTS_FILE)[['field_id', 'day', 'crop_name', 'PP_TWSO']].copy()
pp_raw = pp_raw.rename(columns={'field_id': 'ID_field', 'crop_name': 'crop_name_pp'})
pp_raw['PP_yield_t_ha'] = pp_raw['PP_TWSO'] / 1000.0
pp_raw['ID_field'] = pp_raw['ID_field'].astype(str).str.strip()
pp_raw['year'] = pd.to_datetime(pp_raw['day']).dt.year

# ── Load new WLP results, convert TWSO kg/ha → t/ha ──────────────────────────
wlp_raw = pd.read_excel(WLP_RESULTS_FILE)[['field_id', 'day', 'crop_name', 'WLP_TWSO']].copy()
wlp_raw = wlp_raw.rename(columns={'field_id': 'ID_field', 'crop_name': 'crop_name_wlp'})
wlp_raw['WLP_yield_t_ha'] = wlp_raw['WLP_TWSO'] / 1000.0
wlp_raw['ID_field'] = wlp_raw['ID_field'].astype(str).str.strip()
wlp_raw['year'] = pd.to_datetime(wlp_raw['day']).dt.year

# ── Merge all three on ID_field + year ───────────────────────────────────────
df = actual_df.merge(pp_raw[['ID_field', 'year', 'crop_name_pp', 'PP_yield_t_ha']],
                     on=['ID_field', 'year'], how='outer')
df = df.merge(wlp_raw[['ID_field', 'year', 'crop_name_wlp', 'WLP_yield_t_ha']],
              on=['ID_field', 'year'], how='outer')

df['crop_name'] = (df['crop_name_field']
                   .combine_first(df['crop_name_pp'])
                   .combine_first(df['crop_name_wlp']))

# ── Filter to study period 2023–2025 only ────────────────────────────────────
df = df[df['year'].between(2023, 2025)].copy()

# Normalize crop names
crop_groups = {
    'potato': 'potato',
    'starch potato': 'potato',
    'ware potato': 'potato',
    'seed potato': 'potato',
    'wheat': 'wheat',
    'spring wheat': 'wheat',
    'winter wheat': 'wheat',
}

df['crop_group'] = df['crop_name'].str.strip().str.lower().map(crop_groups)
df = df[df['crop_group'].notna()].copy()

print(f"Loaded data: {df.shape[0]} rows")
print(f"Crop groups: {sorted(df['crop_group'].unique())}")
print(f"Years: {sorted(df['year'].unique())}")

# Define colors for years
year_colors = {
    2023: '#1f77b4',  # Blue
    2024: '#ff7f0e',  # Orange
    2025: '#2ca02c',  # Green
}

# Function to create separate plots for each year
def create_year_plots(crop_name, crop_data):
    """Create separate absolute and relative plots for each year"""
    
    years = sorted(crop_data['year'].unique())
    plot_paths = []
    
    for year in years:
        year_data = crop_data[crop_data['year'] == year].copy()
        
        if year_data.empty:
            continue
        
        print(f"\n  Processing {crop_name} - {year}: {len(year_data)} records")
        
        # Sort by yield gap
        year_data['gap_to_pp'] = year_data['PP_yield_t_ha'] - year_data['converted_yield']
        year_data = year_data.sort_values('gap_to_pp', ascending=False).reset_index(drop=True)
        
        # Prepare data
        x = np.arange(len(year_data))
        actual = year_data['converted_yield'].to_numpy(dtype=float)
        wlp_yield = year_data['WLP_yield_t_ha'].to_numpy(dtype=float)
        pp_yield = year_data['PP_yield_t_ha'].to_numpy(dtype=float)
        field_labels = year_data['ID_field'].astype(str)
        
        # Calculate relative values
        denom = np.where(pp_yield > 0, pp_yield, np.nan)
        actual_pct = actual / denom * 100
        wlp_pct = wlp_yield / denom * 100
        pp_pct = np.full_like(pp_yield, 100.0)
        
        colors = {'wlp': '#FFD700', 'pp': '#4169E1'}
        
        # A4 landscape width with reduced height
        fig_width = 11.69
        fig_height = 6.0
        
        # ═══════════════════════════════════════════════════════════════════
        # PLOT 1: Absolute Yield
        # ═══════════════════════════════════════════════════════════════════
        fig_abs, ax_abs = plt.subplots(figsize=(fig_width, fig_height), constrained_layout=True)
        
        ax_abs.bar(x, pp_yield, width=0.6, color=colors['pp'], edgecolor='#333333', 
                   label='PP yield (TWSO)', alpha=0.7)
        ax_abs.bar(x, wlp_yield, width=0.6, color=colors['wlp'], edgecolor='#333333', 
                   label='WLP yield (TWSO)', alpha=0.9)
        ax_abs.plot(x, actual, linestyle=':', linewidth=2.5, marker='o', markersize=5,
                    color='#D32F2F', label='Actual yield', zorder=4)
        
        ax_abs.set_ylabel('Yield (t ha$^{-1}$)', fontsize=14, fontweight='bold')
        ax_abs.set_xlabel('Field', fontsize=14, fontweight='bold')
        ax_abs.set_title(f'{crop_name.title()} {year}: Absolute Yield', fontsize=16, fontweight='bold')
        ax_abs.set_xticks(x)
        ax_abs.set_xticklabels([])  # Remove field name labels
        ax_abs.tick_params(axis='y', labelsize=10)
        ax_abs.legend(loc='upper right', fontsize=12, frameon=True)
        ax_abs.grid(axis='y', alpha=0.3)
        ax_abs.set_axisbelow(True)
        ax_abs.margins(x=0.01)
        
        # Save absolute plot
        safe_crop = crop_name.lower().replace(' ', '_')
        plot_path_abs = plot_dir / f"{safe_crop}_{year}_absolute_yield.png"
        fig_abs.savefig(plot_path_abs, dpi=300, bbox_inches='tight')
        plt.close(fig_abs)
        plot_paths.append(plot_path_abs)
        print(f"    ✓ Saved: {plot_path_abs.name}")
        
        # ═══════════════════════════════════════════════════════════════════
        # PLOT 2: Relative Yield
        # ═══════════════════════════════════════════════════════════════════
        fig_rel, ax_rel = plt.subplots(figsize=(fig_width, fig_height), constrained_layout=True)
        
        ax_rel.bar(x, pp_pct, width=0.6, color=colors['pp'], edgecolor='#333333', 
                   label='PP yield (100%)', alpha=0.7)
        ax_rel.bar(x, wlp_pct, width=0.6, color=colors['wlp'], edgecolor='#333333', 
                   label='WLP yield', alpha=0.9)
        ax_rel.plot(x, actual_pct, linestyle=':', linewidth=2.5, marker='o', markersize=5,
                    color='#D32F2F', label='Actual yield', zorder=4)
        
        ax_rel.set_ylabel('Share of PP yield (%)', fontsize=14, fontweight='bold')
        ax_rel.set_xlabel('Field', fontsize=14, fontweight='bold')
        ax_rel.set_ylim(0, 120)
        ax_rel.set_title(f'{crop_name.title()} {year}: Relative Yield (% of PP)', fontsize=16, fontweight='bold')
        ax_rel.set_xticks(x)
        ax_rel.set_xticklabels([])  # Remove field name labels
        ax_rel.tick_params(axis='y', labelsize=10)
        ax_rel.legend(loc='upper right', fontsize=12, frameon=True)
        ax_rel.grid(axis='y', alpha=0.3)
        ax_rel.set_axisbelow(True)
        ax_rel.margins(x=0.01)
        
        # Save relative plot
        plot_path_rel = plot_dir / f"{safe_crop}_{year}_relative_yield.png"
        fig_rel.savefig(plot_path_rel, dpi=300, bbox_inches='tight')
        plt.close(fig_rel)
        plot_paths.append(plot_path_rel)
        print(f"    ✓ Saved: {plot_path_rel.name}")
    
    return plot_paths

# Generate plots for potato and wheat
for crop_group in ['potato', 'wheat']:
    crop_data = df[df['crop_group'] == crop_group]
    if not crop_data.empty:
        print(f"\nProcessing {crop_group}: {len(crop_data)} total records")
        create_year_plots(crop_group, crop_data)
    else:
        print(f"⚠ No data for {crop_group}")

print(f"\n✓ All combined plots saved to: {plot_dir}")
