"""Panel de recomendaciones por mercado y cartera personal. Ejecutar con: streamlit run app.py"""
import pandas as pd
import streamlit as st

import config as C
from data import recent_headlines
from pipeline import run, all_queries
from portfolio import analyze
from sentiment import score

st.set_page_config(page_title="Recomendaciones por mercado", layout="wide")
st.title("Recomendaciones de compra y venta")
st.caption("Señales a %d días basadas en noticias y precios. Herramienta experimental; "
           "no es asesoramiento financiero y el pasado no garantiza resultados." % C.HORIZON_DAYS)


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def compute(_progress=None):
    return run(progress=_progress)


if st.sidebar.button("Forzar recálculo"):
    st.cache_data.clear()
st.sidebar.write("Los datos se recalculan cada 6 horas. La primera carga tarda unos minutos.")
st.sidebar.header("Alertas de tu cartera")
stop_loss = st.sidebar.slider("Límite de pérdida (stop-loss)", 3, 30, 10, format="%d%%")
take_profit = st.sidebar.slider("Objetivo de beneficio", 5, 100, 20, format="%d%%")

bar = st.progress(0.0, text="Cargando precios y noticias...")
out = compute(lambda f, t: bar.progress(min(f, 1.0), text=t))
bar.empty()
sig, stats, model, tl = out["sig"], out["stats"], out["model"], out["tl"]

# ---- aviso global si hay alertas de venta en la cartera
cres = st.session_state.get("cartera_res")
if cres and cres["df"] is not None:
    n_sell = int((cres["df"]["nivel"] == "VENDER").sum())
    n_watch = int((cres["df"]["nivel"] == "VIGILAR").sum())
    if n_sell:
        st.error(f"Tienes {n_sell} alerta(s) de venta en tu cartera. Míralas en la pestaña «Mi cartera».")
    elif n_watch:
        st.warning(f"Tienes {n_watch} acción(es) a vigilar en tu cartera (pestaña «Mi cartera»).")

# ---- fiabilidad del modelo
acc = stats["acierto_direccion"]
k1, k2 = st.columns(2)
k1.metric("Acierto de dirección (validación walk-forward)", f"{acc:.1%}")
k2.metric("Diferencia entre señales más altas y más bajas", f"{stats['spread_top_vs_bottom_decil']:.2%}")
if acc < 0.52:
    st.warning("El acierto está cerca del azar (50 %). Las señales de ahora mismo no tienen respaldo estadístico; úsalas solo como referencia.")

# ---- tarjetas por mercado
cols = st.columns(len(C.MARKETS))
for col, mk in zip(cols, C.MARKETS):
    s = sig[sig["mercado"] == mk]
    if s.empty:
        continue
    col.metric(mk, f"{(s['senal'] == 'COMPRAR').sum()} comprar · {(s['senal'] == 'VENDER').sum()} vender",
               delta=f"{s['retorno_esperado'].mean():+.2%} retorno medio esperado")

NAMES = {"nombre": "Empresa", "ticker": "Ticker", "senal": "Señal", "retorno_esperado": "Retorno esperado",
         "sent_directo": "Noticias empresa", "sent_sector": "Noticias sector", "ret5": "Últimos 5 días"}
FMT = {"Retorno esperado": "{:+.2%}", "Noticias empresa": "{:+.2f}", "Noticias sector": "{:+.2f}", "Últimos 5 días": "{:+.2%}"}


def colour(v):
    return {"COMPRAR": "color: #1a7f37; font-weight: 600", "VENDER": "color: #c0392b; font-weight: 600",
            "VIGILAR": "color: #b9770e; font-weight: 600"}.get(v, "")


def tabla(df):
    if df.empty:
        st.write("Ninguna en este momento.")
        return
    v = df[list(NAMES)].rename(columns=NAMES)
    st.dataframe(v.style.format(FMT).map(colour, subset=["Señal"]), use_container_width=True, hide_index=True)


def show_headlines(query, key):
    if st.button("Cargar titulares recientes", key=key):
        h = recent_headlines(query)
        if h.empty:
            st.write("Sin titulares (GDELT no respondió o no hay resultados).")
        else:
            h["sent"] = score(h["title"].tolist())
            for _, r in h.head(10).iterrows():
                st.write(f"{r['sent']:+.2f} · {r['date']:%d/%m} · [{r['title']}]({r['url']})")


def headlines_block(df, key_prefix):
    tk = st.selectbox("Ver titulares de", list(df["ticker"]), key=f"sel_{key_prefix}")
    sector = C.UNIVERSE[tk][1]
    q = all_queries()
    for key, label in [(tk, "Empresa"), (f"SEC_{sector}", f"Sector ({sector})"), ("MACRO", "Macro")]:
        with st.expander(label):
            show_headlines(q[key], f"btn_{key_prefix}_{key}")


def cartera_tab():
    st.subheader("Mi cartera")
    st.write("Añade cada compra con su ticker, fecha e importe. La app calcula tu beneficio actual y te avisa "
             "cuando las noticias o el modelo recomiendan vender. Tu cartera no se guarda en ningún servidor: "
             "descárgala en CSV para conservarla y súbela la próxima vez.")

    if "cartera_base" not in st.session_state:
        st.session_state["cartera_base"] = pd.DataFrame({
            "ticker": pd.Series(dtype="str"), "fecha_compra": pd.Series(dtype="datetime64[ns]"),
            "importe": pd.Series(dtype="float"), "busqueda": pd.Series(dtype="str"), "sector": pd.Series(dtype="str")})

    up = st.file_uploader("Cargar cartera guardada (CSV)", type="csv")
    if up is not None and st.session_state.get("last_upload") != getattr(up, "file_id", up.name):
        try:
            d = pd.read_csv(up)
            for c in ("ticker", "fecha_compra", "importe", "busqueda", "sector"):
                if c not in d:
                    d[c] = None
            d["fecha_compra"] = pd.to_datetime(d["fecha_compra"], errors="coerce")
            d["importe"] = pd.to_numeric(d["importe"], errors="coerce")
            for c in ("ticker", "busqueda", "sector"):
                d[c] = d[c].astype("string").fillna("").astype(str)
            st.session_state["cartera_base"] = d[["ticker", "fecha_compra", "importe", "busqueda", "sector"]]
            st.session_state["last_upload"] = getattr(up, "file_id", up.name)
            st.session_state.pop("editor_cartera", None)
            st.rerun()
        except Exception:
            st.error("No he podido leer ese archivo. Debe ser un CSV descargado desde esta misma pantalla.")

    edited = st.data_editor(
        st.session_state["cartera_base"], num_rows="dynamic", key="editor_cartera",
        use_container_width=True, hide_index=True,
        column_config={
            "ticker": st.column_config.TextColumn("Ticker", help="El de Yahoo Finance. Ej.: SAN.MC, AAPL, ASML.AS"),
            "fecha_compra": st.column_config.DateColumn("Fecha de compra"),
            "importe": st.column_config.NumberColumn("Importe invertido", min_value=0.0, format="%.2f",
                                                     help="En la moneda en la que cotiza la acción"),
            "busqueda": st.column_config.TextColumn("Búsqueda de noticias (opcional)",
                                                    help="Solo para acciones que no están en el panel. En inglés, ej.: Pfizer"),
            "sector": st.column_config.SelectboxColumn("Sector (opcional)", options=list(C.SECTOR_QUERIES),
                                                       help="Solo para acciones que no están en el panel"),
        })

    c1, c2 = st.columns([1, 1])
    go = c1.button("Analizar mi cartera", type="primary")
    c2.download_button("Descargar mi cartera (CSV)", edited.to_csv(index=False).encode("utf-8"),
                       file_name="mi_cartera.csv", mime="text/csv")

    if go:
        bar2 = st.progress(0.0, text="Analizando tu cartera...")
        df, notes, queries = analyze(edited, model, tl, stop_loss, take_profit,
                                     progress=lambda f, t: bar2.progress(min(f, 1.0), text=t))
        bar2.empty()
        if df is None:
            st.info("Añade al menos una compra con ticker, fecha e importe.")
        else:
            st.session_state["cartera_res"] = {"df": df, "notes": notes, "queries": queries}
            st.rerun()

    r = st.session_state.get("cartera_res")
    if not r:
        return
    for n in r["notes"]:
        st.warning(n)
    df = r["df"]
    if df is None or df.empty:
        return

    inv, val = df["invertido"].sum(), df["valor_actual"].sum()
    m1, m2, m3 = st.columns(3)
    m1.metric("Invertido", f"{inv:,.2f}")
    m2.metric("Valor actual", f"{val:,.2f}")
    m3.metric("Beneficio", f"{val - inv:+,.2f}", delta=f"{val / inv - 1:+.1%}")
    st.caption("Los totales suman importes en la moneda de cada acción, sin conversión de divisas.")

    order = {"VENDER": 0, "VIGILAR": 1, "MANTENER": 2}
    alerts = df[df["nivel"] != "MANTENER"].sort_values("nivel", key=lambda s: s.map(order))
    if alerts.empty:
        st.success("Sin alertas: ni las noticias ni el modelo recomiendan vender ninguna de tus acciones ahora mismo.")
    for _, row in alerts.iterrows():
        box = st.error if row["nivel"] == "VENDER" else st.warning
        box(f"**{row['nivel']}: {row['nombre']}** · beneficio {row['beneficio_pct']:+.1%}\n\n"
            + "\n".join(f"- {m}" for m in row["motivos"]))

    v = df.rename(columns={"nombre": "Empresa", "ticker": "Ticker", "desde": "Desde", "invertido": "Invertido",
                           "valor_actual": "Valor actual", "beneficio": "Beneficio", "beneficio_pct": "Beneficio %",
                           "retorno_esperado": "Retorno esperado", "nivel": "Recomendación"})
    v = v[["Empresa", "Ticker", "Desde", "Invertido", "Valor actual", "Beneficio", "Beneficio %",
           "Retorno esperado", "Recomendación"]]
    st.dataframe(v.style.format({"Desde": "{:%d/%m/%Y}", "Invertido": "{:,.2f}", "Valor actual": "{:,.2f}",
                                 "Beneficio": "{:+,.2f}", "Beneficio %": "{:+.1%}", "Retorno esperado": "{:+.2%}"})
                 .map(colour, subset=["Recomendación"]), use_container_width=True, hide_index=True)

    tk = st.selectbox("Ver titulares de", list(df["ticker"]), key="sel_cartera")
    show_headlines(r["queries"].get(tk, tk), "btn_cartera")


tabs = st.tabs(["Resumen", "Mi cartera"] + C.MARKETS)

with tabs[0]:
    a, b = st.columns(2)
    with a:
        st.subheader("Mejores compras")
        tabla(sig[sig["senal"] == "COMPRAR"].head(8).assign(nombre=lambda d: d["nombre"] + " (" + d["mercado"] + ")"))
    with b:
        st.subheader("Mejores ventas")
        tabla(sig[sig["senal"] == "VENDER"].sort_values("retorno_esperado").head(8)
              .assign(nombre=lambda d: d["nombre"] + " (" + d["mercado"] + ")"))
    st.subheader("Retorno esperado por acción")
    st.bar_chart(sig.set_index("nombre")["retorno_esperado"], y_label="Retorno esperado a 5 días")

with tabs[1]:
    cartera_tab()

for tab, mk in zip(tabs[2:], C.MARKETS):
    with tab:
        s = sig[sig["mercado"] == mk]
        if s.empty:
            st.write("No hay datos para este mercado.")
            continue
        a, b = st.columns(2)
        with a:
            st.subheader("Comprar")
            tabla(s[s["senal"] == "COMPRAR"])
        with b:
            st.subheader("Vender")
            tabla(s[s["senal"] == "VENDER"].sort_values("retorno_esperado"))
        st.subheader("Todas las acciones del mercado")
        tabla(s)
        st.bar_chart(s.set_index("nombre")["retorno_esperado"], y_label="Retorno esperado a 5 días")
        headlines_block(s, mk)
