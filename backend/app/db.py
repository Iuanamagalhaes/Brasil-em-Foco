import os
from pathlib import Path
from sqlalchemy import create_engine, text

_DATA = Path(__file__).resolve().parent.parent / "data"
_DATA.mkdir(exist_ok=True)        
URL = os.getenv("DATABASE_URL") or f"sqlite:///{(_DATA / 'bef.db').as_posix()}"
engine = create_engine(URL, future=True)

SCHEMA = [
 """CREATE TABLE IF NOT EXISTS observacao(
      indicador VARCHAR(30), escopo VARCHAR(10), codigo VARCHAR(10), periodo VARCHAR(10),
      valor DOUBLE PRECISION, atual INTEGER, fonte VARCHAR(80),
      PRIMARY KEY (indicador, codigo, periodo))""",
 "CREATE TABLE IF NOT EXISTS municipio(ibge VARCHAR(7) PRIMARY KEY, nome VARCHAR(80), uf VARCHAR(2), populacao INTEGER)",
 "CREATE TABLE IF NOT EXISTS desastre(ibge VARCHAR(7), data VARCHAR(10), tipo VARCHAR(60))",
 """CREATE TABLE IF NOT EXISTS ips(ibge VARCHAR(7) PRIMARY KEY, geral DOUBLE PRECISION,
      necessidades DOUBLE PRECISION, fundamentos DOUBLE PRECISION, oportunidades DOUBLE PRECISION)""",
]

def init():
    with engine.begin() as c:
        for s in SCHEMA:
            c.execute(text(s))

def q(sql, **p):
    with engine.connect() as c:
        return [dict(r._mapping) for r in c.execute(text(sql), p)]

def run(sql, linhas=None, **p):
    with engine.begin() as c:
        c.execute(text(sql), linhas if linhas is not None else p)

def salvar_obs(indicador, escopo, linhas, fonte):
    init()
    run("DELETE FROM observacao WHERE indicador=:i AND escopo=:e", i=indicador, e=escopo)
    if linhas:
        run("INSERT INTO observacao VALUES (:i,:e,:c,:p,:v,:a,:f)",
            [dict(i=indicador, e=escopo, c=c, p=p, v=float(v), a=int(a), f=fonte) for c, p, v, a in linhas])
