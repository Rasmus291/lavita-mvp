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

st.header("🎯 Produkt-Ähnlichkeit (5 Kategorien)")

pie = df_view["competition_grade"].value_counts().sort_index().reset_index()
pie.columns = ["Kategorie", "Anzahl"]
pie["Label"] = pie["Kategorie"].map(GRADE_LABELS)

col_a, col_b = st.columns(2)

with col_a:
    st.plotly_chart(
        px.pie(pie, names="Label", values="Anzahl", hole=0.4,
               color_discrete_sequence=px.colors.sequential.Tealgrn_r),
        use_container_width=True,
    )

with col_b:
    st.write("### Kategorien (1 = nah an LaVita, 5 = fern)")
    st.info("""
    - **Kat 1:** Flüssiges Multivitaminkonzentrat + Mikronährstoffe
    - **Kat 2:** Multivitamin-Pulver zum Trinken + Mikronährstoffe
    - **Kat 3:** Multivitamin-Kapseln/-Tabletten + Mikronährstoffe
    - **Kat 4:** Allgemeines NEM-Pulver/Drink (kein Multi)
    - **Kat 5:** Sonstige NEM, Vitamine, Lifestyle-Health
    """)
    st.caption("Klassifikation via Buzzword-Analyse + Amazon Browse-Nodes")
