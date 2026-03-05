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
from shared import STYLE_CSS, get_latest_values
from cleaner import clean_price

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
    st.session_state.pop("selections", None)

    with st.spinner(f"Suche nach \"{keyword}\" auf Amazon.de..."):
        results = scrape_keyword(SERPAPI_KEY, keyword.strip(), max_results=max_results)

    if results:
        df = pd.DataFrame(results)

        # Bereits getrackte ASINs markieren
        registry = get_registry()
        tracked_asins = set(registry["asin"].dropna().tolist()) if not registry.empty else set()
        df["already_tracked"] = df["asin"].isin(tracked_asins)

        # Vorherige Werte aus master_data laden
        prev_values = get_latest_values(df["asin"].tolist())
        if not prev_values.empty:
            df = df.merge(prev_values, on="asin", how="left")
        else:
            df["prev_position"] = None
            df["prev_price"] = None
            df["prev_rating"] = None
            df["prev_reviews"] = None
            df["prev_bsr"] = None
            df["prev_timestamp"] = None

        # Preis bereinigen für Vergleich
        df["price_clean"] = df["price"].apply(clean_price)

        # Deltas berechnen
        df["reviews_num"] = pd.to_numeric(df["reviews"], errors="coerce").fillna(0)
        df["pos_delta"] = df.apply(
            lambda r: int(r["position"] - r["prev_position"]) if pd.notna(r.get("prev_position")) else None, axis=1
        )
        df["price_delta"] = df.apply(
            lambda r: round(r["price_clean"] - r["prev_price"], 2) if pd.notna(r.get("prev_price")) and pd.notna(r.get("price_clean")) else None, axis=1
        )
        df["rating_delta"] = df.apply(
            lambda r: round(float(r["rating"]) - float(r["prev_rating"]), 1) if pd.notna(r.get("prev_rating")) and pd.notna(r.get("rating")) else None, axis=1
        )
        df["reviews_delta"] = df.apply(
            lambda r: int(r["reviews_num"] - r["prev_reviews"]) if pd.notna(r.get("prev_reviews")) else None, axis=1
        )

        st.session_state.search_results = df
        st.session_state.search_keyword = keyword.strip()
        st.success(f"✅ {len(df)} Produkte gefunden für \"{keyword}\"")
    else:
        st.session_state.search_results = None
        st.warning("Keine Ergebnisse gefunden. Versuche einen anderen Suchbegriff.")

elif search_clicked and not keyword.strip():
    st.warning("Bitte einen Suchbegriff eingeben.")


def _format_delta(val, invert=False, fmt="d"):
    """Formatiert einen Delta-Wert mit Pfeil. invert=True: niedrigerer Wert = grün."""
    if val is None or pd.isna(val):
        return ""
    val_num = float(val)
    if val_num == 0:
        return "→ 0"
    if invert:
        color = "green" if val_num < 0 else "red"
    else:
        color = "green" if val_num > 0 else "red"
    arrow = "▲" if val_num > 0 else "▼"
    if fmt == "d":
        return f":{color}[{arrow} {int(abs(val_num))}]"
    else:
        return f":{color}[{arrow} {abs(val_num):.2f}]"


# --- Ergebnisse anzeigen ---
if st.session_state.search_results is not None and not st.session_state.pipeline_done:
    df = st.session_state.search_results

    st.markdown("---")
    st.subheader("2️⃣ Ergebnisse auswählen")

    tracked_count = int(df["already_tracked"].sum())
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
            st.session_state.selections = {i: True for i in df.index}
        elif select_new:
            st.session_state.selections = {
                i: not row["already_tracked"] for i, row in df.iterrows()
            }
        elif deselect_all:
            st.session_state.selections = {i: False for i in df.index}
        else:
            # Standard: alle Produkte vorausgewählt
            st.session_state.selections = {i: True for i in df.index}

    # --- Tabellen-Header ---
    has_prev = df["already_tracked"].any()

    if has_prev:
        header_cols = st.columns([0.4, 0.7, 0.5, 3.5, 1.2, 1, 0.8, 1, 0.8, 1, 0.8])
        headers = ["", "Status", "Rang", "Produkt", "Marke", "Preis", "Δ", "Reviews", "Δ", "Rating", "Δ"]
    else:
        header_cols = st.columns([0.4, 0.7, 0.5, 4, 1.5, 1, 1, 1])
        headers = ["", "Status", "Rang", "Produkt", "Marke", "Preis", "Reviews", "Rating"]

    for col, h in zip(header_cols, headers):
        col.markdown(f"**{h}**")

    st.markdown("---")

    # --- Produkt-Zeilen ---
    selected_indices = []
    for idx, row in df.iterrows():
        default = st.session_state.selections.get(idx, True)

        if has_prev:
            cols = st.columns([0.4, 0.7, 0.5, 3.5, 1.2, 1, 0.8, 1, 0.8, 1, 0.8])
        else:
            cols = st.columns([0.4, 0.7, 0.5, 4, 1.5, 1, 1, 1])

        # Checkbox
        with cols[0]:
            selected = st.checkbox("", value=default, key=f"sel_{idx}", label_visibility="collapsed")
            if selected:
                selected_indices.append(idx)

        # Status
        with cols[1]:
            if row["already_tracked"]:
                st.markdown("📊 Update")
            else:
                st.markdown("🆕 Neu")

        # Position + Delta
        with cols[2]:
            pos_text = f"**#{int(row['position'])}**"
            if has_prev and pd.notna(row.get("pos_delta")):
                pos_text += f" {_format_delta(row['pos_delta'], invert=True)}"
            st.markdown(pos_text)

        # Title
        with cols[3]:
            title_display = str(row["title"])[:75]
            if len(str(row["title"])) > 75:
                title_display += "..."
            st.markdown(title_display, help=str(row["title"]))

        # Brand
        with cols[4]:
            st.markdown(str(row.get("brand", "—") or "—"))

        if has_prev:
            # Price
            with cols[5]:
                price_text = f"€{row['price_clean']:.2f}" if pd.notna(row.get("price_clean")) else "—"
                st.markdown(price_text)
            # Price Delta
            with cols[6]:
                st.markdown(_format_delta(row.get("price_delta"), invert=True, fmt="f"))
            # Reviews
            with cols[7]:
                st.markdown(str(int(row["reviews_num"])) if row["reviews_num"] > 0 else "0")
            # Reviews Delta
            with cols[8]:
                st.markdown(_format_delta(row.get("reviews_delta"), invert=False))
            # Rating
            with cols[9]:
                rating = row.get("rating")
                st.markdown(f"{float(rating):.1f} ★" if pd.notna(rating) else "—")
            # Rating Delta
            with cols[10]:
                st.markdown(_format_delta(row.get("rating_delta"), invert=False, fmt="f"))
        else:
            # Price
            with cols[5]:
                st.markdown(str(row.get("price", "—") or "—"))
            # Reviews
            with cols[6]:
                reviews = row.get("reviews", 0)
                st.markdown(str(int(reviews)) if pd.notna(reviews) else "0")
            # Rating
            with cols[7]:
                rating = row.get("rating")
                st.markdown(f"{rating} ★" if pd.notna(rating) else "—")

    # --- Tracking starten ---
    st.markdown("---")
    st.subheader("3️⃣ Zum Tracking hinzufügen")

    n_selected = len(selected_indices)
    n_already = sum(1 for i in selected_indices if df.loc[i, "already_tracked"])
    n_new = n_selected - n_already

    st.info(f"📋 **{n_selected}** Produkte ausgewählt ({n_new} neu, {n_already} Updates)")

    track_clicked = st.button(
        f"🚀 {n_selected} Produkte zum Tracking hinzufügen",
        type="primary",
        use_container_width=True,
        disabled=n_selected == 0,
    )

    if track_clicked and n_selected > 0:
        selected_df = df.loc[selected_indices].copy()
        # Pipeline-irrelevante Spalten entfernen
        drop_cols = ["already_tracked", "prev_position", "prev_price", "prev_rating",
                     "prev_reviews", "prev_bsr", "prev_timestamp", "price_clean",
                     "reviews_num", "pos_delta", "price_delta", "rating_delta", "reviews_delta"]
        selected_df = selected_df.drop(columns=[c for c in drop_cols if c in selected_df.columns])

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
