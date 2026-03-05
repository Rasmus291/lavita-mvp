import streamlit as st
import pandas as pd
import plotly.express as px
from shared import get_data, render_sidebar_filters, GRADE_LABELS, STYLE_CSS

st.set_page_config(page_title="Marktanalyse", layout="wide", page_icon="🎯")
st.markdown(STYLE_CSS, unsafe_allow_html=True)

df = get_data()
if df is None or df.empty:
    st.error("Keine Daten gefunden.")
    st.stop()

df_view, date_opt = render_sidebar_filters(df)
df_view = df_view.sort_values('position').drop_duplicates(subset=['asin'], keep='first')

st.header("🎯 Verteilung nach Wettbewerbs-Grad")

pie = df_view["competition_grade"].value_counts().sort_index().reset_index()
pie.columns = ["Grad", "Anzahl"]
pie["Label"] = pie["Grad"].map(GRADE_LABELS)

col_a, col_b = st.columns(2)

with col_a:
    st.plotly_chart(
        px.pie(pie, names="Label", values="Anzahl", hole=0.4),
        use_container_width=True,
    )

with col_b:
    st.write("### Legende")
    st.info("""
    - **Grad 1:** Direkte Konkurrenten (Format: Flüssig/Konzentrat)
    - **Grad 2:** Spezialisierte Immun-Komplexe
    - **Grad 3:** Standard-Multis
    - **Grad 4/5:** Sonstige NE
    """)
