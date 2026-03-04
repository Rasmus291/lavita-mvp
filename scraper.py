"""
Amazon-Produktsuche via SerpAPI.
"""
from datetime import datetime
from typing import List
from serpapi import GoogleSearch


def scrape_keyword(api_key: str, keyword: str, max_results: int = 20) -> List[dict]:
    """
    Sucht auf Amazon.de nach einem Keyword und gibt die organischen Ergebnisse zurück.
    """
    params = {
        "engine": "amazon",
        "amazon_domain": "amazon.de",
        "k": keyword,
        "api_key": api_key,
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()

        if "error" in results:
            print(f"API Fehler: {results['error']}")
            return []

        products = results.get("organic_results", [])
        data = []

        for pos, p in enumerate(products[:max_results], start=1):
            data.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "keyword": keyword,
                "title": p.get("title"),
                "brand": p.get("brand"),
                "price": p.get("price"),
                "rating": p.get("rating"),
                "reviews": p.get("reviews"),
                "asin": p.get("asin"),
                "position": pos,
                "link": p.get("link"),
            })
        return data
    except Exception as e:
        print(f"Scraping Fehler für '{keyword}': {e}")
        return []
