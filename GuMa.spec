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

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icon.ico', '.'),
        ('app/assets', 'app/assets'),
    ],
    hiddenimports=['lxml.etree', 'lxml._elementpath'],
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
