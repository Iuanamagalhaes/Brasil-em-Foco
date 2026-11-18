import csv, io, unicodedata
from .. import db, servicos

def _n(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn").strip()

def _ler(caminho):
    for enc in ("utf-8-sig", "latin-1"):
        try:
            txt = open(caminho, encoding=enc).read()
            break
        except UnicodeDecodeError:
            continue
    sep = ";" if txt.split("\n")[0].count(";") >= txt.split("\n")[0].count(",") else ","
    return list(csv.DictReader(io.StringIO(txt), delimiter=sep))

def _col(cols, *chaves):
    for c in cols:
        if any(k in _n(c) for k in chaves):
            return c
    raise ValueError(f"coluna não encontrada ({'/'.join(chaves)}). Colunas do arquivo: {cols}")

HIDRICOS = ("inunda", "alagament", "enxurrada")

def atlas_linhas(rows):
    c = list(rows[0].keys())
    cib, cdt = _col(c, "ibge", "cod_mun", "codigo"), _col(c, "data")
    ctp = _col(c, "cobrade", "tipo", "descri")
    out = []
    for r in rows:
        tipo = _n(r[ctp])
        d = r[cdt].strip()[:10]
        if d[2:3] == "/":
            d = f"{d[6:10]}-{d[3:5]}-{d[0:2]}"     
        if any(h in tipo for h in HIDRICOS) and r[cib].strip().isdigit():
            out.append((r[cib].strip()[:7], d, r[ctp].strip()[:60]))
    return out

def ips_linhas(rows):
    c = list(rows[0].keys())
    ci, cg = _col(c, "ibge", "cod"), _col(c, "geral", "ips")
    cn, cf, co = _col(c, "necess"), _col(c, "fundament"), _col(c, "oportun")
    f = lambda x: float(x.replace(",", ".")) if x.strip() else None
    return [(r[ci].strip()[:7], f(r[cg]), f(r[cn]), f(r[cf]), f(r[co])) for r in rows if r[ci].strip().isdigit()]

def run_atlas(caminho):
    db.init()
    linhas = atlas_linhas(_ler(caminho))
    db.run("DELETE FROM desastre")
    db.run("INSERT INTO desastre VALUES (:i,:d,:t)", [dict(i=i, d=d, t=t) for i, d, t in linhas])
    servicos.limpar_cache()
    print(f"Atlas: {len(linhas)} registros hídricos")

def run_ips(caminho):
    db.init()
    linhas = ips_linhas(_ler(caminho))
    db.run("DELETE FROM ips")
    db.run("INSERT INTO ips VALUES (:i,:g,:n,:f,:o)", [dict(i=a, g=b, n=c, f=d, o=e) for a, b, c, d, e in linhas])
    print(f"IPS: {len(linhas)} municípios")
