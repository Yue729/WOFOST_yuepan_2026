import os
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAW_DATA_PATH = Path("/Users/panyue/Desktop/final_data/")
input_file = RAW_DATA_PATH / "wofost_results_analysis.xlsx"
plot_dir = RAW_DATA_PATH / "2_yield_data" / "yield_gap_analysis_by_year"

# Create plot directory
plot_dir.mkdir(parents=True, exist_ok=True)

# Read the Excel file
df = pd.read_excel(input_file, sheet_name='Sheet2')

print(f"Loaded data: {df.shape[0]} rows")
print(f"Crops: {df['crop_name'].unique()}")
print(f"Years: {sorted(df['year'].unique())}")

# Normalize crop names for grouping
crop_groups = {
    'sugarbeet': 'sugarbeet',
    'sugar beet': 'sugarbeet',  # Handle space-separated version
    'potato': 'potato',
    'starch potato': 'potato',
    'ware potato': 'potato',
    'seed potato': 'potato',
    'barley': 'cereals',  # Combine barley and wheat
    'spring barley': 'cereals',
    'winter barley': 'cereals',
    'wheat': 'cereals',
    'spring wheat': 'cereals',
    'winter wheat': 'cereals',
    'seed_onion': 'onion',
    'seed onion': 'onion',
}

df['crop_group'] = df['crop_name'].str.strip().str.lower().map(crop_groups)

# Extract field region (ZW or DR from ID_field)
df['region'] = df['ID_field'].str[:2]

# Calculate relative yield gap to PP (%)
# gap_to_pp represents the difference between PP and actual
# Relative gap = (gap_to_pp / PP_yield) * 100
df['relative_gap_to_pp_pct'] = (df['gap_to_pp'] / df['PP_yield_t_ha']) * 100

print("\nData summary:")
print(f"Regions: {df['region'].unique()}")
print(f"Relative gap to PP - Mean: {df['relative_gap_to_pp_pct'].mean():.2f}%, Std: {df['relative_gap_to_pp_pct'].std():.2f}%")

# Create one plot per crop showing year and region comparison
for crop_group in sorted(df['crop_group'].unique()):
    crop_data = df[df['crop_group'] == crop_group].copy()
    
    print(f"\n=== {crop_group.upper()} ===")
    
    # Prepare data for plotting
    years = sorted(crop_data['year'].unique())
    
    # A4 landscape width with reduced height
    fig_width = 11.69
    fig_height = 6.0
    
    # Create plot
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), constrained_layout=True)
    
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
        
        print(f"Year {year}: ZW n={len(zw_data)}, DR n={len(dr_data)}")
    
    # Create box plots
    bp_zw = ax.boxplot(box_data_zw, positions=positions_zw, widths=width*0.8,
                       patch_artist=True, showmeans=True,
                       boxprops=dict(facecolor='#4169E1', alpha=0.7, edgecolor='#333333', linewidth=1.2),
                       medianprops=dict(color='#000000', linewidth=2),
                       meanprops=dict(marker='D', markerfacecolor='red', markeredgecolor='red', markersize=6),
                       whiskerprops=dict(color='#333333', linewidth=1.2),
                       capprops=dict(color='#333333', linewidth=1.2),
                       flierprops=dict(marker='o', markerfacecolor='#4169E1', markersize=4, alpha=0.5))
    
    bp_dr = ax.boxplot(box_data_dr, positions=positions_dr, widths=width*0.8,
                       patch_artist=True, showmeans=True,
                       boxprops=dict(facecolor='#FFD700', alpha=0.7, edgecolor='#333333', linewidth=1.2),
                       medianprops=dict(color='#000000', linewidth=2),
                       meanprops=dict(marker='D', markerfacecolor='red', markeredgecolor='red', markersize=6),
                       whiskerprops=dict(color='#333333', linewidth=1.2),
                       capprops=dict(color='#333333', linewidth=1.2),
                       flierprops=dict(marker='o', markerfacecolor='#FFD700', markersize=4, alpha=0.5))
    
    # Formatting
    ax.set_xlabel('Year', fontsize=14, fontweight='bold')
    ax.set_ylabel('Relative Yield Gap to PP (%)', fontsize=14, fontweight='bold')
    ax.tick_params(axis='both', labelsize=10)
    
    # Create a nice title with proper capitalization
    crop_title = crop_group.replace('_', ' ').title()
    if crop_group == 'cereals':
        crop_title = 'Cereals (Wheat & Barley)'
    
    ax.set_title(f'{crop_title}: Yield Gap to PP Distribution by Year', 
                 fontsize=16, fontweight='bold')
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(years)
    
    # Create custom legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#4169E1', edgecolor='#333333', label='ZW fields', alpha=0.7),
        Patch(facecolor='#FFD700', edgecolor='#333333', label='DR fields', alpha=0.7),
        plt.Line2D([0], [0], marker='D', color='w', markerfacecolor='red', markersize=8, label='Mean')
    ]
    ax.legend(handles=legend_elements, fontsize=12, loc='upper left')
    
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.axhline(y=0, color='black', linewidth=0.8)
    
    # Save plot
    safe_crop = crop_group.lower().replace(' ', '_')
    plot_path = plot_dir / f"{safe_crop}_yield_gap_by_year.png"
    fig.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    
    print(f"  ✓ Saved: {plot_path.name}")

print(f"\n✓ All plots saved to: {plot_dir}")
