"""
Direktes BSR-Scraping von Amazon.de Produktseiten (kein SerpAPI-Verbrauch).
"""
import re
import time
from typing import Optional
import requests
import pandas as pd

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _fetch_amazon_page(asin: str) -> Optional[str]:
    """Holt HTML-Inhalt einer Amazon.de Produktseite."""
    url = f"https://www.amazon.de/dp/{asin}"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"   HTTP {resp.status_code} für {asin}")
            return None
        return resp.text
    except Exception as e:
        print(f"   Fehler für ASIN {asin}: {e}")
        return None


def _extract_bsr_categories(html: str) -> dict:
    """Extrahiert BSR + Kategorien aus Amazon-HTML."""
    pattern = r'Nr\.?\s*([0-9.]+)\s+in\s+(?:<a[^>]*>)?([^<]+?)(?:</a>)?(?:\s*\(|</span>)'
    matches = re.findall(pattern, html)
    results = {}
    for rank_str, category in matches:
        rank = int(rank_str.replace(".", "").replace(",", ""))
        category = category.strip()
        if category and rank > 0:
            results[category] = rank
    return results


def _extract_brand(html: str) -> Optional[str]:
    """Extrahiert die Marke aus der Amazon-Produktseite."""
    patterns = [
        r'id="bylineInfo"[^>]*>[^<]*Besuche den ([^<-]+?)(?:-Store|Store)',
        r'id="bylineInfo"[^>]*>([^<]+)',
        r'Marke\s*</th>\s*<td[^>]*>\s*(?:<[^>]+>)*\s*([^<]+)',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            brand = m.group(1).strip()
            brand = re.sub(r'^Besuche den\s*', '', brand)
            brand = re.sub(r'-?Store$', '', brand)
            brand = re.sub(r'Marke:\s*', '', brand)
            brand = re.sub(r'&lrm;|&rlm;|\u200e|\u200f', '', brand)
            brand = brand.strip()
            if brand and len(brand) > 1:
                return brand
    return None


def scrape_bsr(asin: str) -> Optional[int]:
    """Holt den Haupt-BSR (niedrigste Ebene) für eine ASIN."""
    bsr_data = scrape_bsr_full(asin)
    if bsr_data:
        return list(bsr_data.values())[0]
    return None


def scrape_bsr_full(asin: str) -> dict:
    """Holt BSR + alle Kategorien. Returns: {Kategorie: Rang}"""
    html = _fetch_amazon_page(asin)
    if not html:
        return {}
    return _extract_bsr_categories(html)


def scrape_product_details(asin: str) -> dict:
    """
    Holt BSR-Kategorien + Marke in einem einzigen Request.
    Returns: {"bsr": int|None, "bsr_categories": str|None, "brand": str|None}
    """
    html = _fetch_amazon_page(asin)
    if not html:
        return {"bsr": None, "bsr_categories": None, "brand": None}

    bsr_data = _extract_bsr_categories(html)
    brand = _extract_brand(html)

    return {
        "bsr": list(bsr_data.values())[0] if bsr_data else None,
        "bsr_categories": str(bsr_data) if bsr_data else None,
        "brand": brand,
    }


def enrich_with_bsr(df: pd.DataFrame, delay: float = 1.5) -> pd.DataFrame:
    """
    Reichert DataFrame mit BSR-Daten, Kategorien und Marke an.
    """
    unique_asins = df["asin"].dropna().unique()
    bsr_map = {}
    bsr_categories_map = {}
    brand_map = {}

    for i, asin in enumerate(unique_asins):
        print(f"   -> Details abrufen: {asin} ({i+1}/{len(unique_asins)})")
        details = scrape_product_details(asin)
        bsr_map[asin] = details["bsr"]
        bsr_categories_map[asin] = details["bsr_categories"]
        brand_map[asin] = details["brand"]
        time.sleep(delay)

    df["bsr"] = df["asin"].map(bsr_map)
    df["bsr_categories"] = df["asin"].map(bsr_categories_map)
    df["brand"] = df["brand"].fillna(df["asin"].map(brand_map))
    return df
