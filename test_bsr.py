import requests
import re
import time
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def scrape_bsr_full(asin: str) -> dict:
    """Scrapt BSR + alle Kategorien von Amazon.de"""
    url = f"https://www.amazon.de/dp/{asin}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    html = resp.text
    
    # Finde alle "Nr. X in Kategorie" Einträge
    # Pattern: Nr. 183 in Drogerie & Körperpflege
    pattern = r'Nr\.?\s*([0-9.]+)\s+in\s+(?:<a[^>]*>)?([^<]+?)(?:</a>)?(?:\s*\(|</span>)'
    matches = re.findall(pattern, html)
    
    results = {}
    for rank_str, category in matches:
        rank = int(rank_str.replace(".", ""))
        category = category.strip()
        if category and rank > 0:
            results[category] = rank
    
    return results

# Test mit mehreren ASINs
test_asins = ["B0168KNAKW", "B0DJGP3XQC", "B0BG2ZJ7C9"]
for asin in test_asins:
    print(f"\n=== ASIN: {asin} ===")
    bsr_data = scrape_bsr_full(asin)
    for cat, rank in bsr_data.items():
        print(f"  Nr. {rank} in {cat}")
    time.sleep(2)
