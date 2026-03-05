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

# --- Keyword-Filter ---
st.sidebar.markdown("---")
st.sidebar.header("🔑 Keyword-Filter")
available_keywords = sorted(df_view["keyword"].dropna().unique())
keyword_options = ["Alle Keywords"] + available_keywords
selected_keyword = st.sidebar.selectbox("Keyword", options=keyword_options)

if selected_keyword != "Alle Keywords":
    df_view = df_view[df_view["keyword"] == selected_keyword]

st.header("🏆 Aktuelles Wettbewerbs-Ranking")
if selected_keyword != "Alle Keywords":
    st.caption(f"🔑 Keyword: **{selected_keyword}** | Produkte: {len(df_view)}")

# Sortierung nach Position (Rang)
df_ranked = df_view.sort_values(by=["position"], ascending=[True]).reset_index(drop=True)
df_ranked.index = df_ranked.index + 1

# --- Vergleichszeitpunkt wählen ---
timestamps_sorted = sorted(df["timestamp"].unique())
has_trends = False

if len(timestamps_sorted) >= 2:
    # Aktuelle Zeitstempel ausschließen
    compare_options = [ts for ts in timestamps_sorted if ts != date_opt]

    if compare_options:
        st.sidebar.markdown("---")
        st.sidebar.header("📊 Veränderungs-Vergleich")

        compare_mode = st.sidebar.radio(
            "Vergleichen mit",
            options=["Letzter Scan", "Bestimmtes Datum"],
            index=0,
        )

        if compare_mode == "Letzter Scan":
            # Nächstälterer Zeitpunkt vor dem aktuellen
            older = [ts for ts in compare_options if ts < date_opt]
            compare_ts = older[-1] if older else compare_options[-1]
        else:
            compare_ts = st.sidebar.selectbox(
                "Vergleichsdatum",
                options=sorted(compare_options, reverse=True),
                format_func=lambda x: pd.to_datetime(x).strftime("%d.%m.%Y %H:%M"),
            )

        df_prev = df[df["timestamp"] == compare_ts].copy()
        df_prev = df_prev.sort_values("position").drop_duplicates(subset=["asin"], keep="first")

        prev_lookup = df_prev.set_index("asin")[["position", "bsr", "reviews", "rating"]].rename(
            columns={
                "position": "prev_position",
                "bsr": "prev_bsr",
                "reviews": "prev_reviews",
                "rating": "prev_rating",
            }
        )
        df_ranked = df_ranked.join(prev_lookup, on="asin")

        df_ranked["Rang Δ"] = df_ranked["position"] - df_ranked["prev_position"]
        df_ranked["BSR Δ"] = df_ranked["bsr"] - df_ranked["prev_bsr"]
        df_ranked["Reviews Δ"] = df_ranked["reviews"] - df_ranked["prev_reviews"]
        df_ranked["Rating Δ"] = (df_ranked["rating"] - df_ranked["prev_rating"]).round(1)
        has_trends = True

        compare_label = pd.to_datetime(compare_ts).strftime("%d.%m.%Y %H:%M")
        st.caption(f"📊 Veränderung im Vergleich zu: **{compare_label}**")

# Neu-Kennzeichnung
if "is_new" in df_ranked.columns:
    df_ranked["status"] = df_ranked["is_new"].apply(lambda x: "🆕 Neu" if x else "")
else:
    df_ranked["status"] = ""

# product_id sicherstellen
if "product_id" not in df_ranked.columns:
    df_ranked["product_id"] = ""

# Spalten zusammenstellen
display_cols = ["product_id", "status", "position", "title", "brand", "price_clean", "rating", "reviews", "est_orders", "bsr", "cis_score"]

if has_trends:
    display_cols = [
        "product_id", "status", "position", "Rang Δ", "title", "brand", "price_clean",
        "rating", "Rating Δ", "reviews", "Reviews Δ", "est_orders", "bsr", "BSR Δ", "cis_score"
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

    if has_trends:
        display_cols = [
            "product_id", "status", "position", "Rang Δ", "title", "brand", "price_clean",
            "rating", "Rating Δ", "reviews", "Reviews Δ",
            "est_orders", "bsr", "BSR Δ", "bsr_hauptkategorie", "bsr_subkategorie", "cis_score"
        ]
    else:
        display_cols = [
            "product_id", "status", "position", "title", "brand", "price_clean", "rating", "reviews",
            "est_orders", "bsr", "bsr_hauptkategorie", "bsr_subkategorie", "cis_score"
        ]

st.dataframe(
    df_ranked[display_cols].rename(columns={
        "product_id": "ID",
        "status": "Status",
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
        "Rating Δ": "Rating Δ",
    }),
    use_container_width=True,
    height=500,
)

# --- Einzelprodukt-Trend-Chart ---
st.markdown("---")
st.subheader("📈 Produkt-Trend (Einzelprodukt)")

product_options = df_ranked[["asin", "title", "product_id"]].drop_duplicates(subset=["asin"])
product_labels = {row["asin"]: f"[{row['product_id']}] {row['title'][:65]}" for _, row in product_options.iterrows()}

selected_asin = st.selectbox(
    "Produkt wählen",
    options=list(product_labels.keys()),
    format_func=lambda x: product_labels.get(x, x),
)

if selected_asin:
    df_product = df[df["asin"] == selected_asin].copy()
    df_product["timestamp"] = pd.to_datetime(df_product["timestamp"])

    # Pro Zeitpunkt aggregieren (Produkt kann über mehrere Keywords mehrfach vorkommen)
    agg_cols = {}
    if "position" in df_product.columns:
        agg_cols["position"] = "min"  # Bester Rang
    if "bsr" in df_product.columns:
        agg_cols["bsr"] = "first"
    if "reviews" in df_product.columns:
        agg_cols["reviews"] = "max"
    if "rating" in df_product.columns:
        agg_cols["rating"] = "first"

    df_product = (
        df_product.groupby("timestamp")
        .agg(agg_cols)
        .reset_index()
        .sort_values("timestamp")
    )

    if len(df_product) >= 2:
        col_t1, col_t2, col_t3, col_t4 = st.columns(4)

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

        with col_t4:
            if "rating" in df_product.columns and df_product["rating"].notna().any():
                fig_p_rat = px.line(
                    df_product, x="timestamp", y="rating", markers=True,
                    title="Bewertung (Sterne)", labels={"rating": "Rating", "timestamp": ""},
                )
                fig_p_rat.update_yaxes(range=[1, 5])
                st.plotly_chart(fig_p_rat, use_container_width=True)
            else:
                st.info("Rating noch nicht verfügbar")
    else:
        st.info("Mindestens 2 Scans für dieses Produkt nötig.")
