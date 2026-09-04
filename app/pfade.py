"""
Zentrale Ermittlung des Programm-Basisordners (dort, wo main.py bzw. die
gebaute .exe liegt) - für Icon, Datenbank, Dokumente- und Vorlagen-Ordner.

Bei normalem Start aus dem Quellcode ist das der Ordner zwei Ebenen über
dieser Datei (app/pfade.py -> app -> Projektordner). Als mit PyInstaller
gebaute .exe verpackt (sys.frozen) gibt es aber keinen echten Quellcode-Pfad
mehr - __file__ würde dann auf einen internen, temporären Entpackungsort
zeigen. In dem Fall wird stattdessen der Ordner der .exe selbst verwendet,
damit Falldaten/Dokumente/Vorlagen zuverlässig neben der .exe landen (und
bei einem Update - neue .exe drüberkopieren - erhalten bleiben).
"""
import os
import sys


def basis_ordner() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
