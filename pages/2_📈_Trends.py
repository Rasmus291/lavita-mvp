import streamlit as st
# import pandas as pd
# import plotly.express as px
# from shared import get_data, render_sidebar_filters, STYLE_CSS
from shared import STYLE_CSS

st.set_page_config(page_title="Trends", layout="wide", page_icon="📈")
st.markdown(STYLE_CSS, unsafe_allow_html=True)

# df = get_data()
# if df is None or df.empty:
#     st.error("Keine Daten gefunden.")
#     st.stop()

# df_view, date_opt = render_sidebar_filters(df)

# st.header("📈 Trendanalyse")

# # --- Keyword-Auswahl ---
# all_keywords = sorted(df["keyword"].dropna().unique())
# selected_keywords = st.multiselect(
#     "🔑 Keywords auswählen",
#     options=all_keywords,
#     default=all_keywords,
#     help="Wähle Keywords für die Trendanalyse",
# )

# df_trend = df[df["keyword"].isin(selected_keywords)].copy()
# df_trend["timestamp"] = pd.to_datetime(df_trend["timestamp"])

# if len(df_trend["timestamp"].unique()) < 2:
#     st.warning("⚠️ Mindestens 2 Scan-Zeitpunkte nötig für Trendanalyse.")

# # === Amazon-Rang pro Keyword über Zeit ===
# st.markdown("### 🏆 Amazon-Rang pro Keyword")
# st.caption("Durchschnittliche Suchposition der Produkte pro Keyword (niedriger = besser)")

# rank_trend = df_trend.groupby(["timestamp", "keyword"]).agg(
#     avg_position=("position", "mean")
# ).reset_index()

# fig_rank = px.line(
#     rank_trend, x="timestamp", y="avg_position", color="keyword",
#     markers=True, title="Ø Amazon-Suchrang pro Keyword",
#     labels={"avg_position": "Ø Position", "timestamp": "Zeitpunkt", "keyword": "Keyword"},
# )
# fig_rank.update_yaxes(autorange="reversed")
# st.plotly_chart(fig_rank, use_container_width=True)

# # === BSR-Veränderung pro Keyword über Zeit ===
# st.markdown("### 📦 Bestseller-Rang (BSR) pro Keyword")
# st.caption("Durchschnittlicher BSR der Produkte pro Keyword (niedriger = mehr Verkäufe)")

# if "bsr" in df_trend.columns and df_trend["bsr"].notna().any():
#     bsr_trend = df_trend[df_trend["bsr"].notna()].groupby(["timestamp", "keyword"]).agg(
#         avg_bsr=("bsr", "mean"),
#         min_bsr=("bsr", "min"),
#     ).reset_index()

#     bsr_metric = st.radio("BSR-Metrik:", ["Ø BSR", "Bester BSR"], horizontal=True, key="bsr_metric")
#     y_col = "avg_bsr" if bsr_metric == "Ø BSR" else "min_bsr"

#     fig_bsr = px.line(
#         bsr_trend, x="timestamp", y=y_col, color="keyword",
#         markers=True, title=f"{bsr_metric} pro Keyword über Zeit",
#         labels={y_col: bsr_metric, "timestamp": "Zeitpunkt", "keyword": "Keyword"},
#     )
#     fig_bsr.update_yaxes(autorange="reversed")
#     st.plotly_chart(fig_bsr, use_container_width=True)
# else:
#     st.info("BSR-Daten noch nicht für Trendanalyse verfügbar.")

# # === Reviews-Veränderung pro Keyword über Zeit ===
# st.markdown("### ⭐ Bewertungsanzahl pro Keyword")
# st.caption("Durchschnittliche Rezensionen pro Keyword – zeigt Marktdynamik")

# reviews_trend = df_trend.groupby(["timestamp", "keyword"]).agg(
#     avg_reviews=("reviews", "mean"),
#     total_reviews=("reviews", "sum"),
# ).reset_index()

# review_metric = st.radio("Reviews-Metrik:", ["Ø Reviews", "∑ Reviews"], horizontal=True, key="review_metric")
# y_col_r = "avg_reviews" if review_metric == "Ø Reviews" else "total_reviews"

# fig_reviews = px.line(
#     reviews_trend, x="timestamp", y=y_col_r, color="keyword",
#     markers=True, title=f"{review_metric} pro Keyword über Zeit",
#     labels={y_col_r: review_metric, "timestamp": "Zeitpunkt", "keyword": "Keyword"},
# )
# st.plotly_chart(fig_reviews, use_container_width=True)

# # === Veränderungstabelle (Delta zum vorherigen Scan) ===
# st.markdown("### 📊 Veränderung zum vorherigen Scan")

# timestamps_sorted = sorted(df_trend["timestamp"].unique())
# if len(timestamps_sorted) >= 2:
#     latest_ts = timestamps_sorted[-1]
#     prev_ts = timestamps_sorted[-2]

#     df_latest = df_trend[df_trend["timestamp"] == latest_ts].groupby("keyword").agg(
#         position=("position", "mean"),
#         bsr=("bsr", "mean"),
#         reviews=("reviews", "mean"),
#     )
#     df_prev = df_trend[df_trend["timestamp"] == prev_ts].groupby("keyword").agg(
#         position=("position", "mean"),
#         bsr=("bsr", "mean"),
#         reviews=("reviews", "mean"),
#     )

#     delta = pd.DataFrame({
#         "Keyword": df_latest.index,
#         "Ø Rang (aktuell)": df_latest["position"].values,
#         "Ø Rang (vorher)": [df_prev.loc[kw, "position"] if kw in df_prev.index else None for kw in df_latest.index],
#         "Rang Δ": [df_latest.loc[kw, "position"] - df_prev.loc[kw, "position"] if kw in df_prev.index else None for kw in df_latest.index],
#         "Ø BSR (aktuell)": df_latest["bsr"].values,
#         "Ø BSR (vorher)": [df_prev.loc[kw, "bsr"] if kw in df_prev.index else None for kw in df_latest.index],
#         "BSR Δ": [df_latest.loc[kw, "bsr"] - df_prev.loc[kw, "bsr"] if kw in df_prev.index else None for kw in df_latest.index],
#         "Ø Reviews (aktuell)": df_latest["reviews"].values,
#         "Ø Reviews (vorher)": [df_prev.loc[kw, "reviews"] if kw in df_prev.index else None for kw in df_latest.index],
#         "Reviews Δ": [df_latest.loc[kw, "reviews"] - df_prev.loc[kw, "reviews"] if kw in df_prev.index else None for kw in df_latest.index],
#     })

#     st.caption(f"Vergleich: {pd.to_datetime(prev_ts).strftime('%d.%m.%Y %H:%M')} → {pd.to_datetime(latest_ts).strftime('%d.%m.%Y %H:%M')}")
#     st.dataframe(delta.set_index("Keyword"), use_container_width=True)
# else:
#     st.info("Mindestens 2 Scans nötig für Veränderungsanalyse.")
