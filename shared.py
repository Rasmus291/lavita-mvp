"""
Shared-Modul: Daten laden, aufbereiten und filtern.
Wird von app.py und allen Pages importiert.
"""
import streamlit as st
import pandas as pd
import os

DATA_FILE = "data/master_data.csv"

GRADE_LABELS = {
    1: "🥇 Direkt (Flüssig)",
    2: "🥈 Komplex",
    3: "🥉 Standard",
    4: "4. Sonstige",
    5: "5. Sonstige"
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
    df_slice = df_slice.sort_values('position').drop_duplicates(subset=['asin'], keep='first')

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
