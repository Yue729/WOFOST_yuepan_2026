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
    'potato': 'potato',
    'barley': 'cereal_barley',
    'wheat': 'cereal_wheat',
    'seed_onion': 'onion',
}

df['crop_group'] = df['crop_name'].map(crop_groups)

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
    
    # Group by year and region, calculate mean gap
    grouped = crop_data.groupby(['year', 'region']).agg({
        'relative_gap_to_pp_pct': ['mean', 'std', 'count']
    }).reset_index()
    grouped.columns = ['year', 'region', 'mean_gap', 'std_gap', 'count']
    
    print(grouped)
    
    # Prepare data for plotting
    years = sorted(crop_data['year'].unique())
    x = np.arange(len(years))
    width = 0.35
    
    # Separate data for ZW and DR
    zw_means = []
    zw_stds = []
    dr_means = []
    dr_stds = []
    
    for year in years:
        zw_data = grouped[(grouped['year'] == year) & (grouped['region'] == 'ZW')]
        dr_data = grouped[(grouped['year'] == year) & (grouped['region'] == 'DR')]
        
        zw_means.append(zw_data['mean_gap'].values[0] if len(zw_data) > 0 else 0)
        zw_stds.append(zw_data['std_gap'].values[0] if len(zw_data) > 0 else 0)
        dr_means.append(dr_data['mean_gap'].values[0] if len(dr_data) > 0 else 0)
        dr_stds.append(dr_data['std_gap'].values[0] if len(dr_data) > 0 else 0)
    
    # Create plot
    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    
    # Plot bars with error bars
    ax.bar(x - width/2, zw_means, width, label='ZW fields', 
           color='#4169E1', edgecolor='#333333', alpha=0.8, 
           yerr=zw_stds, capsize=5, error_kw={'linewidth': 1.5})
    
    ax.bar(x + width/2, dr_means, width, label='DR fields', 
           color='#FFD700', edgecolor='#333333', alpha=0.8,
           yerr=dr_stds, capsize=5, error_kw={'linewidth': 1.5})
    
    # Formatting
    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('Relative Yield Gap to PP (%)', fontsize=12, fontweight='bold')
    ax.set_title(f'{crop_group.replace("_", " ").title()}: Average Yield Gap to PP by Year', 
                 fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(years)
    ax.legend(fontsize=11, loc='upper left')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.axhline(y=0, color='black', linewidth=0.8)
    
    # Add value labels on bars
    # Replace NaN with 0 for calculating max std for label positioning
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
    
    # Save plot
    safe_crop = crop_group.lower().replace(' ', '_')
    plot_path = plot_dir / f"{safe_crop}_yield_gap_by_year.png"
    fig.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    
    print(f"  ✓ Saved: {plot_path.name}")

print(f"\n✓ All plots saved to: {plot_dir}")
