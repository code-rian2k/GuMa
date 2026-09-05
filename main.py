"""
GuMa: Fallverwaltung für psychologische Gutachten. Startpunkt.
Einfach doppelklicken (über start_windows.bat) oder mit "python main.py" starten.

Copyright (C) 2026 Hofbrückl (https://www.hofbrueckl.com). Alle Rechte vorbehalten.
Keine Open-Source-Software - Nutzung nur nach Rücksprache, siehe LICENSE.
"""
import sys

from app.gui import starten

if __name__ == "__main__":
    # Windows skaliert Programme ohne DPI-Kennzeichnung selbst hoch (z.B. bei
    # 125%/150% Bildschirmskalierung, wie auf vielen Tablets/Notebooks
    # Standard) - dabei werden ttk-Elemente wie die Reiter-Beschriftungen
    # falsch bemessen und abgeschnitten. Muss VOR dem ersten Tk-Fenster
    # aufgerufen werden, damit GuMa die Skalierung selbst korrekt übernimmt.
    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()  # Fallback für ältere Windows-Versionen
            except Exception:
                pass

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
