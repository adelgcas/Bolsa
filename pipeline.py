"""Pipeline: precios + tono de noticias -> features -> modelo -> señales COMPRAR / VENDER / MANTENER."""
import datetime as dt

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import TimeSeriesSplit

import config as C
from data import get_prices, daily_tone_volume

MACRO_KEY = "MACRO"
FEATS = ["sent_directo", "n_noticias", "sent_sector", "sent_macro", "ret1", "ret5", "ret20", "vol20"]


def all_queries():
    q = {tk: v[0] for tk, v in C.UNIVERSE.items()}
    q.update({f"SEC_{s}": qq for s, qq in C.SECTOR_QUERIES.items()})
    q[MACRO_KEY] = C.MACRO_QUERY
    return q


def collect_timelines(years=C.YEARS_HISTORY, progress=None):
    end = dt.datetime.utcnow()
    start = end - dt.timedelta(days=365 * years)
    out, queries = {}, all_queries()
    for i, (key, query) in enumerate(queries.items()):
        out[key] = daily_tone_volume(key, query, start, end)
        if progress:
            progress((i + 1) / len(queries), f"Noticias: {key}")
    return out


def _series(tl, key, index):
    """Tono medio (ponderado por volumen) de los últimos 3 días y volumen, alineado a días bursátiles."""
    df = tl.get(key)
    if df is None or df.empty:
        z = pd.Series(0.0, index=index)
        return z, z
    df = df.resample("D").agg({"tone": "mean", "vol": "sum"})
    tone, vol = df["tone"].fillna(0.0), df["vol"].fillna(0.0)
    wsum = (tone * vol).rolling(3, min_periods=1).sum()
    vsum = vol.rolling(3, min_periods=1).sum()
    sent = (wsum / vsum.replace(0, np.nan)).fillna(0.0)
    return sent.reindex(index, method="ffill").fillna(0.0), vsum.reindex(index, method="ffill").fillna(0.0)


def build_features(prices, tl):
    rows, h = [], C.HORIZON_DAYS
    mac_s, _ = _series(tl, MACRO_KEY, prices.index)
    for tk, (_, sector) in C.UNIVERSE.items():
        if tk not in prices:
            continue
        p = prices[tk]
        d_s, d_c = _series(tl, tk, prices.index)
        s_s, _ = _series(tl, f"SEC_{sector}", prices.index)
        rows.append(pd.DataFrame({
            "ticker": tk,
            "sent_directo": d_s, "n_noticias": d_c,
            "sent_sector": s_s, "sent_macro": mac_s,
            "ret1": p.pct_change(1), "ret5": p.pct_change(5), "ret20": p.pct_change(20),
            "vol20": p.pct_change().rolling(20).std(),
            "target": p.shift(-h) / p - 1,
        }))
    return pd.concat(rows).dropna(subset=["ret20", "vol20"])


def _model():
    return HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=200)


def backtest(df):
    """Walk-forward: ¿acierta el signo del retorno a 5 días? ¿Qué rinden las señales extremas?"""
    d = df.dropna(subset=["target"]).sort_index()
    hits, top = [], []
    for tr, te in TimeSeriesSplit(n_splits=5, gap=C.HORIZON_DAYS * len(C.UNIVERSE)).split(d):
        m = _model().fit(d.iloc[tr][FEATS], d.iloc[tr]["target"])
        pred = m.predict(d.iloc[te][FEATS])
        real = d.iloc[te]["target"].values
        hits.append(np.mean(np.sign(pred) == np.sign(real)))
        hi, lo = np.quantile(pred, 0.9), np.quantile(pred, 0.1)
        top.append(real[pred >= hi].mean() - real[pred <= lo].mean())
    return {"acierto_direccion": float(np.mean(hits)), "spread_top_vs_bottom_decil": float(np.mean(top))}


def signals(df):
    d = df.dropna(subset=["target"])
    m = _model().fit(d[FEATS], d["target"])
    last = df.sort_index().groupby("ticker").tail(1).copy()
    last["retorno_esperado"] = m.predict(last[FEATS])
    last["senal"] = np.where(last["retorno_esperado"] > C.BUY_THRESHOLD, "COMPRAR",
                             np.where(last["retorno_esperado"] < C.SELL_THRESHOLD, "VENDER", "MANTENER"))
    return last.sort_values("retorno_esperado", ascending=False)


def run(progress=None):
    prices = get_prices(C.UNIVERSE.keys(), C.YEARS_HISTORY)
    tl = collect_timelines(progress=progress)
    feats = build_features(prices, tl)
    return signals(feats), backtest(feats)


if __name__ == "__main__":
    sig, stats = run()
    print("Backtest:", stats)
    print(sig[["ticker", "retorno_esperado", "senal", "sent_directo", "sent_sector", "sent_macro"]].to_string())
