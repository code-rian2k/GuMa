"""
Datenbank-Zugriff für den Gutachten-Manager.
Nutzt SQLite - eine einzelne lokale Datei, keine Server nötig.
"""
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "gutachten_manager.db")


SCHEMA = """
CREATE TABLE IF NOT EXISTS faelle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aktenzeichen TEXT,
    gericht TEXT,
    abteilung TEXT DEFAULT 'Abteilung für Familiensachen',
    richter TEXT,
    in_sachen TEXT,
    kinder TEXT,
    mutter_name TEXT,
    mutter_anschrift TEXT,
    vater_name TEXT,
    vater_anschrift TEXT,
    auftragstext TEXT,
    status TEXT DEFAULT 'offen',
    erstellt_am TEXT,
    geaendert_am TEXT
);

CREATE TABLE IF NOT EXISTS termine (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fall_id INTEGER NOT NULL,
    datum TEXT,
    beschreibung TEXT,
    erledigt INTEGER DEFAULT 0,
    FOREIGN KEY (fall_id) REFERENCES faelle(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notizen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fall_id INTEGER NOT NULL,
    zeitpunkt TEXT,
    text TEXT,
    FOREIGN KEY (fall_id) REFERENCES faelle(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rechnungen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fall_id INTEGER NOT NULL,
    rechnungsnummer TEXT,
    datum TEXT,
    stundensatz REAL DEFAULT 100.0,
    km REAL DEFAULT 0,
    km_satz REAL DEFAULT 0.42,
    porto REAL DEFAULT 0,
    telefon REAL DEFAULT 0,
    zeichen_anzahl INTEGER DEFAULT 0,
    schreibgebuehr_satz REAL DEFAULT 1.5,
    kopien_seiten INTEGER DEFAULT 0,
    mwst_satz REAL DEFAULT 19.0,
    FOREIGN KEY (fall_id) REFERENCES faelle(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rechnung_zeitposten (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rechnung_id INTEGER NOT NULL,
    bezeichnung TEXT,
    minuten INTEGER DEFAULT 0,
    reihenfolge INTEGER DEFAULT 0,
    FOREIGN KEY (rechnung_id) REFERENCES rechnungen(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS einstellungen (
    schluessel TEXT PRIMARY KEY,
    wert TEXT
);

CREATE TABLE IF NOT EXISTS vorlagen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    typ TEXT NOT NULL,
    name TEXT NOT NULL,
    dateiname TEXT NOT NULL,
    erstellt_am TEXT
);
"""

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
}


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        for schluessel, wert in STANDARD_EINSTELLUNGEN.items():
            conn.execute(
                "INSERT OR IGNORE INTO einstellungen (schluessel, wert) VALUES (?, ?)",
                (schluessel, wert),
            )
        conn.commit()


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
