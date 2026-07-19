import os
import unittest
import tempfile

import app.db as db_modul


class TestRepository(unittest.TestCase):
    def setUp(self):
        # Eigene, temporäre Datenbank pro Test, damit nichts mit echten Falldaten kollidiert
        self.tmp_dir = tempfile.mkdtemp()
        db_modul.DB_PATH = os.path.join(self.tmp_dir, "test.db")
        db_modul.init_db()
        import importlib
        import app.repo as repo_modul
        importlib.reload(repo_modul)
        global repo
        repo = repo_modul

    def test_fall_anlegen_und_holen(self):
        fall_id = repo.fall_anlegen({"aktenzeichen": "1 F 1/26", "in_sachen": "Test"})
        fall = repo.fall_holen(fall_id)
        self.assertEqual(fall["aktenzeichen"], "1 F 1/26")
        self.assertEqual(fall["status"], "offen")

    def test_fall_aktualisieren(self):
        fall_id = repo.fall_anlegen({"aktenzeichen": "1 F 1/26"})
        repo.fall_aktualisieren(fall_id, {"aktenzeichen": "2 F 2/26", "status": "in Bearbeitung"})
        fall = repo.fall_holen(fall_id)
        self.assertEqual(fall["aktenzeichen"], "2 F 2/26")
        self.assertEqual(fall["status"], "in Bearbeitung")

    def test_fall_loeschen_entfernt_abhaengige_daten(self):
        fall_id = repo.fall_anlegen({"aktenzeichen": "1 F 1/26"})
        repo.notiz_hinzufuegen(fall_id, "Testnotiz")
        repo.termin_anlegen(fall_id, "01.01.2026", "Testtermin")
        repo.fall_loeschen(fall_id)
        self.assertIsNone(repo.fall_holen(fall_id))
        self.assertEqual(repo.notizen_liste(fall_id), [])
        self.assertEqual(repo.termine_liste(fall_id), [])

    def test_suche_findet_fall(self):
        repo.fall_anlegen({"aktenzeichen": "5 F 99/26", "in_sachen": "Mustermann ./. Musterfrau"})
        treffer = repo.faelle_liste("Mustermann")
        self.assertEqual(len(treffer), 1)

    def test_rechnung_hat_standard_zeitposten(self):
        fall_id = repo.fall_anlegen({"aktenzeichen": "1 F 1/26"})
        rechnung_id = repo.rechnung_anlegen(fall_id, "01-2026", "08.07.2026")
        posten = repo.zeitposten_fuer_rechnung(rechnung_id)
        self.assertEqual(len(posten), 7)

    def test_rechnung_anlegen_nutzt_uebergebene_standard_saetze(self):
        fall_id = repo.fall_anlegen({"aktenzeichen": "1 F 1/26"})
        rechnung_id = repo.rechnung_anlegen(
            fall_id, "01-2026", "08.07.2026",
            stundensatz=120, km_satz=0.5, mwst_satz=7, schreibgebuehr_satz=2.0,
        )
        rechnung = repo.rechnung_holen(rechnung_id)
        self.assertEqual(rechnung["stundensatz"], 120)
        self.assertEqual(rechnung["km_satz"], 0.5)
        self.assertEqual(rechnung["mwst_satz"], 7)
        self.assertEqual(rechnung["schreibgebuehr_satz"], 2.0)

    def test_aufwandsposten_hinzufuegen_speichern_loeschen(self):
        fall_id = repo.fall_anlegen({"aktenzeichen": "1 F 1/26"})
        rechnung_id = repo.rechnung_anlegen(fall_id, "01-2026", "08.07.2026")

        repo.aufwandsposten_hinzufuegen(rechnung_id, "Fahrtkosten Bahn", 45)
        posten = repo.aufwandsposten_fuer_rechnung(rechnung_id)
        self.assertEqual(len(posten), 1)
        self.assertEqual(posten[0]["bezeichnung"], "Fahrtkosten Bahn")
        self.assertEqual(posten[0]["betrag"], 45)

        repo.aufwandsposten_speichern(posten[0]["id"], "Fahrtkosten Auto", 60)
        posten = repo.aufwandsposten_fuer_rechnung(rechnung_id)
        self.assertEqual(posten[0]["bezeichnung"], "Fahrtkosten Auto")
        self.assertEqual(posten[0]["betrag"], 60)

        repo.aufwandsposten_loeschen(posten[0]["id"])
        self.assertEqual(repo.aufwandsposten_fuer_rechnung(rechnung_id), [])

    def test_aufwandsposten_werden_mit_rechnung_geloescht(self):
        fall_id = repo.fall_anlegen({"aktenzeichen": "1 F 1/26"})
        rechnung_id = repo.rechnung_anlegen(fall_id, "01-2026", "08.07.2026")
        repo.aufwandsposten_hinzufuegen(rechnung_id, "Sonstiges", 10)

        repo.rechnung_loeschen(rechnung_id)

        self.assertEqual(repo.aufwandsposten_fuer_rechnung(rechnung_id), [])

    def test_einstellungen_speichern_und_lesen(self):
        repo.einstellung_setzen("iban", "DE00 1234 5678 9000 0000 00")
        werte = repo.einstellungen_holen()
        self.assertEqual(werte["iban"], "DE00 1234 5678 9000 0000 00")


if __name__ == "__main__":
    unittest.main()
