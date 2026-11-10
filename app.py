"""Interfaz Streamlit: streamlit run app.py"""
import streamlit as st

import config as C
from data import recent_headlines
from pipeline import run, all_queries
from sentiment import score

st.set_page_config(page_title="Señales bursátiles por noticias", layout="wide")
st.title("Señales de compra/venta basadas en noticias")
st.caption("Herramienta experimental de apoyo a la decisión. No es asesoramiento financiero; el pasado no garantiza resultados.")


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def compute(_progress=None):
    return run(progress=_progress)


if st.sidebar.button("Forzar recálculo"):
    st.cache_data.clear()

bar = st.progress(0.0, text="Cargando precios y noticias (la primera vez tarda unos minutos)...")
sig, stats = compute(lambda f, t: bar.progress(min(f, 1.0), text=t))
bar.empty()

c1, c2 = st.columns(2)
c1.metric("Acierto de dirección (walk-forward)", f"{stats['acierto_direccion']:.1%}")
c2.metric("Diferencia decil alto vs bajo (5 días)", f"{stats['spread_top_vs_bottom_decil']:.2%}")
st.caption("Un acierto cercano al 50 % significa que el modelo no aporta ventaja sobre el azar.")

st.subheader(f"Ranking a {C.HORIZON_DAYS} días")
view = sig[["ticker", "senal", "retorno_esperado", "sent_directo", "sent_sector", "sent_macro", "n_noticias"]]
st.dataframe(view.style.format({"retorno_esperado": "{:.2%}", "sent_directo": "{:.2f}",
                                "sent_sector": "{:.2f}", "sent_macro": "{:.2f}", "n_noticias": "{:.0f}"}),
             use_container_width=True)

st.subheader("Titulares de los últimos días")
tk = st.selectbox("Acción", list(sig["ticker"]))
sector = C.UNIVERSE[tk][1]
q = all_queries()
for key, label in [(tk, "Directas"), (f"SEC_{sector}", f"Sector ({sector})"), ("MACRO", "Macro")]:
    with st.expander(label, expanded=(key == tk)):
        if st.button("Cargar titulares", key=f"btn_{key}"):
            h = recent_headlines(q[key])
            if h.empty:
                st.write("Sin titulares (GDELT no respondió o no hay resultados).")
            else:
                h["sent"] = score(h["title"].tolist())
                for _, r in h.head(10).iterrows():
                    st.write(f"{r['sent']:+.2f} · {r['date']:%d/%m} · [{r['title']}]({r['url']})")
