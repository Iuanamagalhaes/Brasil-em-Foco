import httpx
from .. import db

def municipios_json(j):
    out = []
    for m in j:
        try:
            uf = m["microrregiao"]["mesorregiao"]["UF"]["sigla"]
        except (TypeError, KeyError):
            uf = m["regiao-imediata"]["regiao-intermediaria"]["UF"]["sigla"]
        out.append((str(m["id"]), m["nome"], uf))
    return out

def populacao_sidra(j):
    return {r["D1C"]: int(r["V"]) for r in j[1:] if str(r.get("V", "")).isdigit()}

def run():
    with httpx.Client(timeout=120, follow_redirects=True) as c:
        muns = municipios_json(c.get("https://servicodados.ibge.gov.br/api/v1/localidades/municipios").json())
        pop = populacao_sidra(c.get("https://apisidra.ibge.gov.br/values/t/4709/n6/all/v/93/p/2022?formato=json").json())
    db.init()
    db.run("DELETE FROM municipio")
    db.run("INSERT INTO municipio VALUES (:i,:n,:u,:p)", [dict(i=i, n=n, u=u, p=pop.get(i)) for i, n, u in muns])
    print(f"IBGE: {len(muns)} municípios, {len(pop)} com população")
