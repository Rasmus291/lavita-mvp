"""
Einmaliges Script: Bestehende master_data.csv mit BSR-Werten, Kategorien und Marke anreichern.
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

def scrape_product_details(asin: str) -> dict:
    """Scrapt BSR + Kategorien + Marke von Amazon.de in einem Request."""
    url = f"https://www.amazon.de/dp/{asin}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return {"bsr": None, "bsr_categories": None, "brand": None}
        html = resp.text
        
        # BSR-Kategorien
        pattern = r'Nr\.?\s*([0-9.]+)\s+in\s+(?:<a[^>]*>)?([^<]+?)(?:</a>)?(?:\s*\(|</span>)'
        matches = re.findall(pattern, html)
        bsr_data = {}
        for rank_str, category in matches:
            rank = int(rank_str.replace(".", "").replace(",", ""))
            category = category.strip()
            if category and rank > 0:
                bsr_data[category] = rank
        
        # Marke extrahieren
        brand = None
        brand_patterns = [
            r'id="bylineInfo"[^>]*>[^<]*Besuche den ([^<-]+?)(?:-Store|Store)',
            r'id="bylineInfo"[^>]*>([^<]+)',
            r'Marke\s*</th>\s*<td[^>]*>\s*(?:<[^>]+>)*\s*([^<]+)',
        ]
        for pat in brand_patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                brand = m.group(1).strip()
                brand = re.sub(r'^Besuche den\s*', '', brand)
                brand = re.sub(r'-?Store$', '', brand)
                brand = re.sub(r'Marke:\s*', '', brand)
                brand = brand.strip()
                if brand and len(brand) > 1:
                    break
                brand = None
        
        return {
            "bsr": list(bsr_data.values())[0] if bsr_data else None,
            "bsr_categories": str(bsr_data) if bsr_data else None,
            "brand": brand,
        }
    except Exception as e:
        print(f"  Fehler für {asin}: {e}")
        return {"bsr": None, "bsr_categories": None, "brand": None}


if __name__ == "__main__":
    master_file = "data/master_data.csv"
    df = pd.read_csv(master_file)
    
    unique_asins = df["asin"].dropna().unique()
    print(f"📦 BSR + Kategorien + Marke abrufen für {len(unique_asins)} ASINs...")
    
    bsr_map = {}
    bsr_categories_map = {}
    brand_map = {}
    
    for i, asin in enumerate(unique_asins):
        print(f"  [{i+1}/{len(unique_asins)}] {asin}", end=" ")
        details = scrape_product_details(asin)
        bsr_map[asin] = details["bsr"]
        bsr_categories_map[asin] = details["bsr_categories"]
        brand_map[asin] = details["brand"]
        print(f"-> BSR: {details['bsr']} | Brand: {details['brand']}")
        time.sleep(1.5)
    
    df["bsr"] = df["asin"].map(bsr_map)
    df["bsr_categories"] = df["asin"].map(bsr_categories_map)
    df["brand"] = df["asin"].map(brand_map)
    
    filled_bsr = df["bsr"].notna().sum()
    filled_brand = df["brand"].notna().sum()
    print(f"\n✅ {filled_bsr}/{len(df)} BSR, {filled_brand}/{len(df)} Marken gefüllt.")
    
    df.to_csv(master_file, index=False)
    print(f"💾 {master_file} gespeichert.")
    
    filtered_file = "data/filtered_classified.csv"
    try:
        df_filtered = pd.read_csv(filtered_file)
        df_filtered["bsr"] = df_filtered["asin"].map(bsr_map)
        df_filtered["bsr_categories"] = df_filtered["asin"].map(bsr_categories_map)
        df_filtered["brand"] = df_filtered["asin"].map(brand_map)
        df_filtered.to_csv(filtered_file, index=False)
        print(f"💾 {filtered_file} gespeichert.")
    except Exception:
        pass
