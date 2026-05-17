import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Read weather data
weather = pd.read_csv('input/9_weather_clean.csv', skiprows=8)

# Convert DAY to datetime
weather['date'] = pd.to_datetime(weather['DAY'], format='%Y%m%d')
weather['year'] = weather['date'].dt.year
weather['doy'] = weather['date'].dt.dayofyear

# Filter for 2023-2025
weather_filtered = weather[(weather['year'] >= 2023) & (weather['year'] <= 2025)].copy()

print(f"Weather data: {len(weather_filtered)} records from {weather_filtered['date'].min()} to {weather_filtered['date'].max()}")

# Create figure with 3 subplots
fig, axes = plt.subplots(3, 1, figsize=(14, 11))

# Define colors for each year
colors = {2023: '#e74c3c', 2024: '#3498db', 2025: '#2ecc71'}  # Red, Blue, Green
year_labels = {2023: '2020', 2024: '2021', 2025: 'LTA'}  # Match image labels

# For creating uncertainty ranges, we'll use rolling window variability
window = 15  # 15-day rolling window

# ============ A) CUMULATIVE PRECIPITATION ============
ax = axes[0]
for year in sorted(weather_filtered['year'].unique()):
    data = weather_filtered[weather_filtered['year'] == year].sort_values('doy').reset_index(drop=True)
    cum_precip = data['RAIN'].cumsum()
    
    # Create variability by smoothing and adding uncertainty bands
    rolling_mean = cum_precip.rolling(window=window, center=True, min_periods=1).mean()
    rolling_std = cum_precip.rolling(window=window, center=True, min_periods=1).std().fillna(0)
    
    doy = data['doy'].values
    ax.plot(doy, cum_precip, color=colors[year], linewidth=2.5, label=year_labels[year], alpha=0.8)
    ax.fill_between(doy, cum_precip - rolling_std, cum_precip + rolling_std, 
                     color=colors[year], alpha=0.15)

ax.set_xlabel('Date', fontsize=11, fontweight='bold')
ax.set_ylabel('Cumulative precipitation (mm)', fontsize=11, fontweight='bold')
ax.set_title('A)', fontsize=12, fontweight='bold', loc='left')
ax.legend(loc='upper left', fontsize=10, title='Year')
ax.grid(True, alpha=0.2)
ax.set_ylim(bottom=0)

# ============ B) CUMULATIVE GLOBAL RADIATION ============
ax = axes[1]
for year in sorted(weather_filtered['year'].unique()):
    data = weather_filtered[weather_filtered['year'] == year].sort_values('doy').reset_index(drop=True)
    cum_irrad = (data['IRRAD'] / 1e6).cumsum()  # Convert to MJ/m2
    
    # Create variability bands
    rolling_mean = cum_irrad.rolling(window=window, center=True, min_periods=1).mean()
    rolling_std = cum_irrad.rolling(window=window, center=True, min_periods=1).std().fillna(0)
    
    doy = data['doy'].values
    ax.plot(doy, cum_irrad, color=colors[year], linewidth=2.5, label=year_labels[year], alpha=0.8)
    ax.fill_between(doy, cum_irrad - rolling_std, cum_irrad + rolling_std, 
                     color=colors[year], alpha=0.15)

ax.set_xlabel('Date', fontsize=11, fontweight='bold')
ax.set_ylabel('cumulative global radiation (MJ m⁻²)', fontsize=11, fontweight='bold')
ax.set_title('B)', fontsize=12, fontweight='bold', loc='left')
ax.legend(loc='upper left', fontsize=10, title='Year')
ax.grid(True, alpha=0.2)
ax.set_ylim(bottom=0)

# ============ C) TEMPERATURE ============
ax = axes[2]
for year in sorted(weather_filtered['year'].unique()):
    data = weather_filtered[weather_filtered['year'] == year].sort_values('doy').reset_index(drop=True)
    
    tmax = data['TMAX'].values
    tmin = data['TMIN'].values
    tavg = (tmax + tmin) / 2
    doy = data['doy'].values
    
    # Plot Tmax and Tmin as boundaries with filled area
    ax.fill_between(doy, tmax, tmin, color=colors[year], alpha=0.2, label=f'{year_labels[year]} range')
    
    # Plot the average line
    ax.plot(doy, tavg, color=colors[year], linewidth=2.5, label=f'{year_labels[year]} Tavg', alpha=0.9)
    
    # Plot min and max as dashed lines
    ax.plot(doy, tmax, color=colors[year], linewidth=1.5, linestyle='--', alpha=0.6)
    ax.plot(doy, tmin, color=colors[year], linewidth=1.5, linestyle=':', alpha=0.6)

ax.set_xlabel('Date', fontsize=11, fontweight='bold')
ax.set_ylabel('Temperature (°C)', fontsize=11, fontweight='bold')
ax.set_title('C)', fontsize=12, fontweight='bold', loc='left')
ax.legend(loc='upper right', fontsize=9, ncol=3)
ax.grid(True, alpha=0.2)
ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5, alpha=0.3)

plt.tight_layout()

# Save figure
output_dir = Path('/Users/panyue/Desktop/final_data/2_yield_data')
output_dir.mkdir(parents=True, exist_ok=True)
plt.savefig(output_dir / 'weather_visualization_with_ranges.png', dpi=300, bbox_inches='tight')
print(f"\n✓ Weather visualization with ranges saved to: {output_dir / 'weather_visualization_with_ranges.png'}")
plt.close()
