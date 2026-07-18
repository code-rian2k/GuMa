<p align="center">
  <img src="app/assets/logo_icon.png" alt="GuMa Logo" width="120">
</p>

# GuMa V11 by HB. - Fallverwaltung für psychologische Gutachten

Lokale Software zur Verwaltung von Gutachterfällen: Falldaten, Fristen,
Notizen, Erstellung von Anschreiben/Gutachten aus selbst hinterlegten
Word-Vorlagen sowie Rechnungserstellung. Alle Daten bleiben ausschließlich
auf diesem Rechner (SQLite-Datenbank in `data/gutachten_manager.db`) - es
gibt keine Cloud-Anbindung.

Gebaut für die Arbeit einer psychologischen Sachverständigen im
Familienrecht - speziell zugeschnitten auf familienpsychologische
Gutachten und den Umgang mit personenbezogenen Falldaten.

**Tech-Stack:** Python 3 · Tkinter (GUI) · SQLite (lokale Datenbank) ·
python-docx + lxml (Word-Vorlagen) · openpyxl (Rechnungs-Export)

## Installation (einmalig)

1. Python installieren: https://www.python.org/downloads/ herunterladen,
   installieren, dabei unbedingt **"Add Python to PATH"** ankreuzen.
2. Diesen Ordner (`gutachten_manager`) an einen festen Ort kopieren, z. B.
   `C:\GuMa`.
3. Doppelklick auf `start_windows.bat`. Beim allerersten Start werden
   automatisch die benötigten Zusatzpakete installiert (dauert ca. 1 Minute,
   Internetverbindung nötig). Danach öffnet sich GuMa.

Ab dem zweiten Mal reicht ein Doppelklick auf `start_windows.bat` - dann
startet die Software sofort, ganz ohne Internet.

Tipp: Rechtsklick auf `start_windows.bat` → "Verknüpfung erstellen" → die
Verknüpfung auf den Desktop legen, dann genügt künftig ein Doppelklick vom
Desktop aus.

## Aufbau

```
gutachten_manager/
  main.py                  Startpunkt
  start_windows.bat         Start unter Windows (Doppelklick)
  requirements.txt          benötigte Python-Pakete
  icon.ico                   Programmsymbol
  app/                       Programmcode (u.a. design.py fürs Erscheinungsbild)
  vorlagen/                   eigene Word-Vorlagen (wird automatisch angelegt)
  data/                       Datenbank (wird automatisch angelegt)
  dokumente/                  erzeugte Word-/Excel-Dateien, je Fall ein Unterordner
  tests/                       automatisierte Tests
```

## Funktionen

- **Fallverwaltung**: Aktenzeichen, Gericht, Parteien, Kinder, Status
- **Fristen & Termine**: mit Erledigt-Markierung
- **Notizen**: laufendes Journal je Fall, automatisch mit Zeitstempel
- **Dokumente**: Anschreiben und Gutachten-Grundgerüst auf Basis selbst
  hinterlegter Word-Vorlagen erzeugen (Titelseite/Anschrift wird automatisch
  befüllt, der eigentliche Gutachtentext wird wie gewohnt in Word verfasst).
  Die Datei wird ohne Rückfrage direkt im Ordner des jeweiligen Falls
  abgelegt (wie alle anderen Dokumente/Unterlagen) und automatisch in Word
  geöffnet. Bereits vorhandene Dateien werden nie überschrieben - bei
  mehrfachem Erstellen wird automatisch durchnummeriert.
- **Eigene Vorlagen**: GuMa liefert selbst keine Word-Vorlagen mit - unter
  Datei-Menü → Einstellungen → "Vorlagen für Anschreiben und Gutachten"
  können beliebig viele eigene `.docx`-Dateien hinzugefügt werden, je Typ
  wird beim Erstellen eines Dokuments per Dropdown ausgewählt, welche Vorlage
  verwendet wird. Damit GuMa Namen, Datum usw. automatisch an der richtigen
  Stelle einträgt, muss die Word-Vorlage an den gewünschten Stellen genau die
  unterstützten Platzhalter der Form `{{NAME}}` enthalten (Groß-/
  Kleinschreibung beachten) - welche das je Dokumenttyp sind, zeigt der
  Einstellungen-Dialog direkt an. Enthält die erzeugte Datei danach noch
  einen dieser Platzhalter unverändert, weist GuMa beim Erstellen darauf hin.
  Beim Hochladen wird die Vorlage automatisch von Resten der Word-
  Änderungsverfolgung sowie Autor-Metadaten bereinigt (siehe Hinweis unten).
- **Rechnungen**: Zeitaufwand (Minuten je Position, automatische Rundung auf
  volle Stunden), Reisekosten, Porto, Telefon, Schreibgebühr (automatisch aus
  Zeichenzahl), Kopierkosten (automatisch gestaffelt: erste 50 Seiten 0,50 €,
  danach 0,15 €/Seite), 19 % MwSt., Export als Excel-Datei
- **Unterlagen**: beliebige Dateien (PDF, Fotos, Scans, ...) zu einem Fall
  hinzufügen - werden in den Fall-Ordner kopiert, dort öffnen/löschen, oder
  den kompletten Fall als ZIP-Datei exportieren (z. B. für den Versand)
- **Stammdaten** (Datei-Menü → Einstellungen): Name, Bankverbindung,
  Steuernummer usw. - werden automatisch in Rechnungen übernommen
- **Speicherort frei wählbar** (Datei-Menü → Einstellungen): Standardmäßig
  liegen alle Fallordner im Unterordner `dokumente` neben dem Programm. Dort
  kann stattdessen ein beliebiger anderer Ordner gewählt werden - wichtig ist
  nur, dass dieser **nicht** mit einem Cloud-Dienst (OneDrive, Dropbox,
  iCloud, Google Drive ...) synchronisiert wird, da dort personenbezogene
  Falldaten liegen. Beim Ändern des Speicherorts bietet GuMa an, bereits
  vorhandene Fälle automatisch in den neuen Ordner zu verschieben.
- **Backup**: Datei-Menü → "Alle Daten sichern (Backup)..." kopiert die
  gesamte Datenbank sowie alle Fall-Ordner (inkl. aller Unterlagen und
  erzeugten Dokumente) gesammelt in einen frei wählbaren Ordner - z. B. eine
  externe Festplatte oder ein Netzlaufwerk/Server. Jedes Backup landet in
  einem eigenen, mit Datum/Uhrzeit benannten Unterordner, sodass ältere
  Sicherungen nicht überschrieben werden.

## Wichtiger Hinweis zu Word-Vorlagen

Wenn Text in Word bei eingeschalteter Änderungsverfolgung ("Änderungen
nachverfolgen") gelöscht wird, verschwindet er nur optisch - in der Datei
bleibt er vollständig gespeichert, auswertbar z. B. mit jedem Zip-/Textwerkzeug,
bis man in Word explizit "Alle Änderungen annehmen" ausführt oder den
Dokumentprüfer nutzt. GuMa bereinigt deshalb jede über die Einstellungen
hinzugefügte Vorlage automatisch programmatisch (`app/docx_bereinigen.py`,
`app/vorlagen.py`) - die eigentliche Datei auf der Festplatte bleibt
unverändert, kopiert wird nur die bereinigte Version in den Vorlagen-Ordner.
Ein automatisierter Test (`tests/test_docx_bereinigen.py`) stellt sicher,
dass dabei wirklich alle Reste entfernt werden.

Trotzdem vorsichtshalber empfehlenswert, bevor eine Vorlage weitergegeben
oder aus einer fremden Quelle übernommen wird: in Word einmal "Überprüfen →
Alle Änderungen annehmen" UND den Dokumentprüfer ("Datei → Informationen →
Auf Probleme überprüfen → Dokument prüfen", Häkchen bei "Kommentare,
Überarbeitungen ...") laufen lassen.

## Datensicherung

Die gesamte Datenbank liegt in einer einzelnen Datei:
`data\gutachten_manager.db`. Diese Datei regelmäßig sichern (z. B. auf einen
USB-Stick oder in einen verschlüsselten Cloud-Ordner kopieren), dann sind
alle Fälle, Notizen und Rechnungen gesichert.

## Tests ausführen (optional, für Entwickler)

```
venv\Scripts\pip install -r requirements.txt pytest
venv\Scripts\pytest tests\
```

## Weiterentwicklung

Der Code liegt vollständig in diesem Repository. Änderungswünsche lassen
sich am einfachsten in einer Coding-Sitzung (z. B. mit Claude Code) direkt
an diesem Repo umsetzen - einfach klonen und loslegen:

```
git clone <URL-dieses-Repos>
```

Wichtig: In diesem Repo liegen **keine** echten Falldaten (siehe
`.gitignore` - `data/`, `dokumente/` und `vorlagen/` werden nie
versioniert).

## Lizenz

GuMa ist freie Software unter der **GNU General Public License v3.0
(GPLv3)** - siehe [LICENSE](LICENSE) bzw. der vollständige, verbindliche
Lizenztext unter <https://www.gnu.org/licenses/gpl-3.0.html>. Kurz
zusammengefasst: Sie dürfen GuMa frei nutzen, verändern und weitergeben,
auch kommerziell - veränderte Versionen müssen dabei ebenfalls unter der
GPLv3 mit offenem Quellcode weitergegeben werden.

© 2026 HB. ([www.hofbrueckl.com](https://www.hofbrueckl.com))
