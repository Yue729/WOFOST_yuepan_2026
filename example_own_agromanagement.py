import datetime as dt
import matplotlib.pyplot as plt
from pathlib import Path
import pandas as pd
from pcse.base import ParameterProvider
from pcse.input import YAMLCropDataProvider, NASAPowerWeatherDataProvider
from pcse.models import Wofost81_PP
import yaml

latitude = 51.98
longitude = 5.66
start_campaign_date = dt.date(2019, 2, 11)
crop_end_date = dt.date(2019, 9, 20)
crop_end_type = "harvest"
crop_name = "potato"
crop_start_date = dt.date(2019, 5, 12)
crop_start_type = "sowing"
max_duration = 365
variety_name = "Innovator"

cwd = Path.cwd()
input_dir = cwd / "input"
agro_fp = input_dir / "agro_template.yaml"
soil_fp = input_dir / "9_Wofost81_PP_soil.yaml"
site_fp = input_dir / "9_Wofost81_PP_site.yaml"

output_dir = cwd / "output"
fig_fp = output_dir / "output_sim_own_agromanagement.jpeg"

with open(agro_fp, "r") as f:
    agro_text = f.read()

agro_text = agro_text.format(
    start_campaign_date = start_campaign_date,
    crop_end_date = crop_end_date,
    crop_end_type = crop_end_type,
    crop_name = crop_name,
    crop_start_date = crop_start_date,
    crop_start_type = crop_start_type,
    max_duration = max_duration,
    variety_name = variety_name
)
agro_dict = yaml.safe_load(agro_text)

with open(soil_fp, "r") as f:
    soil_dict = yaml.safe_load(f.read())

with open(site_fp, "r") as f:
    site_dict = yaml.safe_load(f.read())

crop_dict = YAMLCropDataProvider(Wofost81_PP)
weather_data = NASAPowerWeatherDataProvider(latitude, longitude)
parameters = ParameterProvider(sitedata=site_dict, soildata=soil_dict, cropdata=crop_dict)
wofost = Wofost81_PP(parameters, weather_data, agro_dict)

wofost.run_till_terminate()
output = wofost.get_output()
df_output = pd.DataFrame(output)

fig, ax = plt.subplots()
ax.plot(df_output["day"], df_output["WSO"])
fig.savefig(fig_fp)