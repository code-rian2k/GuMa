"""
Verwaltung eigener Word-Vorlagen für Anschreiben und Gutachten.

GuMa liefert selbst keine Vorlagen mehr mit - jede Nutzerin hinterlegt ihre
eigenen Word-Dateien (Datei-Menü -> Einstellungen -> Vorlagen). Die Dateien
werden in einen eigenen Ordner ("vorlagen") neben dem Programm kopiert und
dabei automatisch bereinigt (siehe app.docx_bereinigen): Reste von Word-
Änderungsverfolgung sowie Autor-Metadaten werden entfernt, damit z.B. ein
mit "Änderungen nachverfolgen" gelöschter Klarname aus einem früheren Fall
nicht unbemerkt in der Vorlage - und damit in jedem daraus erzeugten
Dokument - erhalten bleibt.
"""
import os

from app import repo
from app.dateien import eindeutigen_dateinamen
from app.docx_bereinigen import bereinige_docx

VORLAGEN_ORDNERNAME = "vorlagen"


def ermittle_vorlagen_ordner(basis_ordner: str) -> str:
    pfad = os.path.join(basis_ordner, VORLAGEN_ORDNERNAME)
    os.makedirs(pfad, exist_ok=True)
    return pfad


def vorlage_pfad(basis_ordner: str, vorlage: dict) -> str:
    return os.path.join(ermittle_vorlagen_ordner(basis_ordner), vorlage["dateiname"])


def vorlage_hinzufuegen(basis_ordner: str, typ: str, name: str, quellpfad: str) -> dict:
    """Kopiert quellpfad in den Vorlagen-Ordner, bereinigt die Kopie und
    legt einen Datenbankeintrag an. Das Original bleibt unverändert."""
    ordner = ermittle_vorlagen_ordner(basis_ordner)
    zielname = eindeutigen_dateinamen(ordner, os.path.basename(quellpfad))
    zielpfad = os.path.join(ordner, zielname)
    bereinige_docx(quellpfad, zielpfad)
    vorlage_id = repo.vorlage_anlegen(typ, name, zielname)
    return repo.vorlage_holen(vorlage_id)


def vorlage_entfernen(basis_ordner: str, vorlage: dict):
    pfad = vorlage_pfad(basis_ordner, vorlage)
    if os.path.isfile(pfad):
        os.remove(pfad)
    repo.vorlage_loeschen(vorlage["id"])
