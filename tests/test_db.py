import os
import sqlite3
import tempfile
import unittest

import app.db as db


class TestSchemaMigration(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        db.DB_PATH = os.path.join(self.tmp_dir, "test.db")

    def test_init_db_ist_mehrfach_aufrufbar_ohne_fehler(self):
        db.init_db()
        db.init_db()  # z.B. jeder Programmstart - darf nicht erneut scheitern

    def test_fehlende_spalte_wird_bei_bestehender_datenbank_nachgeruestet(self):
        """Simuliert genau den geschilderten Fall: eine 'alte' Datenbank
        (z.B. aus einem älteren Backup importiert) hat Spalten, die es in der
        aktuellen Version inzwischen gibt, noch nicht. init_db() muss sie
        automatisch nachrüsten, ohne bestehende Daten zu verlieren."""
        conn = sqlite3.connect(db.DB_PATH)
        conn.execute("CREATE TABLE faelle (id INTEGER PRIMARY KEY AUTOINCREMENT, aktenzeichen TEXT)")
        conn.execute("INSERT INTO faelle (aktenzeichen) VALUES ('1 F 1/26')")
        conn.commit()
        conn.close()

        db.init_db()

        conn = sqlite3.connect(db.DB_PATH)
        conn.row_factory = sqlite3.Row
        vorhandene_spalten = {row["name"] for row in conn.execute("PRAGMA table_info(faelle)")}
        zeile = conn.execute("SELECT * FROM faelle").fetchone()
        conn.close()

        erwartete_spalten = {name for name, _definition in db.TABELLEN_SPALTEN["faelle"]}
        self.assertEqual(vorhandene_spalten, erwartete_spalten)  # alle neuen Spalten nachgerüstet
        self.assertEqual(zeile["aktenzeichen"], "1 F 1/26")  # Altdaten unverändert
        self.assertEqual(zeile["status"], "offen")  # Spalte mit DEFAULT wird auch für Altzeilen befüllt
        self.assertIsNone(zeile["in_sachen"])  # Spalte ohne DEFAULT bleibt für Altzeilen leer

    def test_nachgeruestete_spalte_ist_ueber_repo_ganz_normal_nutzbar(self):
        """End-to-End: nach der Migration lässt sich die nachgerüstete Spalte
        über die repo-Funktionen lesen und schreiben - kein Sonderfall."""
        conn = sqlite3.connect(db.DB_PATH)
        conn.execute("CREATE TABLE faelle (id INTEGER PRIMARY KEY AUTOINCREMENT, aktenzeichen TEXT)")
        conn.execute("INSERT INTO faelle (aktenzeichen) VALUES ('1 F 1/26')")
        conn.commit()
        conn.close()

        db.init_db()

        import importlib
        import app.repo as repo_modul
        importlib.reload(repo_modul)

        fall = repo_modul.faelle_liste()[0]
        repo_modul.fall_aktualisieren(fall["id"], {"aktenzeichen": "1 F 1/26", "status": "in Bearbeitung"})
        aktualisiert = repo_modul.fall_holen(fall["id"])
        self.assertEqual(aktualisiert["status"], "in Bearbeitung")

    def test_ueberzaehlige_spalte_aus_altem_backup_stoert_nicht(self):
        """Der umgekehrte Fall: eine 'alte' Datenbank hat eine Spalte, die es
        in der aktuellen Version nicht mehr gibt (z.B. ein entferntes
        Feature). init_db() darf daran nicht scheitern, und die Spalte bleibt
        einfach ungenutzt in der Datenbank liegen."""
        conn = sqlite3.connect(db.DB_PATH)
        conn.execute(
            "CREATE TABLE faelle (id INTEGER PRIMARY KEY AUTOINCREMENT, aktenzeichen TEXT, akademischer_titel TEXT)"
        )
        conn.execute("INSERT INTO faelle (aktenzeichen, akademischer_titel) VALUES ('1 F 1/26', 'Dr.')")
        conn.commit()
        conn.close()

        db.init_db()  # darf nicht scheitern

        import importlib
        import app.repo as repo_modul
        importlib.reload(repo_modul)

        fall = repo_modul.faelle_liste()[0]
        self.assertEqual(fall["aktenzeichen"], "1 F 1/26")


if __name__ == "__main__":
    unittest.main()
