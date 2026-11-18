import json, os
import httpx
from . import dados, servicos

MODELO = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
NV = {"A": "Alto", "M": "Moderado", "B": "Baixo"}

def contexto(sigla):
    i = servicos._idx(sigla)
    sigla_, nome, pop, area, mun = dados.ESTADOS[i]
    inds = []
    for k, ind in enumerate(dados.INDICADORES):
        e = servicos.estado(i, k)
        inds.append(dict(indicador=ind["nome"], unidade=ind["unidade"], valor_atual=e["atual"], media_historica=e["media"], z=e["z"],
                         nivel=NV[e["nivel"]], municipios_em_alerta=e["alertas"], populacao_exposta=e["expostos"], metodo_alerta=e["metodo"],
                         origem_dado=e["origem"], fonte=e["fonte"], confianca_pct=e["confianca"],
                         municipios_destaque=[m["nome"] + " (" + m["rotulo"] + ")" for m in servicos.municipios(sigla, k, 3)]))
    rk = sorted(((servicos.estado(j, 0)["z"], dados.ESTADOS[j][0]) for j in range(27)), reverse=True)
    return dict(estado=nome, sigla=sigla_, populacao_milhoes=pop, area_km2=area, municipios=mun, indicadores=inds,
                posicao_no_ranking_de_alagamentos=[s for _, s in rk].index(sigla_) + 1)

def resumo_local(c):
    linhas = [f"{c['estado']}: {c['populacao_milhoes']:.1f} milhões de habitantes e {c['municipios']} municípios.".replace(".", ",", 1)]
    for x in c["indicadores"]:
        t = f"- {x['indicador']}: nível {x['nivel']} (valor {x['valor_atual']:g} {x['unidade']}, {abs(x['z']):.1f} desvios-padrão {'acima' if x['z'] >= 0 else 'abaixo'} da média). Dado {x['origem_dado']}."
        if x["municipios_destaque"]:
            t += " Destaques: " + "; ".join(x["municipios_destaque"]) + "."
        linhas.append(t)
    linhas.append("Resumo gerado por regras; dados simulados não devem embasar decisões.")
    return "\n".join(linhas)

PROMPT = ("Você é analista de inteligência territorial do projeto Brasil em Foco. Com base APENAS no JSON abaixo, escreva em português "
          "uma visão geral do estado em 150 a 200 palavras, em 2 ou 3 parágrafos curtos, sem markdown. Diga o que está fora do padrão "
          "histórico e por quê (cite valores e z-score), onde estão os municípios de destaque e o que acompanhar. Não invente números, "
          "causas ou previsões. Quando origem_dado for 'simulado', avise que o número é demonstrativo. Mencione que o alerta indica "
          "comportamento fora do padrão, não uma probabilidade.\n\nDADOS:\n")

def visao_geral(sigla):
    c = contexto(sigla)
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return dict(texto=resumo_local(c), gerado_por="regras locais (defina ANTHROPIC_API_KEY para usar a IA)")
    try:
        r = httpx.post("https://api.anthropic.com/v1/messages", timeout=60,
                       headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                       json={"model": MODELO, "max_tokens": 700, "messages": [{"role": "user", "content": PROMPT + json.dumps(c, ensure_ascii=False)}]})
        r.raise_for_status()
        return dict(texto=r.json()["content"][0]["text"].strip(), gerado_por=f"IA ({MODELO})")
    except Exception as e:
        return dict(texto=resumo_local(c), gerado_por=f"regras locais (falha ao chamar a IA: {type(e).__name__})")
