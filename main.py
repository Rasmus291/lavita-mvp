import pandas as pd
import numpy as np
import re
import os
import time
import requests
from datetime import datetime
from typing import List, Optional
from serpapi import GoogleSearch
from dotenv import load_dotenv


class AmazonMarketAnalyzer:
    """
    Hauptklasse zur Analyse des Amazon-Marktes für Nahrungsergänzungsmittel.
    Integriert Scrapping, Filtering, Klassifikation und KPI-Berechnung.
    """
    
    # KLASSE 1: Config & Setup
    def __init__(self, api_key: str, keywords: List[str]):
        self.api_key = api_key
        self.keywords = keywords
        self.raw_data = pd.DataFrame()
        self.filtered_data = pd.DataFrame()
        self.kpi_data = pd.DataFrame()
        self.master_data_file = "data/master_data.csv"
        
    # Interne Hilfsklassen
    class Cleaner:
        """Preisbereinigung"""
        @staticmethod
        def clean_price(price):
            if pd.isna(price):
                return None
            price_str = re.sub(r"[^\d,\.]", "", str(price))
            price_str = price_str.replace(",", ".")
            try:
                return float(price_str)
            except ValueError:
                return None

    class Classifier:
        """Wettbewerbsgrad-Klassifikation basierend auf Titel-Keywords"""
        @staticmethod
        def classify(title: str) -> int:
            t = str(title).lower()
            if "multivitamin" in t and "flüssig" in t:
                return 1  # Direkter Wettbewerber (Premium)
            elif "vitamin komplex" in t:
                return 2
            elif "vitamin" in t:
                return 3
            elif "nahrungsergänzung" in t:
                return 4
            else:
                return 5

    class Calculator:
        """KPIs & Wettbewerbs-Score Berechnung"""
        
        def process(self, df: pd.DataFrame) -> pd.DataFrame:
            if df.empty:
                return df
            
            # Preis bereinigen
            df["price_clean"] = df["price"].apply(
                AmazonMarketAnalyzer.Cleaner.clean_price
            )
            
            # Numerische Konvertierung
            df["reviews"] = pd.to_numeric(df["reviews"], errors="coerce").fillna(0)
            df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
            
            # Geschätzte Bestellanzahl (Branchenstandard: Reviews × 20)
            df["est_orders"] = (df["reviews"] * 20).astype(int)
            
            # Amazon-Ranking (Position) ist bereits vorhanden
            # -> Spalte 'position' aus dem Scraping
            
            # Wettbewerbs-Score (basierend auf Insights aus Marktbericht)
            # Da Natural Elements (Rank 1) führt, priorisieren wir Volume + Rating
            df = self._add_competition_score(df)
            
            return df
        
        def _add_competition_score(self, df: pd.DataFrame) -> pd.DataFrame:
            """Berechnet CIS (Competition Impact Score) - Mathe: 40% Rating, 40% Volumen, 20% Preis"""
            max_rev = df['reviews'].max() if df['reviews'].max() > 0 else 1
            min_price = df['price_clean'].min() if df['price_clean'].min() > 0 else 1
            
            # Normalisierung (0-1)
            df['norm_rating'] = df['rating'] / 5.0
            df['norm_volume'] = np.log1p(df['reviews']) / np.log1p(max_rev)
            df['norm_price'] = min_price / df['price_clean']
            
            # Gewichtung laut Forschungsdesign
            df['cis_score'] = (
                (df['norm_rating'] * 0.4) +
                (df['norm_volume'] * 0.4) +
                (df['norm_price'] * 0.2)
            )
            return df

        def calculate_kpis(self, df: pd.DataFrame) -> pd.DataFrame:
            if df.empty:
                return pd.DataFrame()
            
            kpis = {
                "avg_price": df["price_clean"].mean(),
                "avg_rating": df["rating"].mean(),
                "avg_cis_score": df["cis_score"].mean(),  # NEU: Score statt nur Count
                "avg_reviews": df["reviews"].mean(),
                "total_products": len(df),
                "grade_1_comp": len(df[df["competition_grade"] == 1]),  # Direkte Mitbewerber
                "top_sellers_est": len(df[df["reviews"] >= 1000]), # Schätzung basierend auf Report (Ref: 1)
                "total_est_orders": df["est_orders"].sum(),  # Gesamte geschätzte Bestellungen
                "avg_position": df["position"].mean(),  # Ø Amazon-Ranking
                "avg_bsr": df["bsr"].mean() if "bsr" in df.columns else None,  # Ø Bestseller-Rang
            }
            return pd.DataFrame([kpis])

    # KLASSE 2: Scraper
    def scrape_keyword(self, keyword: str) -> List[dict]:
        params = {
            "engine": "amazon",
            "amazon_domain": "amazon.de",
            "k": keyword,
            "api_key": self.api_key
        }
        
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            
            if "error" in results:
                print(f"API Fehler: {results['error']}")
                return []
                
            products = results.get("organic_results", [])
            data = []
            
            for pos, p in enumerate(products[:20], start=1):
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
                    "link": p.get("link")
                })
            return data
        except Exception as e:
            print(f"Scraping Fehler für '{keyword}': {e}")
            return []

    # HTTP-Headers für direktes Amazon-Scraping
    _HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def scrape_bsr(self, asin: str) -> Optional[int]:
        """
        Holt den Bestseller-Rang (BSR) direkt von der Amazon.de Produktseite.
        Verbraucht keine SerpAPI-Credits.
        """
        bsr_data = self.scrape_bsr_full(asin)
        if bsr_data:
            # Erster Eintrag = Haupt-Kategorie (niedrigste Ebene)
            return list(bsr_data.values())[0]
        return None

    def _fetch_amazon_page(self, asin: str) -> Optional[str]:
        """Holt HTML-Inhalt einer Amazon.de Produktseite."""
        url = f"https://www.amazon.de/dp/{asin}"
        try:
            resp = requests.get(url, headers=self._HEADERS, timeout=15)
            if resp.status_code != 200:
                print(f"   HTTP {resp.status_code} für {asin}")
                return None
            return resp.text
        except Exception as e:
            print(f"   Fehler für ASIN {asin}: {e}")
            return None

    @staticmethod
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

    @staticmethod
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

    def scrape_bsr_full(self, asin: str) -> dict:
        """
        Holt BSR + alle Kategorien direkt von der Amazon.de Produktseite.
        Returns: dict {Kategorie: Rang}
        """
        html = self._fetch_amazon_page(asin)
        if not html:
            return {}
        return self._extract_bsr_categories(html)

    def scrape_product_details(self, asin: str) -> dict:
        """
        Holt BSR-Kategorien + Marke von einer Amazon.de Produktseite in einem Request.
        Returns: {"bsr": int, "bsr_categories": str, "brand": str}
        """
        html = self._fetch_amazon_page(asin)
        if not html:
            return {"bsr": None, "bsr_categories": None, "brand": None}
        
        bsr_data = self._extract_bsr_categories(html)
        brand = self._extract_brand(html)
        
        return {
            "bsr": list(bsr_data.values())[0] if bsr_data else None,
            "bsr_categories": str(bsr_data) if bsr_data else None,
            "brand": brand,
        }

    def enrich_with_bsr(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Reichert DataFrame mit BSR-Daten, Kategorien und Marke an (nur für eindeutige ASINs).
        """
        unique_asins = df["asin"].dropna().unique()
        bsr_map = {}
        bsr_categories_map = {}
        brand_map = {}
        
        for i, asin in enumerate(unique_asins):
            print(f"   -> Details abrufen: {asin} ({i+1}/{len(unique_asins)})")
            details = self.scrape_product_details(asin)
            bsr_map[asin] = details["bsr"]
            bsr_categories_map[asin] = details["bsr_categories"]
            brand_map[asin] = details["brand"]
            time.sleep(1.5)  # Rate-Limit beachten
        
        df["bsr"] = df["asin"].map(bsr_map)
        df["bsr_categories"] = df["asin"].map(bsr_categories_map)
        # Brand nur füllen wenn aktuell leer
        df["brand"] = df["brand"].fillna(df["asin"].map(brand_map))
        return df

    def run_full_pipeline(self, save_interim: bool = True):
        """
        Führt den kompletten ETL-Prozess durch.
        """
        print("🔄 Starte Pipeline...")
        
        # 1. Scraping
        all_data = []
        for kw in self.keywords:
            print(f"   -> Scraping: {kw}")
            all_data.extend(self.scrape_keyword(kw))
        
        self.raw_data = pd.DataFrame(all_data)
        
        # Save Raw
        os.makedirs("data", exist_ok=True)
        self.raw_data.to_csv("data/raw_data.csv", index=False)
        
        # 2. Filter & Clean (entspricht deiner filter_products Logik)
        self.filtered_data = self._apply_filters(self.raw_data)
        
        # 3. Klassifikation
        self.filtered_data["competition_grade"] = \
            self.filtered_data["title"].apply(self.Classifier.classify)
        
        # 3b. BSR-Daten anreichern
        print("📦 BSR-Daten abrufen...")
        self.filtered_data = self.enrich_with_bsr(self.filtered_data)
        
        if save_interim:
            self.filtered_data.to_csv("data/filtered_classified.csv", index=False)
        
        # 4. Prozessierung & KPIs (via interner Klasse)
        calc = self.Calculator()
        processed_df = calc.process(self.filtered_data)
        
        self.kpi_data = calc.calculate_kpis(processed_df)
        self.kpi_data.to_csv("data/kpis.csv", index=False)
        
        # 5. Zeitreihen-Tracking (Append zu Masterfile)
        if os.path.exists(self.master_data_file):
            old = pd.read_csv(self.master_data_file)
            master = pd.concat([old, processed_df], ignore_index=True)
        else:
            master = processed_df
            
        master.to_csv(self.master_data_file, index=False)
        
        print("✅ Pipeline abgeschlossen.")
        return self.kpi_data

    # Interne Filterlogik (entspricht deiner функции)
    @staticmethod
    def _apply_filters(df: pd.DataFrame) -> pd.DataFrame:
        df = df.dropna(subset=["title"])
        
        # Bedingung: Flüssig/Saft/Konzentrat/Pulver (inkl. Trinkpulver, Elotrans etc.)
        mask_format = df["title"].str.contains(
            "flüssig|saft|konzentrat|pulver|trinkpulver", case=False, na=False
        )
        
        # Ausschluss: Kapseln rausfiltern
        mask_no_capsules = ~df["title"].str.contains(
            "kapsel|kapseln|capsule|capsules", case=False, na=False
        )
        
        # Bedingung: Mindestreviews (>50 entspricht Low-Volume Threshold aus Report)
        mask_reviews = df["reviews"].fillna(0) > 50
        
        # Bedingung: Preis vorhanden
        mask_price = df["price"].notnull()
        
        return df[mask_format & mask_no_capsules & mask_reviews & mask_price]


# --- ANWENDUNG ---
if __name__ == "__main__":
    load_dotenv()
    API_KEY = os.getenv("SERPAPI_KEY")
    
    # Keywords basierend auf Studie: Trend zu flüssig/Konzentrate
    KEYWORDS = [
        "Multivitamin Saft",
        "Vitamin Komplex Flüssig", 
        "Nahrungsergänzung Flüssig",
        "Immunsystem Vitamine",
        "Mikronährstoffkonzentrat Amazon"  # NEU: Angelehnt an Report-Titel
    ]
    
    analyzer = AmazonMarketAnalyzer(api_key=API_KEY, keywords=KEYWORDS)
    kpis = analyzer.run_full_pipeline()
    
    print("\n📊 Aktuelle KPIs:")
    print(kpis)