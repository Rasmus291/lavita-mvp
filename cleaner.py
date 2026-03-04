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
    Filtert Produkte nach Format (flüssig/pulver), schließt Kapseln aus,
    und wendet Mindest-Reviews + Preis-Checks an.
    """
    df = df.dropna(subset=["title"])

    # Format: Flüssig/Saft/Konzentrat/Pulver
    mask_format = df["title"].str.contains(
        "flüssig|saft|konzentrat|pulver|trinkpulver", case=False, na=False
    )

    # Ausschluss: Kapseln
    mask_no_capsules = ~df["title"].str.contains(
        "kapsel|kapseln|capsule|capsules", case=False, na=False
    )

    # Mindestreviews (>50)
    mask_reviews = df["reviews"].fillna(0) > 50

    # Preis vorhanden
    mask_price = df["price"].notnull()

    return df[mask_format & mask_no_capsules & mask_reviews & mask_price]
