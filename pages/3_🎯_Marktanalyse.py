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

# ── Anteile berechnen ──────────────────────────────────────────────────
total = len(df_view)
dist = df_view["competition_grade"].value_counts().sort_index()

# Metriken: Anteil je Kategorie als prozentuale Kacheln
cols = st.columns(5)
for i, grade in enumerate(range(1, 6)):
    count = dist.get(grade, 0)
    pct = (count / total * 100) if total > 0 else 0
    label = GRADE_LABELS.get(grade, f"Kat {grade}")
    with cols[i]:
        st.metric(label=label, value=f"{pct:.1f} %", delta=f"{count} Produkte")

st.divider()

# ── Horizontaler Balken: Anteile auf einen Blick ───────────────────────
bar_data = dist.reset_index()
bar_data.columns = ["Kategorie", "Anzahl"]
bar_data["Label"] = bar_data["Kategorie"].map(GRADE_LABELS)
bar_data["Anteil (%)"] = (bar_data["Anzahl"] / total * 100).round(1)

fig = px.bar(
    bar_data, y="Label", x="Anteil (%)",
    orientation="h",
    color="Label",
    text="Anteil (%)",
    color_discrete_sequence=px.colors.sequential.Tealgrn_r,
    title="Anteil der Produkte pro Kategorie",
)
fig.update_traces(texttemplate="%{text:.1f} %", textposition="outside")
fig.update_layout(showlegend=False, xaxis_title="Anteil (%)", yaxis_title="",
                  yaxis=dict(autorange="reversed"))
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Legende ────────────────────────────────────────────────────────────
st.info("""
**Kategorien (1 = nah an LaVita, 5 = fern)**
- **Kat 1:** Flüssiges Multivitaminkonzentrat + Mikronährstoffe
- **Kat 2:** Multivitamin-Pulver zum Trinken + Mikronährstoffe
- **Kat 3:** Multivitamin-Kapseln/-Tabletten + Mikronährstoffe
- **Kat 4:** Allgemeines NEM-Pulver/Drink (kein Multi)
- **Kat 5:** Sonstige NEM, Vitamine, Lifestyle-Health
""")
st.caption("Klassifikation via Buzzword-Analyse + Amazon Browse-Nodes")

st.divider()

import ast

# ── Produkte je Kategorie (sortiert nach BSR-Kategorie + BSR-Rang) ────
st.subheader("📋 Produkte je Kategorie")


def _parse_bsr_cats(val):
    """Parst bsr_categories-String zu Dict."""
    if pd.isna(val) or val is None:
        return {}
    try:
        return ast.literal_eval(str(val))
    except (ValueError, SyntaxError):
        return {}


for grade in range(1, 6):
    label = GRADE_LABELS.get(grade, f"Kat {grade}")
    cat_df = df_view[df_view["competition_grade"] == grade].copy()
    count = len(cat_df)

    with st.expander(f"{label}  —  {count} Produkte", expanded=(grade == 1)):
        if cat_df.empty:
            st.write("Keine Produkte in dieser Kategorie für diesen Scan.")
        else:
            # BSR-Kategorien aufschlüsseln
            rows = []
            for _, row in cat_df.iterrows():
                bsr_dict = _parse_bsr_cats(row.get("bsr_categories"))
                if bsr_dict:
                    for bsr_cat, bsr_rank in bsr_dict.items():
                        rows.append({
                            "BSR-Kategorie": bsr_cat,
                            "BSR-Rang": bsr_rank,
                            "title": row.get("title"),
                            "brand": row.get("brand"),
                            "price": row.get("price"),
                            "rating": row.get("rating"),
                            "reviews": row.get("reviews"),
                        })
                else:
                    rows.append({
                        "BSR-Kategorie": "Keine BSR-Daten",
                        "BSR-Rang": None,
                        "title": row.get("title"),
                        "brand": row.get("brand"),
                        "price": row.get("price"),
                        "rating": row.get("rating"),
                        "reviews": row.get("reviews"),
                    })

            exploded = pd.DataFrame(rows)
            exploded = exploded.sort_values(["BSR-Kategorie", "BSR-Rang"],
                                            na_position="last")

            # Pro BSR-Kategorie anzeigen
            for bsr_cat in exploded["BSR-Kategorie"].unique():
                sub = exploded[exploded["BSR-Kategorie"] == bsr_cat]
                st.markdown(f"**🏷️ {bsr_cat}** ({len(sub)} Einträge)")
                st.dataframe(
                    sub[["BSR-Rang", "title", "brand", "price", "rating", "reviews"]]
                    .reset_index(drop=True),
                    use_container_width=True,
                    hide_index=True,
                )
