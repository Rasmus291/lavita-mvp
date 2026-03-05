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

<<<<<<< HEAD
    return df[mask_format & mask_no_capsules & mask_reviews & mask_price]


def apply_lavita_relevance_filter(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Filtert Produkte auf LaVita-Relevanz:
    Nur flüssige Nahrungsergänzungsmittel, keine Kapseln/Tabletten/Tier-/Garten-Produkte.
    Gibt (gefilterter_df, anzahl_vorher) zurück.
    """
    total_before = len(df)
    if df.empty:
        return df, total_before

    title = df["title"].str.lower().fillna("")

    # AUSSCHLUSS 1 – Tierprodukte
    mask_no_pets = ~title.str.contains(
        r"hund|katze|pferd|tier|haustier|dog|cat|horse|pet|animal|welpe|kitten",
        case=False, na=False
    )

    # AUSSCHLUSS 2 – Säfte / reine Getränke
    mask_no_juice = ~title.str.contains(
        r"\bsaft\b|fruchtsaft|orangensaft|apfelsaft|traubensaft|smoothie|limonade|eistee",
        case=False, na=False
    )

    # AUSSCHLUSS 3 – Sport-Supplements
    mask_no_sports = ~title.str.contains(
        r"whey|protein.?pulver|kreatin|creatine|bcaa|pre.?workout|mass.?gainer|aminosäure|amino acid",
        case=False, na=False
    )

    # AUSSCHLUSS 4 – Kollagen / Kosmetik
    mask_no_collagen = ~title.str.contains(
        r"kollagen|collagen|hyaluron|anti.?aging|hautpflege|skin.?care|beauty.?drink",
        case=False, na=False
    )

    # AUSSCHLUSS 5 – Fitness-Getränke
    mask_no_fitness = ~title.str.contains(
        r"energy.?drink|iso.?drink|elektrolyt|sports?.?drink|recovery.?drink",
        case=False, na=False
    )

    # AUSSCHLUSS 6 – Baby / Kleinkind
    mask_no_baby = ~title.str.contains(
        r"baby|säugling|kleinkind|infant|toddler|babynahrung|folgemilch",
        case=False, na=False
    )

    # AUSSCHLUSS 7 – Garten / Schädlingsbekämpfung
    mask_no_garden = ~title.str.contains(
        r"schädling|pflanzenschutz|insektizid|pestizid|dünger|garten|rasen|unkraut|neem\s*öl|neemöl",
        case=False, na=False
    )

    # AUSSCHLUSS 8 – Kapseln / Tabletten / Pillen
    mask_no_pills = ~title.str.contains(
        r"kapsel|kapseln|capsule|capsules|tablette|tabletten|tablet|tablets|"
        r"pillen|pills|dragee|dragees|softgel|softgels|"
        r"gummies|gummibärchen|pastillen|lutschtabletten|kautabletten|brausetabletten",
        case=False, na=False
    )

    # RELEVANZ – muss Supplement-Keyword enthalten
    mask_supplement = title.str.contains(
        r"vitamin|mineral|mikronährstoff|nahrungsergänzung|supplement|"
        r"multivitamin|nährstoff|vitalstoff|konzentrat|immunsystem|"
        r"spurenelement|vitalstoffe|multimineral|gesundheit|immun",
        case=False, na=False
    )

    combined = (
        mask_no_pets & mask_no_juice & mask_no_sports & mask_no_collagen
        & mask_no_fitness & mask_no_baby & mask_no_garden & mask_no_pills
        & mask_supplement
    )

    filtered = df[combined].copy()

    excluded_count = total_before - len(filtered)
    if excluded_count > 0:
        print(f"  LaVita-Relevanzfilter: {excluded_count} von {total_before} Produkten ausgeschlossen")

    return filtered, total_before
=======
    return df[mask_reviews & mask_price]
>>>>>>> 2366af1431db930f68a052f556dbeb5161179b91
