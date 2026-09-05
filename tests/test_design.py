"""Tests für app/design.py - insbesondere die Reiterbreiten-Berechnung, die
den mehrfachen Fehlerbericht "Reiter-Beschriftung abgeschnitten" beheben soll."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.tk_stub import build_stub_tkinter
build_stub_tkinter()

from tkinter import ttk
from app import design


class _StyleAttrappe:
    """Testdouble für ttk.Style: merkt sich nur den letzten configure()-Aufruf."""

    def __init__(self):
        self.konfiguriert = {}

    def configure(self, name, **kw):
        self.konfiguriert[name] = kw


class TestNotebookTabBreiteAnpassen(unittest.TestCase):
    def test_ohne_reiter_passiert_nichts(self):
        notebook = ttk.Notebook()
        style = _StyleAttrappe()
        design.notebook_tab_breite_anpassen(notebook, style)
        self.assertEqual(style.konfiguriert, {})

    def test_breite_richtet_sich_nach_laengstem_reitertitel(self):
        notebook = ttk.Notebook()
        for titel in ["Übersicht", "Falldaten", "Fristen & Termine", "Notizen"]:
            notebook.add(object(), text=titel)
        style = _StyleAttrappe()

        design.notebook_tab_breite_anpassen(notebook, style, sicherheitsabstand=40)

        breite = style.konfiguriert["TNotebook.Tab"]["width"]
        # Negativer Wert = absolute Pixelbreite (nicht Zeichenanzahl) bei ttk.
        self.assertLess(breite, 0)
        laengster_titel_breite = len("Fristen & Termine") * 10  # Stub: 10px/Zeichen
        self.assertEqual(breite, -(laengster_titel_breite + 40))

    def test_kurze_reiter_beeinflussen_die_breite_nicht(self):
        notebook = ttk.Notebook()
        notebook.add(object(), text="Fristen & Termine")
        style_lang = _StyleAttrappe()
        design.notebook_tab_breite_anpassen(notebook, style_lang)

        notebook_kurz = ttk.Notebook()
        for titel in ["Fristen & Termine", "Notizen"]:
            notebook_kurz.add(object(), text=titel)
        style_kurz = _StyleAttrappe()
        design.notebook_tab_breite_anpassen(notebook_kurz, style_kurz)

        # Ein zusätzlicher kürzerer Reiter darf die (vom längsten Titel
        # bestimmte) Breite nicht verändern.
        self.assertEqual(
            style_lang.konfiguriert["TNotebook.Tab"]["width"],
            style_kurz.konfiguriert["TNotebook.Tab"]["width"],
        )


if __name__ == "__main__":
    unittest.main()
