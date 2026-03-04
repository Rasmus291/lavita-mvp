import streamlit as st
import pandas as pd
import plotly.express as px
import os

# Fix: Globale Variablen vordefinieren
DATA_FILE = "data/master_data.csv"
grade_labels = {1: "🥇 Direkt (Flüssig)", 2: "🥈 Komplex", 3: "🥉 Standard", 4: "4. Sonstige", 5: "5. Sonstige"}

st.set_page_config(page_title="Lavita Intelligence", layout="wide", page_icon="💊")

# --- STYLE CSS ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .rank-high {color: green; font-weight: bold;}
    .rank-low {color: red; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# --- DATEN LADEN ---
@st.cache_data
def load_data(path):
    if not os.path.exists(path):  # <-- KORREKT HIER
        st.error("Datei nicht gefunden!")
        return None
    df = pd.read_csv(path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

df = load_data(DATA_FILE)


if df is None or df.empty:
    st.stop()

# --- SIDEBAR FILTES ---
st.sidebar.header("⚙️ Filter-Einstellungen")

# Filter nach Datum (default: Letzter Scan)
date_options = sorted(df['timestamp'].unique(), reverse=True)
date_opt = st.sidebar.selectbox(
    "Scan-Datum", 
    options=date_options,
    index=0
)

df_slice = df[df['timestamp'] == date_opt]

# Duplikate entfernen: nur das Produkt mit bester (niedrigster) Position pro ASIN behalten
df_slice = df_slice.sort_values('position').drop_duplicates(subset=['asin'], keep='first')

# Filter nach Grade
selected_grades = st.sidebar.multiselect(
    "Wettbewerbs-Grade",
    options=[1, 2, 3, 4, 5],
    default=[1, 2, 3]
)

df_view = df_slice[df_slice['competition_grade'].isin(selected_grades)]

# --- HEADER METRIKEN ---
st.title("💊 Lavita Wettbewerbs-Monitor")
st.caption(f"📅 Stand: {pd.to_datetime(date_opt).strftime('%d.%m.%Y %H:%M')} | 📂 Produkte: {len(df_view)}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Ø Preis", f"€{df_view['price_clean'].mean():.2f}", delta_color="off")
col2.metric("Ø Rating", f"{df_view['rating'].mean():.1f} ★")
col3.metric("Ø Reviews", f"{int(df_view['reviews'].mean())}")
col4.metric("Ø Score (CIS)", f"{df_view['cis_score'].mean():.2f}", delta_color="normal")

# --- TAB STRUKTUR ---
tab1, tab2, tab3 = st.tabs(["🏆 Produkt-Ranking", "📈 Trends", "🎯 Marktanalyse"])

# === TAB 1: PRODUKT RANKING ===
with tab1:
    st.subheader("Aktuelles Wettbewerbs-Ranking")
    
    # Ranking berechnen
    df_ranked = df_view.sort_values(by="cis_score", ascending=False).reset_index(drop=True)
    df_ranked.index = df_ranked.index + 1
    
    # Fix: Spalten korrekt referenzieren
    display_cols = ["title", "brand", "price_clean", "rating", "reviews", "cis_score"]
    
    st.dataframe(
        df_ranked[display_cols].rename(columns={
            "title": "Produkt",
            "brand": "Marke",
            "price_clean": "Preis (€)",
            "rating": "Bewertung",
            "reviews": "Rezensionen",
            "cis_score": "Score"
        }),
        use_container_width=True,
        height=500,
        width=None
    )

# === TAB 2: TRENDS ===
with tab2:
    st.subheader("📈 Marktentwicklung über Zeit")
    
    trend = df.groupby("timestamp").agg({
        "price_clean": "mean",
        "rating": "mean",
        "reviews": "mean",
        "cis_score": "mean"
    }).reset_index()
    
    chart_type = st.radio("Metrik wählen:", ["CIS-Score", "Preis", "Bewertung"], horizontal=True)
    
    if chart_type == "CIS-Score":
        fig = px.line(trend, x="timestamp", y="cis_score", markers=True, title="Wettbewerbs-Druck")
    elif chart_type == "Preis":
        fig = px.line(trend, x="timestamp", y="price_clean", markers=True, title="Ø Preis")
    else:
        fig = px.line(trend, x="timestamp", y="rating", markers=True, title="Ø Bewertung")
        
    st.plotly_chart(fig, use_container_width=True)

# === TAB 3: MARKTANALYSE ===
with tab3:
    st.subheader("Verteilung nach Wettbewerbs-Grad")
    
    pie = df_view['competition_grade'].value_counts().sort_index().reset_index()
    pie.columns = ["Grad", "Anzahl"]
    pie["Label"] = pie["Grad"].map(grade_labels)
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.plotly_chart(px.pie(pie, names="Label", values="Anzahl", hole=0.4), use_container_width=True)
    
    with col_b:
        st.write("### Legende")
        st.info("""
        - **Grad 1:** Direkte Konkurrenten (Format: Flüssig/Konzentrat)
        - **Grad 2:** Spezialisierte Immun-Komplexe
        - **Grad 3:** Standard-Multis
        - **Grad 4/5:** Sonsitge NEM
        """)