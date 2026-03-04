import requests
import re
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def extract_brand(html: str) -> str | None:
    """Extrahiert die Marke aus der Amazon-Produktseite."""
    # Pattern 1: "Marke: X" in Produktdetails
    # Pattern 2: "Besuche den X-Store" im bylineInfo
    patterns = [
        r'id="bylineInfo"[^>]*>[^<]*Besuche den ([^<-]+?)(?:-Store|Store)',
        r'id="bylineInfo"[^>]*>([^<]+)',
        r'"brand"\s*:\s*"([^"]+)"',
        r'Marke\s*</th>\s*<td[^>]*>\s*(?:<[^>]+>)*\s*([^<]+)',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            brand = m.group(1).strip()
            # Clean up
            brand = re.sub(r'^Besuche den\s*', '', brand)
            brand = re.sub(r'-?Store$', '', brand)
            brand = re.sub(r'Marke:\s*', '', brand)
            brand = brand.strip()
            if brand and len(brand) > 1:
                return brand
    return None

test_asins = ["B0168KNAKW", "B0DJGP3XQC", "B06ZZRX62M", "B0BG2ZJ7C9", "B00VU54RGC"]
for asin in test_asins:
    url = f"https://www.amazon.de/dp/{asin}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    brand = extract_brand(resp.text)
    print(f"ASIN {asin}: Brand = {brand}")
    time.sleep(2)
