# -*- mode: python ; coding: utf-8 -*-
# PyInstaller-Konfiguration für die portable Windows-Version von GuMa (ohne
# Installation, ohne Adminrechte, ohne separat installiertes Python -
# siehe .github/workflows/build-windows.yml für den automatischen Build).
#
# contents_directory='.' erzwingt das "alte" flache Ordnerlayout (alle
# Dateien direkt neben GuMa.exe statt in einem versteckten _internal-
# Unterordner) - so bleibt app/pfade.py::basis_ordner() (Icon, Assets,
# Datenbank, Dokumente, Vorlagen immer direkt neben der .exe) unverändert
# gültig, ganz gleich ob aus dem Quellcode oder als gebaute .exe gestartet.
#
# babel (Abhängigkeit von tkcalendar, für die deutschen Monats-/Wochentags-
# namen im Kalender-Popup) legt seine Locale-Daten als Paket-Dateien ab,
# die PyInstallers automatische Importanalyse nicht erfasst - deshalb
# explizit über collect_data_files eingesammelt.
from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icon.ico', '.'),
        ('app/assets', 'app/assets'),
        *collect_data_files('babel'),
    ],
    hiddenimports=['lxml.etree', 'lxml._elementpath', 'tkcalendar'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GuMa',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon='icon.ico',
    contents_directory='.',
    # Eingebettetes Manifest für DPI-Bewusstsein (siehe GuMa.manifest) -
    # zuverlässiger als ein Laufzeit-Aufruf von SetProcessDpiAwareness(),
    # da Windows das Manifest schon vor dem Programmstart liest.
    manifest='GuMa.manifest',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='GuMa',
)
