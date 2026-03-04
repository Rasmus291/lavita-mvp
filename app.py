import streamlit as st
import pandas as pd
import plotly.express as px
import os
import ast

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
@st.cache_data(ttl=60)
def load_data(path):
    if not os.path.exists(path):  # <-- KORREKT HIER
        st.error("Datei nicht gefunden!")
        return None
    df = pd.read_csv(path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

df = load_data(DATA_FILE)

# Est. Bestellanzahl & BSR berechnen/füllen (auch für alte Daten ohne diese Spalten)
if df is not None and not df.empty:
    df["reviews"] = pd.to_numeric(df["reviews"], errors="coerce").fillna(0)
    if "est_orders" not in df.columns:
        df["est_orders"] = (df["reviews"] * 20).astype(int)
    else:
        df["est_orders"] = df["est_orders"].fillna(df["reviews"] * 20).astype(int)
    if "bsr" not in df.columns:
        df["bsr"] = None
    else:
        df["bsr"] = pd.to_numeric(df["bsr"], errors="coerce")
    if "bsr_categories" not in df.columns:
        df["bsr_categories"] = None
    # Brand bereinigen (HTML-Entities entfernen)
    if "brand" in df.columns:
        df["brand"] = df["brand"].astype(str).str.replace(r'&lrm;|&rlm;', '', regex=True).replace('nan', None)


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

# Filter nach BSR (Bestseller-Rang)
if "bsr" in df_view.columns and df_view["bsr"].notna().any():
    bsr_min = int(df_view["bsr"].min())
    bsr_max = int(df_view["bsr"].max())
    bsr_range = st.sidebar.slider(
        "🏆 Bestseller-Rang (BSR)",
        min_value=bsr_min,
        max_value=bsr_max,
        value=(bsr_min, bsr_max),
        help="Niedrigerer BSR = höhere Verkäufe"
    )
    df_view = df_view[
        (df_view["bsr"] >= bsr_range[0]) & (df_view["bsr"] <= bsr_range[1])
    ]
else:
    st.sidebar.info("🏆 BSR-Daten noch nicht verfügbar. Starte `python main.py` erneut, um BSR abzurufen.")

# --- HEADER METRIKEN ---
st.title("💊 Lavita Wettbewerbs-Monitor")
st.caption(f"📅 Stand: {pd.to_datetime(date_opt).strftime('%d.%m.%Y %H:%M')} | 📂 Produkte: {len(df_view)}")

col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
col1.metric("Ø Preis", f"€{df_view['price_clean'].mean():.2f}", delta_color="off")
col2.metric("Ø Rating", f"{df_view['rating'].mean():.1f} ★")
col3.metric("Ø Reviews", f"{int(df_view['reviews'].mean())}")
col4.metric("Ø Score (CIS)", f"{df_view['cis_score'].mean():.2f}", delta_color="normal")
col5.metric("∑ Gesch. Bestellungen", f"{int(df_view['est_orders'].sum()):,}".replace(',','.'))
col6.metric("Ø Amazon-Ranking", f"#{df_view['position'].mean():.1f}")
if df_view["bsr"].notna().any():
    col7.metric("Ø Bestseller-Rang", f"#{int(df_view['bsr'].mean())}")
else:
    col7.metric("Ø Bestseller-Rang", "—")

# --- TAB STRUKTUR ---
tab1, tab2, tab3, tab4 = st.tabs(["🏆 Produkt-Ranking", "📈 Trends", "🎯 Marktanalyse", "🏅 BSR-Kategorien"])

# === TAB 1: PRODUKT RANKING ===
with tab1:
    st.subheader("Aktuelles Wettbewerbs-Ranking")
    
    # Sortierung nach Marke (Firma), dann Position
    df_ranked = df_view.sort_values(by=["brand", "position"], ascending=[True, True]).reset_index(drop=True)
    df_ranked.index = df_ranked.index + 1
    
    # Fix: Spalten korrekt referenzieren
    display_cols = ["position", "title", "brand", "price_clean", "rating", "reviews", "est_orders", "bsr", "cis_score"]
    
    # BSR-Kategorie-Spalte hinzufügen (Hauptkategorie extrahieren)
    if "bsr_categories" in df_ranked.columns and df_ranked["bsr_categories"].notna().any():
        def extract_main_category(cat_str):
            try:
                d = ast.literal_eval(str(cat_str))
                if isinstance(d, dict) and d:
                    return list(d.keys())[0]
            except (ValueError, SyntaxError):
                pass
            return None
        
        def extract_sub_category(cat_str):
            try:
                d = ast.literal_eval(str(cat_str))
                if isinstance(d, dict) and len(d) > 1:
                    keys = list(d.keys())
                    vals = list(d.values())
                    return f"Nr. {vals[1]} in {keys[1]}"
            except (ValueError, SyntaxError):
                pass
            return None
        
        df_ranked["bsr_hauptkategorie"] = df_ranked["bsr_categories"].apply(extract_main_category)
        df_ranked["bsr_subkategorie"] = df_ranked["bsr_categories"].apply(extract_sub_category)
        display_cols = ["brand", "title", "price_clean", "rating", "reviews", "est_orders", "position", "bsr", "bsr_hauptkategorie", "bsr_subkategorie", "cis_score"]
    else:
        display_cols = ["brand", "title", "price_clean", "rating", "reviews", "est_orders", "position", "bsr", "cis_score"]
    
    st.dataframe(
        df_ranked[display_cols].rename(columns={
            "brand": "Firma",
            "title": "Produkt",
            "price_clean": "Preis (€)",
            "rating": "Bewertung",
            "reviews": "Rezensionen",
            "est_orders": "Gesch. Bestellungen",
            "position": "Amazon-Rang",
            "bsr": "BSR (Haupt)",
            "bsr_hauptkategorie": "BSR-Kategorie",
            "bsr_subkategorie": "BSR-Subkategorie",
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
        - **Grad 4/5:** Sonsitge NE
        """)

# === TAB 4: BSR-KATEGORIEN ===
with tab4:
    st.subheader("🏅 BSR-Rankings nach Amazon-Kategorie")
    
    if "bsr_categories" in df_view.columns and df_view["bsr_categories"].notna().any():
        # Alle Kategorien aus den Daten extrahieren
        all_categories = []
        for _, row in df_view.iterrows():
            try:
                d = ast.literal_eval(str(row["bsr_categories"]))
                if isinstance(d, dict):
                    for cat, rank in d.items():
                        all_categories.append({
                            "Produkt": row.get("title", "")[:80],
                            "Marke": row.get("brand", ""),
                            "Kategorie": cat,
                            "BSR-Rang": rank,
                            "ASIN": row.get("asin", "")
                        })
            except (ValueError, SyntaxError):
                continue
        
        if all_categories:
            df_cats = pd.DataFrame(all_categories)
            
            # Übersicht: Welche Kategorien gibt es?
            unique_cats = sorted(df_cats["Kategorie"].unique())
            st.info(f"**{len(unique_cats)} Amazon-Kategorien** gefunden: {', '.join(unique_cats)}")
            
            # Filter nach Kategorie
            selected_cat = st.selectbox("📂 Kategorie wählen", options=["Alle"] + unique_cats)
            
            if selected_cat != "Alle":
                df_cats = df_cats[df_cats["Kategorie"] == selected_cat]
            
            # Sortiert nach BSR-Rang (aufsteigend = bester Rang zuerst)
            df_cats = df_cats.sort_values("BSR-Rang", ascending=True).reset_index(drop=True)
            df_cats.index = df_cats.index + 1
            
            st.dataframe(df_cats, use_container_width=True, height=500)
            
            # Visualisierung: BSR pro Kategorie
            st.subheader("📊 BSR-Verteilung pro Kategorie")
            cat_summary = df_cats.groupby("Kategorie").agg(
                Anzahl_Produkte=("BSR-Rang", "count"),
                Bester_BSR=("BSR-Rang", "min"),
                Durchschnitt_BSR=("BSR-Rang", "mean"),
                Schlechtester_BSR=("BSR-Rang", "max")
            ).reset_index().sort_values("Bester_BSR")
            
            st.dataframe(cat_summary, use_container_width=True)
            
            fig_bsr = px.bar(
                cat_summary, 
                x="Kategorie", 
                y="Durchschnitt_BSR",
                title="Ø BSR-Rang pro Kategorie (niedriger = besser)",
                color="Anzahl_Produkte",
                text="Bester_BSR"
            )
            fig_bsr.update_layout(yaxis_title="BSR-Rang", xaxis_tickangle=-45)
            st.plotly_chart(fig_bsr, use_container_width=True)
    else:
        st.info("🏅 BSR-Kategorie-Daten noch nicht verfügbar. Starte `python main.py` erneut.")