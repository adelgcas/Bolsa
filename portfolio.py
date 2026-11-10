"""Análisis de la cartera del usuario: beneficio actual y alertas de venta según noticias y modelo."""
import datetime as dt

import numpy as np
import pandas as pd
import yfinance as yf

import config as C
from data import daily_tone_volume
from pipeline import FEATS, MACRO_KEY, _series, build_features

Z_ALERT = -1.5  # noticias "inusualmente negativas": 1,5 desviaciones por debajo de lo normal de los últimos 60 días


def _prices_since(tickers, start):
    df = yf.download(list(tickers), start=start.strftime("%Y-%m-%d"), auto_adjust=True, progress=False)["Close"]
    if isinstance(df, pd.Series):
        df = df.to_frame(list(tickers)[0])
    df = df.dropna(how="all").ffill()
    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_localize(None)
    return df


def clean_holdings(df):
    d = df.copy()
    for c in ("ticker", "fecha_compra", "importe", "busqueda", "sector"):
        if c not in d:
            d[c] = None
    d["ticker"] = d["ticker"].fillna("").astype(str).str.strip().str.upper()
    d["fecha_compra"] = pd.to_datetime(d["fecha_compra"], errors="coerce")
    d["importe"] = pd.to_numeric(d["importe"], errors="coerce")
    d = d[(d["ticker"] != "") & d["fecha_compra"].notna() & (d["importe"] > 0)]
    for c in ("busqueda", "sector"):
        d[c] = d[c].fillna("").astype(str).str.strip()
    return d.reset_index(drop=True)


def _z(s):
    s = s.dropna()
    if len(s) < 30:
        return 0.0
    hist = s.iloc[-61:-1]
    sd = hist.std()
    if not sd or np.isnan(sd):
        return 0.0
    return float((s.iloc[-1] - hist.mean()) / sd)


def analyze(holdings, model, tl, stop_loss, take_profit, progress=None):
    """Devuelve (DataFrame por acción, avisos, búsquedas de noticias por ticker)."""
    h = clean_holdings(holdings)
    if h.empty:
        return None, [], {}
    end = dt.datetime.utcnow()
    start = end - dt.timedelta(days=365 * C.YEARS_HISTORY)
    tickers = list(dict.fromkeys(h["ticker"]))

    tl_all, info, queries, needed = dict(tl), {}, {}, {}
    for tk in tickers:
        row = h[h["ticker"] == tk].iloc[0]
        if tk in C.UNIVERSE:
            q, sector, market, name = C.UNIVERSE[tk]
        else:
            q = row["busqueda"] or tk.split(".")[0]
            sector = row["sector"] if row["sector"] in C.SECTOR_QUERIES else None
            market, name = "Cartera", tk
        info[tk], queries[tk] = (q, sector, market, name), q
        if tk not in tl_all:
            needed[tk] = q
        if sector and f"SEC_{sector}" not in tl_all:
            needed[f"SEC_{sector}"] = C.SECTOR_QUERIES[sector]
    for i, (key, q) in enumerate(needed.items()):
        tl_all[key] = daily_tone_volume(key, q, start, end)
        if progress:
            progress((i + 1) / (len(needed) + 1), f"Noticias de {key}...")
    if progress:
        progress(0.95, "Calculando alertas...")

    p_start = min(h["fecha_compra"].min() - pd.Timedelta(days=7), pd.Timestamp(end) - pd.Timedelta(days=150))
    prices = _prices_since(tickers, p_start)

    rows, notes = [], []
    for tk in tickers:
        if tk not in prices or prices[tk].dropna().empty:
            notes.append(f"No se encontró el precio de {tk}. Revisa que el ticker sea el de Yahoo Finance (por ejemplo SAN.MC para Santander en Madrid).")
            continue
        p = prices[tk].dropna()
        lots = h[h["ticker"] == tk]
        shares = invested = 0.0
        for _, lot in lots.iterrows():
            after = p[p.index >= lot["fecha_compra"]]
            px = after.iloc[0] if len(after) else p.iloc[-1]
            shares += lot["importe"] / px
            invested += lot["importe"]
        value = shares * p.iloc[-1]
        pl = value / invested - 1

        f = build_features(p.to_frame(tk), tl_all, {tk: info[tk]}).sort_index()
        if f.empty:
            notes.append(f"No hay suficiente histórico de precios de {tk} para analizarla.")
            continue
        exp = float(model.predict(f.iloc[[-1]][FEATS])[0])

        sector = info[tk][1]
        d_s, d_c = _series(tl_all, tk, p.index)
        s_s, _ = _series(tl_all, f"SEC_{sector}", p.index) if sector else (pd.Series(0.0, index=p.index), None)
        m_s, _ = _series(tl_all, MACRO_KEY, p.index)
        z_d, z_s, z_m = _z(d_s), _z(s_s), _z(m_s)
        hist_vol = d_c.iloc[-61:-1].median()
        spike = float(d_c.iloc[-1] / hist_vol) if hist_vol and hist_vol > 0 else 1.0

        pts, why = 0.0, []
        model_sell = exp < C.SELL_THRESHOLD
        news_bad = z_d <= Z_ALERT or (d_s.iloc[-1] < 0 and spike >= 2)
        if model_sell:
            pts += 2
            why.append(f"El modelo prevé un retorno de {exp:+.1%} a {C.HORIZON_DAYS} días.")
        if news_bad:
            pts += 1
            why.append("Las noticias de la empresa son de las más negativas de los últimos 60 días"
                       + (" y hay un pico de publicaciones." if spike >= 2 else "."))
        if sector and z_s <= Z_ALERT:
            pts += 1
            why.append(f"Noticias inusualmente negativas en su sector ({sector}).")
        if z_m <= Z_ALERT:
            pts += 0.5
            why.append("Noticias macroeconómicas muy negativas (tipos, inflación, aranceles o geopolítica).")
        if pl <= -stop_loss / 100:
            pts += 3
            why.append(f"Pierdes un {abs(pl):.1%}: has alcanzado tu límite de pérdida del {stop_loss}%.")
        if pl >= take_profit / 100 and (model_sell or news_bad):
            pts += 1
            why.append(f"Ganas un {pl:.1%} (tu objetivo era {take_profit}%) y las señales apuntan a bajada: buen momento para recoger beneficios.")

        rows.append({
            "ticker": tk, "nombre": info[tk][3], "desde": lots["fecha_compra"].min(),
            "invertido": invested, "valor_actual": value, "beneficio": value - invested, "beneficio_pct": pl,
            "retorno_esperado": exp, "nivel": "VENDER" if pts >= 3 else "VIGILAR" if pts >= 1.5 else "MANTENER",
            "motivos": why,
        })
    return pd.DataFrame(rows), notes, queries
