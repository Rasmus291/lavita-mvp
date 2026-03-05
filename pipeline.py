"""
ETL-Pipeline: Orchestriert Scraping → Filter → Klassifikation → BSR → KPIs → Speichern.
"""
import os
import pandas as pd
from config import MASTER_DATA_FILE, RAW_DATA_FILE, FILTERED_DATA_FILE, KPI_DATA_FILE
from scraper import scrape_keyword
from bsr_scraper import enrich_with_bsr
from cleaner import apply_filters
from classifier import classify, classify_product
from product_registry import assign_product_ids
import calculator


def run_full_pipeline(api_key: str, keywords: list, save_interim: bool = True) -> pd.DataFrame:
    """
    Führt den kompletten ETL-Prozess durch:
    1. Scraping (SerpAPI)
    2. Filter & Clean
    3. Klassifikation
    4. BSR anreichern (direkt von Amazon.de)
    5. KPIs berechnen
    6. An master_data.csv anhängen
    """
    print("🔄 Starte Pipeline...")

    # 1. Scraping
    all_data = []
    for kw in keywords:
        print(f"   -> Scraping: {kw}")
        all_data.extend(scrape_keyword(api_key, kw))

    raw_data = pd.DataFrame(all_data)

    os.makedirs("data", exist_ok=True)
    raw_data.to_csv(RAW_DATA_FILE, index=False)

    # 2. Filter & Clean
    filtered_data = apply_filters(raw_data)

    # 3. Produkt-IDs zuweisen (neue vs. bekannte Produkte)
    print("🔍 Produkt-IDs zuweisen...")
    filtered_data = assign_product_ids(filtered_data)

    # 4. BSR-Daten anreichern (VOR Klassifikation, da Browse-Nodes benötigt)
    print("📦 BSR-Daten abrufen...")
    filtered_data = enrich_with_bsr(filtered_data)

    # 5. Klassifikation (nutzt Title + Browse-Nodes)
    filtered_data["competition_grade"] = filtered_data.apply(classify_product, axis=1)

    if save_interim:
        filtered_data.to_csv(FILTERED_DATA_FILE, index=False)

    # 5. KPIs berechnen
    processed_df = calculator.process(filtered_data)
    kpi_data = calculator.calculate_kpis(processed_df)
    kpi_data.to_csv(KPI_DATA_FILE, index=False)

    # 6. Zeitreihen-Tracking (Append)
    if os.path.exists(MASTER_DATA_FILE):
        old = pd.read_csv(MASTER_DATA_FILE)
        master = pd.concat([old, processed_df], ignore_index=True)
    else:
        master = processed_df

    master.to_csv(MASTER_DATA_FILE, index=False)

    print("✅ Pipeline abgeschlossen.")
    return kpi_data


def run_manual_pipeline(selected_df: pd.DataFrame, skip_bsr: bool = False,
                        bsr_progress_callback=None) -> pd.DataFrame:
    """
    Pipeline für manuell ausgewählte Produkte (kein Scraping, kein Filter).
    1. Produkt-IDs zuweisen
    2. BSR anreichern (optional, kann übersprungen werden)
    3. Klassifikation
    4. KPIs berechnen
    5. An master_data.csv anhängen

    Gibt den verarbeiteten DataFrame zurück.
    """
    if selected_df.empty:
        return selected_df

    os.makedirs("data", exist_ok=True)

    print("🔄 Manuelle Pipeline gestartet...")

    # 1. Produkt-IDs zuweisen
    selected_df = selected_df.copy()
    print("🔍 Produkt-IDs zuweisen...")
    selected_df = assign_product_ids(selected_df)

    # 2. BSR-Daten anreichern (optional)
    if not skip_bsr:
        print("📦 BSR-Daten abrufen...")
        selected_df = enrich_with_bsr(selected_df, progress_callback=bsr_progress_callback)
    else:
        print("⏭️ BSR-Scraping übersprungen.")
        # Leere BSR-Spalten setzen, falls noch nicht vorhanden
        for col in ["bsr", "bsr_categories"]:
            if col not in selected_df.columns:
                selected_df[col] = None
        if "brand" not in selected_df.columns:
            selected_df["brand"] = None

    # 3. Klassifikation (nutzt Title + Browse-Nodes)
    selected_df["competition_grade"] = selected_df.apply(classify_product, axis=1)

    # 4. KPIs berechnen
    processed_df = calculator.process(selected_df)

    # 5. An master_data.csv anhängen
    if os.path.exists(MASTER_DATA_FILE):
        old = pd.read_csv(MASTER_DATA_FILE)
        master = pd.concat([old, processed_df], ignore_index=True)
    else:
        master = processed_df

    master.to_csv(MASTER_DATA_FILE, index=False)

    print("✅ Manuelle Pipeline abgeschlossen.")
    return processed_df
