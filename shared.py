"""
Shared-Modul: Daten laden, aufbereiten und filtern.
Wird von app.py und allen Pages importiert.
"""
import streamlit as st
import pandas as pd
import os

DATA_FILE = "data/master_data.csv"

GRADE_LABELS = {
    1: "🥇 Kat 1 – Flüssig-Konzentrat",
    2: "🥈 Kat 2 – Pulver-Multi",
    3: "🥉 Kat 3 – Kapsel-Multi",
    4: "4️⃣ Kat 4 – NEM-Drink/Pulver",
    5: "5️⃣ Kat 5 – Sonstige NEM",
}

STYLE_CSS = """
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .rank-high {color: green; font-weight: bold;}
    .rank-low {color: red; font-weight: bold;}
    /* Hauptseiten-Link (app) in der Sidebar ausblenden */
    [data-testid="stSidebarNav"] > ul > li:first-child { display: none; }
</style>
"""


@st.cache_data(ttl=60)
def load_raw_data(path=DATA_FILE):
    """Lädt die Rohdaten aus der CSV."""
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


def prepare_data(df):
    """Bereinigt und ergänzt fehlende Spalten."""
    if df is None or df.empty:
        return df

    # Nur vergangene/aktuelle Daten (keine Zukunfts-Timestamps)
    now = pd.Timestamp.now()
    df = df[df["timestamp"] <= now].copy()

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

    if "brand" in df.columns:
        df["brand"] = (
            df["brand"]
            .astype(str)
            .str.replace(r'&lrm;|&rlm;', '', regex=True)
            .replace('nan', None)
        )

    return df


def get_data():
    """Hauptfunktion: Lädt und bereitet Daten auf. Nutze diese in jeder Page."""
    raw = load_raw_data()
    return prepare_data(raw)


def get_latest_values(asins: list) -> pd.DataFrame:
    """
    Holt die letzten bekannten Werte aus master_data.csv für eine Liste von ASINs.
    Gibt einen DataFrame mit den neuesten Werten pro ASIN zurück.
    Spalten: asin, prev_position, prev_price, prev_rating, prev_reviews, prev_bsr, prev_timestamp
    """
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=["asin"])

    df = pd.read_csv(DATA_FILE)
    if df.empty or "asin" not in df.columns:
        return pd.DataFrame(columns=["asin"])

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df[df["asin"].isin(asins)]

    if df.empty:
        return pd.DataFrame(columns=["asin"])

    # Pro ASIN die neueste Zeile nehmen
    df = df.sort_values("timestamp", ascending=False).drop_duplicates(subset=["asin"], keep="first")

    rename_map = {
        "position": "prev_position",
        "price_clean": "prev_price",
        "rating": "prev_rating",
        "reviews": "prev_reviews",
        "bsr": "prev_bsr",
        "timestamp": "prev_timestamp",
    }
    keep_cols = ["asin"] + [c for c in rename_map.keys() if c in df.columns]
    result = df[keep_cols].rename(columns=rename_map)
    return result


def render_sidebar_filters(df):
    """
    Rendert die Sidebar-Filter und gibt (df_view, date_opt) zurück.
    df_view = gefilterter DataFrame für die aktuelle Ansicht.
    """
    st.sidebar.header("⚙️ Filter-Einstellungen")

    # Datum
    date_options = sorted(df['timestamp'].unique(), reverse=True)
    date_opt = st.sidebar.selectbox("Scan-Datum", options=date_options, index=0)

    df_slice = df[df['timestamp'] == date_opt]
    df_slice = df_slice.sort_values('position')

    df_view = df_slice.copy()

    # BSR
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
        st.sidebar.info("🏆 BSR-Daten noch nicht verfügbar. Starte `python main.py` erneut.")

    return df_view, date_opt


def get_latest_values(asins: list) -> pd.DataFrame:
    """
    Gibt die letzten bekannten Werte für eine Liste von ASINs zurück.
    Wird in der Produkt-Suche genutzt um Deltas zu berechnen.
    """
    raw = load_raw_data()
    if raw is None or raw.empty:
        return pd.DataFrame()

    # Nur ASINs die wir kennen
    df = raw[raw["asin"].isin(asins)].copy()
    if df.empty:
        return pd.DataFrame()

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp", ascending=False)

    # Letzten Eintrag pro ASIN
    latest = df.drop_duplicates(subset=["asin"], keep="first")

    from cleaner import clean_price

    result = latest[["asin"]].copy()
    result["prev_position"] = latest["position"].values
    result["prev_price"] = latest["price"].apply(clean_price).values
    result["prev_rating"] = pd.to_numeric(latest["rating"], errors="coerce").values
    result["prev_reviews"] = pd.to_numeric(latest["reviews"], errors="coerce").values
    result["prev_bsr"] = pd.to_numeric(latest.get("bsr", pd.Series(dtype=float)), errors="coerce").values if "bsr" in latest.columns else None
    result["prev_timestamp"] = latest["timestamp"].values

    return result
