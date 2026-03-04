import os
import re
import pandas as pd

from trendanalyse import TrendAnalyzer
class TrendTracker(TrendAnalyzer):
    """Alias für einfachere Nutzung"""
    pass

    def compare_with_last_run(self):
        """Vergleicht aktuellen Scraping-Lauf mit dem vorherigen."""
        if not os.path.exists(self.master_data_file):
            return None
            
        master = pd.read_csv(self.master_data_file)
        timestamps = sorted(master["timestamp"].unique())
        
        if len(timestamps) < 2:
            return None
            
        prev_date = timestamps[-2]  # Letzte Run
        curr_date = timestamps[-1]   # Dieser Run
        
        df_prev = master[master["timestamp"] == prev_date]
        df_curr = master[master["timestamp"] == curr_date]
        
        comp = self.compare_to_previous_period(df_curr, df_prev)
        
        # Speichere Report
        comp.to_csv("data/competitor_comparison.csv", index=False)
        
        return comp