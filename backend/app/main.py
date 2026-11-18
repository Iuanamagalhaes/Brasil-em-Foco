from pathlib import Path
from fastapi import FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from . import dados, db, ia, relatorio, servicos

app = FastAPI(title="Brasil em Foco", version="0.2.0")
FRONT = Path(__file__).resolve().parents[2] / "frontend"
db.init()

def _k(k):
    if not 0 <= k < len(dados.INDICADORES):
        raise HTTPException(404, "Indicador inexistente")
    return k

def _uf(sigla):
    try:
        return servicos._idx(sigla)
    except KeyError:
        raise HTTPException(404, "Estado inexistente")

@app.get("/api/saude")
def saude():
    return {"status": "ok"}

@app.get("/api/indicadores")
def indicadores():
    return dados.INDICADORES

@app.get("/api/estados")
def estados():
    return [dict(sigla=s, nome=n, populacao_milhoes=p, area_km2=a, municipios=m) for s, n, p, a, m in dados.ESTADOS]

@app.get("/api/modelo")
def modelo(indicador: int = 0):
    return servicos.modelo(_k(indicador))

@app.get("/api/estados/{sigla}")
def estado(sigla: str, indicador: int = 0):
    return servicos.estado(_uf(sigla), _k(indicador))

@app.get("/api/estados/{sigla}/municipios")
def municipios(sigla: str, indicador: int = 0, n: int = 8):
    _uf(sigla)
    return servicos.municipios(sigla, _k(indicador), n)

@app.get("/api/municipios/{ibge}")
def municipio(ibge: str):
    m = servicos.municipio(ibge)
    if not m:
        raise HTTPException(404, "Município não encontrado (rode a ingestão do IBGE)")
    return m

@app.get("/api/ranking")
def ranking(indicador: int = 0, n: int = 5):
    return sorted(servicos.modelo(_k(indicador)), key=lambda x: -x["z"])[:n]

@app.get("/api/comparar")
def comparar(siglas: str, indicador: int = 0):
    lista = [s for s in siglas.split(",") if s][:4]
    for s in lista:
        _uf(s)
    return servicos.comparar(lista, _k(indicador))

@app.get("/api/metricas")
def metricas():
    return servicos.metricas()

@app.get("/api/ia/visao-geral/{sigla}")
def visao_geral(sigla: str):
    _uf(sigla)
    return ia.visao_geral(sigla)

@app.get("/api/relatorio/{sigla}.pdf")
def pdf(sigla: str, indicador: int = 0):
    _uf(sigla)
    return Response(relatorio.gerar(sigla, indicador), media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="brasil-em-foco-{sigla.upper()}.pdf"'})

app.mount("/", StaticFiles(directory=FRONT, html=True), name="front")
