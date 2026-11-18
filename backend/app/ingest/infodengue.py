from datetime import date, datetime, timezone
import httpx
from .. import dados, db

URL = "https://info.dengue.mat.br/api/alertcity"

def mensal(registros):
    out = {}
    for r in registros:
        d = datetime.fromtimestamp(r["data_iniSE"] / 1000, tz=timezone.utc)
        k = date(d.year, d.month, 1).isoformat()
        out[k] = out.get(k, 0.0) + float(r.get("p_inc100k") or 0)
    return out

def run(anos=5, hoje=None):
    hoje = hoje or date.today()
    ult = date(hoje.year, hoje.month, 1).isoformat()
    linhas = []
    with httpx.Client(timeout=90) as c:
        for uf, (geo, _, _) in dados.CAPITAIS.items():
            tot = {}
            for ano in range(hoje.year - anos, hoje.year + 1):
                r = c.get(URL, params=dict(geocode=geo, disease="dengue", format="json", ew_start=1, ew_end=53, ey_start=ano, ey_end=ano))
                if r.status_code == 200:
                    tot.update(mensal(r.json()))
            tot = {k: v for k, v in tot.items() if k < ult}       
            if not tot:
                continue
            ultimo = max(tot)
            linhas += [(uf, k, v, int(k == ultimo)) for k, v in tot.items()]
            print("ok", uf)
    db.salvar_obs("dengue", "estado", linhas, "InfoDengue/Fiocruz")
