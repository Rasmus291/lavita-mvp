"""
KPI-Berechnung und Wettbewerbs-Score (CIS).
"""
import numpy as np
import pandas as pd
from cleaner import clean_price


def process(df: pd.DataFrame) -> pd.DataFrame:
    """
    Bereinigt Preise, berechnet est_orders und CIS-Score.
    Gibt den angereicherten DataFrame zurück.
    """
    if df.empty:
        return df

    df["price_clean"] = df["price"].apply(clean_price)
    df["reviews"] = pd.to_numeric(df["reviews"], errors="coerce").fillna(0)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["est_orders"] = (df["reviews"] * 20).astype(int)

    df = _add_competition_score(df)
    return df


def _add_competition_score(df: pd.DataFrame) -> pd.DataFrame:
    """Berechnet CIS (Competition Impact Score) – 40% Rating, 40% Volumen, 20% Preis."""
    max_rev = df["reviews"].max() if df["reviews"].max() > 0 else 1
    min_price = df["price_clean"].min() if df["price_clean"].min() > 0 else 1

    df["norm_rating"] = df["rating"] / 5.0
    df["norm_volume"] = np.log1p(df["reviews"]) / np.log1p(max_rev)
    df["norm_price"] = min_price / df["price_clean"]

    df["cis_score"] = (
        (df["norm_rating"] * 0.4)
        + (df["norm_volume"] * 0.4)
        + (df["norm_price"] * 0.2)
    )
    return df


def calculate_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Berechnet zusammengefasste KPIs für den gesamten DataFrame."""
    if df.empty:
        return pd.DataFrame()

    kpis = {
        "avg_price": df["price_clean"].mean(),
        "avg_rating": df["rating"].mean(),
        "avg_cis_score": df["cis_score"].mean(),
        "avg_reviews": df["reviews"].mean(),
        "total_products": len(df),
        "grade_1_comp": len(df[df["competition_grade"] == 1]),
        "top_sellers_est": len(df[df["reviews"] >= 1000]),
        "total_est_orders": df["est_orders"].sum(),
        "avg_position": df["position"].mean(),
        "avg_bsr": df["bsr"].mean() if "bsr" in df.columns else None,
    }
    return pd.DataFrame([kpis])
