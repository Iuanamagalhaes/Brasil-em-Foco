import time
from datetime import date, timedelta
import httpx
from .. import dados, db

def janelas7(datas, chuva, passo=7):
    out = []
    for i in range(6, len(datas), passo):
        w = chuva[i - 6:i + 1]
        if all(v is not None for v in w):
            out.append((datas[i], sum(w)))
    return out

def run(anos=10, hoje=None):
    hoje = hoje or date.today()
    hist, atual = [], []
    with httpx.Client(timeout=60) as c:
        for uf, (_, lat, lon) in dados.CAPITAIS.items():
            a = c.get("https://archive-api.open-meteo.com/v1/archive", params=dict(
                latitude=lat, longitude=lon, daily="precipitation_sum", timezone="America/Sao_Paulo",
                start_date=(hoje - timedelta(days=365 * anos)).isoformat(), end_date=(hoje - timedelta(days=6)).isoformat())).json()["daily"]
            hist += [(uf, d, v, 0) for d, v in janelas7(a["time"], a["precipitation_sum"])]
            f = c.get("https://api.open-meteo.com/v1/forecast", params=dict(
                latitude=lat, longitude=lon, daily="precipitation_sum", forecast_days=7, timezone="America/Sao_Paulo")).json()["daily"]
            atual.append((uf, hoje.isoformat(), sum(v or 0 for v in f["precipitation_sum"]), 1))
            print("ok", uf); time.sleep(.5)
    db.salvar_obs("alagamentos", "estado", hist + atual, "Open-Meteo")
