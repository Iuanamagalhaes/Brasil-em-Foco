from datetime import date
from . import anomalia, dados, db

_C = {}
def limpar_cache():
    _C.clear()

def _idx(sigla):
    for i, e in enumerate(dados.ESTADOS):
        if e[0] == sigla.upper():
            return i
    raise KeyError(sigla)

def municipal_focos(sigla):
    if ("f", sigla) in _C:
        return _C[("f", sigla)]
    ind = dados.INDICADORES[1]
    est = db.q("SELECT periodo, valor, atual FROM observacao WHERE indicador='focos_calor' AND codigo=:c", c=sigla)
    ref = next((r["periodo"] for r in est if r["atual"]), None)
    out = []
    if ref:
        base = anomalia.baseline([(r["periodo"], r["valor"]) for r in est if not r["atual"]], ref, ind["tol"])
        per = [p for p, _ in base]
        obs = db.q("""SELECT o.codigo, o.periodo, o.valor FROM observacao o JOIN municipio m ON m.ibge=o.codigo
                      WHERE o.indicador='focos_calor' AND o.escopo='municipio' AND m.uf=:u""", u=sigla)
        por = {}
        for r in obs:
            por.setdefault(r["codigo"], {})[r["periodo"]] = r["valor"]
        for m in db.q("SELECT ibge, nome, populacao FROM municipio WHERE uf=:u", u=sigla):
            d = por.get(m["ibge"], {})
            if len(per) < 3:
                break
            res = anomalia.avaliar([d.get(p, 0.0) for p in per], d.get(ref, 0.0))
            out.append(dict(ibge=m["ibge"], nome=m["nome"], populacao=m["populacao"] or 0, **res))
    _C[("f", sigla)] = out
    return out

def _desastres(sigla, anos=5):
    return db.q("""SELECT m.ibge, m.nome, m.populacao, COUNT(*) n FROM desastre d JOIN municipio m ON m.ibge=d.ibge
                   WHERE m.uf=:u AND d.data>=:d GROUP BY m.ibge, m.nome, m.populacao ORDER BY n DESC""",
                u=sigla, d=str(date.today().year - anos) + "-01-01")

def _alerta(sigla, k, r, pop, mun, origem):
    if origem == "real":
        if dados.INDICADORES[k]["id"] == "focos_calor":
            ms = municipal_focos(sigla)
            if ms:
                sel = [m for m in ms if m["nivel"] == "A" and m["atual"] >= 5]
                return len(sel), sum(m["populacao"] for m in sel), "municipal (INPE)"
        if r["nivel"] != "B":
            d = _desastres(sigla)
            if d:
                return len(d), sum(x["populacao"] or 0 for x in d), "municípios com registro hídrico em 5 anos (Atlas)"
    a, e = anomalia.estimativa(mun, pop, r["z"])
    return a, e, "estimado"

def estado(i, k):
    sigla, nome, pop, area, mun = dados.ESTADOS[i]
    s = dados.serie_estado(i, k)
    r = anomalia.avaliar(s["hist"], s["atual"])
    al, ex, met = _alerta(sigla, k, r, pop, mun, s["origem"])
    return dict(sigla=sigla, nome=nome, origem=s["origem"], fonte=s["fonte"], periodos=s["periodos"], ref=s["ref"],
                alertas=al, expostos=ex, metodo=met, **r)

def modelo(k):
    return [estado(i, k) for i in range(len(dados.ESTADOS))]

def _rotulo_z(m):
    return f"{int(m['atual'])} focos · z {str(m['z']).replace('.', ',')}"

def municipios(sigla, k, n=8):
    sigla = sigla.upper()
    if dados.INDICADORES[k]["id"] == "focos_calor":
        ms = sorted([m for m in municipal_focos(sigla) if m["atual"] >= 5], key=lambda m: -m["z"])[:n]
        if ms:
            return [dict(ibge=m["ibge"], nome=m["nome"], nivel=m["nivel"], rotulo=_rotulo_z(m), populacao=m["populacao"]) for m in ms]
    d = _desastres(sigla)[:n]
    return [dict(ibge=x["ibge"], nome=x["nome"], populacao=x["populacao"], nivel="A" if x["n"] >= 5 else "M" if x["n"] >= 2 else "B",
                 rotulo=f"{x['n']} registros em 5 anos") for x in d]

def municipio(ibge):
    m = db.q("SELECT * FROM municipio WHERE ibge=:i", i=ibge)
    if not m:
        return None
    m = m[0]
    ips = db.q("SELECT * FROM ips WHERE ibge=:i", i=ibge)
    anos = db.q("SELECT SUBSTR(data,1,4) ano, COUNT(*) n FROM desastre WHERE ibge=:i GROUP BY SUBSTR(data,1,4) ORDER BY ano", i=ibge)
    foco = next((x for x in municipal_focos(m["uf"]) if x["ibge"] == ibge), None)
    return dict(ibge=ibge, nome=m["nome"], uf=m["uf"], populacao=m["populacao"], ips=ips[0] if ips else None,
                desastres_por_ano=anos, focos=foco)

def comparar(siglas, k):
    return [estado(_idx(s), k) for s in siglas]

def metricas():
    out = dict(sintetico=anomalia.backtest_sintetico(), real={})
    for k, ind in enumerate(dados.INDICADORES):
        rows = db.q("SELECT codigo, periodo, valor FROM observacao WHERE indicador=:i AND escopo='estado' AND atual=0", i=ind["id"])
        ser = {}
        for r in rows:
            ser.setdefault(r["codigo"], []).append((r["periodo"], r["valor"]))
        res = anomalia.backtest_real(ser, ind["tol"]) if ser else None
        out["real"][ind["id"]] = res or "sem dados reais suficientes (rode a ingestão)"
    return out
