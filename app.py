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


# --- TAB STRUKTUR ---
tab1, tab2, tab3, tab4 = st.tabs(["🏆 Produkt-Ranking", "📈 Trends", "🎯 Marktanalyse", "🏅 BSR-Kategorien"])

# === TAB 1: PRODUKT RANKING ===
with tab1:
    st.subheader("Aktuelles Wettbewerbs-Ranking")
    
    # Sortierung nach Marke (Firma), dann Position
    df_ranked = df_view.sort_values(by=["brand", "position"], ascending=[True, True]).reset_index(drop=True)
    df_ranked.index = df_ranked.index + 1
    
    # --- Produkt-Trends berechnen (Delta zum vorherigen Scan) ---
    timestamps_sorted = sorted(df["timestamp"].unique())
    if len(timestamps_sorted) >= 2:
        prev_ts = timestamps_sorted[-2]
        df_prev = df[df["timestamp"] == prev_ts].copy()
        df_prev = df_prev.sort_values("position").drop_duplicates(subset=["asin"], keep="first")
        
        prev_lookup = df_prev.set_index("asin")[["position", "bsr", "reviews"]].rename(
            columns={"position": "prev_position", "bsr": "prev_bsr", "reviews": "prev_reviews"}
        )
        df_ranked = df_ranked.join(prev_lookup, on="asin")
        
        df_ranked["Rang Δ"] = df_ranked["position"] - df_ranked["prev_position"]
        df_ranked["BSR Δ"] = df_ranked["bsr"] - df_ranked["prev_bsr"]
        df_ranked["Reviews Δ"] = df_ranked["reviews"] - df_ranked["prev_reviews"]
        
        has_trends = True
    else:
        has_trends = False
    
    # Fix: Spalten korrekt referenzieren
    display_cols = ["position", "title", "brand", "price_clean", "rating", "reviews", "est_orders", "bsr", "cis_score"]
    rename_map = {
        "position": "Amazon-Rang",
        "title": "Produkt",
        "brand": "Marke",
        "price_clean": "Preis (€)",
        "rating": "Bewertung",
        "reviews": "Rezensionen",
        "est_orders": "Gesch. Bestellungen",
        "bsr": "BSR (Haupt)",
        "cis_score": "Score"
    }
    
    # Trend-Deltas hinzufügen wenn verfügbar
    if has_trends:
        display_cols = ["position", "Rang Δ", "title", "brand", "price_clean", "rating", "reviews", "Reviews Δ", "est_orders", "bsr", "BSR Δ", "cis_score"]
        rename_map["Rang Δ"] = "Rang Δ"
        rename_map["BSR Δ"] = "BSR Δ"
        rename_map["Reviews Δ"] = "Reviews Δ"
    
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
        display_cols = ["position", "title", "brand", "price_clean", "rating", "reviews", "est_orders", "bsr", "bsr_hauptkategorie", "bsr_subkategorie", "cis_score"]
    
    st.dataframe(
        df_ranked[display_cols].rename(columns={
            "position": "Amazon-Rang",
            "title": "Produkt",
            "brand": "Marke",
            "price_clean": "Preis (€)",
            "rating": "Bewertung",
            "reviews": "Rezensionen",
            "est_orders": "Gesch. Bestellungen",
            "bsr": "BSR (Haupt)",
            "bsr_hauptkategorie": "BSR-Kategorie",
            "bsr_subkategorie": "BSR-Subkategorie",
            "cis_score": "Score"
        }),
        use_container_width=True,
        height=500,
        width=None
    )
    
    # --- Einzelprodukt-Trend-Chart ---
    st.markdown("---")
    st.subheader("📈 Produkt-Trend (Einzelprodukt)")
    
    product_options = df_ranked[["asin", "title"]].drop_duplicates()
    product_labels = {row["asin"]: row["title"][:70] for _, row in product_options.iterrows()}
    
    selected_asin = st.selectbox(
        "Produkt wählen",
        options=list(product_labels.keys()),
        format_func=lambda x: product_labels.get(x, x)
    )
    
    if selected_asin:
        df_product = df[df["asin"] == selected_asin].copy()
        df_product["timestamp"] = pd.to_datetime(df_product["timestamp"])
        df_product = df_product.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="first")
        
        if len(df_product) >= 2:
            col_t1, col_t2, col_t3 = st.columns(3)
            
            with col_t1:
                fig_p_rank = px.line(
                    df_product, x="timestamp", y="position", markers=True,
                    title="Amazon-Rang", labels={"position": "Rang", "timestamp": ""}
                )
                fig_p_rank.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_p_rank, use_container_width=True)
            
            with col_t2:
                if "bsr" in df_product.columns and df_product["bsr"].notna().any():
                    fig_p_bsr = px.line(
                        df_product, x="timestamp", y="bsr", markers=True,
                        title="Bestseller-Rang (BSR)", labels={"bsr": "BSR", "timestamp": ""}
                    )
                    fig_p_bsr.update_yaxes(autorange="reversed")
                    st.plotly_chart(fig_p_bsr, use_container_width=True)
                else:
                    st.info("BSR noch nicht verfügbar")
            
            with col_t3:
                fig_p_rev = px.line(
                    df_product, x="timestamp", y="reviews", markers=True,
                    title="Bewertungsanzahl", labels={"reviews": "Reviews", "timestamp": ""}
                )
                st.plotly_chart(fig_p_rev, use_container_width=True)
        else:
            st.info("Mindestens 2 Scans für dieses Produkt nötig.")

# === TAB 2: TRENDS ===
with tab2:
    st.subheader("📈 Trendanalyse")
    
    # --- Keyword-Auswahl ---
    all_keywords = sorted(df["keyword"].dropna().unique())
    selected_keywords = st.multiselect(
        "🔑 Keywords auswählen",
        options=all_keywords,
        default=all_keywords,
        help="Wähle Keywords für die Trendanalyse"
    )
    
    df_trend = df[df["keyword"].isin(selected_keywords)].copy()
    df_trend["timestamp"] = pd.to_datetime(df_trend["timestamp"])
    
    if len(df_trend["timestamp"].unique()) < 2:
        st.warning("⚠️ Mindestens 2 Scan-Zeitpunkte nötig für Trendanalyse. Starte `python main.py` mehrmals zu verschiedenen Zeiten.")
    
    # === 2a: Amazon-Rang pro Keyword über Zeit ===
    st.markdown("### 🏆 Amazon-Rang pro Keyword")
    st.caption("Durchschnittliche Suchposition der Produkte pro Keyword (niedriger = besser)")
    
    rank_trend = df_trend.groupby(["timestamp", "keyword"]).agg(
        avg_position=("position", "mean")
    ).reset_index()
    
    fig_rank = px.line(
        rank_trend, x="timestamp", y="avg_position", color="keyword",
        markers=True, title="Ø Amazon-Suchrang pro Keyword",
        labels={"avg_position": "Ø Position", "timestamp": "Zeitpunkt", "keyword": "Keyword"}
    )
    fig_rank.update_yaxes(autorange="reversed")  # Rang 1 oben
    st.plotly_chart(fig_rank, use_container_width=True)
    
    # === 2b: BSR-Veränderung pro Keyword über Zeit ===
    st.markdown("### 📦 Bestseller-Rang (BSR) pro Keyword")
    st.caption("Durchschnittlicher BSR der Produkte pro Keyword (niedriger = mehr Verkäufe)")
    
    if "bsr" in df_trend.columns and df_trend["bsr"].notna().any():
        bsr_trend = df_trend[df_trend["bsr"].notna()].groupby(["timestamp", "keyword"]).agg(
            avg_bsr=("bsr", "mean"),
            min_bsr=("bsr", "min")
        ).reset_index()
        
        bsr_metric = st.radio("BSR-Metrik:", ["Ø BSR", "Bester BSR"], horizontal=True, key="bsr_metric")
        y_col = "avg_bsr" if bsr_metric == "Ø BSR" else "min_bsr"
        
        fig_bsr = px.line(
            bsr_trend, x="timestamp", y=y_col, color="keyword",
            markers=True, title=f"{bsr_metric} pro Keyword über Zeit",
            labels={y_col: bsr_metric, "timestamp": "Zeitpunkt", "keyword": "Keyword"}
        )
        fig_bsr.update_yaxes(autorange="reversed")  # BSR 1 oben
        st.plotly_chart(fig_bsr, use_container_width=True)
    else:
        st.info("BSR-Daten noch nicht für Trendanalyse verfügbar.")
    
    # === 2c: Reviews-Veränderung pro Keyword über Zeit ===
    st.markdown("### ⭐ Bewertungsanzahl pro Keyword")
    st.caption("Durchschnittliche Rezensionen pro Keyword – zeigt Marktdynamik")
    
    reviews_trend = df_trend.groupby(["timestamp", "keyword"]).agg(
        avg_reviews=("reviews", "mean"),
        total_reviews=("reviews", "sum")
    ).reset_index()
    
    review_metric = st.radio("Reviews-Metrik:", ["Ø Reviews", "∑ Reviews"], horizontal=True, key="review_metric")
    y_col_r = "avg_reviews" if review_metric == "Ø Reviews" else "total_reviews"
    
    fig_reviews = px.line(
        reviews_trend, x="timestamp", y=y_col_r, color="keyword",
        markers=True, title=f"{review_metric} pro Keyword über Zeit",
        labels={y_col_r: review_metric, "timestamp": "Zeitpunkt", "keyword": "Keyword"}
    )
    st.plotly_chart(fig_reviews, use_container_width=True)
    
    # === 2d: Veränderungstabelle (Delta zum vorherigen Scan) ===
    st.markdown("### 📊 Veränderung zum vorherigen Scan")
    
    timestamps_sorted = sorted(df_trend["timestamp"].unique())
    if len(timestamps_sorted) >= 2:
        latest_ts = timestamps_sorted[-1]
        prev_ts = timestamps_sorted[-2]
        
        df_latest = df_trend[df_trend["timestamp"] == latest_ts].groupby("keyword").agg(
            position=("position", "mean"),
            bsr=("bsr", "mean"),
            reviews=("reviews", "mean")
        )
        df_prev = df_trend[df_trend["timestamp"] == prev_ts].groupby("keyword").agg(
            position=("position", "mean"),
            bsr=("bsr", "mean"),
            reviews=("reviews", "mean")
        )
        
        delta = pd.DataFrame({
            "Keyword": df_latest.index,
            "Ø Rang (aktuell)": df_latest["position"].values,
            "Ø Rang (vorher)": [df_prev.loc[kw, "position"] if kw in df_prev.index else None for kw in df_latest.index],
            "Rang Δ": [df_latest.loc[kw, "position"] - df_prev.loc[kw, "position"] if kw in df_prev.index else None for kw in df_latest.index],
            "Ø BSR (aktuell)": df_latest["bsr"].values,
            "Ø BSR (vorher)": [df_prev.loc[kw, "bsr"] if kw in df_prev.index else None for kw in df_latest.index],
            "BSR Δ": [df_latest.loc[kw, "bsr"] - df_prev.loc[kw, "bsr"] if kw in df_prev.index else None for kw in df_latest.index],
            "Ø Reviews (aktuell)": df_latest["reviews"].values,
            "Ø Reviews (vorher)": [df_prev.loc[kw, "reviews"] if kw in df_prev.index else None for kw in df_latest.index],
            "Reviews Δ": [df_latest.loc[kw, "reviews"] - df_prev.loc[kw, "reviews"] if kw in df_prev.index else None for kw in df_latest.index],
        })
        
        st.caption(f"Vergleich: {pd.to_datetime(prev_ts).strftime('%d.%m.%Y %H:%M')} → {pd.to_datetime(latest_ts).strftime('%d.%m.%Y %H:%M')}")
        st.dataframe(delta.set_index("Keyword"), use_container_width=True)
    else:
        st.info("Mindestens 2 Scans nötig für Veränderungsanalyse.")

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