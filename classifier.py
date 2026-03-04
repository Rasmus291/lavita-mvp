"""
Wettbewerbs-Grad-Klassifikation basierend auf Produkt-Titel.
"""


def classify_product(row):
    """Klassifiziert ein Produkt anhand des Titels (row-basiert, für df.apply)."""
    title = str(row["title"]).lower()
    return classify(title)


def classify(title: str) -> int:
    """
    Klassifiziert einen Produkttitel in Wettbewerbs-Grade 1-5.
    
    1 = Direkter Wettbewerber (Flüssig/Konzentrat)
    2 = Spezialisierte Komplexe (Immun, B-Komplex)
    3 = Standard Vitamine
    4 = Nahrungsergänzung allgemein
    5 = Sonstige
    """
    t = title.lower()

    # 1. FLÜSSIG MULTIVITAMIN (Direkte Wettbewerber - HIGH PRIORITY)
    if "multivitamin" in t and "flüssig" in t:
        return 1
    elif "multivitamin" in t and "konzentrat" in t:
        return 1

    # 2. SPEZIALISIERTE KOMPLEXE (Immun, B-Komplex)
    elif "vitamin komplex" in t or "immun" in t:
        return 2

    # 3. STANDARD VITAMINE (einfache Erwähnung)
    elif "vitamin" in t or "mineral" in t:
        return 3

    # 4. NAHRUNGSERGÄNZUNG ALLGEMEIN
    elif "nahrungsergänzung" in t or "ergänzung" in t:
        return 4

    else:
        return 5