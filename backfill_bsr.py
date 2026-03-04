"""
Einmaliges Script: Bestehende master_data.csv mit BSR-Werten + Kategorien anreichern.
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

def scrape_bsr_full(asin: str) -> dict:
    """Scrapt BSR + alle Kategorien von Amazon.de"""
    url = f"https://www.amazon.de/dp/{asin}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return {}
        html = resp.text
        pattern = r'Nr\.?\s*([0-9.]+)\s+in\s+(?:<a[^>]*>)?([^<]+?)(?:</a>)?(?:\s*\(|</span>)'
        matches = re.findall(pattern, html)
        results = {}
        for rank_str, category in matches:
            rank = int(rank_str.replace(".", "").replace(",", ""))
            category = category.strip()
            if category and rank > 0:
                results[category] = rank
        return results
    except Exception as e:
        print(f"  Fehler für {asin}: {e}")
        return {}


if __name__ == "__main__":
    master_file = "data/master_data.csv"
    df = pd.read_csv(master_file)
    
    unique_asins = df["asin"].dropna().unique()
    print(f"📦 BSR + Kategorien abrufen für {len(unique_asins)} eindeutige ASINs...")
    
    bsr_map = {}
    bsr_categories_map = {}
    
    for i, asin in enumerate(unique_asins):
        print(f"  [{i+1}/{len(unique_asins)}] {asin}", end=" ")
        bsr_data = scrape_bsr_full(asin)
        if bsr_data:
            bsr_map[asin] = list(bsr_data.values())[0]
            bsr_categories_map[asin] = str(bsr_data)
            print(f"-> BSR: {bsr_map[asin]} | Kategorien: {list(bsr_data.keys())}")
        else:
            bsr_map[asin] = None
            bsr_categories_map[asin] = None
            print("-> None")
        time.sleep(1.5)
    
    df["bsr"] = df["asin"].map(bsr_map)
    df["bsr_categories"] = df["asin"].map(bsr_categories_map)
    
    filled = df["bsr"].notna().sum()
    print(f"\n✅ {filled}/{len(df)} Zeilen mit BSR gefüllt.")
    
    df.to_csv(master_file, index=False)
    print(f"💾 {master_file} gespeichert.")
    
    filtered_file = "data/filtered_classified.csv"
    try:
        df_filtered = pd.read_csv(filtered_file)
        df_filtered["bsr"] = df_filtered["asin"].map(bsr_map)
        df_filtered["bsr_categories"] = df_filtered["asin"].map(bsr_categories_map)
        df_filtered.to_csv(filtered_file, index=False)
        print(f"💾 {filtered_file} gespeichert.")
    except Exception:
        pass
