import os
import tempfile
import unittest

from app import dateien


class TestDateiverwaltung(unittest.TestCase):
    def setUp(self):
        self.basis = tempfile.mkdtemp()
        self.fall_ordner = os.path.join(self.basis, "dokumente", "1 F 1-26")
        os.makedirs(self.fall_ordner)
        self.quelle_ordner = tempfile.mkdtemp()

    def _testdatei_anlegen(self, name, inhalt="Testinhalt"):
        pfad = os.path.join(self.quelle_ordner, name)
        with open(pfad, "w") as f:
            f.write(inhalt)
        return pfad

    def test_datei_hinzufuegen_kopiert_original(self):
        quelle = self._testdatei_anlegen("foto.jpg", "binärdaten-platzhalter")
        ziel = dateien.datei_hinzufuegen(self.fall_ordner, quelle)
        self.assertTrue(os.path.isfile(ziel))
        self.assertTrue(os.path.isfile(quelle))  # Original bleibt erhalten

    def test_datei_hinzufuegen_vermeidet_namenskollision(self):
        quelle1 = self._testdatei_anlegen("schreiben.pdf", "a")
        dateien.datei_hinzufuegen(self.fall_ordner, quelle1)
        quelle2 = self._testdatei_anlegen("schreiben.pdf", "b")  # gleicher Name, anderer Inhalt
        with open(quelle2, "w") as f:
            f.write("b")
        ziel2 = dateien.datei_hinzufuegen(self.fall_ordner, quelle2)
        self.assertNotEqual(os.path.basename(ziel2), "schreiben.pdf")
        self.assertEqual(len(dateien.dateien_auflisten(self.fall_ordner)), 2)

    def test_dateien_auflisten_leerer_ordner(self):
        self.assertEqual(dateien.dateien_auflisten(self.fall_ordner), [])

    def test_datei_loeschen(self):
        quelle = self._testdatei_anlegen("x.pdf")
        ziel = dateien.datei_hinzufuegen(self.fall_ordner, quelle)
        dateien.datei_loeschen(ziel)
        self.assertFalse(os.path.isfile(ziel))

    def test_fall_als_zip_exportieren(self):
        quelle = self._testdatei_anlegen("bericht.pdf")
        dateien.datei_hinzufuegen(self.fall_ordner, quelle)
        ziel_zip = os.path.join(self.basis, "export.zip")
        erzeugt = dateien.fall_als_zip_exportieren(self.fall_ordner, ziel_zip)
        self.assertTrue(os.path.isfile(erzeugt))

    def test_backup_erstellen_erzeugt_zip_mit_db_dokumenten_und_vorlagen(self):
        db_pfad = os.path.join(self.basis, "gutachten_manager.db")
        with open(db_pfad, "w") as f:
            f.write("fake-db")
        quelle = self._testdatei_anlegen("notiz.pdf")
        dateien.datei_hinzufuegen(self.fall_ordner, quelle)
        vorlagen_ordner = os.path.join(self.basis, "vorlagen")
        os.makedirs(vorlagen_ordner)
        with open(os.path.join(vorlagen_ordner, "anschreiben_vorlage.docx"), "w") as f:
            f.write("fake-docx")

        ziel_zip = os.path.join(self.basis, "backup.zip")
        erzeugt = dateien.backup_erstellen(db_pfad, os.path.join(self.basis, "dokumente"), vorlagen_ordner, ziel_zip)

        self.assertTrue(os.path.isfile(erzeugt))
        import zipfile
        with zipfile.ZipFile(erzeugt) as zf:
            namen = zf.namelist()
        self.assertIn("gutachten_manager.db", namen)
        self.assertIn("dokumente/1 F 1-26/notiz.pdf", namen)
        self.assertIn("vorlagen/anschreiben_vorlage.docx", namen)

    def test_backup_wiederherstellen_stellt_db_dokumente_und_vorlagen_wieder_her(self):
        db_pfad = os.path.join(self.basis, "gutachten_manager.db")
        with open(db_pfad, "w") as f:
            f.write("fake-db-inhalt")
        quelle = self._testdatei_anlegen("notiz.pdf")
        dateien.datei_hinzufuegen(self.fall_ordner, quelle)
        vorlagen_ordner = os.path.join(self.basis, "vorlagen")
        os.makedirs(vorlagen_ordner)
        with open(os.path.join(vorlagen_ordner, "vorlage.docx"), "w") as f:
            f.write("fake-docx-inhalt")

        ziel_zip = os.path.join(self.basis, "backup.zip")
        dateien.backup_erstellen(db_pfad, os.path.join(self.basis, "dokumente"), vorlagen_ordner, ziel_zip)

        # Simuliert eine frische, noch leere GuMa-Installation auf einem neuen Rechner
        neue_installation = tempfile.mkdtemp()
        neue_db = os.path.join(neue_installation, "gutachten_manager.db")
        neue_dokumente = os.path.join(neue_installation, "dokumente")
        neue_vorlagen = os.path.join(neue_installation, "vorlagen")

        dateien.backup_wiederherstellen(ziel_zip, neue_db, neue_dokumente, neue_vorlagen)

        with open(neue_db) as f:
            self.assertEqual(f.read(), "fake-db-inhalt")
        self.assertTrue(os.path.isfile(os.path.join(neue_dokumente, "1 F 1-26", "notiz.pdf")))
        self.assertTrue(os.path.isfile(os.path.join(neue_vorlagen, "vorlage.docx")))

    def test_fall_ordner_loeschen(self):
        quelle = self._testdatei_anlegen("y.pdf")
        dateien.datei_hinzufuegen(self.fall_ordner, quelle)
        dateien.fall_ordner_loeschen(self.fall_ordner)
        self.assertFalse(os.path.isdir(self.fall_ordner))

    def test_ermittle_dokumente_ordner_standard_ohne_einstellung(self):
        ergebnis = dateien.ermittle_dokumente_ordner(self.basis, {"dokumente_ordner": ""})
        self.assertEqual(ergebnis, os.path.join(self.basis, "dokumente"))
        self.assertTrue(os.path.isdir(ergebnis))

    def test_ermittle_dokumente_ordner_mit_eigenem_pfad(self):
        eigener_ordner = os.path.join(self.basis, "Woanders", "Fallakten")
        ergebnis = dateien.ermittle_dokumente_ordner(self.basis, {"dokumente_ordner": eigener_ordner})
        self.assertEqual(ergebnis, eigener_ordner)
        self.assertTrue(os.path.isdir(eigener_ordner))

    def test_alle_faelle_verschieben(self):
        quelle = self._testdatei_anlegen("bericht.pdf")
        dateien.datei_hinzufuegen(self.fall_ordner, quelle)
        alter_dokumente_ordner = os.path.dirname(self.fall_ordner)

        neuer_dokumente_ordner = os.path.join(self.basis, "Neuer_Speicherort")
        dateien.alle_faelle_verschieben(alter_dokumente_ordner, neuer_dokumente_ordner)

        verschobene_datei = os.path.join(neuer_dokumente_ordner, "1 F 1-26", "bericht.pdf")
        self.assertTrue(os.path.isfile(verschobene_datei))
        self.assertFalse(os.path.isdir(self.fall_ordner))


if __name__ == "__main__":
    unittest.main()
