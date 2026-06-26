import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Load yield gap data
df = pd.read_excel('/Users/panyue/Desktop/final_data/wofost_results_analysis.xlsx')

crop_mapping = {
    'barley': 'CEREALS',
    'spring barley': 'CEREALS',
    'winter barley': 'CEREALS',
    'wheat': 'CEREALS',
    'spring wheat': 'CEREALS',
    'winter wheat': 'CEREALS',
    'seed_onion': 'ONION',
    'seed onion': 'ONION',
    'potato': 'POTATO',
    'starch potato': 'POTATO',
    'ware potato': 'POTATO',
    'seed potato': 'POTATO',
    'sugarbeet': 'SUGARBEET',
    'sugar beet': 'SUGARBEET',
}
df['crop_group'] = df['crop_name'].str.strip().str.lower().map(crop_mapping)
df = df[df['crop_group'].notna()].copy()
df['region'] = df['ID_field'].str[:2]
df['relative_gap_to_pp_pct'] = (df['gap_to_pp'] / df['PP_yield_t_ha']) * 100
df = df.dropna(subset=['relative_gap_to_pp_pct', 'PP_yield_t_ha'])

# ── Load 2025 measured dry weight (t/ha) + std for sugarbeet, onion and potato ──────────
yield_dir = Path('/Users/panyue/Desktop/final_data/2_yield_data/yield_data_2025')
dry_weight_files = {
    'SUGARBEET': 'yield_sugar_beet_2025.xlsx',
    'ONION':     'yield_onion_2025.xlsx',
    'POTATO':    'yield_potato_2025.xlsx',
}
dm_2025 = {}   # {crop_group: {region: (mean, std)}}
for crop_group, fname in dry_weight_files.items():
    fpath = yield_dir / fname
    if fpath.exists():
        raw = pd.read_excel(fpath)
        raw['region'] = raw['ID_field'].str[:2]
        grp = raw.groupby('region').agg(
            dw_mean=('dry weight',        'mean'),
            dw_std =('standard deviation','mean'),
        ).reset_index()
        dm_2025[crop_group] = {row['region']: (row['dw_mean'], row['dw_std'])
                               for _, row in grp.iterrows()}
        print(f"{crop_group} dry weight 2025: {dm_2025[crop_group]}")
    else:
        print(f"⚠ {crop_group} file not found: {fname}")


# Create figure with 2x2 subplots
# A4 landscape width with reduced height, adjusted for 2x2 grid
fig_width = 11.69
fig_height = 10.0  # Taller for 2x2 layout
fig, axes = plt.subplots(2, 2, figsize=(fig_width, fig_height))
axes = axes.flatten()

crops = ['CEREALS', 'SUGARBEET', 'ONION', 'POTATO']
crop_titles = {
    'CEREALS': 'Cereals (Wheat & Barley)',
    'SUGARBEET': 'Sugar Beet',
    'ONION': 'Onion',
    'POTATO': 'Potato'
}
colors = {'ZW': '#1f77b4', 'DR': '#ff7f0e'}  # Blue for ZW, Orange for DR

for idx, crop in enumerate(crops):
    ax = axes[idx]
    crop_data = df[df['crop_group'] == crop]
    
    # Get unique years
    years = sorted(crop_data['year'].unique())
    
    # Prepare box plot data
    box_data_zw = []
    box_data_dr = []
    positions_zw = []
    positions_dr = []
    
    width = 0.35
    
    for i, year in enumerate(years):
        year_data = crop_data[crop_data['year'] == year]
        
        zw_data = year_data[year_data['region'] == 'ZW']['relative_gap_to_pp_pct'].dropna()
        dr_data = year_data[year_data['region'] == 'DR']['relative_gap_to_pp_pct'].dropna()
        
        if len(zw_data) > 0:
            box_data_zw.append(zw_data.values)
            positions_zw.append(i - width/2)
        
        if len(dr_data) > 0:
            box_data_dr.append(dr_data.values)
            positions_dr.append(i + width/2)
    
    # Create box plots
    bp_zw = ax.boxplot(box_data_zw, positions=positions_zw, widths=width*0.8,
                       patch_artist=True, showmeans=True,
                       boxprops=dict(facecolor=colors['ZW'], alpha=0.7, edgecolor='#333333', linewidth=1.2),
                       medianprops=dict(color='#000000', linewidth=2),
                       meanprops=dict(marker='D', markerfacecolor='red', markeredgecolor='red', markersize=6),
                       whiskerprops=dict(color='#333333', linewidth=1.2),
                       capprops=dict(color='#333333', linewidth=1.2),
                       flierprops=dict(marker='o', markerfacecolor=colors['ZW'], markersize=4, alpha=0.5))
    
    bp_dr = ax.boxplot(box_data_dr, positions=positions_dr, widths=width*0.8,
                       patch_artist=True, showmeans=True,
                       boxprops=dict(facecolor=colors['DR'], alpha=0.7, edgecolor='#333333', linewidth=1.2),
                       medianprops=dict(color='#000000', linewidth=2),
                       meanprops=dict(marker='D', markerfacecolor='red', markeredgecolor='red', markersize=6),
                       whiskerprops=dict(color='#333333', linewidth=1.2),
                       capprops=dict(color='#333333', linewidth=1.2),
                       flierprops=dict(marker='o', markerfacecolor=colors['DR'], markersize=4, alpha=0.5))
    
    # Formatting
    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('Relative Yield Gap to PP (%)', fontsize=12, fontweight='bold')
    ax.set_title(crop_titles[crop], fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(years, fontsize=10)
    ax.tick_params(axis='y', labelsize=10)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_ylim(-30, 80)
    
    # Create custom legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=colors['ZW'], edgecolor='#333333', label='ZW', alpha=0.7),
        Patch(facecolor=colors['DR'], edgecolor='#333333', label='DR', alpha=0.7),
        plt.Line2D([0], [0], marker='D', color='w', markerfacecolor='red', markersize=8, label='Mean')
    ]
    ax.legend(handles=legend_elements, fontsize=11, loc='upper left')

plt.tight_layout()
output_dir = Path('/Users/panyue/Desktop/final_data/2_yield_data/yield_gap_analysis_by_year')
output_dir.mkdir(parents=True, exist_ok=True)
plt.savefig(output_dir / 'combined_yield_gap_analysis.png', dpi=300, bbox_inches='tight')
print(f"✓ Combined plot saved to: {output_dir / 'combined_yield_gap_analysis.png'}")
plt.close()
