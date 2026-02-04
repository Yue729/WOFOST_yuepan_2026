import matplotlib.pyplot as plt
from pathlib import Path
import pandas as pd
from pcse.base import ParameterProvider
from pcse.input import CSVWeatherDataProvider, YAMLCropDataProvider
from pcse.models import Wofost81_PP
import yaml

cwd = Path.cwd()
input_dir = cwd / "input"
agro_fp = input_dir / "9_Wofost81_PP_agro.yaml"
soil_fp = input_dir / "9_Wofost81_PP_soil.yaml"
site_fp = input_dir / "9_Wofost81_PP_site.yaml"
weather_fp = input_dir / "9_weather.csv"

output_dir = cwd / "output"
fig_fp = output_dir / "output.jpeg"

with open(agro_fp, "r") as f:
    agro_text = f.read()
    agro_dict = yaml.safe_load(agro_text)

with open(soil_fp, "r") as f:
    soil_dict = yaml.safe_load(f.read())

with open(site_fp, "r") as f:
    site_dict = yaml.safe_load(f.read())

crop_dict = YAMLCropDataProvider(Wofost81_PP)
weather_data = CSVWeatherDataProvider(weather_fp)
parameters = ParameterProvider(sitedata=site_dict, soildata=soil_dict, cropdata=crop_dict)
wofost = Wofost81_PP(parameters, weather_data, agro_dict)

wofost.run_till_terminate()
output = wofost.get_output()
df_output = pd.DataFrame(output)

fig, ax = plt.subplots()
ax.plot(df_output["day"], df_output["WSO"])
fig.savefig(fig_fp)