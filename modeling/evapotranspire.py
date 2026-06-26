from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pcse.input import NASAPowerWeatherDataProvider
from pcse.util import penman_monteith
import warnings
warnings.filterwarnings('ignore')

RAW_DATA_PATH = Path("/Users/panyue/Desktop/final_data/")
LOCATION_DATA_FILE = RAW_DATA_PATH / "4_other_files/locations_data.xlsx"
RESULTS_DIR = Path(__file__).parent / "output" / "model_results"
OUTPUT_DIR = RAW_DATA_PATH / "5_et_analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

YEARS = [2023, 2024, 2025]
COLORS = {'DR': '#ff7f0e', 'ZW': '#1f77b4'}

# ── 1. Load field locations ────────────────────────────────────────────────
def load_locations() -> pd.DataFrame:
    import re
    def parse_dms(dms_str):
        pattern = r"(\d+)°(\d+)'([\d.]+)\"([NSEW])"
        m = re.match(pattern, dms_str.strip())
        if m:

            d, mn, s, direction = m.groups()
            dec = float(d) + float(mn)/60 + float(s)/3600
            return -dec if direction in ['S', 'W'] else dec
        return None

    df = pd.read_excel(LOCATION_DATA_FILE)
    df['lat'] = df['Coordinates'].apply(lambda x: parse_dms(x.split()[0]))
    df['lon'] = df['Coordinates'].apply(lambda x: parse_dms(x.split()[1]))
    df['region'] = df['ID_field'].str[:2]
    return df[['ID_field', 'lat', 'lon', 'region']]


# ── 2. Calculate ET0 from NASA POWER for each field ────────────────────────
def calculate_et0_for_field(field_id: str, lat: float, lon: float,
                             years: list) -> pd.DataFrame:
    """Calculate daily reference ET0 (Penman-Monteith) for a field."""
    print(f"  Fetching weather for {field_id} (lat={lat:.3f}, lon={lon:.3f})...")
    try:
        wdp = NASAPowerWeatherDataProvider(lat, lon)
    except Exception as e:
        print(f"  ⚠ Failed to fetch weather for {field_id}: {e}")
        return pd.DataFrame()

    records = []
    for wdata in wdp.export():
        # handle both dict and object
        if isinstance(wdata, dict):
            day   = wdata['DAY']
            tmin  = wdata['TMIN']
            tmax  = wdata['TMAX']
            irrad = wdata['IRRAD']
            vap   = wdata['VAP']
            wind  = wdata['WIND']
            rain  = wdata['RAIN']
        else:
            day   = wdata.DAY
            tmin  = wdata.TMIN
            tmax  = wdata.TMAX
            irrad = wdata.IRRAD
            vap   = wdata.VAP
            wind  = wdata.WIND
            rain  = wdata.RAIN

        if day.year not in years:
            continue

        try:
            et0 = penman_monteith(
                day, lat, 0, tmin, tmax, irrad, vap, wind
            )
            records.append({
                'field_id': field_id,
                'day':   day,
                'year':  day.year,
                'month': day.month,
                'ET0':   et0,
                'TMIN':  tmin,
                'TMAX':  tmax,
                'RAIN':  rain * 10,  # cm→mm
                'IRRAD': irrad,
            })
        except Exception as e:
            print(f"  ⚠ ET0 error on {day}: {e}")
            continue

    print(f"  → {len(records)} records for {field_id}")
    return pd.DataFrame(records)


# ── 3. Load WOFOST WLP results (actual crop ET = TRA + EVSMX) ─────────────
def load_wofost_et() -> pd.DataFrame:
    wlp_path = RESULTS_DIR / "WOFOST73_WLP_CWB_results.xlsx"
    if not wlp_path.exists():
        print(f"⚠ WLP results not found at {wlp_path}")
        return pd.DataFrame()

    df = pd.read_excel(wlp_path)
    df['region'] = df['field_id'].str[:2]

    # Check available ET columns
    et_cols = [c for c in df.columns if any(
        x in c for x in ['TRA', 'EVS', 'EVW', 'EVWMX', 'EVSMX', 'TRAMX']
    )]
    print(f"  Available ET columns in WLP results: {et_cols}")
    return df, et_cols


# ── 4. Plot ET0 by region and year ────────────────────────────────────────
def plot_et0_by_region(et_df: pd.DataFrame):
    """Monthly ET0 box plots per region per year."""
    et_df['region'] = et_df['field_id'].str[:2]

    fig, axes = plt.subplots(len(YEARS), 2, figsize=(11.69, 8.0),
                              sharey=True, sharex=True)
    fig.suptitle('Monthly Reference Evapotranspiration by Region (Penman-Monteith)',
                 fontsize=14, fontweight='bold')

    for row, year in enumerate(YEARS):
        for col, region in enumerate(['DR', 'ZW']):
            ax = axes[row, col]
            subset = et_df[(et_df['year'] == year) & (et_df['region'] == region)]
            if subset.empty:
                ax.set_visible(False)
                continue

            monthly_data = [subset[subset['month'] == m]['ET0'].values
                            for m in range(1, 13)]
            bp = ax.boxplot(monthly_data, patch_artist=True,
                            medianprops=dict(color='black', linewidth=1.5),
                            flierprops=dict(marker='o', markersize=2,
                                            markerfacecolor='gray',
                                            markeredgecolor='gray', alpha=0.5))
            for patch in bp['boxes']:
                patch.set_facecolor(COLORS[region])
                patch.set_alpha(0.7)

            ax.set_title(f'{region} {year}', fontsize=12, fontweight='bold')
            ax.set_xticks(range(1, 13))
            if row == len(YEARS) - 1:
                ax.set_xticklabels(['Jan','Feb','Mar','Apr','May','Jun',
                                    'Jul','Aug','Sep','Oct','Nov','Dec'],
                                   fontsize=10)
            if col == 0:
                ax.set_ylabel('Evapotranspiration (mm/day)', fontsize=12, fontweight='bold')
            ax.tick_params(axis='y', labelsize=10)
            ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    out = OUTPUT_DIR / "ET0_monthly_by_region.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out}")


def plot_cumulative_et0(et_df: pd.DataFrame):
    """Cumulative ET₀ per day-of-year, one line per year, DR vs ZW side-by-side."""
    et_df = et_df.copy()
    et_df['region'] = et_df['field_id'].str[:2]
    et_df['doy'] = pd.to_datetime(et_df['day']).dt.dayofyear

    month_ticks  = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    month_labels = ['Jan','Feb','Mar','Apr','May','Jun',
                    'Jul','Aug','Sep','Oct','Nov','Dec']
    year_colors  = {2023: '#e74c3c', 2024: '#555555', 2025: '#2ecc71'}

    fig, axes = plt.subplots(1, 2, figsize=(11.69, 6.0),
                              sharey=True, sharex=True)
    fig.suptitle('Cumulative Evapotranspiration by Region (2023–2025)',
                 fontsize=14, fontweight='bold')

    for col, region in enumerate(['DR', 'ZW']):
        ax = axes[col]
        subset = et_df[et_df['region'] == region]

        for year in YEARS:
            yr_data = subset[subset['year'] == year].sort_values('doy')
            # Average ET0 across all fields per doy, then cumsum
            daily_mean = yr_data.groupby('doy')['ET0'].mean().reset_index()
            daily_mean = daily_mean.sort_values('doy')
            cum_et0 = daily_mean['ET0'].cumsum()

            ax.plot(daily_mean['doy'], cum_et0,
                    color=year_colors[year], linewidth=2.5, label=str(year))

            # Shaded range: min/max across fields
            daily_min = yr_data.groupby('doy')['ET0'].min().cumsum()
            daily_max = yr_data.groupby('doy')['ET0'].max().cumsum()
            ax.fill_between(daily_mean['doy'], daily_min, daily_max,
                            color=year_colors[year], alpha=0.12)

        ax.set_title(f'{region} region', fontsize=14, fontweight='bold')
        ax.set_xticks(month_ticks)
        ax.set_xticklabels(month_labels, fontsize=10)
        ax.set_xlabel('Month', fontsize=12, fontweight='bold')
        ax.tick_params(axis='y', labelsize=10)
        ax.grid(True, alpha=0.25, linestyle='--')
        ax.set_ylim(bottom=0)
        ax.legend(title='Year', fontsize=10)

    axes[0].set_ylabel('Cumulative evapotranspiration (mm)', fontsize=13, fontweight='bold')

    plt.tight_layout()
    out = OUTPUT_DIR / "ET0_cumulative_by_region.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out}")


def plot_annual_et0_comparison(et_df: pd.DataFrame):
    """Annual ET0 totals: DR vs ZW side-by-side bar chart."""
    et_df['region'] = et_df['field_id'].str[:2]
    annual = (et_df.groupby(['field_id', 'region', 'year'])['ET0']
              .sum().reset_index())
    summary = (annual.groupby(['region', 'year'])['ET0']
               .agg(['mean', 'std']).reset_index())

    fig, ax = plt.subplots(figsize=(11.69, 6.0))
    x = np.arange(len(YEARS))
    width = 0.35

    for i, region in enumerate(['DR', 'ZW']):
        sub = summary[summary['region'] == region].set_index('year')
        means = [sub.loc[y, 'mean'] if y in sub.index else 0 for y in YEARS]
        stds  = [sub.loc[y, 'std']  if y in sub.index else 0 for y in YEARS]
        offset = (i - 0.5) * width
        ax.bar(x + offset, means, width, yerr=stds, capsize=5,
               color=COLORS[region], alpha=0.8, label=region,
               edgecolor='#333333')

    ax.set_xticks(x)
    ax.set_xticklabels(YEARS, fontsize=10)
    ax.set_xlabel('Year', fontsize=14, fontweight='bold')
    ax.set_ylabel('Annual ET₀ (mm/year)', fontsize=14, fontweight='bold')
    ax.set_title('Annual Reference ET₀ by Region', fontsize=16, fontweight='bold')
    ax.tick_params(axis='y', labelsize=10)
    ax.legend(fontsize=12)
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    out = OUTPUT_DIR / "ET0_annual_comparison.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out}")


def plot_growing_season_et0(et_df: pd.DataFrame, wlp_df: pd.DataFrame):
    """ET0 during growing season only (planting→harvest) per crop per region."""
    et_df['region'] = et_df['field_id'].str[:2]

    # Use harvest dates from WLP results as proxy for growing season
    if wlp_df.empty:
        print("⚠ No WLP results — skipping growing season ET0 plot")
        return

    # Join ET0 with crop calendar info
    wlp_df['day'] = pd.to_datetime(wlp_df['day'])
    et_df['day']  = pd.to_datetime(et_df['day'])

    # Drop 'year' from wlp_df before merge to avoid year_x/year_y collision
    wlp_cols = [c for c in ['field_id', 'day', 'crop_name'] if c in wlp_df.columns]
    merged = pd.merge(et_df, wlp_df[wlp_cols],
                      on=['field_id', 'day'], how='inner')
    if merged.empty:
        print("⚠ No matching rows between ET0 and WLP results")
        return

    # Sum ET0 per field-year-crop
    season_et = (merged.groupby(['field_id', 'region', 'year', 'crop_name'])['ET0']
                 .sum().reset_index())
    season_et = season_et[season_et['crop_name'] != 'unknown']

    crops = season_et['crop_name'].unique()
    fig, axes = plt.subplots(1, len(crops), figsize=(11.69, 6.0),
                              sharey=False)
    if len(crops) == 1:
        axes = [axes]

    fig.suptitle('Growing Season ET₀ by Crop and Region',
                 fontsize=14, fontweight='bold')

    for ax, crop in zip(axes, sorted(crops)):
        sub = season_et[season_et['crop_name'] == crop]
        summary = sub.groupby(['region', 'year'])['ET0'].agg(['mean','std']).reset_index()

        x = np.arange(len(YEARS))
        width = 0.35
        for i, region in enumerate(['DR', 'ZW']):
            rs = summary[summary['region'] == region].set_index('year')
            means = [rs.loc[y, 'mean'] if y in rs.index else 0 for y in YEARS]
            stds  = [rs.loc[y, 'std']  if y in rs.index else 0 for y in YEARS]
            ax.bar(x + (i-0.5)*width, means, width, yerr=stds, capsize=4,
                   color=COLORS[region], alpha=0.8, label=region,
                   edgecolor='#333333')

        ax.set_title(crop.capitalize(), fontsize=12, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(YEARS, fontsize=10)
        ax.tick_params(axis='y', labelsize=10)
        ax.grid(axis='y', alpha=0.3)
        ax.set_xlabel('Year', fontsize=12, fontweight='bold')

    axes[0].set_ylabel('Growing Season ET₀ (mm)', fontsize=14, fontweight='bold')
    handles = [mpatches.Patch(color=COLORS[r], label=r) for r in ['DR', 'ZW']]
    fig.legend(handles=handles, fontsize=12, loc='upper right')

    plt.tight_layout()
    out = OUTPUT_DIR / "ET0_growing_season_by_crop.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out}")


# ── 5. Main ───────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("CALCULATING EVAPOTRANSPIRATION BY REGION")
    print("=" * 60)

    # Load field locations
    locations = load_locations()
    print(f"Loaded {len(locations)} field locations")

    # Load WLP results for growing season info
    print("\nLoading WOFOST WLP results...")
    result = load_wofost_et()
    wlp_df = result[0] if isinstance(result, tuple) else pd.DataFrame()

    # Calculate ET0 for each field
    et_cache = OUTPUT_DIR / "ET0_daily_all_fields.csv"
    if et_cache.exists():
        print(f"\nLoading cached ET0 data from {et_cache}...")
        et_df = pd.read_csv(et_cache, parse_dates=['day'])
    else:
        print(f"\nCalculating ET0 for {len(locations)} fields...")
        all_et = []
        for _, row in locations.iterrows():
            df_et = calculate_et0_for_field(
                row['ID_field'], row['lat'], row['lon'], YEARS
            )
            if not df_et.empty:
                all_et.append(df_et)

        if not all_et:
            print("⚠ No ET0 data calculated")
            return

        et_df = pd.concat(all_et, ignore_index=True)
        et_df.to_csv(et_cache, index=False)
        print(f"Saved ET0 cache → {et_cache}")

    print(f"\nET0 data: {len(et_df)} rows, "
          f"{et_df['field_id'].nunique()} fields, "
          f"years {sorted(et_df['year'].unique())}")

    # ── Generate plots ──────────────────────────────────────────────────
    print("\nGenerating plots...")
    plot_et0_by_region(et_df)
    plot_cumulative_et0(et_df)
    plot_annual_et0_comparison(et_df)
    plot_growing_season_et0(et_df, wlp_df)

    # ── Save summary Excel ──────────────────────────────────────────────
    et_df['region'] = et_df['field_id'].str[:2]
    monthly_summary = (et_df.groupby(['region', 'year', 'month'])['ET0']
                       .agg(['mean', 'std', 'count']).reset_index())
    annual_summary = (et_df.groupby(['field_id', 'region', 'year'])['ET0']
                      .sum().reset_index().rename(columns={'ET0': 'annual_ET0_mm'}))

    out_xlsx = OUTPUT_DIR / "ET0_summary.xlsx"
    with pd.ExcelWriter(out_xlsx) as writer:
        monthly_summary.to_excel(writer, sheet_name='Monthly_ET0', index=False)
        annual_summary.to_excel(writer, sheet_name='Annual_ET0', index=False)
        et_df.to_excel(writer, sheet_name='Daily_ET0', index=False)
    print(f"\nSaved summary → {out_xlsx}")

    print("\n" + "=" * 60)
    print("ET ANALYSIS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()