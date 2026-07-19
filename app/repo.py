"""
Einfache Datenzugriffsfunktionen (Repository) - kapselt alle SQL-Zugriffe,
damit die GUI nicht direkt mit SQL arbeiten muss.
"""
from app.db import get_conn, now_str, STANDARD_ZEITPOSTEN

STATUS_OPTIONEN = [
    "offen",
    "Ortstermin vereinbart",
    "in Bearbeitung",
    "Gutachten abgegeben",
    "abgerechnet",
    "abgeschlossen",
]


# ---------- Fälle ----------

def fall_anlegen(daten: dict) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO faelle
            (aktenzeichen, gericht, abteilung, richter, in_sachen, kinder,
             mutter_name, mutter_anschrift, vater_name, vater_anschrift,
             auftragstext, status, erstellt_am, geaendert_am)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                daten.get("aktenzeichen", ""),
                daten.get("gericht", ""),
                daten.get("abteilung", "Abteilung für Familiensachen"),
                daten.get("richter", ""),
                daten.get("in_sachen", ""),
                daten.get("kinder", ""),
                daten.get("mutter_name", ""),
                daten.get("mutter_anschrift", ""),
                daten.get("vater_name", ""),
                daten.get("vater_anschrift", ""),
                daten.get("auftragstext", ""),
                daten.get("status", "offen"),
                now_str(),
                now_str(),
            ),
        )
        conn.commit()
        return cur.lastrowid


def fall_aktualisieren(fall_id: int, daten: dict):
    felder = [
        "aktenzeichen", "gericht", "abteilung", "richter", "in_sachen", "kinder",
        "mutter_name", "mutter_anschrift", "vater_name", "vater_anschrift",
        "auftragstext", "status",
    ]
    set_klausel = ", ".join(f"{f} = ?" for f in felder)
    werte = [daten.get(f, "") for f in felder]
    with get_conn() as conn:
        conn.execute(
            f"UPDATE faelle SET {set_klausel}, geaendert_am = ? WHERE id = ?",
            werte + [now_str(), fall_id],
        )
        conn.commit()


def fall_loeschen(fall_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM faelle WHERE id = ?", (fall_id,))
        conn.commit()


def faelle_liste(suchtext: str = ""):
    with get_conn() as conn:
        if suchtext:
            like = f"%{suchtext}%"
            rows = conn.execute(
                """SELECT * FROM faelle
                WHERE aktenzeichen LIKE ? OR in_sachen LIKE ? OR kinder LIKE ?
                   OR mutter_name LIKE ? OR vater_name LIKE ?
                ORDER BY geaendert_am DESC""",
                (like, like, like, like, like),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM faelle ORDER BY geaendert_am DESC").fetchall()
        return [dict(r) for r in rows]


def fall_holen(fall_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM faelle WHERE id = ?", (fall_id,)).fetchone()
        return dict(row) if row else None


# ---------- Termine / Fristen ----------

def termin_anlegen(fall_id: int, datum: str, beschreibung: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO termine (fall_id, datum, beschreibung, erledigt) VALUES (?,?,?,0)",
            (fall_id, datum, beschreibung),
        )
        conn.commit()


def termine_liste(fall_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM termine WHERE fall_id = ? ORDER BY datum ASC", (fall_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def termin_erledigt_setzen(termin_id: int, erledigt: bool):
    with get_conn() as conn:
        conn.execute("UPDATE termine SET erledigt = ? WHERE id = ?", (1 if erledigt else 0, termin_id))
        conn.commit()


def termin_loeschen(termin_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM termine WHERE id = ?", (termin_id,))
        conn.commit()


# ---------- Notizen ----------

def notiz_hinzufuegen(fall_id: int, text: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO notizen (fall_id, zeitpunkt, text) VALUES (?,?,?)",
            (fall_id, now_str(), text),
        )
        conn.commit()


def notizen_liste(fall_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM notizen WHERE fall_id = ? ORDER BY id DESC", (fall_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def notiz_loeschen(notiz_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM notizen WHERE id = ?", (notiz_id,))
        conn.commit()


# ---------- Rechnungen ----------

def rechnung_anlegen(
    fall_id: int, rechnungsnummer: str, datum: str,
    stundensatz: float = 100.0, km_satz: float = 0.42,
    mwst_satz: float = 19.0, schreibgebuehr_satz: float = 1.5,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO rechnungen
               (fall_id, rechnungsnummer, datum, stundensatz, km_satz, mwst_satz, schreibgebuehr_satz)
               VALUES (?,?,?,?,?,?,?)""",
            (fall_id, rechnungsnummer, datum, stundensatz, km_satz, mwst_satz, schreibgebuehr_satz),
        )
        rechnung_id = cur.lastrowid
        for i, bezeichnung in enumerate(STANDARD_ZEITPOSTEN):
            conn.execute(
                """INSERT INTO rechnung_zeitposten (rechnung_id, bezeichnung, minuten, reihenfolge)
                   VALUES (?,?,0,?)""",
                (rechnung_id, bezeichnung, i),
            )
        conn.commit()
        return rechnung_id


def rechnung_holen(rechnung_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM rechnungen WHERE id = ?", (rechnung_id,)).fetchone()
        return dict(row) if row else None


def rechnungen_fuer_fall(fall_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM rechnungen WHERE fall_id = ? ORDER BY id DESC", (fall_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def rechnung_aktualisieren(rechnung_id: int, daten: dict):
    felder = [
        "rechnungsnummer", "datum", "stundensatz", "km", "km_satz", "porto",
        "telefon", "zeichen_anzahl", "schreibgebuehr_satz", "kopien_seiten", "mwst_satz",
    ]
    set_klausel = ", ".join(f"{f} = ?" for f in felder)
    werte = [daten.get(f) for f in felder]
    with get_conn() as conn:
        conn.execute(f"UPDATE rechnungen SET {set_klausel} WHERE id = ?", werte + [rechnung_id])
        conn.commit()


def rechnung_loeschen(rechnung_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM rechnungen WHERE id = ?", (rechnung_id,))
        conn.commit()


def zeitposten_fuer_rechnung(rechnung_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM rechnung_zeitposten WHERE rechnung_id = ? ORDER BY reihenfolge ASC",
            (rechnung_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def zeitposten_speichern(posten_id: int, bezeichnung: str, minuten: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE rechnung_zeitposten SET bezeichnung = ?, minuten = ? WHERE id = ?",
            (bezeichnung, minuten, posten_id),
        )
        conn.commit()


def zeitposten_hinzufuegen(rechnung_id: int, bezeichnung: str, minuten: int = 0):
    with get_conn() as conn:
        max_reihenfolge = conn.execute(
            "SELECT COALESCE(MAX(reihenfolge), -1) FROM rechnung_zeitposten WHERE rechnung_id = ?",
            (rechnung_id,),
        ).fetchone()[0]
        conn.execute(
            """INSERT INTO rechnung_zeitposten (rechnung_id, bezeichnung, minuten, reihenfolge)
               VALUES (?,?,?,?)""",
            (rechnung_id, bezeichnung, minuten, max_reihenfolge + 1),
        )
        conn.commit()


def zeitposten_loeschen(posten_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM rechnung_zeitposten WHERE id = ?", (posten_id,))
        conn.commit()


# ---------- Rechnung: freie Zusatzposten (Aufwendungen) ----------

def aufwandsposten_fuer_rechnung(rechnung_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM rechnung_aufwandsposten WHERE rechnung_id = ? ORDER BY reihenfolge ASC",
            (rechnung_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def aufwandsposten_speichern(posten_id: int, bezeichnung: str, betrag: float):
    with get_conn() as conn:
        conn.execute(
            "UPDATE rechnung_aufwandsposten SET bezeichnung = ?, betrag = ? WHERE id = ?",
            (bezeichnung, betrag, posten_id),
        )
        conn.commit()


def aufwandsposten_hinzufuegen(rechnung_id: int, bezeichnung: str, betrag: float = 0):
    with get_conn() as conn:
        max_reihenfolge = conn.execute(
            "SELECT COALESCE(MAX(reihenfolge), -1) FROM rechnung_aufwandsposten WHERE rechnung_id = ?",
            (rechnung_id,),
        ).fetchone()[0]
        conn.execute(
            """INSERT INTO rechnung_aufwandsposten (rechnung_id, bezeichnung, betrag, reihenfolge)
               VALUES (?,?,?,?)""",
            (rechnung_id, bezeichnung, betrag, max_reihenfolge + 1),
        )
        conn.commit()


def aufwandsposten_loeschen(posten_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM rechnung_aufwandsposten WHERE id = ?", (posten_id,))
        conn.commit()


# ---------- Einstellungen ----------

def einstellungen_holen() -> dict:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM einstellungen").fetchall()
        return {r["schluessel"]: r["wert"] for r in rows}


def einstellung_setzen(schluessel: str, wert: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO einstellungen (schluessel, wert) VALUES (?, ?) "
            "ON CONFLICT(schluessel) DO UPDATE SET wert = excluded.wert",
            (schluessel, wert),
        )
        conn.commit()


# ---------- Vorlagen (Word-Dokumentvorlagen für Anschreiben/Gutachten) ----------

VORLAGEN_TYPEN = ["anschreiben", "gutachten"]


def vorlage_anlegen(typ: str, name: str, dateiname: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO vorlagen (typ, name, dateiname, erstellt_am) VALUES (?,?,?,?)",
            (typ, name, dateiname, now_str()),
        )
        conn.commit()
        return cur.lastrowid


def vorlagen_liste(typ: str = None):
    with get_conn() as conn:
        if typ:
            rows = conn.execute(
                "SELECT * FROM vorlagen WHERE typ = ? ORDER BY name ASC", (typ,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM vorlagen ORDER BY typ ASC, name ASC").fetchall()
        return [dict(r) for r in rows]


def vorlage_holen(vorlage_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM vorlagen WHERE id = ?", (vorlage_id,)).fetchone()
        return dict(row) if row else None


def vorlage_loeschen(vorlage_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM vorlagen WHERE id = ?", (vorlage_id,))
        conn.commit()
