"""
Einstiegspunkt: Startet die ETL-Pipeline.
"""
from config import SERPAPI_KEY, KEYWORDS
from pipeline import run_full_pipeline

if __name__ == "__main__":
    kpis = run_full_pipeline(api_key=SERPAPI_KEY, keywords=KEYWORDS)
    print("\n📊 Aktuelle KPIs:")
    print(kpis)