import pandas as pd
import numpy as np
class TrendAnalyzer:
    """
    Berechnet Zeitvergleiche und Ranking-Bewegungen.
    Spiegelt die Logik aus dem Marktbericht wider (vgl. 18.11.25, YOY).
    """
    
    def compare_to_previous_period(self, df_current: pd.DataFrame, df_history: pd.DataFrame) -> pd.DataFrame:
        """
        Vergleicht aktuelle Daten mit historischem Datensatz.
        """
        if df_history.empty:
            return df_current.assign(
                mom_change=0, rank_shift=0
            )
        
        # Aggregiere nach ASIN (eindeutige Produkt-ID)
        curr_agg = df_current.groupby("asin").agg({
            "price_clean": "mean",
            "reviews": "sum",
            "rating": "mean"
        }).reset_index()
        
        hist_agg = df_history.groupby("asin").agg({
            "reviews": "sum",
            "price_clean": "mean"
        }).reset_index()
        
        # Merge für Vergleich
        merged = curr_agg.merge(hist_agg, on="asin", how="left", suffixes=("_now", "_prev"))
        
        # Berechne Veränderungen
        merged["review_mom_pct"] = (
            (merged["reviews_now"] - merged["reviews_prev"]) / 
            merged["reviews_prev"].replace(0, np.nan) * 100
        ).fillna(0)
        
        return merged
    
    def calculate_rank_shifts(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Berechnet Ranking-Bewegung basierend auf Bestseller-Rang.
        """
        # Sortiere nach ASIN und nimm den besten Rang pro Produkt
        df_sorted = df.sort_values(by=["asin", "position"])
        df_best = df_sorted.drop_duplicates(subset=["asin"], keep="first")
        
        # Gruppiere nach Timestamp für Zeitvergleich
        # Beispiel: Shift = Aktueller Rang - Historischer Rang
        # (Requiremaster_data.csv mit früherem Timestamp exists)
        
        return df_best