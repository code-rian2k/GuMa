"""
GuMa: Fallverwaltung für psychologische Gutachten. Startpunkt.
Einfach doppelklicken (über start_windows.bat) oder mit "python main.py" starten.

Copyright (C) 2026 Hofbrückl (https://www.hofbrueckl.com). Alle Rechte vorbehalten.
Keine Open-Source-Software - Nutzung nur nach Rücksprache, siehe LICENSE.
"""
from app.gui import starten

if __name__ == "__main__":
    try:
        starten()
    except Exception:
        # Als gebaute .exe läuft GuMa ohne sichtbares Konsolenfenster - ein
        # Fehler vor dem Start des Hauptfensters (z.B. defekte Datenbank)
        # würde sonst spurlos verschwinden. Deshalb hier zusätzlich als
        # Dialogfenster anzeigen.
        import traceback
        fehlertext = traceback.format_exc()
        try:
            import tkinter as tk
            from tkinter import messagebox
            wurzel = tk.Tk()
            wurzel.withdraw()
            messagebox.showerror("GuMa konnte nicht gestartet werden", fehlertext)
        except Exception:
            pass
        raise
