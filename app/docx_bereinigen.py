"""
Entfernt Word-Änderungsverfolgung (Track Changes) und persönliche Metadaten
vollständig aus einer .docx-Datei.

Hintergrund: Wenn in Word Text bei eingeschalteter Änderungsverfolgung
gelöscht wird ("Änderungen nachverfolgen"), sieht das für die Autorin so
aus, als sei der Text weg - tatsächlich bleibt er aber vollständig in der
Datei gespeichert (als <w:del>-Block), damit die Änderung rückgängig gemacht
werden kann. Das gilt auch nach dem Schließen von Word. Erst "Alle Änderungen
annehmen" bzw. der Word-Dokumentprüfer entfernt das wirklich.

Diese Funktion macht genau das programmatisch, für alle Textteile eines
.docx (Haupttext, Kopf-/Fußzeilen, Fuß-/Endnoten, Kommentare) und bereinigt
zusätzlich Autor-Metadaten in den Dokumenteigenschaften.
"""
import re
import zipfile

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _qn(tag):
    return f"{{{W_NS}}}{tag}"


def _bereinige_xml(xml_bytes: bytes) -> bytes:
    parser = etree.XMLParser(remove_blank_text=False, recover=True)
    root = etree.fromstring(xml_bytes, parser)

    # Gelöschte Inhalte (inkl. moveFrom = alter Standort eines verschobenen
    # Textes) ENDGÜLTIG entfernen - das ist der kritische Teil: der Text in
    # <w:del> ist trotz sichtbarer "Löschung" im Dateiinhalt weiterhin
    # vollständig vorhanden, bis er hier entfernt wird.
    for tag in ("del", "moveFrom"):
        for el in list(root.iter(_qn(tag))):
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)

    # Eingefügte Inhalte (inkl. moveTo) übernehmen: Wrapper entfernen, Inhalt behalten
    for tag in ("ins", "moveTo"):
        for el in list(root.iter(_qn(tag))):
            parent = el.getparent()
            if parent is None:
                continue
            idx = list(parent).index(el)
            for kind in list(el):
                el.remove(kind)
                parent.insert(idx, kind)
                idx += 1
            parent.remove(el)

    # Formatierungs-Änderungsspuren entfernen (i.d.R. kein Text, aber sicherheitshalber)
    for tag in ("rPrChange", "pPrChange", "sectPrChange", "tblPrChange",
                "tblGridChange", "trPrChange", "tcPrChange", "numberingChange"):
        for el in list(root.iter(_qn(tag))):
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)

    # Kommentar-Verknüpfungen entfernen (der Kommentartext selbst steckt in
    # einem separaten Teil comments.xml, der beim Bereinigen ebenfalls
    # durchlaufen bzw. entfernt wird)
    for tag in ("commentRangeStart", "commentRangeEnd", "commentReference"):
        for el in list(root.iter(_qn(tag))):
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def bereinige_docx(quelle: str, ziel: str):
    """Liest `quelle`, entfernt Änderungsverfolgung + Autor-Metadaten, schreibt nach `ziel`."""
    with zipfile.ZipFile(quelle, "r") as zin:
        namen = zin.namelist()
        inhalte = {n: zin.read(n) for n in namen}

    zu_bereinigende_teile = [
        n for n in namen
        if n.startswith("word/") and n.endswith(".xml")
        and (n.startswith("word/document") or n.startswith("word/header")
             or n.startswith("word/footer") or n.startswith("word/footnotes")
             or n.startswith("word/endnotes") or n.startswith("word/comments"))
    ]

    for teil in zu_bereinigende_teile:
        inhalte[teil] = _bereinige_xml(inhalte[teil])

    if "docProps/core.xml" in inhalte:
        core = inhalte["docProps/core.xml"].decode("utf-8")
        core = re.sub(r"<dc:creator>.*?</dc:creator>", "<dc:creator>GuMa</dc:creator>", core)
        core = re.sub(r"<cp:lastModifiedBy>.*?</cp:lastModifiedBy>", "<cp:lastModifiedBy>GuMa</cp:lastModifiedBy>", core)
        core = re.sub(r"<cp:revision>.*?</cp:revision>", "<cp:revision>1</cp:revision>", core)
        inhalte["docProps/core.xml"] = core.encode("utf-8")

    with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in namen:
            zout.writestr(n, inhalte[n])


def enthaelt_versteckte_aenderungen(pfad: str) -> bool:
    """Prüft, ob eine .docx noch Reste von Änderungsverfolgung enthält (für Tests/Kontrolle)."""
    with zipfile.ZipFile(pfad, "r") as z:
        for name in z.namelist():
            if name.startswith("word/") and name.endswith(".xml"):
                inhalt = z.read(name)
                if b"<w:del " in inhalt or b"<w:delText" in inhalt or b"<w:ins " in inhalt:
                    return True
    return False
