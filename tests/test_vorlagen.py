import os
import tempfile
import zipfile
import unittest

import app.db as db_modul

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _docx_mit_aenderungsverfolgung(pfad):
    """Baut eine winzige, gültige .docx-Datei, die einen <w:del>-Block mit
    einem 'gelöschten', aber technisch noch vorhandenen Namen enthält -
    simuliert eine Vorlage, die mit aktiver Änderungsverfolgung aus einem
    früheren Fall wiederverwendet wurde."""
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
      <w:r><w:t>{{{{EMPFAENGER_NAME}}}}</w:t></w:r>
    </w:p>
  </w:body>
</w:document>"""
    with zipfile.ZipFile(pfad, "w") as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document)


try:
    import lxml  # noqa: F401
    LXML_VERFUEGBAR = True
except ImportError:
    LXML_VERFUEGBAR = False


@unittest.skipUnless(LXML_VERFUEGBAR, "lxml nicht installiert (siehe requirements.txt: pip install lxml)")
class TestVorlagenVerwaltung(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        db_modul.DB_PATH = os.path.join(self.tmp_dir, "test.db")
        db_modul.init_db()
        import importlib
        import app.repo as repo_modul
        import app.vorlagen as vorlagen_modul
        importlib.reload(repo_modul)
        importlib.reload(vorlagen_modul)
        global repo, vorlagen
        repo = repo_modul
        vorlagen = vorlagen_modul

        self.basis_ordner = os.path.join(self.tmp_dir, "programm")
        os.makedirs(self.basis_ordner, exist_ok=True)

    def test_vorlage_hinzufuegen_legt_datenbankeintrag_und_datei_an(self):
        quelle = os.path.join(self.tmp_dir, "meine_vorlage.docx")
        _docx_mit_aenderungsverfolgung(quelle)

        vorlage = vorlagen.vorlage_hinzufuegen(self.basis_ordner, "anschreiben", "Standard-Anschreiben", quelle)

        self.assertEqual(vorlage["typ"], "anschreiben")
        self.assertEqual(vorlage["name"], "Standard-Anschreiben")
        self.assertTrue(os.path.isfile(vorlagen.vorlage_pfad(self.basis_ordner, vorlage)))
        self.assertEqual(len(repo.vorlagen_liste("anschreiben")), 1)
        self.assertEqual(len(repo.vorlagen_liste("gutachten")), 0)

    def test_vorlage_hinzufuegen_bereinigt_aenderungsverfolgung(self):
        """Genau das reale Problem: eine wiederverwendete Vorlage kann
        technisch noch Klarnamen aus einem früheren Fall enthalten, obwohl
        der Text in Word als 'gelöscht' angezeigt wird. Der Import muss das
        automatisch entfernen."""
        quelle = os.path.join(self.tmp_dir, "alte_vorlage.docx")
        _docx_mit_aenderungsverfolgung(quelle)

        vorlage = vorlagen.vorlage_hinzufuegen(self.basis_ordner, "anschreiben", "Alt", quelle)

        with zipfile.ZipFile(vorlagen.vorlage_pfad(self.basis_ordner, vorlage)) as z:
            inhalt = z.read("word/document.xml").decode("utf-8")
        self.assertNotIn("Mustermann", inhalt)
        self.assertNotIn("<w:del", inhalt)
        self.assertIn("EMPFAENGER_NAME", inhalt)

        # Das Original an der Quelle bleibt unangetastet
        with zipfile.ZipFile(quelle) as z:
            original_inhalt = z.read("word/document.xml").decode("utf-8")
        self.assertIn("Mustermann", original_inhalt)

    def test_vorlage_entfernen_loescht_datenbankeintrag_und_datei(self):
        quelle = os.path.join(self.tmp_dir, "vorlage.docx")
        _docx_mit_aenderungsverfolgung(quelle)
        vorlage = vorlagen.vorlage_hinzufuegen(self.basis_ordner, "gutachten", "Standard-Gutachten", quelle)
        pfad = vorlagen.vorlage_pfad(self.basis_ordner, vorlage)

        vorlagen.vorlage_entfernen(self.basis_ordner, vorlage)

        self.assertFalse(os.path.isfile(pfad))
        self.assertEqual(repo.vorlagen_liste("gutachten"), [])


if __name__ == "__main__":
    unittest.main()
