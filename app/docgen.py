"""
Erstellt Word-Dokumente (Anschreiben, Gutachten-Grundgerüst) aus den
vorbereiteten Vorlagen, indem {{PLATZHALTER}} durch echte Falldaten ersetzt
werden. Die Formatierung der Vorlage bleibt erhalten.
"""
import os
import re
import docx

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")

PLATZHALTER_MUSTER = re.compile(r"\{\{[A-Z_]+\}\}")


def _ersetze_in_paragraph(paragraph, werte: dict):
    voller_text = "".join(run.text for run in paragraph.runs)
    if "{{" not in voller_text:
        return
    neuer_text = voller_text
    for schluessel, wert in werte.items():
        neuer_text = neuer_text.replace("{{%s}}" % schluessel, str(wert if wert is not None else ""))
    if neuer_text == voller_text:
        return
    if not paragraph.runs:
        paragraph.add_run(neuer_text)
        return
    paragraph.runs[0].text = neuer_text
    for run in paragraph.runs[1:]:
        run.text = ""


def fuelle_dokument(vorlage_pfad: str, ausgabe_pfad: str, werte: dict):
    dokument = docx.Document(vorlage_pfad)
    for paragraph in dokument.paragraphs:
        _ersetze_in_paragraph(paragraph, werte)
    for table in dokument.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    _ersetze_in_paragraph(paragraph, werte)
    os.makedirs(os.path.dirname(ausgabe_pfad), exist_ok=True)
    dokument.save(ausgabe_pfad)
    return ausgabe_pfad


def offene_platzhalter(pfad: str):
    """Findet {{...}}-Platzhalter, die noch nicht ersetzt wurden - zur Kontrolle."""
    dokument = docx.Document(pfad)
    gefunden = set()
    for paragraph in dokument.paragraphs:
        for treffer in PLATZHALTER_MUSTER.findall(paragraph.text):
            gefunden.add(treffer)
    return gefunden


def anschreiben_erstellen(fall: dict, einstellungen: dict, ausgabe_pfad: str, richter_text: str = ""):
    anrede = fall.get("empfaenger_anrede", "Frau")
    endung = "r" if anrede == "Herr" else ""
    werte = {
        "EMPFAENGER_ANREDE": anrede,
        "EMPFAENGER_ANREDE_ENDUNG": endung,
        "EMPFAENGER_NAME": fall.get("empfaenger_name", ""),
        "DATUM": fall.get("datum", ""),
        "RICHTER_TEXT": richter_text or fall.get("richter", ""),
        "KINDER": fall.get("kinder", ""),
        "GUTACHTER_TELEFON": einstellungen.get("telefon", ""),
        "GUTACHTER_NAME": einstellungen.get("name", ""),
    }
    vorlage = os.path.join(TEMPLATES_DIR, "anschreiben_vorlage.docx")
    return fuelle_dokument(vorlage, ausgabe_pfad, werte)


def gutachten_erstellen(fall: dict, ausgabe_pfad: str):
    werte = {
        "GERICHT": fall.get("gericht", ""),
        "ABTEILUNG": fall.get("abteilung", ""),
        "DATUM": fall.get("datum", ""),
        "AKTENZEICHEN": fall.get("aktenzeichen", ""),
    }
    vorlage = os.path.join(TEMPLATES_DIR, "gutachten_vorlage.docx")
    return fuelle_dokument(vorlage, ausgabe_pfad, werte)
