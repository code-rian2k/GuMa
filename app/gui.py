"""
Hauptfenster von GuMa (Gutachten-Manager).
"""
import os
import re
import datetime
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

from app import repo
from app.db import init_db, DB_PATH
from app.gui_rechnung import RechnungFenster
from app import docgen
from app import dateien
from app import vorlagen
from app import design
from app.pfade import basis_ordner
from app import kalenderfeld

BASIS_ORDNER = basis_ordner()
# Wird erst in Anwendung.__init__() anhand der Einstellungen bestimmt (siehe
# app.dateien.ermittle_dokumente_ordner) - kann in den Einstellungen frei
# gewählt werden, z.B. auf ein lokales Laufwerk außerhalb jeder
# Cloud-Synchronisierung, damit keine personenbezogenen Daten in die Cloud
# gelangen.
DOKUMENTE_ORDNER = None

# Dezente Hintergrundfarbe je Status in der Fallliste - so ist auf einen
# Blick erkennbar, wo ein Fall steht, ohne die Status-Spalte lesen zu müssen.
STATUS_FARBEN = {
    "offen": "#FDECEA",
    "Ortstermin vereinbart": "#FFF6E0",
    "in Bearbeitung": "#E8F1FB",
    "Gutachten abgegeben": "#E9F7EF",
    "abgerechnet": "#EAF7F6",
    "abgeschlossen": "#F1F1F1",
}

# "Ampel" für die Fristen-Übersicht: Fristen, die schon überfällig oder in
# Kürze fällig sind, sollen ins Auge springen, ohne dass man jedes Datum
# einzeln nachrechnen muss.
FRIST_WARNSCHWELLE_TAGE = 3
FRIST_FARBEN = {
    "ueberfaellig": "#F8D7DA",
    "bald_faellig": "#FFF3CD",
}


def heute():
    return datetime.date.today().strftime("%d.%m.%Y")


def _frist_dringlichkeit(datum_text):
    """Ordnet ein Fristen-Datum (Text, TT.MM.JJJJ) einer Dringlichkeits-Stufe
    für die farbliche Hervorhebung in der Übersicht zu. Nicht auswertbare
    Daten bekommen keine besondere Hervorhebung."""
    try:
        datum = datetime.datetime.strptime(datum_text or "", "%d.%m.%Y").date()
    except ValueError:
        return None
    heute_datum = datetime.date.today()
    if datum < heute_datum:
        return "ueberfaellig"
    if (datum - heute_datum).days <= FRIST_WARNSCHWELLE_TAGE:
        return "bald_faellig"
    return None


def _text_zu_zahl(text, standard=0.0):
    try:
        text = (text or "").strip().replace(",", ".")
        return float(text) if text else standard
    except ValueError:
        return standard


class Anwendung(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(design.PROGRAMMNAME)
        self.geometry("1250x780")
        self.minsize(1000, 620)
        self._maximiert_starten()
        self.aktueller_fall_id = None
        self._stammdaten_dirty = False

        self.style = design.style_anwenden(self)
        design.icon_setzen(self, BASIS_ORDNER)

        init_db()
        self._dokumente_ordner_neu_einlesen()

        design.kopfzeile_erstellen(self, basis_ordner=BASIS_ORDNER)
        self._menu_aufbauen()
        self._layout_aufbauen()
        self._faelle_neu_laden()
        self.protocol("WM_DELETE_WINDOW", self._beenden)

    def _dokumente_ordner_neu_einlesen(self):
        """Liest den aktuell konfigurierten Speicherort aus den Einstellungen
        und aktualisiert die globale DOKUMENTE_ORDNER-Variable, die von allen
        anderen Methoden dieser Klasse verwendet wird."""
        global DOKUMENTE_ORDNER
        DOKUMENTE_ORDNER = dateien.ermittle_dokumente_ordner(BASIS_ORDNER, repo.einstellungen_holen())

    def _maximiert_starten(self):
        """Startet das Hauptfenster maximiert. Funktioniert direkt unter
        Windows; auf anderen Systemen (z.B. beim Testen) wird das übliche
        Fenstermaß aus geometry() beibehalten, falls 'zoomed' nicht
        unterstützt wird."""
        try:
            self.state("zoomed")
        except tk.TclError:
            try:
                self.attributes("-zoomed", True)
            except tk.TclError:
                pass

    def report_callback_exception(self, exc, val, tb):
        """
        Tkinter ruft diese Methode auf, wenn in einem Button-Befehl o.ä. ein
        Fehler auftritt. Ohne diese Überschreibung würde der Fehler nur
        unsichtbar in der Konsole landen und die App würde nach außen so
        wirken, als würde "nichts passieren". Stattdessen zeigen wir jetzt
        immer eine Meldung an.
        """
        import traceback
        traceback.print_exception(exc, val, tb)
        try:
            messagebox.showerror(
                "Es ist ein Fehler aufgetreten",
                f"{val}\n\nBitte den Vorgang erneut versuchen. Falls der Fehler "
                f"wieder auftritt, bitte Screenshot machen und weitergeben.",
            )
        except Exception:
            pass

    # ---------- Menü ----------

    def _menu_aufbauen(self):
        menu = tk.Menu(self)
        self.config(menu=menu)
        datei_menu = tk.Menu(menu, tearoff=0)
        datei_menu.add_command(label="Stammdaten / Einstellungen...", command=self._einstellungen_oeffnen)
        datei_menu.add_separator()
        datei_menu.add_command(label="Alle Daten sichern (Backup)...", command=self._backup_erstellen)
        datei_menu.add_command(label="Backup importieren...", command=self._backup_importieren)
        datei_menu.add_separator()
        datei_menu.add_command(label="Beenden", command=self._beenden)
        menu.add_cascade(label="Datei", menu=datei_menu)

        info_menu = tk.Menu(menu, tearoff=0)
        info_menu.add_command(label="Über GuMa...", command=self._info_oeffnen)
        menu.add_cascade(label="Info", menu=info_menu)

    def _springe_zu_fall(self, fall_id, tab_index=1):
        """Wählt den angegebenen Fall in der Fallliste aus und wechselt in den
        angegebenen Tab (Standard: Falldaten) - z.B. beim Doppelklick in
        der Übersicht."""
        # Ein aktiver Suchfilter könnte den Fall aus der Liste ausblenden.
        self.suche_var.set("")
        self._faelle_neu_laden()
        if str(fall_id) in self.fall_baum.get_children():
            self.fall_baum.selection_set(str(fall_id))
            self.fall_baum.focus(str(fall_id))
            self._fall_ausgewaehlt()
            self.notebook.select(tab_index)

    def _info_oeffnen(self):
        fenster = tk.Toplevel(self)
        fenster.title("Über GuMa")
        fenster.geometry("440x300")
        fenster.resizable(False, False)
        fenster.configure(bg=design.FARBE_HINTERGRUND)
        design.icon_setzen(fenster, BASIS_ORDNER)

        inhalt = ttk.Frame(fenster, padding=20)
        inhalt.pack(fill="both", expand=True)

        ttk.Label(inhalt, text=f"GuMa {design.VERSION}", font=("TkDefaultFont", 16, "bold")).pack(anchor="w")
        ttk.Label(inhalt, text="Fallverwaltung für psychologische Gutachten", font=("TkDefaultFont", 10)).pack(
            anchor="w", pady=(0, 15)
        )

        def _link_erstellen(text, url):
            link = tk.Label(
                inhalt, text=text, fg=design.FARBE_PRIMAER, bg=design.FARBE_HINTERGRUND,
                cursor="hand2", font=("TkDefaultFont", 10, "underline"),
            )
            link.pack(anchor="w")
            link.bind("<Button-1>", lambda _e: webbrowser.open(url))

        _link_erstellen(design.WEBSITE_URL, design.WEBSITE_URL)

        ttk.Separator(inhalt, orient="horizontal").pack(fill="x", pady=10)

        ttk.Label(
            inhalt,
            text=f"© {datetime.date.today().year} {design.AUTOR_KUERZEL}. Alle Rechte vorbehalten.\n"
                 "Diese Software ist keine Open-Source-Software. Nutzung,\n"
                 "Veränderung oder Weitergabe nur nach Rücksprache und mit\n"
                 "ausdrücklicher Zustimmung des Urhebers.",
            justify="left", font=("TkDefaultFont", 8),
        ).pack(anchor="w", pady=(0, 8))

        ttk.Button(inhalt, text="Schließen", command=fenster.destroy).pack(anchor="e", pady=(15, 0))

    def _backup_erstellen(self):
        zeitstempel = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        ziel = filedialog.asksaveasfilename(
            title="Backup-Datei speichern (z. B. auf einem USB-Stick oder Netzlaufwerk)",
            initialfile=f"GuMa-Backup_{zeitstempel}.zip",
            defaultextension=".zip",
            filetypes=[("ZIP-Archiv", "*.zip")],
        )
        if not ziel:
            return
        try:
            backup_datei = dateien.backup_erstellen(
                DB_PATH, DOKUMENTE_ORDNER, vorlagen.ermittle_vorlagen_ordner(BASIS_ORDNER), ziel
            )
        except Exception as fehler:
            messagebox.showerror("Backup fehlgeschlagen", str(fehler))
            return
        messagebox.showinfo(
            "Backup erstellt",
            f"Alle Falldaten, Einstellungen, Dokumente/Unterlagen und Vorlagen wurden gesichert in:\n{backup_datei}\n\n"
            "Diese eine Datei reicht aus, um auf einer neuen GuMa-Installation über "
            "Datei → \"Backup importieren...\" wieder mit allen Daten weiterzuarbeiten.",
        )

    def _backup_importieren(self):
        if not messagebox.askyesno(
            "Backup importieren",
            "Beim Import werden die aktuellen Falldaten, Einstellungen, Dokumente/Unterlagen "
            "und Vorlagen durch den Inhalt der Backup-Datei überschrieben bzw. ergänzt.\n\n"
            "Das ist z.B. direkt nach einer frischen GuMa-Installation gedacht, um dort "
            "sofort mit allen bisherigen Daten weiterzuarbeiten. Fortfahren?",
        ):
            return
        quelle = filedialog.askopenfilename(
            title="Backup-Datei auswählen", filetypes=[("ZIP-Archiv", "*.zip")]
        )
        if not quelle:
            return
        try:
            dateien.backup_wiederherstellen(
                quelle, DB_PATH, DOKUMENTE_ORDNER, vorlagen.ermittle_vorlagen_ordner(BASIS_ORDNER)
            )
        except Exception as fehler:
            messagebox.showerror("Import fehlgeschlagen", str(fehler))
            return
        messagebox.showinfo(
            "Backup importiert",
            "Das Backup wurde eingespielt. Bitte GuMa jetzt einmal beenden und neu starten, "
            "damit alle Daten geladen werden.",
        )

    def _beenden(self):
        if not self._ungespeicherte_aenderungen_bestaetigen():
            return
        self.destroy()

    # ---------- Grundlayout ----------

    def _layout_aufbauen(self):
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)

        # Linke Seite: Fallliste
        links = ttk.Frame(paned, padding=8)
        paned.add(links, weight=1)

        ttk.Label(links, text="Fälle durchsuchen (Aktenzeichen, Namen, Kinder):").pack(anchor="w")
        suchleiste = ttk.Frame(links)
        suchleiste.pack(fill="x", pady=(0, 5))
        self.suche_var = tk.StringVar()
        self.suche_var.trace_add("write", lambda *_: self._faelle_neu_laden())
        ttk.Entry(suchleiste, textvariable=self.suche_var).pack(side="left", fill="x", expand=True)

        filter_zeile = ttk.Frame(links)
        filter_zeile.pack(fill="x", pady=(0, 5))
        ttk.Label(filter_zeile, text="Status:").pack(side="left")
        self.status_filter_var = tk.StringVar(value="Alle")
        ttk.Combobox(
            filter_zeile, textvariable=self.status_filter_var,
            values=["Alle"] + repo.STATUS_OPTIONEN, width=22, state="readonly",
        ).pack(side="left", padx=5)
        self.status_filter_var.trace_add("write", lambda *_: self._faelle_neu_laden())

        ttk.Button(links, text="+ Neuer Fall anlegen", style="Accent.TButton", command=self._neuer_fall).pack(fill="x", pady=(0, 5))

        spalten = ("aktenzeichen", "in_sachen", "status")
        self.fall_baum = ttk.Treeview(links, columns=spalten, show="headings", selectmode="browse")
        for spalte, breite in zip(spalten, (110, 220, 130)):
            self.fall_baum.heading(spalte, text={"aktenzeichen": "Aktenzeichen", "in_sachen": "In Sachen", "status": "Status"}[spalte])
            self.fall_baum.column(spalte, width=breite)
        for status, farbe in STATUS_FARBEN.items():
            self.fall_baum.tag_configure(status, background=farbe)
        self.fall_baum.pack(fill="both", expand=True)
        self.fall_baum.bind("<<TreeviewSelect>>", self._fall_ausgewaehlt)

        ttk.Button(links, text="Fall löschen", command=self._fall_loeschen).pack(fill="x", pady=(5, 0))

        # Rechte Seite: Tabs für ausgewählten Fall
        rechts = ttk.Frame(paned, padding=8)
        paned.add(rechts, weight=3)

        self.notebook = ttk.Notebook(rechts)
        self.notebook.pack(fill="both", expand=True)

        self._tab_uebersicht_aufbauen()
        self._tab_stammdaten_aufbauen()
        self._tab_fristen_aufbauen()
        self._tab_notizen_aufbauen()
        self._tab_dokumente_aufbauen()
        self._tab_unterlagen_aufbauen()
        self._tab_rechnungen_aufbauen()

        # Erzwingt eine Mindestbreite je Reiter anhand einer echten Schriftvermessung
        # auf diesem System (siehe design.py) - eine geschätzte Zeichenanzahl war
        # auf manchen Windows-Systemen zu knapp bemessen, weil Segoe UI dort breiter
        # gerendert wird als angenommen.
        design.notebook_tab_breite_anpassen(self.notebook, self.style)
        self.update_idletasks()

        self._faelle_neu_laden()
        self._uebersicht_fristen_laden()
        self._uebersicht_gutachten_laden()

    # ---------- Fallliste ----------

    def _faelle_neu_laden(self):
        for zeile in self.fall_baum.get_children():
            self.fall_baum.delete(zeile)
        status_filter = self.status_filter_var.get()
        status_filter = None if status_filter in ("", "Alle") else status_filter
        for fall in repo.faelle_liste(self.suche_var.get(), status_filter):
            self.fall_baum.insert("", "end", iid=str(fall["id"]),
                                   values=(fall["aktenzeichen"], fall["in_sachen"], fall["status"]),
                                   tags=(fall["status"],))

    def _fall_ausgewaehlt(self, _event=None):
        auswahl = self.fall_baum.selection()
        neue_id = int(auswahl[0]) if auswahl else None
        if neue_id == self.aktueller_fall_id:
            return
        if self._stammdaten_dirty and not self._ungespeicherte_aenderungen_bestaetigen():
            # Wechsel abbrechen: Auswahl in der Liste auf den bisherigen Fall
            # zurücksetzen, die (noch ungespeicherten) Falldaten bleiben unverändert.
            if self.aktueller_fall_id and str(self.aktueller_fall_id) in self.fall_baum.get_children():
                self.fall_baum.selection_set(str(self.aktueller_fall_id))
            else:
                self.fall_baum.selection_remove(*self.fall_baum.selection())
            return
        self.aktueller_fall_id = neue_id
        self._fall_in_tabs_laden()

    def _ungespeicherte_aenderungen_bestaetigen(self) -> bool:
        """Fragt nach, falls es nicht gespeicherte Änderungen bei den Falldaten
        gibt. Gibt True zurück, wenn fortgefahren werden darf (keine
        Änderungen oder Nutzer bestätigt das Verwerfen), sonst False."""
        if not self._stammdaten_dirty:
            return True
        return messagebox.askyesno(
            "Ungespeicherte Änderungen",
            "Es gibt ungespeicherte Änderungen bei den Falldaten.\n\n"
            "Ohne Speichern fortfahren und Änderungen verwerfen?",
        )

    def _stammdaten_dirty_setzen(self, *_args):
        self._stammdaten_dirty = True

    def _neuer_fall(self):
        neue_id = repo.fall_anlegen({"status": "offen"})
        # Suchfeld leeren: sonst würde der neue (noch leere) Fall sofort
        # durch einen aktiven Suchfilter wieder ausgeblendet und ließe sich
        # nicht auswählen.
        self.suche_var.set("")
        self._faelle_neu_laden()
        if str(neue_id) in self.fall_baum.get_children():
            self.fall_baum.selection_set(str(neue_id))
            self.fall_baum.focus(str(neue_id))
            self._fall_ausgewaehlt()
        else:
            messagebox.showerror(
                "Fehler beim Anlegen",
                "Der neue Fall konnte nicht in der Liste angezeigt werden. Bitte erneut versuchen.",
            )
        self.notebook.select(1)  # zur Falldaten-Ansicht springen

    def _fall_loeschen(self):
        if not self.aktueller_fall_id:
            return
        if not messagebox.askyesno(
            "Fall löschen",
            "Diesen Fall inkl. aller Notizen, Fristen und Rechnungen unwiderruflich löschen?",
        ):
            return
        ordner = self._fall_ordner()
        auch_dateien_loeschen = messagebox.askyesno(
            "Dateien auch löschen?",
            f"Sollen auch die zugehörigen Dokumente/Unterlagen im Ordner\n{ordner}\ngelöscht werden?\n\n"
            "'Nein' behält alle Dateien auf der Festplatte, es wird nur der Fall aus der Liste entfernt.",
        )
        repo.fall_loeschen(self.aktueller_fall_id)
        if auch_dateien_loeschen:
            dateien.fall_ordner_loeschen(ordner)
        self.aktueller_fall_id = None
        self._faelle_neu_laden()
        self._fall_in_tabs_laden()
        self._uebersicht_gutachten_laden()

    def _fall_in_tabs_laden(self):
        self._stammdaten_laden()
        self._fristen_laden()
        self._notizen_laden()
        self._unterlagen_laden()
        self._rechnungen_laden()

    # ---------- Tab: Übersicht ----------

    def _tab_uebersicht_aufbauen(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Übersicht")

        ttk.Label(tab, text="Kalenderübersicht:", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.uebersicht_kalender = kalenderfeld.uebersicht_kalender_erstellen(tab)
        self.uebersicht_kalender.pack(anchor="w", pady=(0, 5))
        self._uebersicht_kalender_tag_zu_fall = {}
        self.uebersicht_kalender.bind("<<CalendarSelected>>", self._uebersicht_kalender_tag_ausgewaehlt)
        ttk.Label(
            tab, text="(Grün markierte Tage haben einen offenen Termin - Klick springt zum Fall)",
            font=("TkDefaultFont", 8, "italic"),
        ).pack(anchor="w", pady=(0, 15))

        ttk.Label(tab, text="Offene Fristen & Termine über alle Fälle:", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.uebersicht_fristen_baum = ttk.Treeview(tab, columns=("datum", "fall", "beschreibung"), show="headings")
        for spalte, text, breite in [("datum", "Datum", 100), ("fall", "Fall", 220), ("beschreibung", "Beschreibung", 340)]:
            self.uebersicht_fristen_baum.heading(spalte, text=text)
            self.uebersicht_fristen_baum.column(spalte, width=breite)
        for tag, farbe in FRIST_FARBEN.items():
            self.uebersicht_fristen_baum.tag_configure(tag, background=farbe)
        self.uebersicht_fristen_baum.pack(fill="both", expand=True, pady=(0, 5))
        self._uebersicht_termin_fall_ids = {}
        self.uebersicht_fristen_baum.bind("<Double-1>", self._uebersicht_termin_oeffnen)
        ttk.Label(
            tab,
            text="(Doppelklick öffnet den Fall im Tab \"Fristen & Termine\" - rot = überfällig, "
                 f"gelb = fällig in den nächsten {FRIST_WARNSCHWELLE_TAGE} Tagen)",
            font=("TkDefaultFont", 8, "italic"),
        ).pack(anchor="w", pady=(0, 15))

        ttk.Label(tab, text="Gutachten schnell öffnen:", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        spalten = ("aktenzeichen", "in_sachen", "dateiname")
        self.uebersicht_gutachten_baum = ttk.Treeview(tab, columns=spalten, show="headings")
        for spalte, text, breite in [
            ("aktenzeichen", "Aktenzeichen", 110), ("in_sachen", "In Sachen", 220), ("dateiname", "Datei", 340),
        ]:
            self.uebersicht_gutachten_baum.heading(spalte, text=text)
            self.uebersicht_gutachten_baum.column(spalte, width=breite)
        self.uebersicht_gutachten_baum.pack(fill="both", expand=True, pady=(0, 5))
        self._uebersicht_gutachten_pfade = {}
        self.uebersicht_gutachten_baum.bind("<Double-1>", self._uebersicht_gutachten_oeffnen)
        ttk.Label(
            tab, text="(Doppelklick öffnet die Gutachten-Datei direkt)",
            font=("TkDefaultFont", 8, "italic"),
        ).pack(anchor="w")

    def _uebersicht_fristen_laden(self):
        for zeile in self.uebersicht_fristen_baum.get_children():
            self.uebersicht_fristen_baum.delete(zeile)
        self._uebersicht_termin_fall_ids = {}
        alle_termine = repo.alle_offenen_termine()
        for termin in alle_termine:
            fall_bezeichnung = termin.get("aktenzeichen") or termin.get("in_sachen") or f"Fall {termin['fall_id']}"
            tag = _frist_dringlichkeit(termin["datum"])
            self.uebersicht_fristen_baum.insert(
                "", "end", iid=str(termin["id"]),
                values=(termin["datum"], fall_bezeichnung, termin["beschreibung"]),
                tags=(tag,) if tag else (),
            )
            self._uebersicht_termin_fall_ids[str(termin["id"])] = termin["fall_id"]
        self._uebersicht_kalender_tag_zu_fall = kalenderfeld.kalender_termine_markieren(
            self.uebersicht_kalender, alle_termine
        )

    def _uebersicht_termin_oeffnen(self, _event=None):
        auswahl = self.uebersicht_fristen_baum.selection()
        if not auswahl:
            return
        fall_id = self._uebersicht_termin_fall_ids.get(auswahl[0])
        if fall_id is None:
            return
        self._springe_zu_fall(fall_id, tab_index=2)  # Tab "Fristen & Termine"

    def _uebersicht_kalender_tag_ausgewaehlt(self, _event=None):
        datum = self.uebersicht_kalender.selection_get()
        fall_id = self._uebersicht_kalender_tag_zu_fall.get(datum)
        if fall_id is not None:
            self._springe_zu_fall(fall_id, tab_index=2)  # Tab "Fristen & Termine"

    def _uebersicht_gutachten_laden(self):
        for zeile in self.uebersicht_gutachten_baum.get_children():
            self.uebersicht_gutachten_baum.delete(zeile)
        self._uebersicht_gutachten_pfade = {}
        for fall in repo.faelle_liste():
            ordner = dateien.fall_ordner_pfad(DOKUMENTE_ORDNER, fall, fall["id"])
            for datei in dateien.dateien_auflisten(ordner):
                if not datei["name"].lower().startswith("gutachten"):
                    continue
                iid = f"{fall['id']}:{datei['name']}"
                self.uebersicht_gutachten_baum.insert(
                    "", "end", iid=iid,
                    values=(fall["aktenzeichen"], fall["in_sachen"], datei["name"]),
                )
                self._uebersicht_gutachten_pfade[iid] = datei["pfad"]

    def _uebersicht_gutachten_oeffnen(self, _event=None):
        auswahl = self.uebersicht_gutachten_baum.selection()
        if not auswahl:
            return
        pfad = self._uebersicht_gutachten_pfade.get(auswahl[0])
        if not pfad:
            return
        try:
            os.startfile(pfad)  # Windows
        except AttributeError:
            messagebox.showinfo("Datei", f"Datei liegt hier:\n{pfad}")

    # ---------- Tab: Stammdaten ----------

    def _tab_stammdaten_aufbauen(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Falldaten")

        self.stamm_vars = {}

        # Zuerst am unteren Rand einplanen, BEVOR die (teils recht hohen)
        # Formularbereiche gepackt werden: so bleibt der Button auch auf
        # kleineren Bildschirmen/Fenstern garantiert sichtbar, statt von den
        # darüberliegenden Feldern nach unten aus dem sichtbaren Bereich
        # verdrängt zu werden.
        ttk.Button(tab, text="Speichern", style="Accent.TButton", command=self._stammdaten_speichern).pack(
            side="bottom", anchor="w", pady=10
        )

        verfahren_rahmen = ttk.LabelFrame(tab, text="Verfahren", padding=10)
        verfahren_rahmen.pack(fill="x", pady=(0, 10))
        verfahren_felder = [
            ("aktenzeichen", "Aktenzeichen"), ("gericht", "Gericht"),
            ("abteilung", "Abteilung"), ("richter", "Richter/-in (für Anschreiben)"),
            ("in_sachen", "In Sachen"), ("kinder", "Kinder"),
        ]
        for i, (schluessel, label) in enumerate(verfahren_felder):
            ttk.Label(verfahren_rahmen, text=label + ":").grid(row=i, column=0, sticky="e", pady=3, padx=5)
            var = tk.StringVar()
            ttk.Entry(verfahren_rahmen, textvariable=var, width=45).grid(row=i, column=1, sticky="w", pady=3, padx=5)
            self.stamm_vars[schluessel] = var

        eltern_rahmen = ttk.LabelFrame(tab, text="Eltern", padding=10)
        eltern_rahmen.pack(fill="x", pady=(0, 10))
        ttk.Label(eltern_rahmen, text="Mutter", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))
        ttk.Label(eltern_rahmen, text="Vater", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=2, columnspan=2, sticky="w", padx=(25, 0), pady=(0, 5))
        ttk.Label(eltern_rahmen, text="Name:").grid(row=1, column=0, sticky="e", padx=5, pady=3)
        var = tk.StringVar()
        ttk.Entry(eltern_rahmen, textvariable=var, width=26).grid(row=1, column=1, sticky="w", pady=3)
        self.stamm_vars["mutter_name"] = var
        ttk.Label(eltern_rahmen, text="Anschrift:").grid(row=2, column=0, sticky="e", padx=5, pady=3)
        var = tk.StringVar()
        ttk.Entry(eltern_rahmen, textvariable=var, width=26).grid(row=2, column=1, sticky="w", pady=3)
        self.stamm_vars["mutter_anschrift"] = var
        ttk.Label(eltern_rahmen, text="Name:").grid(row=1, column=2, sticky="e", padx=(25, 5), pady=3)
        var = tk.StringVar()
        ttk.Entry(eltern_rahmen, textvariable=var, width=26).grid(row=1, column=3, sticky="w", pady=3)
        self.stamm_vars["vater_name"] = var
        ttk.Label(eltern_rahmen, text="Anschrift:").grid(row=2, column=2, sticky="e", padx=(25, 5), pady=3)
        var = tk.StringVar()
        ttk.Entry(eltern_rahmen, textvariable=var, width=26).grid(row=2, column=3, sticky="w", pady=3)
        self.stamm_vars["vater_anschrift"] = var

        status_rahmen = ttk.LabelFrame(tab, text="Status & Auftrag", padding=10)
        status_rahmen.pack(fill="both", expand=True)
        ttk.Label(status_rahmen, text="Status:").grid(row=0, column=0, sticky="ne", pady=3, padx=5)
        self.status_var = tk.StringVar()
        ttk.Combobox(status_rahmen, textvariable=self.status_var, values=repo.STATUS_OPTIONEN, width=30, state="readonly").grid(
            row=0, column=1, sticky="w", pady=3, padx=5
        )
        ttk.Label(status_rahmen, text="Auftragstext (Beweisbeschluss o.ä.):").grid(row=1, column=0, sticky="ne", pady=3, padx=5)
        self.auftragstext_text = tk.Text(status_rahmen, width=60, height=5)
        self.auftragstext_text.grid(row=1, column=1, sticky="w", pady=3, padx=5)

        # Änderungen an den Falldaten nachverfolgen, damit beim Fallwechsel
        # oder Beenden ohne vorheriges Speichern gewarnt werden kann.
        for var in self.stamm_vars.values():
            var.trace_add("write", self._stammdaten_dirty_setzen)
        self.status_var.trace_add("write", self._stammdaten_dirty_setzen)
        self.auftragstext_text.bind("<<Modified>>", self._auftragstext_geaendert)

    def _auftragstext_geaendert(self, _event=None):
        if self.auftragstext_text.edit_modified():
            self._stammdaten_dirty_setzen()

    def _stammdaten_laden(self):
        fall = repo.fall_holen(self.aktueller_fall_id) if self.aktueller_fall_id else None
        for schluessel, var in self.stamm_vars.items():
            var.set(fall[schluessel] if fall and fall.get(schluessel) else "")
        self.status_var.set(fall["status"] if fall else "offen")
        self.auftragstext_text.delete("1.0", "end")
        if fall and fall.get("auftragstext"):
            self.auftragstext_text.insert("1.0", fall["auftragstext"])
        # Das Befüllen der Felder oben löst über die Trace-Bindungen selbst
        # ein "dirty" aus - deshalb hier am Ende wieder zurücksetzen.
        self.auftragstext_text.edit_modified(False)
        self._stammdaten_dirty = False

    def _stammdaten_speichern(self):
        if not self.aktueller_fall_id:
            messagebox.showwarning("Kein Fall ausgewählt", "Bitte links in der Liste zuerst einen Fall auswählen oder über '+ Neuer Fall anlegen' einen neuen Fall erstellen.")
            return
        daten = {schluessel: var.get() for schluessel, var in self.stamm_vars.items()}
        daten["status"] = self.status_var.get()
        daten["auftragstext"] = self.auftragstext_text.get("1.0", "end").strip()
        repo.fall_aktualisieren(self.aktueller_fall_id, daten)
        self._stammdaten_dirty = False
        self._faelle_neu_laden()
        if str(self.aktueller_fall_id) in self.fall_baum.get_children():
            self.fall_baum.selection_set(str(self.aktueller_fall_id))
        messagebox.showinfo("Gespeichert", "Falldaten wurden gespeichert.")

    # ---------- Tab: Fristen ----------

    def _tab_fristen_aufbauen(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Fristen & Termine")

        eingabe = ttk.Frame(tab)
        eingabe.pack(fill="x", pady=(0, 10))
        ttk.Label(eingabe, text="Datum:").pack(side="left")
        self.neuer_termin_datum = tk.StringVar(value=heute())
        kalenderfeld.datumsfeld_erstellen(
            eingabe, self.neuer_termin_datum, repo.einstellungen_holen(), width=12
        ).pack(side="left", padx=5)
        ttk.Label(eingabe, text="Beschreibung:").pack(side="left")
        self.neuer_termin_text = tk.StringVar()
        ttk.Entry(eingabe, textvariable=self.neuer_termin_text, width=40).pack(side="left", padx=5)
        ttk.Button(eingabe, text="Hinzufügen", command=self._termin_hinzufuegen).pack(side="left", padx=5)

        self.termine_baum = ttk.Treeview(tab, columns=("datum", "beschreibung"), show="headings")
        for spalte, text, breite in [("datum", "Datum", 100), ("beschreibung", "Beschreibung", 460)]:
            self.termine_baum.heading(spalte, text=text)
            self.termine_baum.column(spalte, width=breite)
        self.termine_baum.tag_configure("erledigt", font=("TkDefaultFont", 10, "overstrike"), foreground="#888888")
        self.termine_baum.pack(fill="both", expand=True)
        self.termine_baum.bind("<Double-1>", self._termin_erledigt_umschalten)

        button_leiste = ttk.Frame(tab)
        button_leiste.pack(fill="x", pady=5)
        ttk.Label(button_leiste, text="(Doppelklick = erledigt/offen umschalten)", font=("TkDefaultFont", 8, "italic")).pack(side="left")
        ttk.Button(button_leiste, text="Ausgewählten Termin löschen", command=self._termin_loeschen).pack(side="right")

    def _fristen_laden(self):
        for z in self.termine_baum.get_children():
            self.termine_baum.delete(z)
        if self.aktueller_fall_id:
            for termin in repo.termine_liste(self.aktueller_fall_id):
                self.termine_baum.insert(
                    "", "end", iid=str(termin["id"]),
                    values=(termin["datum"], termin["beschreibung"]),
                    tags=("erledigt",) if termin["erledigt"] else (),
                )
        self._uebersicht_fristen_laden()

    def _termin_hinzufuegen(self):
        if not self.aktueller_fall_id:
            messagebox.showwarning("Kein Fall ausgewählt", "Bitte links in der Liste zuerst einen Fall auswählen.")
            return
        if not self.neuer_termin_text.get().strip():
            messagebox.showwarning("Fehlende Angabe", "Bitte eine Beschreibung für den Termin eingeben.")
            return
        gesperrte_wochentage = kalenderfeld.gesperrte_wochentage_lesen(repo.einstellungen_holen())
        if kalenderfeld.ist_gesperrter_tag(self.neuer_termin_datum.get(), gesperrte_wochentage):
            if not messagebox.askyesno(
                "Fester Tag",
                f"Der {self.neuer_termin_datum.get()} ist als fester (freier/verplanter) Tag hinterlegt.\n\n"
                "Trotzdem einen Termin an diesem Tag einplanen?",
            ):
                return
        repo.termin_anlegen(self.aktueller_fall_id, self.neuer_termin_datum.get(), self.neuer_termin_text.get())
        self.neuer_termin_text.set("")
        self._fristen_laden()

    def _termin_erledigt_umschalten(self, _event=None):
        auswahl = self.termine_baum.selection()
        if not auswahl:
            return
        termin_id = int(auswahl[0])
        aktuell_erledigt = "erledigt" in self.termine_baum.item(auswahl[0])["tags"]
        repo.termin_erledigt_setzen(termin_id, not aktuell_erledigt)
        self._fristen_laden()

    def _termin_loeschen(self):
        auswahl = self.termine_baum.selection()
        if not auswahl:
            return
        repo.termin_loeschen(int(auswahl[0]))
        self._fristen_laden()

    # ---------- Tab: Notizen ----------

    def _tab_notizen_aufbauen(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Notizen")

        eingabe = ttk.Frame(tab)
        eingabe.pack(fill="x")
        self.neue_notiz_text = tk.Text(eingabe, height=4)
        self.neue_notiz_text.pack(fill="x", side="left", expand=True)
        ttk.Button(eingabe, text="Notiz hinzufügen", command=self._notiz_hinzufuegen).pack(side="left", padx=5)

        self.notizen_liste_widget = tk.Text(tab, state="disabled", wrap="word")
        self.notizen_liste_widget.pack(fill="both", expand=True, pady=(10, 0))

    def _notizen_laden(self):
        self.notizen_liste_widget.config(state="normal")
        self.notizen_liste_widget.delete("1.0", "end")
        if self.aktueller_fall_id:
            for notiz in repo.notizen_liste(self.aktueller_fall_id):
                self.notizen_liste_widget.insert("end", f"[{notiz['zeitpunkt']}]\n{notiz['text']}\n\n")
        self.notizen_liste_widget.config(state="disabled")

    def _notiz_hinzufuegen(self):
        if not self.aktueller_fall_id:
            messagebox.showwarning("Kein Fall ausgewählt", "Bitte links in der Liste zuerst einen Fall auswählen.")
            return
        text = self.neue_notiz_text.get("1.0", "end").strip()
        if not text:
            return
        repo.notiz_hinzufuegen(self.aktueller_fall_id, text)
        self.neue_notiz_text.delete("1.0", "end")
        self._notizen_laden()

    # ---------- Tab: Dokumente ----------

    def _tab_dokumente_aufbauen(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Dokumente")

        ttk.Label(tab, text="Anschreiben an einen Elternteil erstellen", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(0, 5))
        anschreiben_frame = ttk.Frame(tab)
        anschreiben_frame.pack(fill="x", pady=(0, 15))

        self.empfaenger_anrede_var = tk.StringVar(value="Frau")
        self.empfaenger_name_var = tk.StringVar()
        self.anschreiben_datum_var = tk.StringVar(value=heute())
        self.anschreiben_vorlage_var = tk.StringVar()

        ttk.Label(anschreiben_frame, text="Anrede:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(anschreiben_frame, textvariable=self.empfaenger_anrede_var, values=["Frau", "Herr"], width=8, state="readonly").grid(row=0, column=1, padx=5)
        ttk.Label(anschreiben_frame, text="Name:").grid(row=0, column=2, sticky="w")
        ttk.Entry(anschreiben_frame, textvariable=self.empfaenger_name_var, width=25).grid(row=0, column=3, padx=5)
        ttk.Label(anschreiben_frame, text="Datum:").grid(row=0, column=4, sticky="w")
        kalenderfeld.datumsfeld_erstellen(
            anschreiben_frame, self.anschreiben_datum_var, repo.einstellungen_holen(), width=12
        ).grid(row=0, column=5, padx=5)

        ttk.Label(anschreiben_frame, text="Vorlage:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.anschreiben_vorlage_combobox = ttk.Combobox(
            anschreiben_frame, textvariable=self.anschreiben_vorlage_var, width=32, state="readonly"
        )
        self.anschreiben_vorlage_combobox.grid(row=1, column=1, columnspan=3, sticky="w", padx=5, pady=(6, 0))
        ttk.Button(anschreiben_frame, text="Anschreiben erstellen...", command=self._anschreiben_erstellen).grid(
            row=1, column=4, columnspan=2, padx=10, pady=(6, 0), sticky="w"
        )

        ttk.Separator(tab, orient="horizontal").pack(fill="x", pady=10)

        ttk.Label(tab, text="Gutachten-Grundgerüst erstellen", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(0, 5))
        ttk.Label(tab, text="Erstellt eine Kopie der gewählten Gutachten-Vorlage mit ausgefüllter Titelseite\n"
                             "(Gericht, Abteilung, Datum, Aktenzeichen). Der restliche Text wird direkt in Word verfasst.",
                  justify="left").pack(anchor="w")
        self.gutachten_datum_var = tk.StringVar(value=heute())
        self.gutachten_vorlage_var = tk.StringVar()
        gutachten_frame = ttk.Frame(tab)
        gutachten_frame.pack(fill="x", pady=(5, 0))
        ttk.Label(gutachten_frame, text="Datum:").pack(side="left")
        kalenderfeld.datumsfeld_erstellen(
            gutachten_frame, self.gutachten_datum_var, repo.einstellungen_holen(), width=12
        ).pack(side="left", padx=5)
        ttk.Label(gutachten_frame, text="Vorlage:").pack(side="left", padx=(15, 0))
        self.gutachten_vorlage_combobox = ttk.Combobox(
            gutachten_frame, textvariable=self.gutachten_vorlage_var, width=32, state="readonly"
        )
        self.gutachten_vorlage_combobox.pack(side="left", padx=5)
        ttk.Button(gutachten_frame, text="Gutachten erstellen...", command=self._gutachten_erstellen).pack(side="left", padx=10)

        ttk.Separator(tab, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(
            tab,
            text="Keine passende Vorlage dabei? Unter Datei → Stammdaten / Einstellungen können eigene\n"
                 "Word-Vorlagen hinzugefügt werden.",
            justify="left", font=("TkDefaultFont", 8, "italic"),
        ).pack(anchor="w")
        ttk.Button(tab, text="Dokumente-Ordner dieses Falls öffnen", command=self._dokumente_ordner_oeffnen).pack(anchor="w", pady=(8, 0))

        self._vorlagen_dropdown_aktualisieren()

    def _vorlagen_combobox_befuellen(self, combobox, var, vorlagen_nach_name):
        namen = list(vorlagen_nach_name.keys())
        combobox.config(values=namen)
        if var.get() not in vorlagen_nach_name:
            var.set(namen[0] if namen else "")

    def _vorlagen_dropdown_aktualisieren(self):
        """Liest die hinterlegten Vorlagen neu ein - wird beim Start sowie nach
        Änderungen an den Vorlagen in den Einstellungen aufgerufen."""
        self._anschreiben_vorlagen = {v["name"]: v for v in repo.vorlagen_liste("anschreiben")}
        self._gutachten_vorlagen = {v["name"]: v for v in repo.vorlagen_liste("gutachten")}
        self._vorlagen_combobox_befuellen(self.anschreiben_vorlage_combobox, self.anschreiben_vorlage_var, self._anschreiben_vorlagen)
        self._vorlagen_combobox_befuellen(self.gutachten_vorlage_combobox, self.gutachten_vorlage_var, self._gutachten_vorlagen)

    def _fall_ordner(self):
        fall = repo.fall_holen(self.aktueller_fall_id)
        name = (fall.get("aktenzeichen") or f"Fall_{self.aktueller_fall_id}").replace("/", "-").strip() or f"Fall_{self.aktueller_fall_id}"
        pfad = os.path.join(DOKUMENTE_ORDNER, name)
        os.makedirs(pfad, exist_ok=True)
        return pfad

    def _anschreiben_erstellen(self):
        if not self.aktueller_fall_id:
            messagebox.showwarning("Kein Fall", "Bitte zuerst einen Fall auswählen.")
            return
        vorlage = self._anschreiben_vorlagen.get(self.anschreiben_vorlage_var.get())
        if not vorlage:
            messagebox.showwarning(
                "Keine Vorlage",
                "Es ist noch keine Anschreiben-Vorlage hinterlegt.\n\n"
                "Bitte unter Datei → Stammdaten / Einstellungen eine Word-Vorlage hinzufügen.",
            )
            return
        fall = repo.fall_holen(self.aktueller_fall_id)
        fall = dict(fall)
        fall["empfaenger_anrede"] = self.empfaenger_anrede_var.get()
        fall["empfaenger_name"] = self.empfaenger_name_var.get()
        fall["datum"] = self.anschreiben_datum_var.get()

        einstellungen = repo.einstellungen_holen()
        ordner = self._fall_ordner()
        dateiname = dateien.eindeutigen_dateinamen(ordner, f"Anschreiben_{fall['empfaenger_name'] or 'Empfaenger'}.docx")
        pfad = os.path.join(ordner, dateiname)
        docgen.anschreiben_erstellen(fall, einstellungen, pfad, vorlagen.vorlage_pfad(BASIS_ORDNER, vorlage))
        self._unterlagen_laden()
        self._dokument_oeffnen_und_melden(pfad, "Anschreiben", docgen.offene_platzhalter(pfad))

    def _gutachten_erstellen(self):
        if not self.aktueller_fall_id:
            messagebox.showwarning("Kein Fall", "Bitte zuerst einen Fall auswählen.")
            return
        vorlage = self._gutachten_vorlagen.get(self.gutachten_vorlage_var.get())
        if not vorlage:
            messagebox.showwarning(
                "Keine Vorlage",
                "Es ist noch keine Gutachten-Vorlage hinterlegt.\n\n"
                "Bitte unter Datei → Stammdaten / Einstellungen eine Word-Vorlage hinzufügen.",
            )
            return
        fall = repo.fall_holen(self.aktueller_fall_id)
        fall = dict(fall)
        fall["datum"] = self.gutachten_datum_var.get()

        ordner = self._fall_ordner()
        dateiname = dateien.eindeutigen_dateinamen(ordner, "Gutachten.docx")
        pfad = os.path.join(ordner, dateiname)
        docgen.gutachten_erstellen(fall, pfad, vorlagen.vorlage_pfad(BASIS_ORDNER, vorlage))
        self._unterlagen_laden()
        self._uebersicht_gutachten_laden()
        self._dokument_oeffnen_und_melden(pfad, "Gutachten-Grundgerüst", docgen.offene_platzhalter(pfad))

    def _dokument_oeffnen_und_melden(self, pfad, bezeichnung, offene_platzhalter=None):
        geoeffnet = False
        try:
            os.startfile(pfad)  # Windows: öffnet die Datei direkt in Word
            geoeffnet = True
        except AttributeError:
            pass
        except OSError:
            pass
        hinweis = ""
        if offene_platzhalter:
            hinweis = (
                "\n\nAchtung: Die Vorlage enthält Platzhalter, die GuMa nicht befüllen konnte:\n"
                + ", ".join(sorted(offene_platzhalter))
                + "\n\nBitte im Dokument von Hand prüfen bzw. in der Vorlage die unterstützten "
                  "Platzhalter-Namen verwenden."
            )
        if geoeffnet:
            messagebox.showinfo("Erstellt", f"{bezeichnung} wurde erstellt und wird geöffnet:\n{pfad}{hinweis}")
        else:
            messagebox.showinfo("Erstellt", f"{bezeichnung} wurde erstellt:\n{pfad}{hinweis}")

    def _dokumente_ordner_oeffnen(self):
        if not self.aktueller_fall_id:
            return
        pfad = self._fall_ordner()
        try:
            os.startfile(pfad)  # Windows
        except AttributeError:
            messagebox.showinfo("Ordner", f"Dokumente liegen hier:\n{pfad}")

    # ---------- Tab: Unterlagen (PDFs, Fotos, sonstige Dateien) ----------

    def _tab_unterlagen_aufbauen(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Unterlagen")

        ttk.Label(
            tab,
            text="Alle Dateien, die zu diesem Fall gehören (PDFs, Fotos, Scans, Word-/Excel-Dateien).\n"
                 "Jeder Fall hat einen eigenen Ordner auf der Festplatte - hinzugefügte Dateien werden dorthin kopiert.",
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        button_leiste = ttk.Frame(tab)
        button_leiste.pack(fill="x", pady=(0, 10))
        ttk.Button(button_leiste, text="Datei(en) hinzufügen...", command=self._unterlagen_hinzufuegen).pack(side="left")
        ttk.Button(button_leiste, text="Öffnen", command=self._unterlagen_oeffnen).pack(side="left", padx=5)
        ttk.Button(button_leiste, text="Löschen", command=self._unterlagen_loeschen).pack(side="left")
        ttk.Button(button_leiste, text="Ordner im Explorer anzeigen", command=self._dokumente_ordner_oeffnen).pack(side="left", padx=5)
        ttk.Button(button_leiste, text="Fall als ZIP exportieren...", command=self._fall_als_zip_exportieren).pack(side="right")

        spalten = ("name", "groesse", "geaendert")
        self.unterlagen_baum = ttk.Treeview(tab, columns=spalten, show="headings")
        for spalte, text, breite in [("name", "Dateiname", 380), ("groesse", "Größe (KB)", 100), ("geaendert", "Geändert am", 150)]:
            self.unterlagen_baum.heading(spalte, text=text)
            self.unterlagen_baum.column(spalte, width=breite)
        self.unterlagen_baum.pack(fill="both", expand=True)
        self.unterlagen_baum.bind("<Double-1>", lambda _e: self._unterlagen_oeffnen())

    def _unterlagen_laden(self):
        for z in self.unterlagen_baum.get_children():
            self.unterlagen_baum.delete(z)
        if not self.aktueller_fall_id:
            return
        for datei in dateien.dateien_auflisten(self._fall_ordner()):
            self.unterlagen_baum.insert("", "end", iid=datei["pfad"],
                                         values=(datei["name"], datei["groesse_kb"], datei["geaendert"]))

    def _unterlagen_hinzufuegen(self):
        if not self.aktueller_fall_id:
            messagebox.showwarning("Kein Fall", "Bitte zuerst einen Fall auswählen.")
            return
        quellpfade = filedialog.askopenfilenames(title="Dateien auswählen (PDF, Fotos, ...)")
        if not quellpfade:
            return
        ordner = self._fall_ordner()
        for quelle in quellpfade:
            dateien.datei_hinzufuegen(ordner, quelle)
        self._unterlagen_laden()

    def _unterlagen_oeffnen(self):
        auswahl = self.unterlagen_baum.selection()
        if not auswahl:
            return
        pfad = auswahl[0]
        try:
            os.startfile(pfad)  # Windows
        except AttributeError:
            messagebox.showinfo("Datei", f"Datei liegt hier:\n{pfad}")

    def _unterlagen_loeschen(self):
        auswahl = self.unterlagen_baum.selection()
        if not auswahl:
            return
        if messagebox.askyesno("Löschen", "Diese Datei unwiderruflich löschen?"):
            dateien.datei_loeschen(auswahl[0])
            self._unterlagen_laden()
            self._uebersicht_gutachten_laden()

    def _fall_als_zip_exportieren(self):
        if not self.aktueller_fall_id:
            messagebox.showwarning("Kein Fall", "Bitte zuerst einen Fall auswählen.")
            return
        fall = repo.fall_holen(self.aktueller_fall_id)
        vorschlag = f"{dateien.fall_ordner_name(dict(fall), self.aktueller_fall_id)}.zip"
        ziel = filedialog.asksaveasfilename(initialfile=vorschlag, defaultextension=".zip", filetypes=[("ZIP-Archiv", "*.zip")])
        if not ziel:
            return
        erzeugt = dateien.fall_als_zip_exportieren(self._fall_ordner(), ziel)
        messagebox.showinfo("Exportiert", f"Fall wurde exportiert nach:\n{erzeugt}")

    # ---------- Tab: Rechnungen ----------

    def _tab_rechnungen_aufbauen(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Rechnungen")

        button_leiste = ttk.Frame(tab)
        button_leiste.pack(fill="x", pady=(0, 10))
        ttk.Button(button_leiste, text="Neue Rechnung", command=self._rechnung_neu).pack(side="left")
        ttk.Button(button_leiste, text="Öffnen / Bearbeiten", command=self._rechnung_oeffnen).pack(side="left", padx=5)
        ttk.Button(button_leiste, text="Löschen", command=self._rechnung_loeschen).pack(side="left")

        self.rechnungen_baum = ttk.Treeview(tab, columns=("nummer", "datum"), show="headings")
        self.rechnungen_baum.heading("nummer", text="Rechnungsnummer")
        self.rechnungen_baum.heading("datum", text="Datum")
        self.rechnungen_baum.pack(fill="both", expand=True)
        self.rechnungen_baum.bind("<Double-1>", lambda _e: self._rechnung_oeffnen())

    def _rechnungen_laden(self):
        for z in self.rechnungen_baum.get_children():
            self.rechnungen_baum.delete(z)
        if not self.aktueller_fall_id:
            return
        for rechnung in repo.rechnungen_fuer_fall(self.aktueller_fall_id):
            self.rechnungen_baum.insert("", "end", iid=str(rechnung["id"]),
                                         values=(rechnung["rechnungsnummer"], rechnung["datum"]))

    def _naechste_rechnungsnummer(self):
        jahr = datetime.date.today().year
        bestehende = repo.rechnungen_fuer_fall(self.aktueller_fall_id) if self.aktueller_fall_id else []
        # Auf der höchsten bereits vergebenen Nummer aufbauen statt auf der
        # Anzahl bestehender Rechnungen - sonst könnte nach dem Löschen einer
        # Rechnung eine bereits vergebene Nummer erneut vorgeschlagen werden
        # (z.B. 01,02,03 vorhanden, 02 gelöscht -> Anzahl 2 -> "03" erneut
        # vorgeschlagen, obwohl "03" schon existiert).
        muster = re.compile(rf"^(\d+)-{jahr}$")
        hoechste = 0
        for rechnung in bestehende:
            treffer = muster.match(rechnung.get("rechnungsnummer") or "")
            if treffer:
                hoechste = max(hoechste, int(treffer.group(1)))
        return f"{hoechste + 1:02d}-{jahr}"

    def _rechnung_neu(self):
        if not self.aktueller_fall_id:
            messagebox.showwarning("Kein Fall", "Bitte zuerst einen Fall auswählen.")
            return
        nummer = self._naechste_rechnungsnummer()
        einstellungen = repo.einstellungen_holen()
        rechnung_id = repo.rechnung_anlegen(
            self.aktueller_fall_id, nummer, heute(),
            stundensatz=_text_zu_zahl(einstellungen.get("standard_stundensatz"), 100.0),
            km_satz=_text_zu_zahl(einstellungen.get("standard_km_satz"), 0.42),
            mwst_satz=_text_zu_zahl(einstellungen.get("standard_mwst_satz"), 19.0),
            schreibgebuehr_satz=_text_zu_zahl(einstellungen.get("standard_schreibgebuehr_satz"), 1.5),
        )
        self._rechnungen_laden()
        self._rechnung_fenster_oeffnen(rechnung_id)

    def _rechnung_oeffnen(self):
        auswahl = self.rechnungen_baum.selection()
        if not auswahl:
            return
        self._rechnung_fenster_oeffnen(int(auswahl[0]))

    def _rechnung_fenster_oeffnen(self, rechnung_id):
        fall = repo.fall_holen(self.aktueller_fall_id)
        fenster = RechnungFenster(self, dict(fall), rechnung_id, self._fall_ordner())
        fenster.grab_set()
        self.wait_window(fenster)
        self._rechnungen_laden()
        # Ein Excel-Export im Rechnungsfenster legt die Datei im Fall-Ordner
        # ab - Unterlagen-Liste entsprechend auffrischen, damit sie ohne
        # Fallwechsel sofort sichtbar ist.
        self._unterlagen_laden()

    def _rechnung_loeschen(self):
        auswahl = self.rechnungen_baum.selection()
        if not auswahl:
            return
        if messagebox.askyesno("Löschen", "Diese Rechnung wirklich löschen?"):
            repo.rechnung_loeschen(int(auswahl[0]))
            self._rechnungen_laden()

    # ---------- Einstellungen ----------

    def _einstellungen_oeffnen(self):
        fenster = tk.Toplevel(self)
        fenster.title("GuMa - Stammdaten / Einstellungen")
        fenster.geometry("640x600")
        fenster.minsize(560, 420)
        fenster.configure(bg=design.FARBE_HINTERGRUND)
        design.icon_setzen(fenster, BASIS_ORDNER)

        werte = repo.einstellungen_holen()

        # Die Speichern-Schaltfläche wird ZUERST unten fest eingeplant, damit
        # sie immer sichtbar bleibt - unabhängig von der Fenstergröße oder
        # davon, wie viel Inhalt darüber Platz braucht (siehe gleiches Problem
        # beim Rechnungsfenster).
        button_leiste = ttk.Frame(fenster, padding=10)
        button_leiste.pack(side="bottom", fill="x")

        # Scrollbarer Bereich für den restlichen Inhalt
        canvas = tk.Canvas(fenster, highlightthickness=0, bg=design.FARBE_HINTERGRUND)
        scrollbar = ttk.Scrollbar(fenster, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        inhalt = ttk.Frame(canvas)
        canvas_fenster = canvas.create_window((0, 0), window=inhalt, anchor="nw")

        def _scrollregion_aktualisieren(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _breite_anpassen(event):
            canvas.itemconfig(canvas_fenster, width=event.width)

        inhalt.bind("<Configure>", _scrollregion_aktualisieren)
        canvas.bind("<Configure>", _breite_anpassen)

        def _mausrad(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # Nur binden, während sich die Maus über diesem Fenster befindet -
        # sonst bliebe die Bindung nach dem Schließen des Fensters
        # anwendungsweit aktiv (bind_all) und würde beim nächsten Scrollen
        # irgendwo in GuMa versuchen, dieses längst geschlossene Fenster zu
        # scrollen (Fehler, weil das Widget dann nicht mehr existiert).
        def _mausrad_aktivieren(_event=None):
            canvas.bind_all("<MouseWheel>", _mausrad)

        def _mausrad_deaktivieren(_event=None):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _mausrad_aktivieren)
        canvas.bind("<Leave>", _mausrad_deaktivieren)

        def _fenster_geschlossen(event):
            if event.widget is fenster:
                _mausrad_deaktivieren()
                # Vorlagen können bereits während des Dialogs (unabhängig von
                # "Speichern"/"Abbrechen") hinzugefügt oder entfernt worden
                # sein - Dropdown im Dokumente-Tab entsprechend auffrischen.
                self._vorlagen_dropdown_aktualisieren()

        fenster.bind("<Destroy>", _fenster_geschlossen)

        # --- Speicherort für Fälle/Dokumente ---
        ordner_rahmen = ttk.LabelFrame(inhalt, text="Speicherort für Fälle und Dokumente", padding=10)
        ordner_rahmen.grid(row=0, column=0, columnspan=2, sticky="we", padx=10, pady=(10, 5))

        ttk.Label(
            ordner_rahmen,
            text="Hier legt GuMa alle Fallordner mit Dokumenten, Rechnungen und Unterlagen ab.\n"
                 "Wichtig: keinen Ordner wählen, der mit einem Cloud-Dienst (OneDrive, Dropbox,\n"
                 "iCloud, Google Drive ...) synchronisiert wird, da hier personenbezogene Daten liegen.",
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

        ordner_zeile = ttk.Frame(ordner_rahmen)
        ordner_zeile.pack(fill="x")
        aktueller_ordner = werte.get("dokumente_ordner") or dateien.ermittle_dokumente_ordner(BASIS_ORDNER, werte)
        ordner_var = tk.StringVar(value=aktueller_ordner)
        ttk.Entry(ordner_zeile, textvariable=ordner_var, width=55).pack(side="left", fill="x", expand=True)

        def ordner_waehlen():
            gewaehlt = filedialog.askdirectory(title="Ordner für Fälle/Dokumente wählen", parent=fenster)
            if gewaehlt:
                ordner_var.set(gewaehlt)

        ttk.Button(ordner_zeile, text="Ordner wählen...", command=ordner_waehlen).pack(side="left", padx=(8, 0))

        # --- Stammdaten ---
        stamm_rahmen = ttk.LabelFrame(inhalt, text="Stammdaten für Rechnungen/Anschreiben", padding=10)
        stamm_rahmen.grid(row=1, column=0, columnspan=2, sticky="we", padx=10, pady=5)

        labels = {
            "name": "Name / Titel", "telefon": "Telefon",
            "iban": "IBAN", "bank": "Bank",
            "kontoinhaberin": "Kontoinhaberin",
            "finanzamt": "Finanzamt", "steuernummer": "Steuernummer",
            "ust_idnr": "USt-IdNr.", "steuer_id": "Steuer-ID",
            "absender_adresse": "Absenderadresse",
        }
        vars_ = {}
        for i, (schluessel, label) in enumerate(labels.items()):
            ttk.Label(stamm_rahmen, text=label + ":").grid(row=i, column=0, sticky="e", padx=5, pady=4)
            var = tk.StringVar(value=werte.get(schluessel, ""))
            ttk.Entry(stamm_rahmen, textvariable=var, width=35).grid(row=i, column=1, pady=4, padx=5)
            vars_[schluessel] = var

        # --- Vorlagen für Anschreiben/Gutachten ---
        vorlagen_rahmen = ttk.LabelFrame(inhalt, text="Vorlagen für Anschreiben und Gutachten", padding=10)
        vorlagen_rahmen.grid(row=2, column=0, columnspan=2, sticky="we", padx=10, pady=(5, 10))

        ttk.Label(
            vorlagen_rahmen,
            text="Eigene Word-Vorlagen (.docx) hinzufügen. GuMa ersetzt darin automatisch alle\n"
                 "unten aufgeführten {{PLATZHALTER}} durch die jeweiligen Falldaten.",
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

        VORLAGEN_TYP_BESCHRIFTUNG = {"anschreiben": "Anschreiben", "gutachten": "Gutachten"}
        vorlagen_platzhalter_text = {
            "anschreiben": ", ".join("{{%s}}" % p for p in docgen.ANSCHREIBEN_PLATZHALTER),
            "gutachten": ", ".join("{{%s}}" % p for p in docgen.GUTACHTEN_PLATZHALTER),
        }
        vorlagen_zeilen = {"anschreiben": [], "gutachten": []}
        vorlagen_listen_container = {}

        def vorlagen_liste_neu_aufbauen(typ):
            for zeile in vorlagen_zeilen[typ]:
                zeile.destroy()
            vorlagen_zeilen[typ] = []
            for vorlage in repo.vorlagen_liste(typ):
                zeile = ttk.Frame(vorlagen_listen_container[typ])
                zeile.pack(fill="x", anchor="w")
                ttk.Label(zeile, text=vorlage["name"], width=35).pack(side="left")
                ttk.Button(
                    zeile, text="Entfernen",
                    command=lambda v=vorlage, t=typ: vorlage_entfernen_dialog(t, v),
                ).pack(side="left", padx=5)
                vorlagen_zeilen[typ].append(zeile)
            _scrollregion_aktualisieren()

        def vorlage_hinzufuegen_dialog(typ):
            quellpfad = filedialog.askopenfilename(
                title=f"Word-Vorlage für {VORLAGEN_TYP_BESCHRIFTUNG[typ]} wählen",
                filetypes=[("Word-Dokument", "*.docx")],
                parent=fenster,
            )
            if not quellpfad:
                return
            vorschlag = os.path.splitext(os.path.basename(quellpfad))[0]
            name = simpledialog.askstring(
                "Vorlage benennen", "Name für diese Vorlage:", initialvalue=vorschlag, parent=fenster
            )
            if not name:
                return
            try:
                vorlagen.vorlage_hinzufuegen(BASIS_ORDNER, typ, name, quellpfad)
            except Exception as fehler:
                messagebox.showerror("Fehler beim Hinzufügen", str(fehler), parent=fenster)
                return
            vorlagen_liste_neu_aufbauen(typ)

        def vorlage_entfernen_dialog(typ, vorlage):
            if not messagebox.askyesno(
                "Vorlage entfernen", f"Vorlage '{vorlage['name']}' wirklich entfernen?", parent=fenster
            ):
                return
            vorlagen.vorlage_entfernen(BASIS_ORDNER, vorlage)
            vorlagen_liste_neu_aufbauen(typ)

        for typ in repo.VORLAGEN_TYPEN:
            typ_rahmen = ttk.Frame(vorlagen_rahmen)
            typ_rahmen.pack(fill="x", pady=(4, 8))
            ttk.Label(typ_rahmen, text=f"{VORLAGEN_TYP_BESCHRIFTUNG[typ]}:", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
            ttk.Label(
                typ_rahmen, text="Unterstützte Platzhalter (Text zum Kopieren markieren):",
                font=("TkDefaultFont", 8),
            ).pack(anchor="w")
            platzhalter_feld = tk.Text(
                typ_rahmen, height=2, wrap="word", font=("TkDefaultFont", 8),
                relief="flat", background=design.FARBE_HINTERGRUND, borderwidth=0,
                highlightthickness=0,
            )
            platzhalter_feld.insert("1.0", vorlagen_platzhalter_text[typ])
            platzhalter_feld.configure(state="disabled")
            platzhalter_feld.pack(anchor="w", fill="x")
            liste_container = ttk.Frame(typ_rahmen)
            liste_container.pack(fill="x", anchor="w", pady=(4, 4))
            vorlagen_listen_container[typ] = liste_container
            ttk.Button(typ_rahmen, text="Vorlage hinzufügen...", command=lambda t=typ: vorlage_hinzufuegen_dialog(t)).pack(anchor="w")

        for typ in repo.VORLAGEN_TYPEN:
            vorlagen_liste_neu_aufbauen(typ)

        # --- Standard-Sätze für Rechnungen ---
        saetze_rahmen = ttk.LabelFrame(inhalt, text="Standard-Sätze für Rechnungen", padding=10)
        saetze_rahmen.grid(row=3, column=0, columnspan=2, sticky="we", padx=10, pady=(5, 10))

        ttk.Label(
            saetze_rahmen,
            text="Vorbelegung für jede neue Rechnung - bleibt pro Rechnung wie gewohnt änderbar.",
            justify="left",
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        saetze_labels = {
            "standard_stundensatz": "Stundensatz (€)",
            "standard_km_satz": "km-Satz (€/km)",
            "standard_mwst_satz": "MwSt.-Satz (%)",
            "standard_schreibgebuehr_satz": "Schreibgebühr (€ je 1000 Zeichen)",
        }
        for i, (schluessel, label) in enumerate(saetze_labels.items()):
            row, col = divmod(i, 2)
            ttk.Label(saetze_rahmen, text=label + ":").grid(row=row + 1, column=col * 2, sticky="e", padx=5, pady=4)
            var = tk.StringVar(value=werte.get(schluessel, ""))
            ttk.Entry(saetze_rahmen, textvariable=var, width=12).grid(row=row + 1, column=col * 2 + 1, sticky="w", pady=4, padx=(0, 15))
            vars_[schluessel] = var

        ttk.Separator(saetze_rahmen, orient="horizontal").grid(row=3, column=0, columnspan=4, sticky="we", pady=8)

        ttk.Label(
            saetze_rahmen,
            text="Kopien-Staffelung: bis zur Grenze der erste Satz, ab der nächsten Seite der zweite Satz.",
            justify="left",
        ).grid(row=4, column=0, columnspan=4, sticky="w", pady=(0, 8))

        kopien_labels = {
            "kopien_grenze": "Grenze (Seiten)",
            "kopien_satz_bis_grenze": "Satz bis Grenze (€/Seite)",
            "kopien_satz_ab_grenze": "Satz ab Grenze (€/Seite)",
        }
        for i, (schluessel, label) in enumerate(kopien_labels.items()):
            ttk.Label(saetze_rahmen, text=label + ":").grid(row=5 + i, column=0, sticky="e", padx=5, pady=4)
            var = tk.StringVar(value=werte.get(schluessel, ""))
            ttk.Entry(saetze_rahmen, textvariable=var, width=12).grid(row=5 + i, column=1, sticky="w", pady=4, padx=(0, 15))
            vars_[schluessel] = var

        # --- Feste Tage für die Terminplanung ---
        feste_tage_rahmen = ttk.LabelFrame(inhalt, text="Feste Tage für die Terminplanung", padding=10)
        feste_tage_rahmen.grid(row=4, column=0, columnspan=2, sticky="we", padx=10, pady=(5, 10))

        ttk.Label(
            feste_tage_rahmen,
            text="Angehakte Wochentage gelten als fest (frei oder verplant) - sie werden im\n"
                 "Kalender rot markiert, und beim Anlegen eines Termins an so einem Tag fragt\n"
                 "GuMa vorher nach.",
            justify="left",
        ).grid(row=0, column=0, columnspan=7, sticky="w", pady=(0, 8))

        bereits_gesperrte_wochentage = kalenderfeld.gesperrte_wochentage_lesen(werte)
        wochentag_vars = []
        for index, kuerzel in enumerate(kalenderfeld.WOCHENTAGE_KUERZEL):
            var = tk.BooleanVar(value=index in bereits_gesperrte_wochentage)
            ttk.Checkbutton(feste_tage_rahmen, text=kuerzel, variable=var).grid(row=1, column=index, padx=5)
            wochentag_vars.append(var)

        def speichern():
            alter_ordner = dateien.ermittle_dokumente_ordner(BASIS_ORDNER, repo.einstellungen_holen())
            neuer_ordner = ordner_var.get().strip()

            for schluessel, var in vars_.items():
                repo.einstellung_setzen(schluessel, var.get())
            repo.einstellung_setzen("dokumente_ordner", neuer_ordner)
            gesperrte_wochentage = {index for index, var in enumerate(wochentag_vars) if var.get()}
            repo.einstellung_setzen("gesperrte_wochentage", kalenderfeld.gesperrte_wochentage_schreiben(gesperrte_wochentage))

            if neuer_ordner and os.path.normcase(os.path.normpath(neuer_ordner)) != os.path.normcase(os.path.normpath(alter_ordner)):
                if os.path.isdir(alter_ordner) and os.listdir(alter_ordner):
                    verschieben = messagebox.askyesno(
                        "Speicherort geändert",
                        f"Der Speicherort wurde geändert.\n\nVorhandene Fallordner liegen noch hier:\n{alter_ordner}\n\n"
                        f"Sollen sie automatisch in den neuen Ordner verschoben werden?\n{neuer_ordner}",
                        parent=fenster,
                    )
                    if verschieben:
                        try:
                            dateien.alle_faelle_verschieben(alter_ordner, neuer_ordner)
                        except Exception as fehler:
                            messagebox.showerror("Fehler beim Verschieben", str(fehler), parent=fenster)

            self._dokumente_ordner_neu_einlesen()
            fenster.destroy()

        ttk.Button(button_leiste, text="Speichern", style="Accent.TButton", command=speichern).pack(side="right")
        ttk.Button(button_leiste, text="Abbrechen", command=fenster.destroy).pack(side="right", padx=(0, 8))


def starten():
    app = Anwendung()
    app.mainloop()
