import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from pathlib import Path

# ============================================================
# COORDINATE CONVERSION: Dutch RD New (EPSG:28992) -> WGS84
# ============================================================
def rd_to_wgs84(x, y):
    """Convert Dutch RD New coordinates to WGS84 lat/lon."""
    x0, y0 = 155000, 463000
    phi0, lam0 = 52.15517440, 5.38720621
    dx = (x - x0) * 1e-5
    dy = (y - y0) * 1e-5
    Kp  = [0, 2, 0, 2, 0, 2, 1, 4, 2, 4, 1]
    Kq  = [1, 0, 2, 1, 3, 2, 0, 0, 3, 1, 1]
    Kpq = [3235.65389, -32.58297, -0.24750, -0.84978, -0.06550, -0.01709,
           -0.00738, 0.00530, -0.00039, 0.00033, -0.00012]
    Lp  = [1, 1, 1, 3, 1, 3, 0, 3, 1, 0, 2, 5]
    Lq  = [0, 1, 2, 0, 3, 1, 1, 2, 0, 2, 0, 0]
    Lpq = [5260.52916, 105.94684, 2.45656, -0.81885, 0.05594, -0.05607,
           0.01199, -0.00256, 0.00128, 0.00022, -0.00022, 0.00026]
    phi = sum(Kpq[i] * dx**Kp[i] * dy**Kq[i] for i in range(len(Kpq)))
    lam = sum(Lpq[i] * dx**Lp[i] * dy**Lq[i] for i in range(len(Lpq)))
    return phi0 + phi / 3600, lam0 + lam / 3600

# Calculate centroids
dr_lat, dr_lon = rd_to_wgs84(255393, 536074)
zw_lat, zw_lon = rd_to_wgs84(98901, 417009)
print(f"DR centroid (Drenthe):          lat={dr_lat:.5f}, lon={dr_lon:.5f}")
print(f"ZW centroid (Zeeland/Z-Holland): lat={zw_lat:.5f}, lon={zw_lon:.5f}")

# ============================================================
# FETCH REAL NASA POWER DATA
# ============================================================
def fetch_nasa_power(lat, lon, start='20230101', end='20251231'):
    """Fetch daily weather data from NASA POWER API."""
    url = (
        f"https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters=T2M_MAX,T2M_MIN,T2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN"
        f"&community=AG&longitude={lon}&latitude={lat}"
        f"&start={start}&end={end}&format=JSON"
    )
    print(f"  Fetching from NASA POWER...")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()['properties']['parameter']

    df = pd.DataFrame({
        'date':   pd.to_datetime(list(data['T2M_MAX'].keys()), format='%Y%m%d'),
        'tmax':   list(data['T2M_MAX'].values()),
        'tmin':   list(data['T2M_MIN'].values()),
        'tavg':   list(data['T2M'].values()),
        'precip': list(data['PRECTOTCORR'].values()),
        'irrad':  list(data['ALLSKY_SFC_SW_DWN'].values()),  # MJ/m2/day
    })
    df['doy'] = df['date'].dt.dayofyear
    df['year'] = df['date'].dt.year
    # Replace fill values (-999) with NaN
    df.replace(-999, np.nan, inplace=True)
    return df

print("\nFetching DR region weather data...")
df_dr = fetch_nasa_power(dr_lat, dr_lon)
print(f"  DR: {len(df_dr)} records")

print("Fetching ZW region weather data...")
df_zw = fetch_nasa_power(zw_lat, zw_lon)
print(f"  ZW: {len(df_zw)} records")

# ============================================================
# PLOT FUNCTION
# ============================================================
from matplotlib.lines import Line2D

years = [2023, 2024, 2025]
colors = {2023: '#e74c3c', 2024: '#555555', 2025: '#2ecc71'}
month_ticks  = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
month_labels = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

output_dir = Path('/Users/panyue/Desktop/final_data/2_yield_data')
output_dir.mkdir(parents=True, exist_ok=True)

def make_plot(df, region_name, out_path):
    fig, axes = plt.subplots(3, 1, figsize=(12, 11))
    fig.suptitle(f'Weather data 2023–2025: {region_name}', fontsize=13, fontweight='bold')

    for year in years:
        data = df[df['year'] == year].sort_values('doy')
        doy   = data['doy'].values
        color = colors[year]

        # A) Cumulative Precipitation
        cum_p = data['precip'].cumsum().values
        axes[0].plot(doy, cum_p, color=color, linewidth=2, label=str(year))

        # B) Cumulative Global Radiation
        cum_r = data['irrad'].cumsum().values
        axes[1].plot(doy, cum_r, color=color, linewidth=2, label=str(year))

        # C) Temperature
        axes[2].plot(doy, data['tmax'].values, color=color, linewidth=1.5, linestyle='--')
        axes[2].plot(doy, data['tavg'].values, color=color, linewidth=2,   label=str(year))
        axes[2].plot(doy, data['tmin'].values, color=color, linewidth=1.5, linestyle=':')

    # Formatting A
    axes[0].set_ylabel('Cumulative precipitation (mm)', fontsize=11)
    axes[0].set_title('A)', loc='left', fontweight='bold')
    axes[0].legend(title='Year', loc='upper left')
    axes[0].set_ylim(bottom=0)
    axes[0].grid(True, alpha=0.25, linestyle='--')
    axes[0].set_xticks(month_ticks)
    axes[0].set_xticklabels([])

    # Formatting B
    axes[1].set_ylabel('Cumulative global radiation (MJ m⁻²)', fontsize=11)
    axes[1].set_title('B)', loc='left', fontweight='bold')
    axes[1].legend(title='Year', loc='upper left')
    axes[1].set_ylim(bottom=0)
    axes[1].grid(True, alpha=0.25, linestyle='--')
    axes[1].set_xticks(month_ticks)
    axes[1].set_xticklabels([])

    # Formatting C
    axes[2].set_ylabel('Temperature (°C)', fontsize=11)
    axes[2].set_xlabel('Date', fontsize=11)
    axes[2].set_title('C)', loc='left', fontweight='bold')
    axes[2].axhline(0, color='k', linewidth=0.5, alpha=0.4)
    axes[2].grid(True, alpha=0.25, linestyle='--')
    axes[2].set_xticks(month_ticks)
    axes[2].set_xticklabels(month_labels)

    # Two legends on temperature panel: year colors + line styles
    year_handles = [Line2D([0],[0], color=colors[y], linewidth=2, label=str(y)) for y in years]
    style_handles = [
        Line2D([0],[0], color='gray', linewidth=1.5, linestyle='--', label='Tmax'),
        Line2D([0],[0], color='gray', linewidth=2,   linestyle='-',  label='Tavg'),
        Line2D([0],[0], color='gray', linewidth=1.5, linestyle=':',  label='Tmin'),
    ]
    leg1 = axes[2].legend(handles=year_handles,  loc='upper left',  title='Year',     fontsize=9)
    axes[2].add_artist(leg1)
    axes[2].legend(handles=style_handles, loc='upper right', title='Variable', fontsize=9)

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {out_path}")
    plt.close()

make_plot(df_dr, 'DR region (Drenthe)',           output_dir / 'weather_nasa_power_DR_2023_2025.png')
make_plot(df_zw, 'ZW region (Zeeland/Z-Holland)', output_dir / 'weather_nasa_power_ZW_2023_2025.png')
