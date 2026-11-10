"""Precios (yfinance) y noticias (GDELT, gratuito).

Histórico: series diarias de tono y volumen de noticias (modos timeline de GDELT, desde 2017),
una sola petición por tema. Actualidad: titulares de los últimos días, bajo demanda.
"""
import os
import time
import datetime as dt

import pandas as pd
import requests
import yfinance as yf

from config import CACHE_DIR

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
PAUSE = 5.5  # GDELT pide ~1 petición cada 5 s
os.makedirs(CACHE_DIR, exist_ok=True)


def get_prices(tickers, years):
    df = yf.download(list(tickers), period=f"{years}y", auto_adjust=True, progress=False)["Close"]
    df = df.dropna(how="all").ffill()
    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_localize(None)
    return df


def _get_json(params):
    for _ in range(4):
        try:
            r = requests.get(GDELT_URL, params=params, timeout=45)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        time.sleep(PAUSE + 1)
    return None


def _timeline(query, mode, start, end):
    data = _get_json({
        "query": f"({query}) sourcelang:english",
        "mode": mode,
        "format": "json",
        "startdatetime": start.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end.strftime("%Y%m%d%H%M%S"),
    })
    try:
        pts = data["timeline"][0]["data"]
        s = pd.Series({pd.to_datetime(p["date"], format="%Y%m%dT%H%M%SZ"): p["value"] for p in pts})
        return s.astype(float)
    except Exception:
        return pd.Series(dtype=float)


def daily_tone_volume(key, query, start, end):
    """DataFrame diario con 'tone' (tono medio GDELT) y 'vol' (nº de artículos). Cacheado por día."""
    path = os.path.join(CACHE_DIR, f"{key}_{dt.date.today():%Y%m%d}.csv")
    if os.path.exists(path):
        return pd.read_csv(path, index_col=0, parse_dates=True)
    tone = _timeline(query, "timelinetone", start, end)
    time.sleep(PAUSE)
    vol = _timeline(query, "timelinevolraw", start, end)
    time.sleep(PAUSE)
    df = pd.DataFrame({
        "tone": tone.resample("D").mean() if len(tone) else pd.Series(dtype=float),
        "vol": vol.resample("D").sum() if len(vol) else pd.Series(dtype=float),
    })
    df.to_csv(path)
    return df


def recent_headlines(query, days=7, maxrecords=40):
    """Titulares de los últimos días para un tema (para mostrar qué mueve la señal)."""
    end = dt.datetime.utcnow()
    start = end - dt.timedelta(days=days)
    data = _get_json({
        "query": f"({query}) sourcelang:english",
        "mode": "artlist",
        "format": "json",
        "maxrecords": maxrecords,
        "sort": "datedesc",
        "startdatetime": start.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end.strftime("%Y%m%d%H%M%S"),
    })
    rows = []
    for a in (data or {}).get("articles", []):
        try:
            rows.append({"date": pd.to_datetime(a["seendate"], format="%Y%m%dT%H%M%SZ"),
                         "title": a["title"], "url": a.get("url", "")})
        except Exception:
            continue
    return pd.DataFrame(rows, columns=["date", "title", "url"])
