"""
Datenbereinigung und Produktfilter.
"""
import re
import pandas as pd


def clean_price(price) -> float | None:
    """Bereinigt Preisstrings zu float-Werten."""
    if pd.isna(price):
        return None
    price_str = re.sub(r"[^\d,\.]", "", str(price))
    price_str = price_str.replace(",", ".")
    try:
        return float(price_str)
    except ValueError:
        return None


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filtert Produkte: Basis-Qualitätsfilter (Reviews, Preis).
    Format-Filterung entfällt – die Klassifikation (classifier.py) übernimmt
    die Einordnung in die 5 Ähnlichkeits-Kategorien.
    """
    df = df.dropna(subset=["title"])

    # Mindestreviews (>50)
    mask_reviews = df["reviews"].fillna(0) > 50

    # Preis vorhanden
    mask_price = df["price"].notnull()

    return df[mask_reviews & mask_price]
