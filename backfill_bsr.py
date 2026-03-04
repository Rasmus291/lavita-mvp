"""
Einmaliges Script: Bestehende master_data.csv mit BSR-Werten anreichern.
Verbraucht KEINE SerpAPI-Credits – scrapt direkt von Amazon.de.
"""
import pandas as pd
import requests
import re
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def scrape_bsr(asin: str) -> int | None:
    url = f"https://www.amazon.de/dp/{asin}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        html = resp.text
        patterns = [
            r'Amazon[\s\-]*Bestseller[\s\-]*Rang.*?Nr\.?\s*([0-9.]+)\s+in\s',
            r'<th[^>]*>\s*Amazon\s*Bestseller-Rang\s*</th>.*?Nr\.?\s*([0-9.]+)\s+in\s',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                rank_str = match.group(1).replace(".", "").replace(",", "")
                try:
                    return int(rank_str)
                except ValueError:
                    continue
        return None
    except Exception as e:
        print(f"  Fehler für {asin}: {e}")
        return None


if __name__ == "__main__":
    master_file = "data/master_data.csv"
    df = pd.read_csv(master_file)
    
    # Eindeutige ASINs holen
    unique_asins = df["asin"].dropna().unique()
    print(f"📦 BSR abrufen für {len(unique_asins)} eindeutige ASINs...")
    
    bsr_map = {}
    for i, asin in enumerate(unique_asins):
        print(f"  [{i+1}/{len(unique_asins)}] {asin}", end=" ")
        bsr = scrape_bsr(asin)
        bsr_map[asin] = bsr
        print(f"-> BSR: {bsr}")
        time.sleep(1.5)
    
    # BSR in DataFrame eintragen
    df["bsr"] = df["asin"].map(bsr_map)
    
    filled = df["bsr"].notna().sum()
    print(f"\n✅ {filled}/{len(df)} Zeilen mit BSR gefüllt.")
    
    # Speichern
    df.to_csv(master_file, index=False)
    print(f"💾 {master_file} gespeichert.")
    
    # Auch filtered_classified.csv aktualisieren
    filtered_file = "data/filtered_classified.csv"
    try:
        df_filtered = pd.read_csv(filtered_file)
        df_filtered["bsr"] = df_filtered["asin"].map(bsr_map)
        df_filtered.to_csv(filtered_file, index=False)
        print(f"💾 {filtered_file} gespeichert.")
    except Exception:
        pass
