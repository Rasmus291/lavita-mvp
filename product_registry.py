"""
Produkt-Registry: Verwaltet eindeutige Produkt-IDs basierend auf ASIN.
Erkennt neue vs. bereits bekannte Produkte.
"""
import os
import pandas as pd
from datetime import datetime

REGISTRY_FILE = "data/product_registry.csv"

REGISTRY_COLUMNS = ["product_id", "asin", "first_seen", "title", "brand"]


def _load_registry() -> pd.DataFrame:
    """Lädt die bestehende Registry oder erstellt eine leere."""
    if os.path.exists(REGISTRY_FILE):
        return pd.read_csv(REGISTRY_FILE)
    return pd.DataFrame(columns=REGISTRY_COLUMNS)


def _save_registry(registry: pd.DataFrame):
    """Speichert die Registry."""
    os.makedirs("data", exist_ok=True)
    registry.to_csv(REGISTRY_FILE, index=False)


def _next_product_id(registry: pd.DataFrame) -> str:
    """Generiert die nächste Produkt-ID (P0001, P0002, ...)."""
    if registry.empty:
        return "P0001"
    max_id = registry["product_id"].str.extract(r"P(\d+)").astype(int).max().iloc[0]
    return f"P{max_id + 1:04d}"


def assign_product_ids(df: pd.DataFrame) -> pd.DataFrame:
    """
    Weist jedem Produkt im DataFrame eine eindeutige product_id zu.
    Neue Produkte bekommen eine neue ID + is_new=True.
    Bekannte Produkte (gleiche ASIN) bekommen ihre bestehende ID + is_new=False.

    Gibt den angereicherten DataFrame zurück und aktualisiert die Registry.
    """
    if df.empty:
        df["product_id"] = []
        df["first_seen"] = []
        df["is_new"] = []
        return df

    registry = _load_registry()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    product_ids = []
    is_new_flags = []
    first_seen_dates = []
    new_entries = []

    for _, row in df.iterrows():
        asin = row.get("asin")
        match = registry[registry["asin"] == asin]

        if not match.empty:
            # Bekanntes Produkt
            product_ids.append(match.iloc[0]["product_id"])
            first_seen_dates.append(match.iloc[0]["first_seen"])
            is_new_flags.append(False)
        else:
            # Neues Produkt
            pid = _next_product_id(registry)
            product_ids.append(pid)
            first_seen_dates.append(now)
            is_new_flags.append(True)

            new_entry = {
                "product_id": pid,
                "asin": asin,
                "first_seen": now,
                "title": str(row.get("title", ""))[:120],
                "brand": row.get("brand", ""),
            }
            new_entries.append(new_entry)

            # Zur Registry hinzufügen (damit nächste Zeile mit gleicher ASIN erkannt wird)
            registry = pd.concat(
                [registry, pd.DataFrame([new_entry])], ignore_index=True
            )

    df["product_id"] = product_ids
    df["first_seen"] = first_seen_dates
    df["is_new"] = is_new_flags

    if new_entries:
        _save_registry(registry)
        print(f"   🆕 {len(new_entries)} neue Produkte registriert, {len(df) - len(new_entries)} bekannte Produkte erkannt.")
    else:
        print(f"   ✅ Alle {len(df)} Produkte bereits bekannt.")

    return df


def get_registry() -> pd.DataFrame:
    """Gibt die aktuelle Registry zurück."""
    return _load_registry()


def get_product_count() -> int:
    """Gibt die Anzahl registrierter Produkte zurück."""
    registry = _load_registry()
    return len(registry)
