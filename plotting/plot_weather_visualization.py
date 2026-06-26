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
print(f"Years: {sorted(weather_filtered['year'].unique())}")

# Create figure with 3 subplots
fig, axes = plt.subplots(3, 1, figsize=(14, 10))

# Define colors for each year
colors = {2023: '#1f77b4', 2024: '#ff7f0e', 2025: '#2ca02c'}  # Blue, Orange, Green
year_labels = {2023: '2023', 2024: '2024', 2025: '2025'}

# ============ A) CUMULATIVE PRECIPITATION ============
ax = axes[0]
for year in sorted(weather_filtered['year'].unique()):
    data = weather_filtered[weather_filtered['year'] == year].sort_values('doy')
    cum_precip = data['RAIN'].cumsum()
    ax.plot(data['doy'], cum_precip, label=year_labels[year], color=colors[year], linewidth=2.5)

ax.set_xlabel('Date (Day of Year)', fontsize=11, fontweight='bold')
ax.set_ylabel('Cumulative Precipitation (mm)', fontsize=11, fontweight='bold')
ax.set_title('A) Cumulative Precipitation', fontsize=12, fontweight='bold', loc='left')
ax.legend(loc='upper left', fontsize=10, title='Year')
ax.grid(True, alpha=0.3)
ax.set_ylim(bottom=0)

# ============ B) CUMULATIVE GLOBAL RADIATION ============
ax = axes[1]
for year in sorted(weather_filtered['year'].unique()):
    data = weather_filtered[weather_filtered['year'] == year].sort_values('doy')
    # Convert IRRAD from J/m2/day to MJ/m2/day (divide by 1e6)
    cum_irrad = (data['IRRAD'] / 1e6).cumsum()
    ax.plot(data['doy'], cum_irrad, label=year_labels[year], color=colors[year], linewidth=2.5)

ax.set_xlabel('Date (Day of Year)', fontsize=11, fontweight='bold')
ax.set_ylabel('Cumulative Global Radiation (MJ m⁻²)', fontsize=11, fontweight='bold')
ax.set_title('B) Cumulative Global Radiation', fontsize=12, fontweight='bold', loc='left')
ax.legend(loc='upper left', fontsize=10, title='Year')
ax.grid(True, alpha=0.3)
ax.set_ylim(bottom=0)

# ============ C) TEMPERATURE ============
ax = axes[2]
for year in sorted(weather_filtered['year'].unique()):
    data = weather_filtered[weather_filtered['year'] == year].sort_values('doy')
    
    # Plot Tmax and Tmin as lines
    ax.plot(data['doy'], data['TMAX'], color=colors[year], linewidth=2, linestyle='-', label=f'{year_labels[year]} Tmax')
    ax.plot(data['doy'], data['TMIN'], color=colors[year], linewidth=2, linestyle=':', label=f'{year_labels[year]} Tmin')
    
    # Calculate and plot average temperature
    tavg = (data['TMAX'] + data['TMIN']) / 2
    ax.plot(data['doy'], tavg, color=colors[year], linewidth=2.5, linestyle='-', alpha=0.7)

ax.set_xlabel('Date (Day of Year)', fontsize=11, fontweight='bold')
ax.set_ylabel('Temperature (°C)', fontsize=11, fontweight='bold')
ax.set_title('C) Temperature', fontsize=12, fontweight='bold', loc='left')
ax.legend(loc='upper right', fontsize=9, ncol=3)
ax.grid(True, alpha=0.3)
ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5, alpha=0.3)

plt.tight_layout()

# Save figure
output_dir = Path('/Users/panyue/Desktop/final_data/2_yield_data')
output_dir.mkdir(parents=True, exist_ok=True)
plt.savefig(output_dir / 'weather_visualization_2023_2025.png', dpi=300, bbox_inches='tight')
print(f"\n✓ Weather visualization saved to: {output_dir / 'weather_visualization_2023_2025.png'}")
plt.close()
