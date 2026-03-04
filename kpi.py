import pandas as pd
import numpy as np
import re


class MarketDataProcessor:
    """
    Verarbeitet Rohdaten von Amazon-Suchergebnissen:
    - Preisbereinigung
    - Typkonvertierung
    - KPI-Berechnung
    """

    def __init__(self):
        pass

    @staticmethod
    def clean_price(price):
        """
        Bereinigt Preisangaben (Entfernt Währungssymbole, wandelt Komma in Punkt um).
        """
        if pd.isna(price):
            return None
        
        # Alle Zeichen außer Zahlen, Punkt und Komma entfernen
        price_str = re.sub(r"[^\d,\.]", "", str(price))
        
        # Komma in Punkt umwandeln (für deutsche Schreibweise)
        price_str = price_str.replace(",", ".")
        
        try:
            return float(price_str)
        except ValueError:
            return None

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Hauptmethode: Führt alle Transformationen auf einen Schlag durch.
        """
        if df.empty:
            return df

        # 1. Spalte 'price_clean' erstellen
        df["price_clean"] = df["price"].apply(self.clean_price)

        # 2. Reviews & Rating in numerische Werte umwandeln
        df["reviews"] = pd.to_numeric(df["reviews"], errors="coerce").fillna(0)
        df["rating"] = pd.to_numeric(df["rating"], error="coerce")

        return df

    def calculate_kpis(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Berechnet Kennzahlen basierend auf den verarbeiteten Daten.
        """
        if df.empty:
            return pd.DataFrame()

        # Stelle sicher, dass Daten verarbeitet wurden
        if "price_clean" not in df.columns:
            df = self.process(df)

        kpis = {
            "avg_price": df["price_clean"].mean(),
            "median_price": df["price_clean"].median(),
            "min_price": df["price_clean"].min(),
            "max_price": df["price_clean"].max(),
            
            "avg_rating": df["rating"].mean(),
            "avg_reviews": df["reviews"].mean(),
            "total_reviews": df["reviews"].sum(),
            
            "total_products": len(df),
            "grade_1_count": len(df[df["competition_grade"] == 1]),
            "grade_2_count": len(df[df["competition_grade"] == 2]),
            "grade_3_count": len(df[df["competition_grade"] == 3]),
        }

        return pd.DataFrame([kpis])


# --- Anwendung ---
if __name__ == "__main__":
    # Beispielhafte Anwendung
    processor = MarketDataProcessor()
    
    # Daten laden (dein Scraping-Ergebnis)
    # df = pd.read_csv("data/filtered_classified.csv")
    
    # Verarbeitung
    # df_processed = processor.process(df)
    
    # KPIs holen
    # kpi_result = processor.calculate_kpis(df_processed)
    # print(kpi_result)