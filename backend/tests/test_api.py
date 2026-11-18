import io
from datetime import date
import pytest
from fastapi.testclient import TestClient
from app import anomalia, db, servicos
from app.main import app
from app.ingest import arquivos, infodengue, inpe, ibge, openmeteo

c = TestClient(app)

def test_simulado_sp_como_no_mockup():
    d = c.get("/api/estados/SP?indicador=0").json()
    assert d["origem"] == "simulado" and d["atual"] == 82 and d["nivel"] == "A" and d["alertas"] == 18 and d["expostos"] == 250000

def test_zscore_e_niveis():
    _, _, z = anomalia.zscore([10, 12, 11, 9, 10, 11, 10, 12, 9, 10, 11], 20)
    assert anomalia.nivel(z) == "A" and anomalia.nivel(0.2) == "B"

def test_baseline_mesma_epoca_anos_anteriores():
    pts = [("2023-10-01", 5), ("2024-10-01", 6), ("2025-10-01", 7), ("2025-03-01", 99), ("2026-10-01", 8)]
    assert [v for _, v in anomalia.baseline(pts, "2026-10-01", 15)] == [5, 6, 7]

def test_backtest_sintetico():
    m = anomalia.backtest_sintetico(n=1500)
    assert 0 <= m["precisao"] <= 1 and m["f1"] > .5

def test_parsers_das_fontes():
    est, mun = inpe.contar(io.StringIO("lat,lon,estado,municipio_id\n1,2,SÃO PAULO,3550308\n1,2,SÃO PAULO,3550308\n1,2,ACRE,1200401\n"))
    assert est == {"SP": 2, "AC": 1} and mun["3550308"] == 2
    assert infodengue.mensal([{"data_iniSE": 1759276800000, "p_inc100k": 3.5}, {"data_iniSE": 1759881600000, "p_inc100k": 1.5}]) == {"2025-10-01": 5.0}
    assert openmeteo.janelas7([f"d{i}" for i in range(14)], [1.0] * 14) == [("d6", 7.0), ("d13", 7.0)]
    assert ibge.populacao_sidra([{"V": "Valor"}, {"D1C": "3550308", "V": "11451999"}]) == {"3550308": 11451999}

def _csv(tmp_path, nome, txt):
    p = tmp_path / nome
    p.write_text(txt, encoding="utf-8")
    return str(p)

@pytest.fixture(scope="module")
def base(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("d")
    db.init()
    db.run("INSERT INTO municipio VALUES (:i,:n,:u,:p)", [dict(i="3550308", n="São Paulo", u="SP", p=11451999), dict(i="3509502", n="Campinas", u="SP", p=1139047), dict(i="3304557", n="Rio de Janeiro", u="RJ", p=6211223)])
    est, mun = [], []
    for ano in range(2019, 2027):                    
        v = 1000 + 10 * (ano % 3)
        est.append(("SP", f"{ano}-10-01", 3000 if ano == 2026 else v, int(ano == 2026)))
        mun += [("3550308", f"{ano}-10-01", 300 if ano == 2026 else 20 + ano % 3, int(ano == 2026)), ("3509502", f"{ano}-10-01", 12, int(ano == 2026))]
    est += [(s, f"{a}-{m:02d}-01", 500 + (a * m) % 40, 0) for s in ("SP", "RJ") for a in range(2019, 2026) for m in range(1, 13) if m != 10]
    db.salvar_obs("focos_calor", "estado", est, "teste")
    db.salvar_obs("focos_calor", "municipio", mun, "teste")
    atlas = _csv(tmp, "atlas.csv", "Código IBGE;Data;Descrição do tipo\n3550308;15/01/2025;Alagamentos\n3550308;10/02/2024;Inundações\n3509502;03/03/2025;Enxurradas\n3509502;03/03/2025;Estiagem\n")
    arquivos.run_atlas(atlas)
    ips = _csv(tmp, "ips.csv", "cod_ibge,IPS Geral,Necessidades Humanas Básicas,Fundamentos do Bem-estar,Oportunidades\n3550308,\"71,2\",\"80,1\",\"70,3\",\"63,2\"\n")
    arquivos.run_ips(ips)
    servicos.limpar_cache()

def test_estado_real_e_alerta_municipal(base):
    d = c.get("/api/estados/SP?indicador=1").json()
    assert d["origem"] == "real" and d["nivel"] == "A" and d["metodo"].startswith("municipal") and d["alertas"] >= 1
    assert d["expostos"] >= 11451999 and len(d["periodos"]) == 7

def test_municipios_e_detalhe(base):
    top = c.get("/api/estados/SP/municipios?indicador=1").json()
    assert top[0]["nome"] == "São Paulo" and top[0]["nivel"] == "A"
    hid = c.get("/api/estados/SP/municipios?indicador=0").json()
    assert hid[0]["nome"] == "São Paulo" and hid[0]["rotulo"].startswith("2 registros")
    m = c.get("/api/municipios/3550308").json()
    assert m["ips"]["geral"] == 71.2 and m["focos"]["nivel"] == "A" and c.get("/api/municipios/0000000").status_code == 404

def test_comparar_e_metricas_reais(base):
    r = c.get("/api/comparar?siglas=SP,RJ&indicador=1").json()
    assert [x["sigla"] for x in r] == ["SP", "RJ"]
    m = c.get("/api/metricas").json()
    assert m["sintetico"]["f1"] > .5 and isinstance(m["real"]["focos_calor"], dict)
    assert isinstance(m["real"]["dengue"], str)           # sem dado real ainda

def test_ia_sem_chave_e_pdf(base):
    d = c.get("/api/ia/visao-geral/SP").json()
    assert "regras locais" in d["gerado_por"] and "São Paulo" in d["texto"]
    r = c.get("/api/relatorio/SP.pdf")
    assert r.headers["content-type"] == "application/pdf" and r.content[:4] == b"%PDF"
    assert c.get("/api/estados/XX").status_code == 404

def test_front_servido():
    assert "Brasil em Foco" in c.get("/").text
