"""
Descarga indicadores del World Bank para Colombia.
Sectores de empleo y desempleo.
"""
import requests
import pandas as pd
from pathlib import Path

RAW = Path("data/raw")
PROCESSED = Path("data/processed")
RAW.mkdir(parents=True, exist_ok=True)
PROCESSED.mkdir(parents=True, exist_ok=True)

INDICATORS = {
    "SL.AGR.EMPL.ZS": "Empleo en agricultura (% del total)",
    "SL.IND.EMPL.ZS": "Empleo en industria (% del total)",
    "SL.SRV.EMPL.ZS": "Empleo en servicios (% del total)",
    "SL.UEM.TOTL.ZS": "Desempleo total (% fuerza laboral)",
    "SL.EMP.TOTL.SP.ZS": "Población activa (% total)",
    "SL.EMP.WORK.ZS": "Asalariados formales (% del empleo)",
    "SL.EMP.SELF.ZS": "Trabajadores por cuenta propia (%)",
    "SL.GDP.PCAP.EM.KD": "PIB por persona empleada (USD const. 2017)",
}

BASE_URL = "https://api.worldbank.org/v2/country/COL/indicator/{}"

all_data = []
for code, name in INDICATORS.items():
    url = BASE_URL.format(code)
    params = {"format": "json", "per_page": 100, "date": "2010:2025"}
    print(f"Descargando {code}...")
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    if len(data) > 1 and data[1]:
        for item in data[1]:
            all_data.append({
                "indicator_code": code,
                "indicator_name": name,
                "year": int(item["date"]),
                "value": item["value"],
                "country": item["country"]["value"],
            })

df = pd.DataFrame(all_data)
df = df.dropna(subset=["value"])
df = df.sort_values(["indicator_code", "year"])

output = PROCESSED / "worldbank_colombia.csv"
df.to_csv(output, index=False)
print(f"Guardado: {output} ({len(df)} filas)")
print(df.head(20))
