from datetime import date
import numpy as np

LIMIAR_ALTO, LIMIAR_MODERADO = 2.0, 1.0

def zscore(hist, atual):
    h = np.asarray(hist, float)
    media, desvio = float(h.mean()), float(h.std(ddof=1))
    piso = max(1.0, .5 * np.sqrt(max(media, 1.0)))     
    return media, desvio, float((atual - media) / max(desvio, piso))

def nivel(z):
    return "A" if z >= LIMIAR_ALTO else "M" if z >= LIMIAR_MODERADO else "B"

def avaliar(hist, atual):
    media, desvio, z = zscore(hist, atual)
    return dict(hist=[round(float(v), 2) for v in hist], atual=atual, media=round(media, 2), desvio=round(desvio, 2),
                z=round(z, 2), nivel=nivel(z), confianca=int(round(min(96, 50 + 10 * abs(z) + min(len(hist), 30) * .4))))

def estimativa(municipios, pop_mi, z):
    zp = max(z, 0.0)
    return int(round(municipios * zp / 3 * .035)), int(round(pop_mi * 1e6 * .00235 * zp / 1e4)) * 10000

def _dist(d1, d2):
    a = abs(d1.timetuple().tm_yday - d2.timetuple().tm_yday)
    return min(a, 366 - a)

def baseline(pontos, ref, tol):
    r = date.fromisoformat(ref)
    sel = []
    for p, v in pontos:
        d = date.fromisoformat(p)
        if d.year < r.year and _dist(d, r) <= tol:
            sel.append((p, v))
    return sorted(sel)

def backtest_sintetico(n=3000, seed=42, limiar=LIMIAR_ALTO, prevalencia=.15):
    rng = np.random.default_rng(seed)
    tp = fp = fn = tn = 0
    for _ in range(n):
        base, sd = rng.uniform(20, 500), rng.uniform(.08, .25)
        hist = base * (1 + sd * rng.normal(size=11))
        real = rng.random() < prevalencia
        atual = base * (1 + sd * (rng.normal() + (rng.uniform(2.5, 4) if real else 0)))
        alerta = zscore(hist, atual)[2] >= limiar
        tp += alerta and real; fp += alerta and not real; fn += (not alerta) and real; tn += (not alerta) and not real
    return _metricas(tp, fp, fn, tn, limiar, "Séries sintéticas com anomalias injetadas (valida o código, não o desempenho real).")

def backtest_real(series, tol, limiar=LIMIAR_ALTO, pct=90, min_hist=3):
    tp = fp = fn = tn = 0
    for pts in series.values():
        if len(pts) < 24:
            continue
        pts = sorted(pts)
        lim = float(np.percentile([v for _, v in pts], pct))
        for j, (p, v) in enumerate(pts):
            base = baseline(pts[:j], p, tol)
            if len(base) < min_hist:
                continue
            alerta = zscore([b for _, b in base], v)[2] >= limiar
            ocorr = v > lim
            tp += alerta and ocorr; fp += alerta and not ocorr; fn += (not alerta) and ocorr; tn += (not alerta) and not ocorr
    if tp + fp + fn + tn < 30:
        return None
    return _metricas(tp, fp, fn, tn, limiar, f"Walk-forward em dados reais; ocorrência = valor acima do percentil {pct} da série do estado.")

def _metricas(tp, fp, fn, tn, limiar, obs):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return dict(precisao=round(p, 3), recall=round(r, 3), f1=round(f1, 3), amostras=int(tp + fp + fn + tn), limiar_z=limiar,
                matriz=dict(vp=int(tp), fp=int(fp), fn=int(fn), vn=int(tn)), observacao=obs)
