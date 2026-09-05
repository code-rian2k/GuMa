"""
Einheitliches Erscheinungsbild von GuMa: Farben, Schrift, ttk-Style und
eine wiederverwendbare Kopfzeile. Alles an einer Stelle, damit sich das
Aussehen künftig leicht zentral anpassen lässt.
"""
import os
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

# Versionsschema: V<Jahr, 2-stellig>.<Monat ohne führende Null> - wird bei
# jeder veröffentlichten Änderung manuell auf den aktuellen Monat gesetzt
# (siehe CLAUDE.md).
VERSION = "V26.9"
AUTOR_KUERZEL = "HB."
WEBSITE_URL = "https://www.hofbrueckl.com"

PROGRAMMNAME = f"GuMa {VERSION} by {AUTOR_KUERZEL}"
UNTERTITEL = "– Fallverwaltung für psychologische Gutachten"

FARBE_PRIMAER = "#2B3A42"
FARBE_PRIMAER_DUNKEL = "#1B262C"
FARBE_AKZENT = "#3FA9A0"
FARBE_HINTERGRUND = "#F2F4F5"
FARBE_KARTE = "#FFFFFF"
FARBE_TEXT = "#1F2A30"
FARBE_RAND = "#D6DBDD"

SCHRIFT = "Segoe UI"


def style_anwenden(root):
    """Wendet ein einheitliches, modernes ttk-Theme auf die gesamte Anwendung an."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=FARBE_HINTERGRUND)

    style.configure(".", background=FARBE_HINTERGRUND, foreground=FARBE_TEXT, font=(SCHRIFT, 10))
    style.configure("TFrame", background=FARBE_HINTERGRUND)
    style.configure("TLabel", background=FARBE_HINTERGRUND, foreground=FARBE_TEXT)
    style.configure("TLabelframe", background=FARBE_HINTERGRUND, bordercolor=FARBE_RAND)
    style.configure("TLabelframe.Label", background=FARBE_HINTERGRUND, foreground=FARBE_PRIMAER, font=(SCHRIFT, 10, "bold"))

    style.configure("TButton", padding=(10, 6), font=(SCHRIFT, 10))
    style.map("TButton", background=[("active", "#E3EAEE")])

    style.configure("Accent.TButton", background=FARBE_PRIMAER, foreground="white", font=(SCHRIFT, 10, "bold"), padding=(12, 7))
    style.map(
        "Accent.TButton",
        background=[("active", FARBE_PRIMAER_DUNKEL), ("pressed", FARBE_PRIMAER_DUNKEL), ("disabled", "#B7C3C9")],
        foreground=[("disabled", "#EFEFEF")],
    )

    style.configure("TEntry", padding=4)
    style.configure("TCombobox", padding=4)

    style.configure("TNotebook", background=FARBE_HINTERGRUND, borderwidth=0)
    style.configure("TNotebook.Tab", padding=(16, 9), font=(SCHRIFT, 10))
    style.map("TNotebook.Tab", background=[("selected", FARBE_PRIMAER)], foreground=[("selected", "white")])

    style.configure(
        "Treeview", rowheight=27, font=(SCHRIFT, 10),
        background=FARBE_KARTE, fieldbackground=FARBE_KARTE, bordercolor=FARBE_RAND,
    )
    style.configure("Treeview.Heading", font=(SCHRIFT, 10, "bold"), background=FARBE_PRIMAER, foreground="white", relief="flat")
    style.map("Treeview.Heading", background=[("active", FARBE_PRIMAER_DUNKEL)])
    style.map("Treeview", background=[("selected", FARBE_PRIMAER)], foreground=[("selected", "white")])

    style.configure("TPanedwindow", background=FARBE_HINTERGRUND)
    style.configure("TSeparator", background=FARBE_RAND)

    return style


def notebook_tab_breite_anpassen(notebook, style, schriftart=SCHRIFT, schriftgroesse=10, sicherheitsabstand=40):
    """Erzwingt eine Mindestbreite je Notebook-Reiter, anhand einer echten
    Schriftvermessung des längsten aktuell vorhandenen Reiter-Titels auf DIESEM
    System - statt einer geschätzten Zeichenanzahl. Ein fester Zeichen-Wert
    (z.B. width=20) hatte sich als nicht robust erwiesen: Segoe UI wird auf
    manchen Windows-Systemen breiter gerendert als angenommen, sodass lange
    Reiter wie "Fristen & Termine" trotzdem abgeschnitten blieben. Ein
    negativer width-Wert bedeutet bei ttk-Textelementen eine absolute Breite
    in Pixeln (statt einer Zeichenanzahl) - deshalb hier direkt die gemessene
    Pixelbreite verwenden, das ist unabhängig davon, wie breit ein einzelnes
    Zeichen der tatsächlich verwendeten Schriftart auf diesem System ist."""
    tab_ids = notebook.tabs()
    if not tab_ids:
        return
    schrift = tkfont.Font(family=schriftart, size=schriftgroesse)
    breite_px = max(schrift.measure(notebook.tab(tab_id, "text")) for tab_id in tab_ids)
    style.configure("TNotebook.Tab", width=-(breite_px + sicherheitsabstand))


def _logo_bild_laden(basis_ordner, hoehe=44):
    """Lädt das GuMa-Logo als Tk-PhotoImage, falls die Datei vorhanden ist.
    Gibt None zurück, wenn das Logo fehlt oder nicht geladen werden kann
    (z. B. auf Systemen ohne PNG-Unterstützung in Tk) - die Kopfzeile
    funktioniert dann einfach ohne Bild weiter."""
    pfad = os.path.join(basis_ordner, "app", "assets", "logo_header.png")
    if not os.path.isfile(pfad):
        return None
    try:
        bild = tk.PhotoImage(file=pfad)
        # Tk-PhotoImage kann nur ganzzahlig herunterskaliert werden (subsample)
        aktuelle_hoehe = bild.height()
        if aktuelle_hoehe > hoehe > 0:
            faktor = max(1, aktuelle_hoehe // hoehe)
            bild = bild.subsample(faktor, faktor)
        return bild
    except Exception:
        return None


def kopfzeile_erstellen(parent, untertitel=UNTERTITEL, basis_ordner=None):
    """Blaue Kopfzeile mit Logo, Programmnamen + Untertitel und dünnem Akzentbalken."""
    header = tk.Frame(parent, bg=FARBE_PRIMAER, height=60)
    header.pack(fill="x", side="top")
    header.pack_propagate(False)

    logo_bild = None
    if basis_ordner:
        logo_bild = _logo_bild_laden(basis_ordner)
    if logo_bild is not None:
        logo_label = tk.Label(header, image=logo_bild, bg=FARBE_PRIMAER)
        logo_label.image = logo_bild  # Referenz halten, sonst Garbage Collection
        logo_label.pack(side="left", padx=(18, 6), pady=8)

    tk.Label(header, text=PROGRAMMNAME, bg=FARBE_PRIMAER, fg="white", font=(SCHRIFT, 19, "bold")).pack(
        side="left", padx=(0 if logo_bild is not None else 20, 8), pady=8
    )
    if untertitel:
        tk.Label(header, text=untertitel, bg=FARBE_PRIMAER, fg="#CFE0E8", font=(SCHRIFT, 11)).pack(
            side="left", pady=8
        )

    balken = tk.Frame(parent, bg=FARBE_AKZENT, height=3)
    balken.pack(fill="x", side="top")
    return header


def icon_setzen(fenster, basis_ordner):
    """Setzt das GuMa-Programmsymbol, falls vorhanden. Schlägt auf Nicht-Windows-
    Systemen lautlos fehl (z.B. beim Entwickeln/Testen) statt einen Fehler zu werfen."""
    pfad = os.path.join(basis_ordner, "icon.ico")
    if os.path.isfile(pfad):
        try:
            fenster.iconbitmap(pfad)
        except Exception:
            pass
