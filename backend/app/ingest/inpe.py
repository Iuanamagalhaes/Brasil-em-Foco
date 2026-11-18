import csv, unicodedata
from datetime import date
import httpx
from .. import dados, db, servicos

URL = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/mensal/Brasil/focos_mensal_br_{ym}.csv"

def _n(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.upper().strip()) if unicodedata.category(c) != "Mn")
NOME2UF = {_n(e[1]): e[0] for e in dados.ESTADOS}

def contar(linhas):
    est, mun = {}, {}
    for r in csv.DictReader(linhas):
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        uf = NOME2UF.get(_n(r.get("estado", "")))
        if not uf:
            continue
        est[uf] = est.get(uf, 0) + 1
        mid = r.get("municipio_id", "")
        if mid.replace(".0", "").isdigit():
            mid = mid.replace(".0", "")[:7]
            mun[mid] = mun.get(mid, 0) + 1
    return est, mun

def meses(ultimo, n):
    y, m, out = ultimo.year, ultimo.month, []
    for _ in range(n):
        out.append(date(y, m, 1))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out[::-1]

def run(anos=5, rapido=False, hoje=None):
    hoje = hoje or date.today()
    ult = meses(date(hoje.year - (hoje.month == 1), (hoje.month - 2) % 12 + 1, 1), 1)[0]   # último mês completo
    lista = meses(ult, anos * 12)
    if rapido:
        lista = [d for d in lista if d.month == ult.month]
    le, lm = [], []
    with httpx.Client(timeout=300, follow_redirects=True) as c:
        for d in lista:
            u = URL.format(ym=d.strftime("%Y%m"))
            with c.stream("GET", u) as r:
                if r.status_code != 200:
                    print("sem arquivo:", u); continue
                est, mun = contar(r.iter_lines())
            atual = int(d == ult)
            le += [(s[0], d.isoformat(), est.get(s[0], 0), atual) for s in dados.ESTADOS]
            lm += [(i, d.isoformat(), v, atual) for i, v in mun.items()]
            print("ok", d.strftime("%Y-%m"), sum(est.values()), "focos")
    db.salvar_obs("focos_calor", "estado", le, "INPE BDQueimadas")
    db.salvar_obs("focos_calor", "municipio", lm, "INPE BDQueimadas")
    servicos.limpar_cache()
