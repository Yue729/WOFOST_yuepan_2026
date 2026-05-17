import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Load yield gap data
df = pd.read_excel('/Users/panyue/Desktop/final_data/wofost_results_analysis.xlsx')

crop_mapping = {
    'barley': 'CEREAL_BARLEY',
    'wheat': 'CEREAL_WHEAT',
    'seed_onion': 'ONION',
    'potato': 'POTATO'
}
df['crop_group'] = df['crop_name'].map(crop_mapping)
df = df[df['crop_group'].notna()].copy()
df['region'] = df['ID_field'].str[:2]
df['relative_gap_to_pp_pct'] = (df['gap_to_pp'] / df['PP_yield_t_ha']) * 100
df = df.dropna(subset=['relative_gap_to_pp_pct', 'PP_yield_t_ha'])

# ── Load 2025 measured dry weight (t/ha) + std for onion and potato ──────────
yield_dir = Path('/Users/panyue/Desktop/final_data/2_yield_data/yield_data_2025')
dry_weight_files = {
    'ONION':  'yield_onion_2025.xlsx',
    'POTATO': 'yield_potato_2025.xlsx',
}
dm_2025 = {}   # {crop_group: {region: (mean, std)}}
for crop_group, fname in dry_weight_files.items():
    raw = pd.read_excel(yield_dir / fname)
    raw['region'] = raw['ID_field'].str[:2]
    grp = raw.groupby('region').agg(
        dw_mean=('dry weight',        'mean'),
        dw_std =('standard deviation','mean'),
    ).reset_index()
    dm_2025[crop_group] = {row['region']: (row['dw_mean'], row['dw_std'])
                           for _, row in grp.iterrows()}
    print(f"{crop_group} dry weight 2025: {dm_2025[crop_group]}")


# Create figure with 2x2 subplots
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
axes = axes.flatten()

crops = ['CEREAL_BARLEY', 'CEREAL_WHEAT', 'ONION', 'POTATO']
colors = {'ZW': '#1f77b4', 'DR': '#ff7f0e'}  # Blue for ZW, Orange for DR

for idx, crop in enumerate(crops):
    ax = axes[idx]
    crop_data = df[df['crop_group'] == crop]
    
    # Group by year and region
    grouped = crop_data.groupby(['year', 'region'])['relative_gap_to_pp_pct'].agg(['mean', 'std', 'count']).reset_index()
    
    # Get unique years
    years = sorted(grouped['year'].unique())
    zw_years = grouped[grouped['region'] == 'ZW']['year'].values
    dr_years = grouped[grouped['region'] == 'DR']['year'].values
    
    # Prepare data for plotting
    x_pos = np.arange(len(years))
    width = 0.35
    
    zw_means = []
    zw_stds = []
    dr_means = []
    dr_stds = []
    
    for year in years:
        zw_data = grouped[(grouped['year'] == year) & (grouped['region'] == 'ZW')]
        dr_data = grouped[(grouped['year'] == year) & (grouped['region'] == 'DR')]
        
        if not zw_data.empty:
            zw_means.append(zw_data['mean'].values[0])
            zw_stds.append(zw_data['std'].values[0] if not np.isnan(zw_data['std'].values[0]) else 0)
        else:
            zw_means.append(0)
            zw_stds.append(0)
        
        if not dr_data.empty:
            dr_means.append(dr_data['mean'].values[0])
            dr_stds.append(dr_data['std'].values[0] if not np.isnan(dr_data['std'].values[0]) else 0)
        else:
            dr_means.append(0)
            dr_stds.append(0)
    
    # Plot bars
    bars1 = ax.bar(x_pos - width/2, zw_means, width, label='ZW', color=colors['ZW'], 
                    yerr=zw_stds, capsize=5, alpha=0.8, error_kw={'elinewidth': 1.5})
    bars2 = ax.bar(x_pos + width/2, dr_means, width, label='DR', color=colors['DR'], 
                    yerr=dr_stds, capsize=5, alpha=0.8, error_kw={'elinewidth': 1.5})
    
    # Add value labels on bars
    zw_stds_clean = [s if not np.isnan(s) else 0 for s in zw_stds]
    dr_stds_clean = [s if not np.isnan(s) else 0 for s in dr_stds]
    max_zw_std = max(zw_stds_clean) if zw_stds_clean else 1
    max_dr_std = max(dr_stds_clean) if dr_stds_clean else 1
    max_std = max(max_zw_std, max_dr_std)
    
    for i, (zw, dr) in enumerate(zip(zw_means, dr_means)):
        if zw > 0:
            ax.text(i - width/2, zw + max_std*0.5, f'{zw:.1f}%', 
                   ha='center', va='bottom', fontsize=9, fontweight='bold')
        if dr > 0:
            ax.text(i + width/2, dr + max_std*0.5, f'{dr:.1f}%', 
                   ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # Formatting
    ax.set_xlabel('Year', fontsize=11, fontweight='bold')
    ax.set_ylabel('Relative Yield Gap to PP (%)', fontsize=11, fontweight='bold')
    ax.set_title(crop.replace('_', ' '), fontsize=12, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(years)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_ylim(0, 80)

    # ── Overlay 2025 measured dry weight on secondary Y-axis ─────────────────
    if crop in dm_2025 and 2025 in years:
        ax2 = ax.twinx()
        year_2025_x = years.index(2025)
        dm_colors = {'ZW': '#1a5276', 'DR': '#7d3c00'}  # Darker than bar colors
        for region, x_offset in [('ZW', -width / 2), ('DR', +width / 2)]:
            if region in dm_2025[crop]:
                dw_mean, dw_std = dm_2025[crop][region]
                x = year_2025_x + x_offset
                ax2.errorbar(x, dw_mean, yerr=dw_std, fmt='D',
                             color=dm_colors[region], markersize=7,
                             capsize=5, linewidth=2, zorder=5,
                             label=f'{region} dry weight 2025')
                ax2.text(x, dw_mean + dw_std + 0.3, f'{dw_mean:.1f}',
                         ha='center', va='bottom', fontsize=8,
                         color=dm_colors[region], fontweight='bold')
        ax2.set_ylabel('Measured dry weight (t/ha)', fontsize=10, color='#555555')
        ax2.tick_params(axis='y', labelcolor='#555555')
        ax2.set_ylim(0, 40)
        ax2.legend(loc='center right', fontsize=8)

    ax.legend(loc='upper right', fontsize=10)

plt.tight_layout()
output_dir = Path('/Users/panyue/Desktop/final_data/2_yield_data/yield_gap_analysis_by_year')
output_dir.mkdir(parents=True, exist_ok=True)
plt.savefig(output_dir / 'combined_yield_gap_analysis.png', dpi=300, bbox_inches='tight')
print(f"✓ Combined plot saved to: {output_dir / 'combined_yield_gap_analysis.png'}")
plt.close()
