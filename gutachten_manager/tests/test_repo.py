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

    def test_einstellungen_speichern_und_lesen(self):
        repo.einstellung_setzen("iban", "DE00 1234 5678 9000 0000 00")
        werte = repo.einstellungen_holen()
        self.assertEqual(werte["iban"], "DE00 1234 5678 9000 0000 00")


if __name__ == "__main__":
    unittest.main()
