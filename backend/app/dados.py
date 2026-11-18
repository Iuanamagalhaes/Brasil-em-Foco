import numpy as np
from . import anomalia, db

ESTADOS = [
 ("AC","Acre",.83,164173,22),("AL","Alagoas",3.13,27830,102),("AM","Amazonas",3.94,1559256,62),
 ("AP","Amapá",.73,142471,16),("BA","Bahia",14.14,564760,417),("CE","Ceará",8.79,148894,184),
 ("ES","Espírito Santo",3.83,46074,78),("GO","Goiás",7.02,340242,246),("MA","Maranhão",6.78,329651,217),
 ("MG","Minas Gerais",20.54,586513,853),("MS","Mato Grosso do Sul",2.76,357142,79),("MT","Mato Grosso",3.66,903208,142),
 ("PA","Pará",8.12,1245871,144),("PB","Paraíba",3.97,56467,223),("PE","Pernambuco",9.06,98068,185),
 ("PI","Piauí",3.27,251616,224),("PR","Paraná",11.44,199308,399),("RJ","Rio de Janeiro",16.06,43750,92),
 ("RN","Rio Grande do Norte",3.3,52810,167),("RO","Rondônia",1.58,237765,52),("RR","Roraima",.64,223645,15),
 ("RS","Rio Grande do Sul",10.88,281707,497),("SC","Santa Catarina",7.61,95731,295),("SE","Sergipe",2.21,21938,75),
 ("SP","São Paulo",44.41,248219.485,645),("TO","Tocantins",1.51,277423,139),("DF","Distrito Federal",2.82,5760,1),
]

CAPITAIS = {
 "AC":(1200401,-9.97,-67.81),"AL":(2704302,-9.67,-35.74),"AM":(1302603,-3.12,-60.02),"AP":(1600303,0.03,-51.07),
 "BA":(2927408,-12.97,-38.51),"CE":(2304400,-3.73,-38.52),"ES":(3205309,-20.32,-40.34),"GO":(5208707,-16.68,-49.25),
 "MA":(2111300,-2.53,-44.30),"MG":(3106200,-19.92,-43.94),"MS":(5002704,-20.47,-54.62),"MT":(5103403,-15.60,-56.10),
 "PA":(1501402,-1.46,-48.50),"PB":(2507507,-7.12,-34.86),"PE":(2611606,-8.05,-34.88),"PI":(2211001,-5.09,-42.80),
 "PR":(4106902,-25.43,-49.27),"RJ":(3304557,-22.91,-43.17),"RN":(2408102,-5.79,-35.21),"RO":(1100205,-8.76,-63.90),
 "RR":(1400100,2.82,-60.67),"RS":(4314902,-30.03,-51.22),"SC":(4205407,-27.60,-48.55),"SE":(2800308,-10.91,-37.07),
 "SP":(3550308,-23.55,-46.63),"TO":(1721000,-10.18,-48.33),"DF":(5300108,-15.78,-47.93),
}

INDICADORES = [
 dict(id="alagamentos", nome="Risco de Alagamentos", rotulo="Precipitação Prevista", unidade="mm", sub="(próx. 7 dias)",
      lo=25, hi=115, sp=82, z_sp=2.4, tol=10, fonte="Open-Meteo (previsão e reanálise ERA5), capital como referência"),
 dict(id="focos_calor", nome="Focos de Calor", rotulo="Focos de Calor", unidade="focos", sub="(último mês completo)",
      lo=30, hi=900, sp=310, z_sp=2.1, tol=15, fonte="INPE BDQueimadas"),
 dict(id="dengue", nome="Casos de Dengue", rotulo="Incidência", unidade="casos/100 mil", sub="(último mês completo)",
      lo=30, hi=420, sp=190, z_sp=1.7, tol=15, fonte="InfoDengue/Fiocruz, capital como referência"),
]

def simulada(i, k):
    ind = INDICADORES[k]
    rng = np.random.default_rng(i * 131 + k * 17 + 7)
    z = rng.uniform(-.8, 2.8)
    atual = float(round(rng.uniform(ind["lo"], ind["hi"])))
    if ESTADOS[i][0] == "SP":
        z, atual = ind["z_sp"], float(ind["sp"])
    ruido = rng.normal(size=11)
    ruido = (ruido - ruido.mean()) / ruido.std(ddof=1)
    media = atual / (1 + .18 * z)
    return dict(hist=list(media * (1 + .18 * ruido)), atual=atual, origem="simulado", fonte="Simulação", periodos=None, ref=None)

def serie_estado(i, k):
    ind, sigla = INDICADORES[k], ESTADOS[i][0]
    rows = db.q("SELECT periodo, valor, atual FROM observacao WHERE indicador=:i AND codigo=:c ORDER BY periodo", i=ind["id"], c=sigla) if _tem_tabela() else []
    atuais = [r for r in rows if r["atual"]]
    if atuais:
        a = atuais[-1]
        base = anomalia.baseline([(r["periodo"], r["valor"]) for r in rows if not r["atual"]], a["periodo"], ind["tol"])
        if len(base) >= 3:
            return dict(hist=[v for _, v in base], atual=a["valor"], origem="real", fonte=ind["fonte"],
                        periodos=[p for p, _ in base], ref=a["periodo"])
    return simulada(i, k)

def _tem_tabela():
    try:
        db.q("SELECT 1 FROM observacao LIMIT 1")
        return True
    except Exception:
        db.init()
        return True
