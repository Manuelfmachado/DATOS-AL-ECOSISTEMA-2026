"""
Prueba rápida de Chronos-Bolt con datos del World Bank.
"""
import pandas as pd
import torch
from chronos import ChronosPipeline

# Cargar datos
wb = pd.read_csv("data/processed/worldbank_colombia.csv")
print("Indicadores:", wb['indicator_name'].unique())

# Tomar empleo en servicios
services = wb[wb['indicator_code'] == 'SL.SRV.EMPL.ZS'].sort_values('year')
values = services['value'].values
print(f"Serie servicios ({len(values)} años): {values}")

# Cargar modelo
print("Cargando Chronos T5 small...")
pipeline = ChronosPipeline.from_pretrained(
    "amazon/chronos-t5-small",
    device_map="cpu",
    torch_dtype=torch.float32,
)

# Predecir 5 y 10 años
context = torch.tensor(values).unsqueeze(0)
for horizon in [5, 10]:
    print(f"Prediciendo {horizon} años...")
    forecast = pipeline.predict(context, horizon)
    print(f"Forecast {horizon}: {forecast[0].tolist()}")
