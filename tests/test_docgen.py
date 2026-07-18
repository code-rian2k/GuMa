import os
import unittest
import tempfile
import docx

from app.docgen import anschreiben_erstellen, gutachten_erstellen, offene_platzhalter


class TestDokumentErstellung(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.fall = {
            "empfaenger_anrede": "Frau", "empfaenger_name": "Musterfrau",
            "datum": "08.07.2026", "richter": "Herrn Müller, Richter am Amtsgericht Augsburg",
            "kinder": "Max und Lisa", "gericht": "Augsburg",
            "abteilung": "Abteilung für Familiensachen", "aktenzeichen": "123 F 456/26",
        }
        self.einstellungen = {"telefon": "0821/349 43 73", "name": "Raphaela Hofbrückl, Dipl.-Psych."}

    def test_anschreiben_hat_keine_offenen_platzhalter(self):
        pfad = os.path.join(self.tmp, "anschreiben.docx")
        anschreiben_erstellen(self.fall, self.einstellungen, pfad)
        self.assertEqual(offene_platzhalter(pfad), set())

    def test_anschreiben_enthaelt_falldaten(self):
        pfad = os.path.join(self.tmp, "anschreiben.docx")
        anschreiben_erstellen(self.fall, self.einstellungen, pfad)
        text = "\n".join(p.text for p in docx.Document(pfad).paragraphs)
        self.assertIn("Musterfrau", text)
        self.assertIn("Max und Lisa", text)
        self.assertIn("0821/349 43 73", text)

    def test_gutachten_hat_keine_offenen_platzhalter(self):
        pfad = os.path.join(self.tmp, "gutachten.docx")
        gutachten_erstellen(self.fall, pfad)
        self.assertEqual(offene_platzhalter(pfad), set())

    def test_gutachten_enthaelt_aktenzeichen(self):
        pfad = os.path.join(self.tmp, "gutachten.docx")
        gutachten_erstellen(self.fall, pfad)
        text = "\n".join(p.text for p in docx.Document(pfad).paragraphs)
        self.assertIn("123 F 456/26", text)
        self.assertIn("Augsburg", text)

    def test_leere_felder_erzeugen_keinen_fehler(self):
        pfad = os.path.join(self.tmp, "anschreiben_leer.docx")
        anschreiben_erstellen({}, {}, pfad)
        self.assertTrue(os.path.exists(pfad))


if __name__ == "__main__":
    unittest.main()
