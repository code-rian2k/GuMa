# Hinweise für Claude

## Versionsnummer

Schema: `V<Jahr, 2-stellig>.<Monat ohne führende Null>` (z. B. `V26.7` für Juli 2026).

Bei jeder Änderung, die gemerged wird, die Versionsnummer auf den aktuellen
Jahr/Monat aktualisieren (nicht hochzählen, sondern dem aktuellen Datum
entsprechend setzen) an diesen drei Stellen:

- `app/design.py` (`VERSION = "V..."`)
- `README.md` (Überschrift `# GuMa V... by HB. - ...`)
- `start_windows.bat` (`title GuMa V... by HB.`)
