"""Relatório em PDF (módulo 4): indicadores, motivo do alerta, evolução histórica, fontes e limitações."""
from datetime import date
from io import BytesIO
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from . import dados, servicos

NV = {"A": "Alto", "M": "Moderado", "B": "Baixo"}
VERDE, GRAFITE = colors.HexColor("#295438"), colors.HexColor("#343434")

def _grafico(e):
    v = e["hist"] + [e["atual"]]
    d = Drawing(440, 150)
    lp = LinePlot()
    lp.x, lp.y, lp.width, lp.height = 40, 20, 380, 115
    lp.data = [[(j, y) for j, y in enumerate(v)], [(0, e["media"]), (len(v) - 1, e["media"])]]
    lp.lines[0].strokeColor, lp.lines[0].strokeWidth = GRAFITE, 1.6
    lp.lines[1].strokeColor, lp.lines[1].strokeDashArray = VERDE, (3, 3)
    lp.xValueAxis.visible = False
    d.add(lp)
    return d

def _motivo(e, ind):
    sent = "acima" if e["z"] >= 0 else "abaixo"
    t = (f"O valor atual ({e['atual']:g} {ind['unidade']}) está {abs(e['z']):.1f} desvios-padrão {sent} da média de "
         f"{e['media']:g} observada na mesma época em anos anteriores ({len(e['hist'])} pontos).")
    return t + (" Comportamento fora do padrão histórico." if e["nivel"] == "A" else " Sinal de agravamento a acompanhar." if e["nivel"] == "M" else " Dentro do padrão esperado.")

def gerar(sigla, indicador=0):
    i = servicos._idx(sigla)
    _, nome, pop, area, mun = dados.ESTADOS[i]
    st = getSampleStyleSheet()
    h = st["Heading2"]; h.textColor = VERDE
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm, title=f"Brasil em Foco - {nome}")
    f = [Paragraph(f"Brasil em Foco: relatório de {nome}", st["Title"]), Paragraph(f"Gerado em {date.today():%d/%m/%Y}. População {pop:.1f} mi · área {area:,.0f} km² · {mun} municípios.".replace(",", "."), st["Normal"])]
    fontes, simulado = [], False
    for k, ind in enumerate(dados.INDICADORES):
        e = servicos.estado(i, k)
        simulado |= e["origem"] != "real"
        fontes.append(f"{ind['nome']}: {e['fonte']}")
        f += [Spacer(1, 12), Paragraph(ind["nome"], h)]
        t = Table([["Nível", NV[e["nivel"]], "Valor atual", f"{e['atual']:g} {ind['unidade']}"],
                   ["Média histórica", f"{e['media']:g}", "Desvios-padrão (z)", f"{e['z']:.2f}"],
                   ["Municípios em alerta", e["alertas"], "População exposta", f"{e['expostos']:,}".replace(",", ".")],
                   ["Confiança do modelo", f"{e['confianca']}%", "Origem do dado", e["origem"]]], colWidths=[4 * cm, 3.6 * cm, 4 * cm, 4.8 * cm])
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), .4, colors.grey), ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E7F3C8")), ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#E7F3C8")), ("FONTSIZE", (0, 0), (-1, -1), 9)]))
        f += [t, Spacer(1, 6), Paragraph("<b>Por que o alerta:</b> " + _motivo(e, ind) + f" (método dos municípios em alerta: {e['metodo']}).", st["Normal"]), _grafico(e)]
        ms = servicos.municipios(sigla, k, 5)
        if ms:
            f.append(Paragraph("<b>Municípios em destaque:</b> " + "; ".join(f"{m['nome']} ({m['rotulo']})" for m in ms), st["Normal"]))
    f += [Spacer(1, 12), Paragraph("Fontes", h), Paragraph("<br/>".join(fontes) + "<br/>População, área e municípios: IBGE (Censo 2022).", st["Normal"]),
          Paragraph("Limitações", h),
          Paragraph("O alerta indica comportamento fora do padrão histórico da mesma época, não uma probabilidade de ocorrência. Clima e dengue usam a capital como referência do estado. "
                    "Municípios em alerta e população exposta podem ser estimativas quando não há dado municipal (veja o método). "
                    + ("<b>Atenção: parte dos dados deste relatório é simulada e serve apenas para demonstração.</b>" if simulado else ""), st["Normal"])]
    doc.build(f)
    return buf.getvalue()
