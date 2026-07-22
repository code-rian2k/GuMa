"""
Datenbank-Zugriff für den Gutachten-Manager.
Nutzt SQLite - eine einzelne lokale Datei, keine Server nötig.
"""
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "gutachten_manager.db")


# Eine Tabelle je Eintrag, Spalten als (Name, SQL-Definition)-Paare. Dient
# als EINZIGE Quelle der Wahrheit für das Schema: daraus werden sowohl die
# CREATE TABLE-Anweisungen für neue Datenbanken als auch (in init_db(), über
# _fehlende_spalten_nachruesten()) automatische ALTER TABLE ADD COLUMN für
# bereits bestehende Datenbanken abgeleitet - z.B. nach dem Import eines
# älteren Backups, dem eine seitdem neu hinzugekommene Spalte noch fehlt.
#
# Für neue Spalten an bestehenden Tabellen gilt: NOT NULL nur zusammen mit
# einem DEFAULT verwenden (SQLites ALTER TABLE ADD COLUMN erlaubt sonst
# keinen Wert für schon vorhandene Zeilen) und kein PRIMARY KEY/UNIQUE
# (dafür fehlt bei ALTER TABLE ADD COLUMN die Unterstützung).
TABELLEN_SPALTEN = {
    "faelle": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("aktenzeichen", "TEXT"),
        ("gericht", "TEXT"),
        ("abteilung", "TEXT DEFAULT 'Abteilung für Familiensachen'"),
        ("richter", "TEXT"),
        ("in_sachen", "TEXT"),
        ("kinder", "TEXT"),
        ("mutter_name", "TEXT"),
        ("mutter_anschrift", "TEXT"),
        ("vater_name", "TEXT"),
        ("vater_anschrift", "TEXT"),
        ("auftragstext", "TEXT"),
        ("status", "TEXT DEFAULT 'offen'"),
        ("erstellt_am", "TEXT"),
        ("geaendert_am", "TEXT"),
    ],
    "termine": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("fall_id", "INTEGER NOT NULL REFERENCES faelle(id) ON DELETE CASCADE"),
        ("datum", "TEXT"),
        ("beschreibung", "TEXT"),
        ("erledigt", "INTEGER DEFAULT 0"),
    ],
    "notizen": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("fall_id", "INTEGER NOT NULL REFERENCES faelle(id) ON DELETE CASCADE"),
        ("zeitpunkt", "TEXT"),
        ("text", "TEXT"),
    ],
    "rechnungen": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("fall_id", "INTEGER NOT NULL REFERENCES faelle(id) ON DELETE CASCADE"),
        ("rechnungsnummer", "TEXT"),
        ("datum", "TEXT"),
        ("stundensatz", "REAL DEFAULT 100.0"),
        ("km", "REAL DEFAULT 0"),
        ("km_satz", "REAL DEFAULT 0.42"),
        ("porto", "REAL DEFAULT 0"),
        ("telefon", "REAL DEFAULT 0"),
        ("zeichen_anzahl", "INTEGER DEFAULT 0"),
        ("schreibgebuehr_satz", "REAL DEFAULT 1.5"),
        ("kopien_seiten", "INTEGER DEFAULT 0"),
        ("mwst_satz", "REAL DEFAULT 19.0"),
    ],
    "rechnung_zeitposten": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("rechnung_id", "INTEGER NOT NULL REFERENCES rechnungen(id) ON DELETE CASCADE"),
        ("bezeichnung", "TEXT"),
        ("minuten", "INTEGER DEFAULT 0"),
        ("reihenfolge", "INTEGER DEFAULT 0"),
    ],
    "rechnung_aufwandsposten": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("rechnung_id", "INTEGER NOT NULL REFERENCES rechnungen(id) ON DELETE CASCADE"),
        ("bezeichnung", "TEXT"),
        ("betrag", "REAL DEFAULT 0"),
        ("reihenfolge", "INTEGER DEFAULT 0"),
    ],
    "einstellungen": [
        ("schluessel", "TEXT PRIMARY KEY"),
        ("wert", "TEXT"),
    ],
    "vorlagen": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("typ", "TEXT NOT NULL"),
        ("name", "TEXT NOT NULL"),
        ("dateiname", "TEXT NOT NULL"),
        ("erstellt_am", "TEXT"),
    ],
}

STANDARD_ZEITPOSTEN = [
    "Schreiben zur Terminabstimmung und sonstige Mitteilungen",
    "Studium und Auswertung der Akten und sonstiger Unterlagen",
    "Diagnostik",
    "Auswertung des Datenmaterials",
    "Erstellung des Sachverständigengutachtens",
    "Anfahrzeit",
    "Telefonzeit",
]

STANDARD_EINSTELLUNGEN = {
    "name": "",
    "iban": "",
    "bank": "",
    "kontoinhaberin": "",
    "finanzamt": "",
    "steuernummer": "",
    "ust_idnr": "",
    "steuer_id": "",
    "telefon": "",
    "absender_adresse": "",
    "dokumente_ordner": "",  # leer = Standardordner neben dem Programm
    # Vorbelegung für neue Rechnungen (bleibt pro Rechnung änderbar wie bisher)
    "standard_stundensatz": "100",
    "standard_km_satz": "0.42",
    "standard_mwst_satz": "19",
    "standard_schreibgebuehr_satz": "1.5",
    # Kopien-Staffelung: bis zur Grenze der erste Satz, danach der zweite
    "kopien_grenze": "50",
    "kopien_satz_bis_grenze": "0.50",
    "kopien_satz_ab_grenze": "0.15",
}


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_conn() as conn:
        for tabelle, spalten in TABELLEN_SPALTEN.items():
            spalten_sql = ",\n    ".join(f"{name} {definition}" for name, definition in spalten)
            conn.execute(f"CREATE TABLE IF NOT EXISTS {tabelle} (\n    {spalten_sql}\n)")
        _fehlende_spalten_nachruesten(conn)
        for schluessel, wert in STANDARD_EINSTELLUNGEN.items():
            conn.execute(
                "INSERT OR IGNORE INTO einstellungen (schluessel, wert) VALUES (?, ?)",
                (schluessel, wert),
            )
        conn.commit()


def _fehlende_spalten_nachruesten(conn):
    """Rüstet Spalten nach, die in TABELLEN_SPALTEN neu hinzugekommen, in
    einer schon bestehenden Datenbank (z.B. aus einem älteren Backup
    importiert) aber noch nicht vorhanden sind - rein additiv, nichts wird
    verändert oder gelöscht. So werden künftige Schema-Erweiterungen
    automatisch auch bei bestehenden Datenbanken nachgezogen, ohne dass
    beim Importieren eines älteren Backups Fehler wegen fehlender Spalten
    auftreten (CREATE TABLE IF NOT EXISTS allein würde eine schon
    bestehende Tabelle nicht um neue Spalten ergänzen)."""
    for tabelle, spalten in TABELLEN_SPALTEN.items():
        vorhandene_spalten = {row["name"] for row in conn.execute(f"PRAGMA table_info({tabelle})")}
        for name, definition in spalten:
            if name in vorhandene_spalten or "PRIMARY KEY" in definition:
                continue
            conn.execute(f"ALTER TABLE {tabelle} ADD COLUMN {name} {definition}")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def now_str():
    return datetime.now().strftime("%d.%m.%Y %H:%M")
