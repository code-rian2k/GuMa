import datetime
import unittest

from app.kalenderfeld import (
    gesperrte_wochentage_lesen, gesperrte_wochentage_schreiben, ist_gesperrter_tag,
    kalender_termine_markieren, TERMIN_TAG_TAG,
)


class _KalenderAttrappe:
    """Testdouble für ein tkcalendar-Kalender-Widget, ohne echtes Tk."""

    def __init__(self):
        self.erstellte_events = []
        self.entfernte_tags = []
        self.konfigurierte_tags = {}

    def calevent_remove(self, tag=None):
        self.entfernte_tags.append(tag)

    def calevent_create(self, date, text, tags):
        self.erstellte_events.append((date, text, tags))

    def tag_config(self, tag, **kw):
        self.konfigurierte_tags[tag] = kw


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


class TestKalenderTermineMarkieren(unittest.TestCase):
    def test_markiert_jeden_termin_und_liefert_datum_zu_fall_mapping(self):
        kalender = _KalenderAttrappe()
        termine = [
            {"datum": "19.09.2026", "beschreibung": "Ortstermin", "fall_id": 1},
            {"datum": "21.09.2026", "beschreibung": "Anhörung", "fall_id": 2},
        ]

        mapping = kalender_termine_markieren(kalender, termine)

        self.assertEqual(len(kalender.erstellte_events), 2)
        self.assertEqual(mapping, {
            datetime.date(2026, 9, 19): 1,
            datetime.date(2026, 9, 21): 2,
        })
        self.assertIn(TERMIN_TAG_TAG, kalender.konfigurierte_tags)

    def test_mehrere_termine_am_selben_tag_erster_gewinnt_im_mapping(self):
        kalender = _KalenderAttrappe()
        termine = [
            {"datum": "19.09.2026", "beschreibung": "Zuerst", "fall_id": 1},
            {"datum": "19.09.2026", "beschreibung": "Danach", "fall_id": 2},
        ]

        mapping = kalender_termine_markieren(kalender, termine)

        self.assertEqual(mapping, {datetime.date(2026, 9, 19): 1})
        self.assertEqual(len(kalender.erstellte_events), 2)  # beide trotzdem im Kalender markiert

    def test_entfernt_vorherige_markierungen_vor_dem_neu_markieren(self):
        kalender = _KalenderAttrappe()
        kalender_termine_markieren(kalender, [])
        self.assertEqual(kalender.entfernte_tags, [TERMIN_TAG_TAG])

    def test_unklares_datum_wird_uebersprungen(self):
        kalender = _KalenderAttrappe()
        mapping = kalender_termine_markieren(kalender, [{"datum": "kein Datum", "fall_id": 1}])
        self.assertEqual(mapping, {})
        self.assertEqual(kalender.erstellte_events, [])


if __name__ == "__main__":
    unittest.main()
