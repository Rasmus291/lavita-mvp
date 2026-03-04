def classify_product(row):
    title = str(row["title"]).lower()
    
    # 1. FLÜSSIG MULTIVITAMIN (Direkte Wettbewerber - HIGH PRIORITY)
    if "multivitamine" in title and "flüssig" in title:
        return 1
    elif "multivitamin" in title and "konzentrat" in title: # NEU: Konzentrate erfassen
        return 1
    
    # 2. SPEZIALISIERTE KOMPLEXE (Immun, B-Komplex)
    elif "vitamin komplex" in title or "immun" in title: # NEU: Immun-Marken erfassen
        return 2
    
    # 3. STANDARD VITAMINE (einfache Erwähnung)
    elif "vitamin" in title or "mineral" in title:
        return 3
    
    # 4. NAHRUNGSERGÄNZUNG ALLGEMEIN
    elif "nahrungsergänzung" in title or "ergänzung" in title:
        return 4
    
    else:
        return 5