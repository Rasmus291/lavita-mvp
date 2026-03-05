"""
Produkt-Ähnlichkeits-Klassifikation (5 Kategorien).

Nutzt zwei Signale:
  1. Buzzword-Analyse (Keywords im Produkttitel)
  2. Browse-Node-Auswertung (Amazon-Kategorien aus BSR-Scraping)

Kategorien (1 = nah an LaVita, 5 = weit entfernt):
  1 = Flüssiges Multivitaminkonzentrat mit Mikronährstoffen
  2 = Multivitamin-Pulver zum Trinken mit Mikronährstoffen
  3 = Multivitamin-Kapseln/-Tabletten mit Mikronährstoffen
  4 = Allgemeines NEM-Pulver/Drink (kein Multivitamin)
  5 = Sonstige NEM, Vitamine, Lifestyle-Health-Produkte
"""
import ast
from typing import Optional


# ── Buzzword-Listen (pro Kategorie ergänzbar) ──────────────────────────

# Keywords die auf Multivitamin/Mikronährstoff hinweisen
MULTI_KEYWORDS = [
    "multivitamin", "mikronährstoff", "mikronährstoffkonzentrat",
    "multi vitamin", "vitalkomplex", "vital komplex",
    # → Hier weitere ergänzen
]

# Darreichungsform-Keywords
FORM_LIQUID = [
    "flüssig", "liquid", "konzentrat", "saft", "tropfen", "elixier",
    # → Hier weitere ergänzen
]
FORM_POWDER = [
    "pulver", "trinkpulver", "powder", "drink mix", "trinkgranulat",
    # → Hier weitere ergänzen
]
FORM_CAPSULE = [
    "kapsel", "kapseln", "capsule", "capsules",
    "tablette", "tabletten", "tablet", "tablets",
    "dragee", "softgel",
    # → Hier weitere ergänzen
]

# Keywords für allgemeine NEM (Kategorie 4)
NEM_KEYWORDS = [
    "nahrungsergänzung", "nahrungsergänzungsmittel", "supplement",
    "ergänzungsmittel", "vitamin", "mineral", "immunsystem",
    # → Hier weitere ergänzen
]

# Ausschluss-Keywords (z.B. reine Fruchtsäfte → keine NEM)
EXCLUDE_KEYWORDS = [
    "100% saft", "100% fruchtsaft", "fruchtsaft", "fruchtgehalt",
    "orangensaft", "apfelsaft",
    # → Hier weitere ergänzen
]


# ── Browse-Node-Listen ──────────────────────────────────────────────────

# Browse Nodes die auf Nahrungsergänzung/Supplement hinweisen
SUPPLEMENT_NODES = [
    "multivitaminpräparate", "mineralien", "nahrungsergänzung",
    "vitamine", "aminosäure",
    # → Hier weitere ergänzen
]

# Browse Nodes die GEGEN NEM sprechen (reine Getränke/Lebensmittel)
NON_SUPPLEMENT_NODES = [
    "fruchtsäfte", "softdrinks",
    # → Hier weitere ergänzen
]


# ── Hauptlogik ──────────────────────────────────────────────────────────

def classify(title: str, bsr_categories: Optional[str] = None) -> int:
    """
    Klassifiziert ein Produkt in Kategorie 1-5.
    
    Bottom-Up-Logik: Jedes Produkt startet bei Kat 5 (Sonstige).
    Dann wird schrittweise geprüft ob es in eine höhere Kategorie gehört:
      5 → 4 → 3 → 2 → 1

    Args:
        title: Produkttitel
        bsr_categories: String-Repr. eines Dicts, z.B. "{'Kategorie': Rang}"

    Returns:
        Kategorie 1-5
    """
    t = title.lower()
    nodes = _parse_browse_nodes(bsr_categories)

    # ── Signale ermitteln ──
    is_multi = _has_any(t, MULTI_KEYWORDS)
    is_liquid = _has_any(t, FORM_LIQUID)
    is_powder = _has_any(t, FORM_POWDER)
    is_capsule = _has_any(t, FORM_CAPSULE)
    is_nem = _has_any(t, NEM_KEYWORDS)
    is_excluded = _has_any(t, EXCLUDE_KEYWORDS)

    is_supplement_node = _node_match(nodes, SUPPLEMENT_NODES)
    is_juice_node = _node_match(nodes, NON_SUPPLEMENT_NODES) and not is_supplement_node

    # ── Start: Kat 5 (Sonstige) ──
    grade = 5

    # ── Hochstufen auf Kat 4: NEM-Pulver/Drink? ──
    if is_nem and (is_powder or is_liquid) and not is_excluded:
        grade = 4
    elif is_supplement_node and (is_powder or is_liquid) and not is_excluded:
        grade = 4

    # ── Hochstufen auf Kat 3: Multivitamin-Kapsel? ──
    if is_multi and is_capsule:
        grade = 3
    elif is_multi and not is_liquid and not is_powder and not is_capsule:
        # Multivitamin ohne erkennbare Darreichungsform → Kat 3 als Default
        grade = 3

    # ── Hochstufen auf Kat 2: Multivitamin-Pulver? ──
    if is_multi and is_powder:
        grade = 2

    # ── Hochstufen auf Kat 1: Flüssiges Multivitaminkonzentrat? ──
    if is_multi and is_liquid:
        grade = 1

    # ── Herabstufen: Fruchtsäfte ohne Supplement-Node bleiben Kat 5 ──
    if is_excluded and not is_supplement_node:
        grade = 5
    if is_juice_node and not is_multi:
        grade = 5

    return grade


def classify_product(row) -> int:
    """Row-basierte Klassifikation für df.apply()."""
    title = str(row.get("title", ""))
    bsr_cat = row.get("bsr_categories", None)
    if isinstance(bsr_cat, float):  # NaN
        bsr_cat = None
    return classify(title, str(bsr_cat) if bsr_cat is not None else None)


# ── Hilfsfunktionen ────────────────────────────────────────────────────

def _parse_browse_nodes(bsr_categories) -> list:
    """Parst bsr_categories-String zu Liste von Kategorienamen (lowercase)."""
    if bsr_categories is None or isinstance(bsr_categories, float):
        return []
    try:
        if isinstance(bsr_categories, str):
            cat_dict = ast.literal_eval(bsr_categories)
        elif isinstance(bsr_categories, dict):
            cat_dict = bsr_categories
        else:
            return []
        return [k.lower() for k in cat_dict.keys()]
    except (ValueError, SyntaxError):
        return []


def _has_any(text: str, keywords: list) -> bool:
    """Prüft ob mindestens ein Keyword im Text vorkommt."""
    return any(kw in text for kw in keywords)


def _node_match(nodes: list, node_keywords: list) -> bool:
    """Prüft ob mindestens ein Browse-Node-Keyword in der Node-Liste vorkommt."""
    return any(
        any(nk in node for nk in node_keywords)
        for node in nodes
    )