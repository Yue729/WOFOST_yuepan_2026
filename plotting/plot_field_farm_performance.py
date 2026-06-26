"""
Field and Farm Performance Analysis
Ranks fields by yield gap and calculates average performance scores across years/crops.
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
plot_dir = RAW_DATA_PATH / "2_yield_data" / "yield_plots_performance"

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

# ── Calculate yield gap (PP - actual) ─────────────────────────────────────────
df['gap_to_pp'] = df['PP_yield_t_ha'] - df['converted_yield']

# ── Filter to study period 2023–2025 and valid records ───────────────────────
df = df[df['year'].between(2023, 2025)].copy()
df = df.dropna(subset=['gap_to_pp', 'converted_yield', 'PP_yield_t_ha']).copy()

# Normalize crop names for grouping
crop_groups = {
    'sugarbeet': 'sugarbeet',
    'sugar beet': 'sugarbeet',
    'potato': 'potato',
    'starch potato': 'potato',
    'ware potato': 'potato',
    'seed potato': 'potato',
    'barley': 'cereal',
    'spring barley': 'cereal',
    'winter barley': 'cereal',
    'wheat': 'cereal',
    'spring wheat': 'cereal',
    'winter wheat': 'cereal',
    'seed_onion': 'onion',
    'seed onion': 'onion',
    'onion': 'onion',
}
df['crop_group'] = df['crop_name'].str.strip().str.lower().map(crop_groups)
df = df[df['crop_group'].notna()].copy()

# ── Exclude sugar beet from performance analysis ──────────────────────────────
df = df[df['crop_group'] != 'sugarbeet'].copy()

print(f"Loaded {len(df)} valid records (2023-2025, excluding sugar beet)")
print(f"Crops: {sorted(df['crop_group'].unique())}")
print(f"Years: {sorted(df['year'].unique())}")

# ── Extract farm ID from field ID ────────────────────────────────────────────
# e.g., "DR01_03" → "DR01", "ZW14_01" → "ZW14"
df['farm_id'] = df['ID_field'].str.extract(r'^([A-Z]+\d+)_')[0]

# ── Calculate relative yield gap: (Yp - Ya) / Yp ─────────────────────────────
df['relative_gap_to_pp'] = df['gap_to_pp'] / df['PP_yield_t_ha']

# ── Rank fields into 5 quantiles by relative yield gap for each crop-year combination ───
def assign_quantile_score(group):
    """
    Assign scores 1-5 based on relative yield gap quintiles.
    1 = highest relative gap (worst performance)
    5 = lowest relative gap (best performance)
    """
    # Sort by relative gap descending (highest gap first)
    group = group.sort_values('relative_gap_to_pp', ascending=False).copy()
    n = len(group)
    
    # Divide into 5 groups as evenly as possible
    quantile_size = n / 5
    scores = []
    for i in range(n):
        if i < quantile_size:
            scores.append(1)  # Highest relative gap (worst)
        elif i < 2 * quantile_size:
            scores.append(2)
        elif i < 3 * quantile_size:
            scores.append(3)
        elif i < 4 * quantile_size:
            scores.append(4)
        else:
            scores.append(5)  # Lowest relative gap (best)
    
    group['performance_score'] = scores
    return group

# Apply quintile scoring for each crop-year combination
df_scored = df.groupby(['crop_group', 'year'], group_keys=False).apply(assign_quantile_score)

print(f"\nPerformance scores assigned:")
print(df_scored.groupby('performance_score').size())

# ── Calculate average score per field across all crops/years ─────────────────
field_scores = df_scored.groupby('ID_field').agg(
    performance_score=('performance_score', 'mean'),
    farm_id=('farm_id', 'first'),
    gap_to_pp=('gap_to_pp', 'mean'),
    relative_gap_to_pp=('relative_gap_to_pp', 'mean'),
    n_records=('performance_score', 'count')  # Count number of crop-year combinations
)

field_scores = field_scores.sort_values('performance_score').reset_index()

print(f"\nField-level performance:")
print(f"  {len(field_scores)} unique fields")
print(f"  Score range: {field_scores['performance_score'].min():.2f} - {field_scores['performance_score'].max():.2f}")

# ── Calculate average score per farm across all crops/years ──────────────────
farm_scores = df_scored.groupby('farm_id').agg(
    performance_score=('performance_score', 'mean'),
    gap_to_pp=('gap_to_pp', 'mean'),
    relative_gap_to_pp=('relative_gap_to_pp', 'mean'),
    n_records=('performance_score', 'count')  # Count number of field-crop-year combinations
)

farm_scores = farm_scores.sort_values('performance_score').reset_index()

print(f"\nFarm-level performance:")
print(f"  {len(farm_scores)} unique farms")
print(f"  Score range: {farm_scores['performance_score'].min():.2f} - {farm_scores['performance_score'].max():.2f}")

# ══════════════════════════════════════════════════════════════════════════════
# PLOT 1: Field-level performance
# ══════════════════════════════════════════════════════════════════════════════
# A4 landscape width with reduced height
fig_width = 14.0  # or 16.0
fig_height = 6.0
fig, ax = plt.subplots(figsize=(fig_width, fig_height), constrained_layout=True)

x = np.arange(len(field_scores))

# Color by region: ZW (blue) vs DR (orange)
region_colors = {'ZW': '#1f77b4', 'DR': '#ff7f0e'}  # Blue for ZW, Orange for DR
colors = [region_colors[field_id[:2]] for field_id in field_scores['ID_field']]

bars = ax.bar(x, field_scores['performance_score'], color=colors, edgecolor='#333333', linewidth=0.5, alpha=0.7)

# Add reference lines for quintile boundaries
ax.axhline(y=1, color='#d32f2f', linestyle='--', linewidth=1, alpha=0.3, label='Score 1 (worst)')
ax.axhline(y=2, color='#ff9800', linestyle='--', linewidth=1, alpha=0.3, label='Score 2')
ax.axhline(y=3, color='#ffeb3b', linestyle='--', linewidth=1, alpha=0.3, label='Score 3')
ax.axhline(y=4, color='#9ccc65', linestyle='--', linewidth=1, alpha=0.3, label='Score 4')
ax.axhline(y=5, color='#4caf50', linestyle='--', linewidth=1, alpha=0.3, label='Score 5 (best)')

ax.set_xlabel('Field', fontsize=14, fontweight='bold')
ax.set_ylabel('Average Performance Score', fontsize=14, fontweight='bold')
ax.set_title('Field Performance Ranking (2023-2025)\nScore 1–5: green = best performance, red = worst performance', 
             fontsize=16, fontweight='bold', pad=20)
ax.set_ylim(0.5, 5.5)
ax.set_yticks([1, 2, 3, 4, 5])
ax.set_yticklabels(['1 (worst)', '2', '3', '4', '5 (best)'], fontsize=10)

# Show every 3rd field label
step = 3
ax.set_xticks(x[::step])
ax.set_xticklabels(field_scores['ID_field'].iloc[::step], rotation=90, ha='center', fontsize=8)

ax.grid(axis='y', alpha=0.25)
ax.set_axisbelow(True)
ax.margins(x=0.005)

# Add legend for regions
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor=region_colors['ZW'], edgecolor='#333333', label='ZW fields', alpha=0.7),
    Patch(facecolor=region_colors['DR'], edgecolor='#333333', label='DR fields', alpha=0.7)
]
ax.legend(handles=legend_elements, loc='upper left', fontsize=10, frameon=True)

# Add text annotation with summary stats
summary_text = (f"Total fields: {len(field_scores)}\n"
                f"Best (score ≥4.0): {(field_scores['performance_score'] >= 4.0).sum()}\n"
                f"Worst (score ≤2.0): {(field_scores['performance_score'] <= 2.0).sum()}")
ax.text(0.98, 0.97, summary_text, transform=ax.transAxes, 
        fontsize=10, verticalalignment='top', horizontalalignment='right',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

field_plot_path = plot_dir / "field_performance_ranking_no_sugarbeet.png"
fig.savefig(field_plot_path, dpi=300, bbox_inches='tight')
plt.close(fig)
print(f"\n✓ Saved: {field_plot_path}")

# ══════════════════════════════════════════════════════════════════════════════
# PLOT 1B: Field-level performance with TWO-TIER X-axis labels (show all fields)
# ══════════════════════════════════════════════════════════════════════════════
fig_width_extended = 16.0  # Wider to accommodate all labels
fig_height_extended = 7.0  # Taller to fit two-tier labels
fig, ax = plt.subplots(figsize=(fig_width_extended, fig_height_extended), constrained_layout=True)

x = np.arange(len(field_scores))

# Color by region: ZW (blue) vs DR (orange)
colors = [region_colors[field_id[:2]] for field_id in field_scores['ID_field']]

bars = ax.bar(x, field_scores['performance_score'], color=colors, edgecolor='#333333', linewidth=0.5, alpha=0.7)

# Add reference lines
ax.axhline(y=1, color='#d32f2f', linestyle='--', linewidth=1, alpha=0.3)
ax.axhline(y=2, color='#ff9800', linestyle='--', linewidth=1, alpha=0.3)
ax.axhline(y=3, color='#ffeb3b', linestyle='--', linewidth=1, alpha=0.3)
ax.axhline(y=4, color='#9ccc65', linestyle='--', linewidth=1, alpha=0.3)
ax.axhline(y=5, color='#4caf50', linestyle='--', linewidth=1, alpha=0.3)

ax.set_ylabel('Average Performance Score', fontsize=14, fontweight='bold')
ax.set_title('Field Performance Ranking (2023-2025, excl. sugar beet) - Extended View\nScore 1–5: green = best performance, red = worst performance', 
             fontsize=16, fontweight='bold', pad=20)
ax.set_ylim(0.5, 5.5)
ax.set_yticks([1, 2, 3, 4, 5])
ax.set_yticklabels(['1 (worst)', '2', '3', '4', '5 (best)'], fontsize=10)

# Show every 3rd field label
step = 3
ax.set_xticks(x[::step])
ax.set_xticklabels(field_scores['ID_field'].iloc[::step], rotation=90, ha='center', fontsize=8)

ax.grid(axis='y', alpha=0.25)
ax.set_axisbelow(True)
ax.margins(x=0.005)

# Add legend for regions
legend_elements = [
    Patch(facecolor=region_colors['ZW'], edgecolor='#333333', label='ZW fields', alpha=0.7),
    Patch(facecolor=region_colors['DR'], edgecolor='#333333', label='DR fields', alpha=0.7)
]
ax.legend(handles=legend_elements, loc='upper left', fontsize=10, frameon=True)

# Add summary text
summary_text = (f"Total fields: {len(field_scores)}\n"
                f"Best (score ≥4.0): {(field_scores['performance_score'] >= 4.0).sum()}\n"
                f"Worst (score ≤2.0): {(field_scores['performance_score'] <= 2.0).sum()}")
ax.text(0.98, 0.97, summary_text, transform=ax.transAxes, 
        fontsize=10, verticalalignment='top', horizontalalignment='right',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

field_plot_path_twotier = plot_dir / "field_performance_ranking_extended_no_sugarbeet.png"
fig.savefig(field_plot_path_twotier, dpi=300, bbox_inches='tight')
plt.close(fig)
print(f"✓ Saved: {field_plot_path_twotier}")

# ══════════════════════════════════════════════════════════════════════════════
# PLOT 1C: Field-level performance with INVERTED AXES (horizontal bars, show all fields)
# ══════════════════════════════════════════════════════════════════════════════
fig_width_horizontal = 10.0
fig_height_horizontal = 20.0  # Much taller to fit all 135 fields vertically
fig, ax = plt.subplots(figsize=(fig_width_horizontal, fig_height_horizontal), constrained_layout=True)

y = np.arange(len(field_scores))

# Color by region: ZW (blue) vs DR (orange)
colors = [region_colors[field_id[:2]] for field_id in field_scores['ID_field']]

# Horizontal bars (inverted axes)
bars = ax.barh(y, field_scores['performance_score'], color=colors, edgecolor='#333333', linewidth=0.5, alpha=0.7)

# Add reference lines (now vertical since axes are swapped)
ax.axvline(x=1, color='#d32f2f', linestyle='--', linewidth=1, alpha=0.3)
ax.axvline(x=2, color='#ff9800', linestyle='--', linewidth=1, alpha=0.3)
ax.axvline(x=3, color='#ffeb3b', linestyle='--', linewidth=1, alpha=0.3)
ax.axvline(x=4, color='#9ccc65', linestyle='--', linewidth=1, alpha=0.3)
ax.axvline(x=5, color='#4caf50', linestyle='--', linewidth=1, alpha=0.3)

ax.set_xlabel('Average Performance Score', fontsize=14, fontweight='bold')
ax.set_ylabel('Field ID', fontsize=14, fontweight='bold')
ax.set_title('Field Performance Ranking (2023-2025, excl. sugar beet) - Complete View\nScore 1–5: green = best performance, red = worst performance', 
             fontsize=16, fontweight='bold', pad=20)
ax.set_xlim(0.5, 5.5)
ax.set_xticks([1, 2, 3, 4, 5])
ax.set_xticklabels(['1 (worst)', '2', '3', '4', '5 (best)'], fontsize=10)

# Y-axis labels: all field IDs
ax.set_yticks(y)
ax.set_yticklabels(field_scores['ID_field'], fontsize=8)
ax.tick_params(axis='y', labelsize=8)

ax.grid(axis='x', alpha=0.25)
ax.set_axisbelow(True)
ax.margins(y=0.005)

# Invert y-axis to have worst performers at bottom, best at top
ax.invert_yaxis()

# Add legend for regions
legend_elements = [
    Patch(facecolor=region_colors['ZW'], edgecolor='#333333', label='ZW fields', alpha=0.7),
    Patch(facecolor=region_colors['DR'], edgecolor='#333333', label='DR fields', alpha=0.7)
]
ax.legend(handles=legend_elements, loc='lower right', fontsize=10, frameon=True)

# Add summary text
summary_text = (f"Total fields: {len(field_scores)}\n"
                f"Best (score ≥4.0): {(field_scores['performance_score'] >= 4.0).sum()}\n"
                f"Worst (score ≤2.0): {(field_scores['performance_score'] <= 2.0).sum()}")
ax.text(0.98, 0.02, summary_text, transform=ax.transAxes, 
        fontsize=10, verticalalignment='bottom', horizontalalignment='right',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

field_plot_path_complete = plot_dir / "field_performance_ranking_horizontal_no_sugarbeet.png"
fig.savefig(field_plot_path_complete, dpi=300, bbox_inches='tight')
plt.close(fig)
print(f"✓ Saved: {field_plot_path_complete}")

# ══════════════════════════════════════════════════════════════════════════════
# PLOT 2: Farm-level performance
# ══════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(fig_width, fig_height), constrained_layout=True)

x = np.arange(len(farm_scores))

# Color by region: ZW (blue) vs DR (orange)
colors = [region_colors[farm_id[:2]] for farm_id in farm_scores['farm_id']]

bars = ax.bar(x, farm_scores['performance_score'], color=colors, edgecolor='#333333', linewidth=0.8, alpha=0.7)

# Add reference lines for quintile boundaries
ax.axhline(y=1, color='#d32f2f', linestyle='--', linewidth=1, alpha=0.3, label='Score 1 (worst)')
ax.axhline(y=2, color='#ff9800', linestyle='--', linewidth=1, alpha=0.3, label='Score 2')
ax.axhline(y=3, color='#ffeb3b', linestyle='--', linewidth=1, alpha=0.3, label='Score 3')
ax.axhline(y=4, color='#9ccc65', linestyle='--', linewidth=1, alpha=0.3, label='Score 4')
ax.axhline(y=5, color='#4caf50', linestyle='--', linewidth=1, alpha=0.3, label='Score 5 (best)')

ax.set_xlabel('Farm ID', fontsize=14, fontweight='bold')
ax.set_ylabel('Average Performance Score', fontsize=14, fontweight='bold')
ax.set_title('Farm Performance Ranking (2023-2025)\nScore 1–5: green = best performance, red = worst performance', 
             fontsize=16, fontweight='bold', pad=20)
ax.set_ylim(0.5, 5.5)
ax.set_yticks([1, 2, 3, 4, 5])
ax.set_yticklabels(['1 (worst)', '2', '3', '4', '5 (best)'], fontsize=10)

ax.set_xticks(x)
ax.set_xticklabels(farm_scores['farm_id'], rotation=45, ha='right', fontsize=10)

ax.grid(axis='y', alpha=0.25)
ax.set_axisbelow(True)
ax.margins(x=0.01)

# Add legend for regions
legend_elements = [
    Patch(facecolor=region_colors['ZW'], edgecolor='#333333', label='ZW farms', alpha=0.7),
    Patch(facecolor=region_colors['DR'], edgecolor='#333333', label='DR farms', alpha=0.7)
]
ax.legend(handles=legend_elements, loc='upper left', fontsize=10, frameon=True)

# Add text annotation with summary stats
summary_text = (f"Total farms: {len(farm_scores)}\n"
                f"Best (score ≥3.0): {(farm_scores['performance_score'] >= 3.0).sum()}\n"
                f"Worst (score ≤2.0): {(farm_scores['performance_score'] <= 2.0).sum()}")
ax.text(0.98, 0.97, summary_text, transform=ax.transAxes, 
        fontsize=10, verticalalignment='top', horizontalalignment='right',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

farm_plot_path = plot_dir / "farm_performance_ranking_no_sugarbeet.png"
fig.savefig(farm_plot_path, dpi=300, bbox_inches='tight')
plt.close(fig)
print(f"✓ Saved: {farm_plot_path}")

# ══════════════════════════════════════════════════════════════════════════════
# PLOT 3: Farm performance over time (multi-panel)
# ══════════════════════════════════════════════════════════════════════════════
# Need to get year data from original df and merge with scores
df_with_scores = df[['ID_field', 'farm_id', 'year', 'crop_group', 'crop_name', 'gap_to_pp']].copy()
df_with_scores = df_with_scores.merge(
    df_scored[['ID_field', 'crop_name', 'performance_score']], 
    on=['ID_field', 'crop_name'], 
    how='inner'
)

# Calculate farm-level scores per year
farm_year_scores = df_with_scores.groupby(['farm_id', 'year']).agg(
    performance_score=('performance_score', 'mean'),
    gap_to_pp=('gap_to_pp', 'mean'),
    n_records=('performance_score', 'count')
).reset_index()

# Get all unique farms, sorted by overall performance
all_farms = farm_scores.sort_values('performance_score', ascending=False)['farm_id'].tolist()
n_farms = len(all_farms)

# Set grid layout to 8 rows × 5 columns
n_rows = 8
n_cols = 5

# Create multi-panel figure with adjusted spacing
fig, axes = plt.subplots(n_rows, n_cols, figsize=(n_cols * 2.8, n_rows * 2.2), 
                         constrained_layout=False)
fig.subplots_adjust(left=0.05, right=0.98, top=0.96, bottom=0.04, hspace=0.35, wspace=0.25)
axes = axes.flatten() if n_farms > 1 else [axes]

for idx, farm_id in enumerate(all_farms):
    ax = axes[idx]
    
    # Calculate row and column position
    row = idx // n_cols
    col = idx % n_cols
    
    # Get data for this farm
    farm_data = farm_year_scores[farm_year_scores['farm_id'] == farm_id].sort_values('year')
    
    if len(farm_data) > 0:
        years = farm_data['year'].values
        scores = farm_data['performance_score'].values
        
        # Color points based on score
        colors = plt.cm.RdYlGn_r(scores / 4.0)
        
        # Plot line and points
        ax.plot(years, scores, color='#666', linewidth=1.5, alpha=0.7, zorder=1)
        ax.scatter(years, scores, c=colors, s=100, edgecolor='#333', linewidth=1.5, zorder=3)
        
        # Add score labels on points
        for year, score in zip(years, scores):
            ax.text(year, score, f'{score:.2f}', ha='center', va='bottom', 
                   fontsize=7, fontweight='bold')
    
    # Styling
    ax.set_xlim(2022.5, 2025.5)
    ax.set_ylim(0.5, 4.5)
    ax.set_xticks([2023, 2024, 2025])
    ax.set_yticks([1, 2, 3, 4])
    ax.set_title(farm_id, fontsize=9, fontweight='bold', pad=4)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.tick_params(axis='both', labelsize=7)
    
    # Reference lines
    ax.axhline(y=2.5, color='#999', linestyle=':', linewidth=1, alpha=0.5)
    
    # Only show y-tick labels on leftmost column
    if col == 0:
        ax.set_yticklabels(['1', '2', '3', '4'], fontsize=9)
        ax.set_ylabel('Score', fontsize=11)
    else:
        ax.set_yticklabels([])
    
    # Only show x-tick labels on bottom row
    if row == n_rows - 1:
        ax.set_xticklabels(['2023', '2024', '2025'], fontsize=9)
        ax.set_xlabel('Year', fontsize=11)
    else:
        ax.set_xticklabels([])

# Hide extra subplots if n_farms doesn't fill the grid
for idx in range(n_farms, len(axes)):
    axes[idx].set_visible(False)

fig.suptitle('Farm Performance Over Time (2023-2025, excl. sugar beet)', 
             fontsize=16, fontweight='bold')

farm_timeline_path = plot_dir / "farm_performance_over_time_no_sugarbeet.png"
fig.savefig(farm_timeline_path, dpi=300, bbox_inches='tight')
plt.close(fig)
print(f"✓ Saved: {farm_timeline_path}")

# ── Save detailed results to Excel ────────────────────────────────────────────
output_excel = plot_dir / "performance_scores_detailed_no_sugarbeet.xlsx"

# Prepare the detailed records by merging back with original data to get all columns
df_export = df_scored.copy()
if 'year' not in df_export.columns:
    # Re-merge if groupby removed the columns
    df_export = df.merge(df_scored[['ID_field', 'crop_name', 'performance_score']], 
                         on=['ID_field', 'crop_name'], how='inner')

with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
    # Sheet 1: All individual crop-year-field scores
    export_cols = ['ID_field', 'farm_id', 'year', 'crop_group', 'crop_name', 
                   'gap_to_pp', 'performance_score', 'PP_yield_t_ha', 'converted_yield']
    # Only include columns that exist
    export_cols = [c for c in export_cols if c in df_export.columns]
    df_export[export_cols].to_excel(writer, sheet_name='All_Records', index=False)
    
    # Sheet 2: Field-level averages
    field_scores.to_excel(writer, sheet_name='Field_Averages', index=False)
    
    # Sheet 3: Farm-level averages
    farm_scores.to_excel(writer, sheet_name='Farm_Averages', index=False)

    # Sheet 4: Best & Worst performing fields (top/bottom 15)
    field_scores_ranked = field_scores.copy()
    field_scores_ranked['region'] = field_scores_ranked['ID_field'].str[:2]
    field_scores_ranked = field_scores_ranked.rename(columns={
        'performance_score': 'avg_score',
        'gap_to_pp': 'avg_gap_t_ha',
        'relative_gap_to_pp': 'avg_relative_gap',
    })
    display_cols = ['ID_field', 'region', 'farm_id', 'avg_score', 'avg_gap_t_ha', 'avg_relative_gap', 'n_records']
    display_cols = [c for c in display_cols if c in field_scores_ranked.columns]

    best15 = field_scores_ranked.nlargest(15, 'avg_score')[display_cols].copy()
    best15.insert(0, 'rank', range(1, 16))
    best15.insert(0, 'category', 'Best')

    worst15 = field_scores_ranked.nsmallest(15, 'avg_score')[display_cols].copy()
    worst15.insert(0, 'rank', range(1, 16))
    worst15.insert(0, 'category', 'Worst')

    best_worst = pd.concat([best15, worst15], ignore_index=True)
    if 'avg_relative_gap' in best_worst.columns:
        best_worst['avg_relative_gap_%'] = (best_worst['avg_relative_gap'] * 100).round(1)
        best_worst = best_worst.drop(columns=['avg_relative_gap'])
    best_worst.to_excel(writer, sheet_name='Best_Worst_Fields', index=False)

print(f"✓ Saved: {output_excel}")

print(f"\n{'='*70}")
print(f"SUMMARY")
print(f"{'='*70}")
print(f"Field performance ranking: {field_plot_path.name}")
print(f"Field performance ranking (extended): {field_plot_path_twotier.name}")
print(f"Field performance ranking (horizontal): {field_plot_path_complete.name}")
print(f"Farm performance ranking: {farm_plot_path.name}")
print(f"Farm performance over time: {farm_timeline_path.name}")
print(f"Detailed scores: {output_excel.name}")
print(f"\nTop 5 best performing fields:")
print(field_scores.nlargest(5, 'performance_score')[['ID_field', 'performance_score', 'gap_to_pp', 'n_records']])
print(f"\nTop 5 worst performing fields:")
print(field_scores.nsmallest(5, 'performance_score')[['ID_field', 'performance_score', 'gap_to_pp', 'n_records']])
print(f"\nTop 5 best performing farms:")
print(farm_scores.nlargest(5, 'performance_score')[['farm_id', 'performance_score', 'gap_to_pp', 'n_records']])
print(f"\nTop 5 worst performing farms:")
print(farm_scores.nsmallest(5, 'performance_score')[['farm_id', 'performance_score', 'gap_to_pp', 'n_records']])
