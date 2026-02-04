from datetime import datetime

import pandas as pd
from pathlib import Path
from pcse.input import NASAPowerWeatherDataProvider

latitude = 51.98
longitude = 5.66

cwd = Path.cwd()
output_dir = cwd / "output"
output_fp = output_dir / "DailyWeatherFromNASAPower.xlsx"

weather_data = NASAPowerWeatherDataProvider(latitude, longitude)
df_weather = pd.DataFrame(weather_data.export())
df_weather.to_excel(output_fp)