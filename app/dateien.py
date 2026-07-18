"""
Dateiverwaltung: Ablage von Unterlagen (PDF, Fotos, ...) je Fall im
zugehörigen Fall-Ordner, sowie gesammelter Export/Backup aller Fälle.

Jeder Fall bekommt automatisch einen eigenen Ordner unter dokumente/<Fallname>.
Dort landen sowohl die von der App erzeugten Word-/Excel-Dokumente als auch
manuell hinzugefügte Dateien (PDF, Fotos, Scans usw.) - eine einfache,
transparente Struktur, die auch ohne die App im Windows-Explorer nachvollziehbar
bleibt.
"""
import os
import shutil
import datetime


def fall_ordner_name(fall: dict, fall_id: int) -> str:
    name = (fall.get("aktenzeichen") or f"Fall_{fall_id}").replace("/", "-").replace("\\", "-").strip()
    return name or f"Fall_{fall_id}"


def fall_ordner_pfad(dokumente_ordner: str, fall: dict, fall_id: int) -> str:
    pfad = os.path.join(dokumente_ordner, fall_ordner_name(fall, fall_id))
    os.makedirs(pfad, exist_ok=True)
    return pfad


def ermittle_dokumente_ordner(basis_ordner: str, einstellungen: dict) -> str:
    """
    Liefert den Ordner, in dem Fälle/Dokumente abgelegt werden.

    Ist in den Einstellungen ein eigener Ordner hinterlegt (z.B. ein lokales
    Laufwerk außerhalb jeder Cloud-Synchronisierung), wird dieser verwendet.
    Andernfalls der Standardordner "dokumente" direkt neben dem Programm.
    """
    konfiguriert = (einstellungen.get("dokumente_ordner") or "").strip()
    if konfiguriert:
        os.makedirs(konfiguriert, exist_ok=True)
        return konfiguriert
    standard = os.path.join(basis_ordner, "dokumente")
    os.makedirs(standard, exist_ok=True)
    return standard


def alle_faelle_verschieben(alter_ordner: str, neuer_ordner: str):
    """
    Verschiebt den Inhalt eines Dokumente-Ordners komplett in einen neuen
    Ordner - genutzt, wenn der Speicherort in den Einstellungen geändert
    wird und die Nutzerin die vorhandenen Fälle mitnehmen möchte.
    """
    if not os.path.isdir(alter_ordner):
        return
    os.makedirs(neuer_ordner, exist_ok=True)
    for name in os.listdir(alter_ordner):
        quelle = os.path.join(alter_ordner, name)
        ziel = os.path.join(neuer_ordner, name)
        if os.path.exists(ziel):
            continue  # im Zweifel nichts überschreiben
        shutil.move(quelle, ziel)


def dateien_auflisten(ordner: str):
    """Liste aller Dateien (keine Unterordner) im Fall-Ordner, neueste zuerst."""
    if not os.path.isdir(ordner):
        return []
    eintraege = []
    for name in os.listdir(ordner):
        pfad = os.path.join(ordner, name)
        if os.path.isfile(pfad):
            stat = os.stat(pfad)
            eintraege.append({
                "name": name,
                "pfad": pfad,
                "groesse_kb": round(stat.st_size / 1024, 1),
                "geaendert": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M"),
                "zeitstempel": stat.st_mtime,
            })
    eintraege.sort(key=lambda e: e["zeitstempel"], reverse=True)
    return eintraege


def eindeutigen_dateinamen(ordner: str, dateiname: str) -> str:
    """
    Liefert einen Dateinamen, der im Ordner noch nicht existiert - hängt bei
    Bedarf ' (1)', ' (2)', ... an, damit nie versehentlich eine vorhandene
    Datei (z.B. ein bereits begonnenes Gutachten) überschrieben wird.
    """
    basis, endung = os.path.splitext(dateiname)
    ziel = dateiname
    zaehler = 1
    while os.path.exists(os.path.join(ordner, ziel)):
        ziel = f"{basis} ({zaehler}){endung}"
        zaehler += 1
    return ziel


def datei_hinzufuegen(ordner: str, quellpfad: str) -> str:
    """Kopiert eine Datei in den Fall-Ordner (Original bleibt am Ursprungsort erhalten)."""
    dateiname = os.path.basename(quellpfad)
    zielname = eindeutigen_dateinamen(ordner, dateiname)
    zielpfad = os.path.join(ordner, zielname)
    shutil.copy2(quellpfad, zielpfad)
    return zielpfad


def datei_loeschen(pfad: str):
    if os.path.isfile(pfad):
        os.remove(pfad)


def fall_ordner_loeschen(ordner: str):
    if os.path.isdir(ordner):
        shutil.rmtree(ordner)


def fall_als_zip_exportieren(fall_ordner: str, ziel_zip_pfad: str) -> str:
    """Exportiert den kompletten Fall-Ordner (Dokumente + Unterlagen) als ZIP-Datei."""
    ziel_ohne_endung = ziel_zip_pfad[:-4] if ziel_zip_pfad.lower().endswith(".zip") else ziel_zip_pfad
    erzeugt = shutil.make_archive(ziel_ohne_endung, "zip", root_dir=fall_ordner)
    return erzeugt


def backup_erstellen(db_pfad: str, dokumente_ordner: str, ziel_basis_ordner: str) -> str:
    """
    Sichert die gesamte Datenbank sowie alle Fall-Ordner (inkl. aller
    Unterlagen und erzeugten Dokumente) gesammelt in einen frei wählbaren
    Zielordner - z.B. eine externe Festplatte oder ein Netzlaufwerk/Server.
    Legt dort einen neuen, mit Datum/Uhrzeit benannten Unterordner an, damit
    ältere Backups nicht überschrieben werden.
    """
    zeitstempel = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    ziel_ordner = os.path.join(ziel_basis_ordner, f"Gutachten-Manager-Backup_{zeitstempel}")
    os.makedirs(ziel_ordner, exist_ok=True)

    if os.path.isfile(db_pfad):
        shutil.copy2(db_pfad, os.path.join(ziel_ordner, os.path.basename(db_pfad)))

    if os.path.isdir(dokumente_ordner):
        ziel_dokumente = os.path.join(ziel_ordner, "dokumente")
        shutil.copytree(dokumente_ordner, ziel_dokumente)

    return ziel_ordner
