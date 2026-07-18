import os
import tempfile
import zipfile
import unittest

try:
    from app.docx_bereinigen import bereinige_docx, enthaelt_versteckte_aenderungen
    LXML_VERFUEGBAR = True
except ImportError:
    # lxml ist bewusst NICHT Teil von requirements.txt (wird von der App im
    # normalen Betrieb nicht gebraucht, nur für dieses Wartungswerkzeug).
    # Für diesen Test lokal: "pip install lxml"
    LXML_VERFUEGBAR = False

from app.docgen import TEMPLATES_DIR


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _docx_mit_aenderungsverfolgung(pfad):
    """Baut eine winzige, gültige .docx-Datei, die einen <w:del>-Block mit
    einem 'gelöschten', aber technisch noch vorhandenen Namen enthält -
    simuliert genau das reale Problem."""
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '</Types>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/></Relationships>'
    )
    document = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{W_NS}">
  <w:body>
    <w:p>
      <w:del w:id="1" w:author="Test" w:date="2026-01-01T00:00:00Z">
        <w:r><w:delText>Geheimer Familienname Mustermann</w:delText></w:r>
      </w:del>
      <w:ins w:id="2" w:author="Test" w:date="2026-01-01T00:00:00Z">
        <w:r><w:t>Aktueller Text</w:t></w:r>
      </w:ins>
    </w:p>
  </w:body>
</w:document>"""
    with zipfile.ZipFile(pfad, "w") as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document)


@unittest.skipUnless(LXML_VERFUEGBAR, "lxml nicht installiert (nur für dieses Wartungswerkzeug nötig: pip install lxml)")
class TestDocxBereinigen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_geloeschter_name_wird_vollstaendig_entfernt(self):
        quelle = os.path.join(self.tmp, "mit_aenderungen.docx")
        ziel = os.path.join(self.tmp, "bereinigt.docx")
        _docx_mit_aenderungsverfolgung(quelle)

        self.assertTrue(enthaelt_versteckte_aenderungen(quelle))

        bereinige_docx(quelle, ziel)

        with zipfile.ZipFile(ziel) as z:
            inhalt = z.read("word/document.xml").decode("utf-8")
        self.assertNotIn("Mustermann", inhalt)
        self.assertNotIn("Geheimer Familienname", inhalt)
        self.assertNotIn("<w:del", inhalt)
        self.assertNotIn("<w:delText", inhalt)
        # Eingefügter Text bleibt erhalten, nur der Tracking-Wrapper verschwindet
        self.assertIn("Aktueller Text", inhalt)
        self.assertNotIn("<w:ins", inhalt)

        self.assertFalse(enthaelt_versteckte_aenderungen(ziel))

    def test_ausgelieferte_vorlagen_enthalten_keine_versteckten_aenderungen(self):
        """
        Schutztest: stellt dauerhaft sicher, dass die mit GuMa ausgelieferten
        Word-Vorlagen keine Reste von Word-Änderungsverfolgung mehr enthalten
        - genau das Problem, das bei der echten Gutachten-Vorlage auftrat
        (Klarnamen/Geburtsdaten einer früheren Familie waren über
        "gelöschte" Änderungen weiterhin im Dateiinhalt vorhanden).
        """
        for dateiname in ["anschreiben_vorlage.docx", "gutachten_vorlage.docx"]:
            pfad = os.path.join(TEMPLATES_DIR, dateiname)
            if os.path.isfile(pfad):
                self.assertFalse(
                    enthaelt_versteckte_aenderungen(pfad),
                    f"{dateiname} enthält noch Reste von Word-Änderungsverfolgung!",
                )


if __name__ == "__main__":
    unittest.main()
