# Brasil em Foco

Plataforma de inteligência socioambiental: mapa dos estados, indicadores, alertas por **detecção de anomalias**
(z-score contra a mesma época de anos anteriores), análise municipal, comparação entre estados, relatório em PDF
e visão geral com IA.

## 1. Rodar
    python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    cd backend && uvicorn app.main:app --reload             # http://localhost:8000  (docs: /docs)
Com Docker + PostgreSQL: `docker compose up --build`. Testes: `cd backend && pytest`.
Sem dados carregados, os indicadores aparecem com o selo **"Dado simulado"**.

## 2. Carregar dados reais (precisa de internet; rode dentro de `backend/`)
    python -m app.ingest ibge            # municípios + população (IBGE: localidades e SIDRA 4709)
    python -m app.ingest inpe            # focos de calor, 5 anos (~60 arquivos mensais; use --rapido p/ só o mesmo mês)
    python -m app.ingest openmeteo       # chuva prevista 7 dias + histórico de 10 anos (capitais)
    python -m app.ingest infodengue      # dengue (InfoDengue/Fiocruz, capitais)
    python -m app.ingest atlas atlas.csv # Atlas Digital de Desastres (baixe no site e exporte para CSV)
    python -m app.ingest ips ips.csv     # IPS Brasil (baixe a planilha e exporte para CSV)
Repita a ingestão periodicamente (cron) para manter os alertas atualizados.
- **atlas.csv:** precisa de colunas de código IBGE, data e tipo/COBRADE; só entram inundação, alagamento e enxurrada.
- **ips.csv:** colunas de código IBGE, IPS geral, Necessidades Humanas Básicas, Fundamentos do Bem-estar e Oportunidades.

## 3. IA
Defina `ANTHROPIC_API_KEY` (e opcionalmente `ANTHROPIC_MODEL`). O botão "Visão geral com IA" envia à API apenas os números
calculados (nunca dados pessoais). Sem a chave, devolve um resumo por regras e informa isso na tela.

## 4. API
`/api/modelo` · `/api/estados/{uf}` · `/api/estados/{uf}/municipios` · `/api/municipios/{ibge}` · `/api/ranking` ·
`/api/comparar?siglas=SP,RJ` · `/api/metricas` · `/api/ia/visao-geral/{uf}` · `/api/relatorio/{uf}.pdf`

## 5. Como o alerta funciona
Para cada indicador, compara o valor atual com os valores da mesma época (±10 a 15 dias do ano) em anos anteriores:
z ≥ 2 = Alto, z ≥ 1 = Moderado. Municípios em alerta: focos de calor usa o z de cada município (INPE); alagamentos usa
os municípios com registro hídrico nos últimos 5 anos (Atlas) quando o estado está em Moderado/Alto; nos demais casos é
uma estimativa (o campo `metodo` informa qual).

## 6. Métricas (precisão, recall, F1)
`/api/metricas` devolve duas avaliações: **sintética** (valida só o código) e **real** (walk-forward com os dados
carregados; ocorrência = valor acima do percentil 90 da série do estado; alerta = z ≥ 2). O limite de 90% é uma
definição nossa e deve ser ajustada com a equipe.
