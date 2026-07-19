import os
import tempfile
import unittest

import openpyxl

from app.invoice_export import exportiere_rechnung_xlsx


class TestRechnungExport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.fall = {"gericht": "Augsburg", "abteilung": "Abteilung für Familiensachen",
                     "in_sachen": "Mustermann ./. Musterfrau", "aktenzeichen": "1 F 1/26"}
        self.rechnung = {
            "datum": "08.07.2026", "rechnungsnummer": "01-2026",
            "stundensatz": 100, "km": 0, "km_satz": 0.42, "porto": 0, "telefon": 0,
            "zeichen_anzahl": 0, "schreibgebuehr_satz": 1.5, "kopien_seiten": 20, "mwst_satz": 19,
        }
        self.einstellungen = {}

    def _alle_zellwerte(self, pfad):
        wb = openpyxl.load_workbook(pfad)
        ws = wb.active
        return [zelle.value for zeile in ws.iter_rows() for zelle in zeile if zelle.value is not None]

    def test_export_enthaelt_zusatzposten_zeile(self):
        pfad = os.path.join(self.tmp, "rechnung.xlsx")
        exportiere_rechnung_xlsx(
            pfad, self.fall, self.rechnung, [], self.einstellungen,
            zusatzposten=[{"bezeichnung": "Fahrtkosten Bahn", "betrag": 45.0}],
        )
        werte = self._alle_zellwerte(pfad)
        self.assertIn("Fahrtkosten Bahn", werte)
        self.assertIn(45.0, werte)

    def test_export_ohne_zusatzposten_funktioniert_weiterhin(self):
        pfad = os.path.join(self.tmp, "rechnung.xlsx")
        ergebnis = exportiere_rechnung_xlsx(pfad, self.fall, self.rechnung, [], self.einstellungen)
        self.assertTrue(os.path.isfile(pfad))
        self.assertEqual(ergebnis.zusatzposten_summe, 0.0)

    def test_export_nutzt_konfigurierte_kopien_staffel_aus_einstellungen(self):
        pfad = os.path.join(self.tmp, "rechnung.xlsx")
        einstellungen = {
            "kopien_grenze": "10", "kopien_satz_bis_grenze": "1.0", "kopien_satz_ab_grenze": "0.2",
        }
        ergebnis = exportiere_rechnung_xlsx(pfad, self.fall, self.rechnung, [], einstellungen)
        # 20 Kopien-Seiten: 10 x 1,00 € + 10 x 0,20 € = 12,00 €
        self.assertEqual(ergebnis.kopien_kosten, 12.0)
        werte = self._alle_zellwerte(pfad)
        self.assertIn(1.0, werte)
        self.assertIn(0.2, werte)

    def test_export_faellt_ohne_einstellung_auf_werkseinstellung_zurueck(self):
        pfad = os.path.join(self.tmp, "rechnung.xlsx")
        ergebnis = exportiere_rechnung_xlsx(pfad, self.fall, self.rechnung, [], {})
        # Werkseinstellung: 20 Seiten liegen unter der Grenze von 50 -> 20 x 0,50 €
        self.assertEqual(ergebnis.kopien_kosten, 10.0)


if __name__ == "__main__":
    unittest.main()
