import streamlit as st
import pandas as pd
import plotly.express as px
import ast
from shared import get_data, render_sidebar_filters, GRADE_LABELS, STYLE_CSS

st.set_page_config(page_title="Produkt-Ranking", layout="wide", page_icon="🏆")
st.markdown(STYLE_CSS, unsafe_allow_html=True)

df = get_data()
if df is None or df.empty:
    st.error("Keine Daten gefunden.")
    st.stop()

df_view, date_opt = render_sidebar_filters(df)

st.header("🏆 Aktuelles Wettbewerbs-Ranking")

# Sortierung nach Marke, dann Position
df_ranked = df_view.sort_values(by=["brand", "position"], ascending=[True, True]).reset_index(drop=True)
df_ranked.index = df_ranked.index + 1

# --- Produkt-Trends berechnen (Delta zum vorherigen Scan) ---
timestamps_sorted = sorted(df["timestamp"].unique())
has_trends = False
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

# Spalten zusammenstellen
display_cols = ["position", "title", "brand", "price_clean", "rating", "reviews", "est_orders", "bsr", "cis_score"]

if has_trends:
    display_cols = [
        "position", "Rang Δ", "title", "brand", "price_clean",
        "rating", "reviews", "Reviews Δ", "est_orders", "bsr", "BSR Δ", "cis_score"
    ]

# BSR-Kategorie-Spalte hinzufügen
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
    display_cols = [
        "position", "title", "brand", "price_clean", "rating", "reviews",
        "est_orders", "bsr", "bsr_hauptkategorie", "bsr_subkategorie", "cis_score"
    ]

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
        "cis_score": "Score",
        "Rang Δ": "Rang Δ",
        "BSR Δ": "BSR Δ",
        "Reviews Δ": "Reviews Δ",
    }),
    use_container_width=True,
    height=500,
)

# --- Einzelprodukt-Trend-Chart ---
st.markdown("---")
st.subheader("📈 Produkt-Trend (Einzelprodukt)")

product_options = df_ranked[["asin", "title"]].drop_duplicates()
product_labels = {row["asin"]: row["title"][:70] for _, row in product_options.iterrows()}

selected_asin = st.selectbox(
    "Produkt wählen",
    options=list(product_labels.keys()),
    format_func=lambda x: product_labels.get(x, x),
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
                title="Amazon-Rang", labels={"position": "Rang", "timestamp": ""},
            )
            fig_p_rank.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_p_rank, use_container_width=True)

        with col_t2:
            if "bsr" in df_product.columns and df_product["bsr"].notna().any():
                fig_p_bsr = px.line(
                    df_product, x="timestamp", y="bsr", markers=True,
                    title="Bestseller-Rang (BSR)", labels={"bsr": "BSR", "timestamp": ""},
                )
                fig_p_bsr.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_p_bsr, use_container_width=True)
            else:
                st.info("BSR noch nicht verfügbar")

        with col_t3:
            fig_p_rev = px.line(
                df_product, x="timestamp", y="reviews", markers=True,
                title="Bewertungsanzahl", labels={"reviews": "Reviews", "timestamp": ""},
            )
            st.plotly_chart(fig_p_rev, use_container_width=True)
    else:
        st.info("Mindestens 2 Scans für dieses Produkt nötig.")
