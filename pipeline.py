"""
ETL-Pipeline: Orchestriert Scraping → Filter → Klassifikation → BSR → KPIs → Speichern.
"""
import os
import pandas as pd
from config import MASTER_DATA_FILE, RAW_DATA_FILE, FILTERED_DATA_FILE, KPI_DATA_FILE
from scraper import scrape_keyword
from bsr_scraper import enrich_with_bsr
from cleaner import apply_filters
from classifier import classify
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

    # 3. Klassifikation
    filtered_data["competition_grade"] = filtered_data["title"].apply(
        lambda t: classify(str(t))
    )

    # 4. BSR-Daten anreichern
    print("📦 BSR-Daten abrufen...")
    filtered_data = enrich_with_bsr(filtered_data)

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
