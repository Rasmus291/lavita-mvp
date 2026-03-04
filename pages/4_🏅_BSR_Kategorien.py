import streamlit as st
import pandas as pd
import plotly.express as px
import ast
from shared import get_data, render_sidebar_filters, STYLE_CSS

st.set_page_config(page_title="BSR-Kategorien", layout="wide", page_icon="🏅")
st.markdown(STYLE_CSS, unsafe_allow_html=True)

df = get_data()
if df is None or df.empty:
    st.error("Keine Daten gefunden.")
    st.stop()

df_view, date_opt = render_sidebar_filters(df)

st.header("🏅 BSR-Rankings nach Amazon-Kategorie")

if "bsr_categories" in df_view.columns and df_view["bsr_categories"].notna().any():
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
                        "ASIN": row.get("asin", ""),
                    })
        except (ValueError, SyntaxError):
            continue

    if all_categories:
        df_cats = pd.DataFrame(all_categories)

        unique_cats = sorted(df_cats["Kategorie"].unique())
        st.info(f"**{len(unique_cats)} Amazon-Kategorien** gefunden: {', '.join(unique_cats)}")

        selected_cat = st.selectbox("📂 Kategorie wählen", options=["Alle"] + unique_cats)

        if selected_cat != "Alle":
            df_cats = df_cats[df_cats["Kategorie"] == selected_cat]

        df_cats = df_cats.sort_values("BSR-Rang", ascending=True).reset_index(drop=True)
        df_cats.index = df_cats.index + 1

        st.dataframe(df_cats, use_container_width=True, height=500)

        # Visualisierung: BSR pro Kategorie
        st.subheader("📊 BSR-Verteilung pro Kategorie")
        cat_summary = (
            df_cats.groupby("Kategorie")
            .agg(
                Anzahl_Produkte=("BSR-Rang", "count"),
                Bester_BSR=("BSR-Rang", "min"),
                Durchschnitt_BSR=("BSR-Rang", "mean"),
                Schlechtester_BSR=("BSR-Rang", "max"),
            )
            .reset_index()
            .sort_values("Bester_BSR")
        )

        st.dataframe(cat_summary, use_container_width=True)

        fig_bsr = px.bar(
            cat_summary,
            x="Kategorie",
            y="Durchschnitt_BSR",
            title="Ø BSR-Rang pro Kategorie (niedriger = besser)",
            color="Anzahl_Produkte",
            text="Bester_BSR",
        )
        fig_bsr.update_layout(yaxis_title="BSR-Rang", xaxis_tickangle=-45)
        st.plotly_chart(fig_bsr, use_container_width=True)
    else:
        st.info("Keine BSR-Kategoriedaten zum Anzeigen.")
else:
    st.info("🏅 BSR-Kategorie-Daten noch nicht verfügbar. Starte `python main.py` erneut.")
