import pdfplumber
import re
import json
import os

# --- EINSTELLUNGEN ---
PDF_DATEI = "spielplana2.pdf"     # Der Name deiner PDF Datei
JSON_OUTPUT = "saison_datena2.json" # Hier werden die Rohdaten gespeichert

def extract_from_pdf():
    if not os.path.exists(PDF_DATEI):
        print(f"FEHLER: Datei '{PDF_DATEI}' nicht gefunden.")
        return

    matches = []
    current_spieltag = 0
    
    print("Lese PDF ein...")
    
    with pdfplumber.open(PDF_DATEI) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue

            for line in text.split('\n'):
                line = line.strip()
                
                # 1. Spieltag erkennen (z.B. "1 . SPIELTAG")
                if "SPIELTAG" in line:
                    parts = line.split('.')
                    if parts[0].strip().isdigit():
                        current_spieltag = int(parts[0].strip())
                    continue

                # 2. Spielzeile erkennen
                # Sucht nach Zeilen, die mit 3 Ziffern beginnen (die Spielnummer)
                # Beispiel: "008 25.07.2025 18:30 Team A - Team B"
                if len(line) > 10 and line[:3].isdigit():
                    parts = line.split()
                    
                    # Mindestens Nummer, Datum, Uhrzeit, TeamA, -, TeamB
                    if len(parts) < 5: continue
                    
                    try:
                        # Die ersten 3 Teile sind fast immer fest
                        sp_nr = parts[0]
                        datum = parts[1]
                        uhrzeit = parts[2]
                        
                        # Der Rest ist "Team A - Team B Ergebnis"
                        # Wir fügen den Rest zusammen und splitten am Bindestrich
                        rest_text = " ".join(parts[3:])
                        
                        if " - " in rest_text:
                            teams_raw = rest_text.split(" - ")
                            heim = teams_raw[0].strip()
                            gast_part = teams_raw[1].strip()
                            
                            # Prüfen ob am Ende ein Ergebnis steht (z.B. "2:1")
                            ergebnis = "-:-"
                            gast = gast_part
                            
                            # Wenn das letzte "Wort" Ziffer:Ziffer enthält
                            last_word = gast_part.split()[-1]
                            if ':' in last_word and any(c.isdigit() for c in last_word):
                                ergebnis = last_word
                                # Gastname ist alles VOR dem Ergebnis
                                gast = " ".join(gast_part.split()[:-1])
                            
                            matches.append({
                                "spieltag": current_spieltag,
                                "datum": datum,
                                "uhrzeit": uhrzeit,
                                "heim": heim,
                                "gast": gast,
                                "ergebnis": ergebnis
                            })
                    except Exception as e:
                        print(f"Konnte Zeile nicht lesen: {line} -> {e}")
                        continue

    # Speichern als JSON
    with open(JSON_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(matches, f, ensure_ascii=False, indent=4)
        
    print(f"Erfolg! {len(matches)} Spiele extrahiert.")
    print(f"Daten gespeichert in '{JSON_OUTPUT}'")

if __name__ == "__main__":
    extract_from_pdf()