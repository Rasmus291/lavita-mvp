"""
Zentrale Konfiguration: API-Key, Keywords, Dateipfade.
"""
import os
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

MASTER_DATA_FILE = "data/master_data.csv"
RAW_DATA_FILE = "data/raw_data.csv"
FILTERED_DATA_FILE = "data/filtered_classified.csv"
KPI_DATA_FILE = "data/kpis.csv"
REGISTRY_FILE = "data/product_registry.csv"

# Keywords basierend auf Studie: Trend zu flüssig/Konzentrate
KEYWORDS = [
    "Multivitamin Saft",
    "Vitamin Komplex Flüssig",
    "Nahrungsergänzung Flüssig",
    "Immunsystem Vitamine",
    "Mikronährstoffkonzentrat Amazon",
]
