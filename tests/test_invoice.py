import unittest
from app.invoice import berechne_rechnung, berechne_kopien_kosten, berechne_schreibgebuehr


class TestRechnungsberechnung(unittest.TestCase):
    def test_entspricht_bisheriger_excel_vorlage(self):
        """Nachrechnen des realen Beispiels aus 'vorlage rechnung.xlsx'."""
        zeitposten = [{"minuten": m} for m in [230, 300, 840, 300, 680, 802, 240]]
        ergebnis = berechne_rechnung(
            zeitposten=zeitposten, stundensatz=100, km=992, km_satz=0.42,
            porto=36.99, telefon=2.97, zeichen_anzahl=210650,
            schreibgebuehr_satz=1.5, kopien_seiten=476, mwst_satz=19,
        )
        self.assertEqual(ergebnis.stunden_aufgerundet, 57)
        self.assertEqual(ergebnis.summe_zeitaufwand, 5700)
        self.assertEqual(ergebnis.reisekosten, 416.64)
        self.assertEqual(ergebnis.schreibgebuehr, 316.5)
        self.assertEqual(ergebnis.kopien_kosten, 88.9)
        self.assertEqual(ergebnis.summe_aufwendungen, 862.0)
        self.assertEqual(ergebnis.zwischensumme, 6562.0)
        self.assertEqual(ergebnis.mwst_betrag, 1246.78)
        self.assertEqual(ergebnis.gesamtsumme, 7808.78)

    def test_kopien_unter_grenze(self):
        self.assertEqual(berechne_kopien_kosten(30), 15.0)

    def test_kopien_genau_an_grenze(self):
        self.assertEqual(berechne_kopien_kosten(50), 25.0)

    def test_kopien_ueber_grenze(self):
        # 50 Seiten à 0,50 + 10 Seiten à 0,15 = 25 + 1.5 = 26.5
        self.assertEqual(berechne_kopien_kosten(60), 26.5)

    def test_kopien_null(self):
        self.assertEqual(berechne_kopien_kosten(0), 0.0)

    def test_schreibgebuehr_rundet_auf(self):
        einheiten, betrag = berechne_schreibgebuehr(1001, 1.5)
        self.assertEqual(einheiten, 2)
        self.assertEqual(betrag, 3.0)

    def test_schreibgebuehr_genau_1000(self):
        einheiten, betrag = berechne_schreibgebuehr(1000, 1.5)
        self.assertEqual(einheiten, 1)
        self.assertEqual(betrag, 1.5)

    def test_leere_rechnung_ergibt_null(self):
        ergebnis = berechne_rechnung(
            zeitposten=[], stundensatz=100, km=0, km_satz=0.42, porto=0,
            telefon=0, zeichen_anzahl=0, schreibgebuehr_satz=1.5,
            kopien_seiten=0, mwst_satz=19,
        )
        self.assertEqual(ergebnis.gesamtsumme, 0.0)

    def test_keine_krummen_rundungsfehler_bei_stunden(self):
        # 60 Minuten = genau 1 Stunde, kein Aufrunden auf 2
        zeitposten = [{"minuten": 60}]
        ergebnis = berechne_rechnung(
            zeitposten=zeitposten, stundensatz=100, km=0, km_satz=0.42, porto=0,
            telefon=0, zeichen_anzahl=0, schreibgebuehr_satz=1.5,
            kopien_seiten=0, mwst_satz=19,
        )
        self.assertEqual(ergebnis.stunden_aufgerundet, 1)


if __name__ == "__main__":
    unittest.main()
