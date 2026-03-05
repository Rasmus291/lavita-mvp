import streamlit as st
import pandas as pd
from shared import get_data, render_sidebar_filters, STYLE_CSS

st.set_page_config(page_title="Lavita Intelligence", layout="wide", page_icon="💊")
st.markdown(STYLE_CSS, unsafe_allow_html=True)

df = get_data()

if df is None or df.empty:
    st.error("Keine Daten gefunden. Starte `python main.py` zuerst.")
    st.stop()

df_view, date_opt = render_sidebar_filters(df)
df_view = df_view.sort_values('position').drop_duplicates(subset=['asin'], keep='first')

# --- HEADER ---
st.title("💊 Lavita Wettbewerbs-Monitor")
new_count = len(df_view[df_view["is_new"] == True]) if "is_new" in df_view.columns else 0
new_label = f" | 🆕 Neue Produkte: {new_count}" if new_count > 0 else ""
st.caption(f"📅 Stand: {pd.to_datetime(date_opt).strftime('%d.%m.%Y %H:%M')} | 📂 Produkte: {len(df_view)}{new_label}")

# --- KPI-METRIKEN ---
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
col1.metric("Ø Preis", f"€{df_view['price_clean'].mean():.2f}", delta_color="off")
col2.metric("Ø Rating", f"{df_view['rating'].mean():.1f} ★")
col3.metric("Ø Reviews", f"{int(df_view['reviews'].mean())}")
col4.metric("Ø Score (CIS)", f"{df_view['cis_score'].mean():.2f}", delta_color="normal")
col5.metric("∑ Gesch. Bestellungen", f"{int(df_view['est_orders'].sum()):,}".replace(',', '.'))
col6.metric("Ø Amazon-Ranking", f"#{df_view['position'].mean():.1f}")
if df_view["bsr"].notna().any():
    col7.metric("Ø Bestseller-Rang", f"#{int(df_view['bsr'].mean())}")
else:
    col7.metric("Ø Bestseller-Rang", "—")

st.markdown("---")
st.info("👈 Nutze die **Seitenleiste** um zwischen den Analyse-Seiten zu wechseln: Produkt-Ranking, Trends, Marktanalyse, BSR-Kategorien.")