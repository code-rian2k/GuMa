import unittest

from app.kalenderfeld import (
    gesperrte_wochentage_lesen, gesperrte_wochentage_schreiben, ist_gesperrter_tag,
)


class TestGesperrteWochentage(unittest.TestCase):
    def test_lesen_leerer_wert_ergibt_leere_menge(self):
        self.assertEqual(gesperrte_wochentage_lesen({"gesperrte_wochentage": ""}), set())
        self.assertEqual(gesperrte_wochentage_lesen({}), set())

    def test_lesen_und_schreiben_sind_umkehrbar(self):
        wochentage = {0, 5, 6}
        text = gesperrte_wochentage_schreiben(wochentage)
        self.assertEqual(gesperrte_wochentage_lesen({"gesperrte_wochentage": text}), wochentage)

    def test_schreiben_sortiert_und_kommagetrennt(self):
        self.assertEqual(gesperrte_wochentage_schreiben({6, 0, 5}), "0,5,6")

    def test_ist_gesperrter_tag_erkennt_wochenende(self):
        # 19.09.2026 ist ein Samstag (Wochentag 5)
        self.assertTrue(ist_gesperrter_tag("19.09.2026", {5, 6}))
        self.assertTrue(ist_gesperrter_tag("20.09.2026", {5, 6}))  # Sonntag

    def test_ist_gesperrter_tag_erkennt_werktag_als_nicht_gesperrt(self):
        # 21.09.2026 ist ein Montag
        self.assertFalse(ist_gesperrter_tag("21.09.2026", {5, 6}))

    def test_ist_gesperrter_tag_ohne_gesperrte_wochentage(self):
        self.assertFalse(ist_gesperrter_tag("19.09.2026", set()))

    def test_ist_gesperrter_tag_bei_unklarem_datum_keine_warnung(self):
        self.assertFalse(ist_gesperrter_tag("kein Datum", {0, 1, 2, 3, 4, 5, 6}))
        self.assertFalse(ist_gesperrter_tag("", {0, 1, 2, 3, 4, 5, 6}))


if __name__ == "__main__":
    unittest.main()
