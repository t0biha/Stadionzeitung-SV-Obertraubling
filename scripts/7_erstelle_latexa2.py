import json
import os

# --- KONFIGURATION ---
JSON_INPUT = "saison_datena2.json"
OUTPUT_TEX = "generated/tabelle_dspieltaga2.tex"
PFAD_LOGOS = "bilder/logos/"

# DEINE LOGO ZUORDNUNG (Namen müssen exakt matchen!)
LOGO_NAMEN = {
  "SV Obertraubling II": "obertraubling.pdf",
  "SpVgg Stadtamhof Rgbg II": "stadtamhof.png",
  "FK Phoenix Regensburg": "phoenix.png",
  "TV Barbing II": "barbing.pdf",
  "(SG) Matting II/Oberndorf II": "matting_oberndorf.pdf",
  "Kosova Regensburg II": "kosova.pdf",
  "FSV Prüfening II": "pruefening.pdf",
  "FC Oberhinkofen II": "oberhinkofen.pdf",
  "TSV Oberisling Rgbg II": "oberisling.pdf",
  "SV Burgweinting Rgbg. II": "burgweinting.pdf",
  "VfR Regensburg II": "vfr_regensburg.pdf",
  "NK Hrvatska Regensburg": "hrvatska.pdf",
  "TSV Neutraubling II zg.": "neutraubling.pdf"
}

def finde_logo(team_name):
    if team_name in LOGO_NAMEN: return LOGO_NAMEN[team_name]
    for key, val in LOGO_NAMEN.items():
        if key in team_name: return val
    return None

def main():
    if not os.path.exists(JSON_INPUT):
        print("FEHLER: 'saison_daten.json' fehlt.")
        return

    with open(JSON_INPUT, 'r', encoding='utf-8') as f:
        alle_spiele = json.load(f)

    print("-" * 30)
    eingabe = input("Welchen Spieltag möchtest du erstellen? (z.B. 2): ")
    try:
        tag = int(eingabe)-1
    except:
        return

    spiele = [s for s in alle_spiele if s['spieltag'] == tag]
    if not spiele:
        print("Keine Spiele gefunden.")
        return

    # --- LATEX GENERIERUNG (DAS NEUE DESIGN) ---
    
    # 1. Tabellenkopf:
    # Spalten: 
    # l = Datum (klein)
    # >{\raggedleft\arraybackslash}X = Heimteam (drückt Text nach rechts zum Logo)
    # c = Logo Heim
    # c = Ergebnis (Mitte, fett)
    # c = Logo Gast
    # >{\raggedright\arraybackslash}X = Gastteam (drückt Text nach links zum Logo)
    
    latex = f"""
% --- SPIELTAG ÜBERSCHRIFT ---
\\vspace{{1em}}
\\begin{{center}}
    {{\\Large\\bfseries\\color{{VereinsBlau}} {tag}. Spieltag}}
\\end{{center}}
\\vspace{{0.8em}}

% --- TABELLE ---
\\setlength{{\\tabcolsep}}{{3pt}}
\\renewcommand{{\\arraystretch}}{{1.6}}
\\arrayrulecolor{{gray!50}}

\\begin{{tabularx}}{{\\textwidth}}{{ l >{{\\raggedleft\\arraybackslash}}X c c c >{{\\raggedright\\arraybackslash}}X }}
    \\hline
"""

    for spiel in spiele:
        heim = spiel['heim']
        gast = spiel['gast']
        res = spiel['ergebnis']
        
        # Logos laden
        f_heim = finde_logo(heim)
        f_gast = finde_logo(gast)
        
        # LOGO BEFEHL MIT RAISEBOX (Zentriert das Bild vertikal zur Schrift)
        # Wir setzen die Höhe auf 3.5ex (entspricht ca. der Texthöhe + etwas Luft)
        logo_h = f"\\raisebox{{-0.4\\height}}{{\\includegraphics[height=3.5ex]{{{PFAD_LOGOS}{f_heim}}}}}" if f_heim else ""
        logo_g = f"\\raisebox{{-0.4\\height}}{{\\includegraphics[height=3.5ex]{{{PFAD_LOGOS}{f_gast}}}}}" if f_gast else ""

        # Datum formatieren (25.07.2025 -> 25.07. | 18:30)
        datum = spiel['datum'][:-5]
        zeit = spiel['uhrzeit']
        
        # Zeile bauen:
        # Datum & Heim & LogoH & Ergebnis & LogoG & Gast \\ \hline
        line = (
            f"    \\footnotesize \\color{{gray}} {datum} {zeit} & "  # Datum klein und grau
            f"\\textbf{{{heim}}} & "                                # Heimname fett
            f"{logo_h} & "
            f"\\large \\textbf{{{res}}} & "                         # Ergebnis groß und fett
            f"{logo_g} & "
            f"\\textbf{{{gast}}} \\\\ \\hline"                      # Gastname fett + Linie
        )
        latex += line + "\n"

    latex += r"\end{tabularx}"
    
    with open(OUTPUT_TEX, "w", encoding="utf-8") as f:
        f.write(latex)

    print(f"Fertig! '{OUTPUT_TEX}' erstellt (Neues Design).")

if __name__ == "__main__":
    main()