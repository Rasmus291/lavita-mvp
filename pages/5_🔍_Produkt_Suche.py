"""
Manuelle Produktsuche: Keyword eingeben → Amazon scrapen → Produkte zum Tracking hinzufügen.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from config import SERPAPI_KEY
from scraper import scrape_keyword
from product_registry import get_registry
from pipeline import run_manual_pipeline
from shared import STYLE_CSS

st.set_page_config(page_title="Produkt-Suche", layout="wide", page_icon="🔍")
st.markdown(STYLE_CSS, unsafe_allow_html=True)

st.title("🔍 Produkt-Suche & Tracking")
st.caption("Suche nach Produkten auf Amazon.de und füge sie zum Tracking hinzu.")

# --- Session State initialisieren ---
if "search_results" not in st.session_state:
    st.session_state.search_results = None
if "search_keyword" not in st.session_state:
    st.session_state.search_keyword = ""
if "pipeline_done" not in st.session_state:
    st.session_state.pipeline_done = False
if "pipeline_result" not in st.session_state:
    st.session_state.pipeline_result = None

# --- Suchbereich ---
st.subheader("1️⃣ Amazon-Suche")
col_input, col_count = st.columns([3, 1])

with col_input:
    keyword = st.text_input(
        "Suchbegriff eingeben",
        placeholder="z.B. Vitamin D Tropfen, Magnesium Flüssig...",
        key="keyword_input",
    )

with col_count:
    max_results = st.number_input("Max. Ergebnisse", min_value=5, max_value=50, value=20, step=5)

search_clicked = st.button("🔎 Suchen", type="primary", use_container_width=True)

if search_clicked and keyword.strip():
    st.session_state.pipeline_done = False
    st.session_state.pipeline_result = None

    with st.spinner(f"Suche nach \"{keyword}\" auf Amazon.de..."):
        results = scrape_keyword(SERPAPI_KEY, keyword.strip(), max_results=max_results)

    if results:
        df = pd.DataFrame(results)
        # Bereits getrackte ASINs markieren
        registry = get_registry()
        tracked_asins = set(registry["asin"].dropna().tolist()) if not registry.empty else set()
        df["already_tracked"] = df["asin"].isin(tracked_asins)

        st.session_state.search_results = df
        st.session_state.search_keyword = keyword.strip()
        st.success(f"✅ {len(df)} Produkte gefunden für \"{keyword}\"")
    else:
        st.session_state.search_results = None
        st.warning("Keine Ergebnisse gefunden. Versuche einen anderen Suchbegriff.")

elif search_clicked and not keyword.strip():
    st.warning("Bitte einen Suchbegriff eingeben.")

# --- Ergebnisse anzeigen ---
if st.session_state.search_results is not None and not st.session_state.pipeline_done:
    df = st.session_state.search_results

    st.markdown("---")
    st.subheader("2️⃣ Ergebnisse auswählen")

    tracked_count = df["already_tracked"].sum()
    new_count = len(df) - tracked_count
    st.caption(f"📊 {len(df)} Ergebnisse | ✅ {tracked_count} bereits getrackt | 🆕 {new_count} neu")

    # Auswahlmöglichkeiten
    col_all, col_new, col_none = st.columns(3)
    with col_all:
        select_all = st.button("Alle auswählen", use_container_width=True)
    with col_new:
        select_new = st.button("Nur neue auswählen", use_container_width=True)
    with col_none:
        deselect_all = st.button("Auswahl aufheben", use_container_width=True)

    # Checkbox-State verwalten
    if "selections" not in st.session_state or select_all or select_new or deselect_all:
        if select_all:
            st.session_state.selections = {i: True for i in range(len(df))}
        elif select_new:
            st.session_state.selections = {
                i: not row["already_tracked"] for i, row in df.iterrows()
            }
        elif deselect_all:
            st.session_state.selections = {i: False for i in range(len(df))}
        else:
            # Standard: neue Produkte vorausgewählt
            st.session_state.selections = {
                i: not row["already_tracked"] for i, row in df.iterrows()
            }

    # Produkt-Tabelle mit Checkboxen
    selected_indices = []
    for idx, row in df.iterrows():
        col_check, col_status, col_pos, col_title, col_brand, col_price, col_rating, col_reviews = st.columns(
            [0.5, 0.8, 0.5, 4, 1.5, 1, 1, 1]
        )

        with col_check:
            default = st.session_state.selections.get(idx, not row["already_tracked"])
            selected = st.checkbox("", value=default, key=f"sel_{idx}", label_visibility="collapsed")
            if selected:
                selected_indices.append(idx)

        with col_status:
            if row["already_tracked"]:
                st.markdown("✅ Getrackt")
            else:
                st.markdown("🆕 Neu")

        with col_pos:
            st.markdown(f"**#{row['position']}**")

        with col_title:
            title_display = str(row["title"])[:80]
            if len(str(row["title"])) > 80:
                title_display += "..."
            st.markdown(title_display, help=str(row["title"]))

        with col_brand:
            st.markdown(str(row.get("brand", "—") or "—"))

        with col_price:
            st.markdown(str(row.get("price", "—") or "—"))

        with col_rating:
            rating = row.get("rating")
            st.markdown(f"{rating} ★" if pd.notna(rating) else "—")

        with col_reviews:
            reviews = row.get("reviews", 0)
            st.markdown(str(int(reviews)) if pd.notna(reviews) else "0")

    # --- Tracking starten ---
    st.markdown("---")
    st.subheader("3️⃣ Zum Tracking hinzufügen")

    n_selected = len(selected_indices)
    n_already = sum(1 for i in selected_indices if df.loc[i, "already_tracked"])
    n_new = n_selected - n_already

    st.info(f"📋 **{n_selected}** Produkte ausgewählt ({n_new} neu, {n_already} bereits getrackt)")

    track_clicked = st.button(
        f"🚀 {n_selected} Produkte zum Tracking hinzufügen",
        type="primary",
        use_container_width=True,
        disabled=n_selected == 0,
    )

    if track_clicked and n_selected > 0:
        selected_df = df.loc[selected_indices].copy()
        # already_tracked Spalte entfernen (nicht für Pipeline benötigt)
        selected_df = selected_df.drop(columns=["already_tracked"], errors="ignore")

        with st.spinner("Pipeline läuft: Klassifikation → Registrierung → BSR → KPIs..."):
            result = run_manual_pipeline(selected_df)

        st.session_state.pipeline_done = True
        st.session_state.pipeline_result = result
        st.rerun()

# --- Ergebnis-Anzeige nach Pipeline ---
if st.session_state.pipeline_done and st.session_state.pipeline_result is not None:
    result = st.session_state.pipeline_result
    st.markdown("---")
    st.success(f"✅ {len(result)} Produkte erfolgreich zum Tracking hinzugefügt!")

    st.subheader("📊 Verarbeitete Produkte")

    display_cols = ["product_id", "title", "brand", "price_clean", "rating", "reviews",
                    "est_orders", "competition_grade", "bsr", "cis_score", "is_new"]
    available_cols = [c for c in display_cols if c in result.columns]

    st.dataframe(
        result[available_cols].style.format({
            "price_clean": "€{:.2f}",
            "cis_score": "{:.3f}",
            "rating": "{:.1f}",
        }, na_rep="—"),
        use_container_width=True,
        hide_index=True,
    )

    # Neuen Suchlauf starten
    if st.button("🔄 Neue Suche starten", type="secondary", use_container_width=True):
        st.session_state.search_results = None
        st.session_state.pipeline_done = False
        st.session_state.pipeline_result = None
        st.session_state.pop("selections", None)
        st.rerun()
