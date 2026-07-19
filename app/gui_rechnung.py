"""
Fenster zum Bearbeiten einer einzelnen Rechnung: Zeitposten, Aufwendungen,
Live-Berechnung und Excel-Export.
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from app import repo
from app.invoice import berechne_rechnung, KOPIEN_GRENZE, KOPIEN_SATZ_BIS_GRENZE, KOPIEN_SATZ_AB_GRENZE
from app.invoice_export import exportiere_rechnung_xlsx
from app import design

BASIS_ORDNER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class RechnungFenster(tk.Toplevel):
    def __init__(self, master, fall: dict, rechnung_id: int, dokumente_ordner: str):
        super().__init__(master)
        self.fall = fall
        self.rechnung_id = rechnung_id
        self.dokumente_ordner = dokumente_ordner
        self.title(f"GuMa - Rechnung - {fall.get('aktenzeichen','') or 'Fall'}")
        self.geometry("820x680")
        self.minsize(700, 480)
        self.configure(bg=design.FARBE_HINTERGRUND)
        design.icon_setzen(self, BASIS_ORDNER)

        self.zeitposten_zeilen = []  # Liste von dicts mit id, bezeichnung_var, minuten_var
        self.zusatzposten_zeilen = []  # Liste von dicts mit id, bezeichnung_var, betrag_var

        # Kopien-Staffelung kommt aus den Einstellungen (Datei → Stammdaten /
        # Einstellungen), fällt ohne eigene Angabe auf die Werkseinstellung
        # zurück - gilt für alle Rechnungen gleichermaßen, ist also keine
        # Eigenschaft der einzelnen Rechnung.
        einstellungen = repo.einstellungen_holen()
        self.kopien_grenze = int(self._text_zu_zahl(einstellungen.get("kopien_grenze"), KOPIEN_GRENZE))
        self.kopien_satz_bis_grenze = self._text_zu_zahl(einstellungen.get("kopien_satz_bis_grenze"), KOPIEN_SATZ_BIS_GRENZE)
        self.kopien_satz_ab_grenze = self._text_zu_zahl(einstellungen.get("kopien_satz_ab_grenze"), KOPIEN_SATZ_AB_GRENZE)

        self._aufbauen()
        self._laden()
        self._neu_berechnen()

    # ---------- UI Aufbau ----------

    def _aufbauen(self):
        # Die Speichern/Export/Schließen-Buttons werden ZUERST unten fest
        # eingeplant, damit sie immer sichtbar bleiben - unabhängig davon,
        # wie viel Inhalt (z.B. viele Zeitpositionen) darüber Platz braucht.
        button_leiste = ttk.Frame(self, padding=10)
        button_leiste.pack(side="bottom", fill="x")
        ttk.Button(button_leiste, text="Speichern", style="Accent.TButton", command=self._speichern).pack(side="left", padx=5)
        ttk.Button(button_leiste, text="Als Excel exportieren...", command=self._exportieren).pack(side="left", padx=5)
        ttk.Button(button_leiste, text="Schließen", command=self.destroy).pack(side="right", padx=5)

        hinweis_leiste = ttk.Frame(self, padding=(10, 0))
        hinweis_leiste.pack(side="bottom", fill="x")
        ttk.Label(
            hinweis_leiste,
            text="Die Rechnung enthält personenbezogene Falldaten - beim Export keinen Cloud-Ordner\n"
                 "(OneDrive, Dropbox, iCloud, Google Drive ...) als Speicherort wählen.",
            justify="left", font=("TkDefaultFont", 8, "italic"),
        ).pack(anchor="w", pady=(0, 5))

        # Der restliche Inhalt kommt in einen scrollbaren Bereich, damit bei
        # vielen Zeitpositionen oder kleineren Bildschirmen nichts abgeschnitten
        # wird, sondern man mit dem Mausrad oder der Bildlaufleiste scrollen kann.
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
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
        self.bind("<Destroy>", lambda e: _mausrad_deaktivieren() if e.widget is self else None)

        kopf = ttk.Frame(inhalt, padding=10)
        kopf.pack(fill="x")

        self.rechnungsnummer_var = tk.StringVar()
        self.datum_var = tk.StringVar()

        ttk.Label(kopf, text="Rechnungsnummer:").grid(row=0, column=0, sticky="w")
        ttk.Entry(kopf, textvariable=self.rechnungsnummer_var, width=20).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(kopf, text="Datum (TT.MM.JJJJ):").grid(row=0, column=2, sticky="w", padx=(20, 0))
        ttk.Entry(kopf, textvariable=self.datum_var, width=15).grid(row=0, column=3, sticky="w", padx=5)

        # --- Zeitaufwand ---
        zeit_rahmen = ttk.LabelFrame(inhalt, text="1. Zeitaufwand (Minuten je Position)", padding=10)
        zeit_rahmen.pack(fill="x", padx=10, pady=5)

        self.zeitposten_frame = ttk.Frame(zeit_rahmen)
        self.zeitposten_frame.pack(fill="x")

        ttk.Button(zeit_rahmen, text="+ Position hinzufügen", command=self._zeile_hinzufuegen).pack(anchor="w", pady=5)

        stundensatz_frame = ttk.Frame(zeit_rahmen)
        stundensatz_frame.pack(fill="x", pady=(5, 0))
        ttk.Label(stundensatz_frame, text="Stundensatz (€):").pack(side="left")
        self.stundensatz_var = tk.StringVar(value="100")
        ttk.Entry(stundensatz_frame, textvariable=self.stundensatz_var, width=10).pack(side="left", padx=5)
        self.stundensatz_var.trace_add("write", lambda *_: self._neu_berechnen())

        # --- Aufwendungen ---
        aufw_rahmen = ttk.LabelFrame(inhalt, text="2. Aufwendungen", padding=10)
        aufw_rahmen.pack(fill="x", padx=10, pady=5)

        self.km_var = tk.StringVar(value="0")
        self.km_satz_var = tk.StringVar(value="0.42")
        self.porto_var = tk.StringVar(value="0")
        self.telefon_var = tk.StringVar(value="0")
        self.zeichen_var = tk.StringVar(value="0")
        self.schreibgebuehr_satz_var = tk.StringVar(value="1.5")
        self.kopien_var = tk.StringVar(value="0")
        self.mwst_var = tk.StringVar(value="19")

        felder = [
            ("Reisekosten - km:", self.km_var), ("...à € / km:", self.km_satz_var),
            ("Porto (€):", self.porto_var), ("Telefon (€):", self.telefon_var),
            ("Schreibgebühr - Zeichenanzahl:", self.zeichen_var), ("...€ je angef. 1000 Zeichen:", self.schreibgebuehr_satz_var),
            ("Kopien GA - Seitenzahl gesamt:", self.kopien_var), ("MwSt. (%):", self.mwst_var),
        ]
        for i, (label, var) in enumerate(felder):
            row, col = divmod(i, 2)
            f = ttk.Frame(aufw_rahmen)
            f.grid(row=row, column=col, sticky="w", padx=10, pady=3)
            ttk.Label(f, text=label, width=28).pack(side="left")
            entry = ttk.Entry(f, textvariable=var, width=12)
            entry.pack(side="left")
            var.trace_add("write", lambda *_: self._neu_berechnen())

        ttk.Label(
            aufw_rahmen,
            text=(
                f"Kopien werden automatisch gestaffelt berechnet: erste {self.kopien_grenze} Seiten "
                f"à {self.kopien_satz_bis_grenze:.2f} €, ab Seite {self.kopien_grenze + 1} "
                f"à {self.kopien_satz_ab_grenze:.2f} € (anpassbar in den Einstellungen)."
            ),
            font=("TkDefaultFont", 8, "italic"),
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=(5, 10))

        ttk.Separator(aufw_rahmen, orient="horizontal").grid(row=5, column=0, columnspan=2, sticky="we", padx=10, pady=(0, 8))

        ttk.Label(aufw_rahmen, text="Weitere Positionen (frei benannt):").grid(
            row=6, column=0, columnspan=2, sticky="w", padx=10
        )
        self.zusatzposten_frame = ttk.Frame(aufw_rahmen)
        self.zusatzposten_frame.grid(row=7, column=0, columnspan=2, sticky="we", padx=10, pady=(3, 0))
        ttk.Button(
            aufw_rahmen, text="+ Position hinzufügen", command=self._zusatzposten_zeile_hinzufuegen
        ).grid(row=8, column=0, columnspan=2, sticky="w", padx=10, pady=5)

        # --- Ergebnis ---
        ergebnis_rahmen = ttk.LabelFrame(inhalt, text="Berechnung", padding=10)
        ergebnis_rahmen.pack(fill="both", expand=True, padx=10, pady=5)
        self.ergebnis_text = tk.Text(ergebnis_rahmen, height=12, state="disabled", font=("Courier", 10))
        self.ergebnis_text.pack(fill="both", expand=True)

    def _zeile_hinzufuegen(self, bezeichnung="", minuten=0, posten_id=None):
        zeile_frame = ttk.Frame(self.zeitposten_frame)
        zeile_frame.pack(fill="x", pady=1)

        bez_var = tk.StringVar(value=bezeichnung)
        min_var = tk.StringVar(value=str(minuten))

        bez_entry = ttk.Entry(zeile_frame, textvariable=bez_var, width=50)
        bez_entry.pack(side="left", padx=2)
        min_entry = ttk.Entry(zeile_frame, textvariable=min_var, width=8)
        min_entry.pack(side="left", padx=2)
        ttk.Label(zeile_frame, text="Min.").pack(side="left")

        min_var.trace_add("write", lambda *_: self._neu_berechnen())

        eintrag = {"id": posten_id, "frame": zeile_frame, "bezeichnung": bez_var, "minuten": min_var}

        def entfernen():
            self.zeitposten_zeilen.remove(eintrag)
            zeile_frame.destroy()
            self._neu_berechnen()

        ttk.Button(zeile_frame, text="✕", width=3, command=entfernen).pack(side="left", padx=2)

        self.zeitposten_zeilen.append(eintrag)

    def _zusatzposten_zeile_hinzufuegen(self, bezeichnung="", betrag=0, posten_id=None):
        zeile_frame = ttk.Frame(self.zusatzposten_frame)
        zeile_frame.pack(fill="x", pady=1)

        bez_var = tk.StringVar(value=bezeichnung)
        betrag_var = tk.StringVar(value=str(betrag))

        bez_entry = ttk.Entry(zeile_frame, textvariable=bez_var, width=50)
        bez_entry.pack(side="left", padx=2)
        betrag_entry = ttk.Entry(zeile_frame, textvariable=betrag_var, width=8)
        betrag_entry.pack(side="left", padx=2)
        ttk.Label(zeile_frame, text="€").pack(side="left")

        betrag_var.trace_add("write", lambda *_: self._neu_berechnen())

        eintrag = {"id": posten_id, "frame": zeile_frame, "bezeichnung": bez_var, "betrag": betrag_var}

        def entfernen():
            self.zusatzposten_zeilen.remove(eintrag)
            zeile_frame.destroy()
            self._neu_berechnen()

        ttk.Button(zeile_frame, text="✕", width=3, command=entfernen).pack(side="left", padx=2)

        self.zusatzposten_zeilen.append(eintrag)

    # ---------- Daten laden / speichern ----------

    def _laden(self):
        rechnung = repo.rechnung_holen(self.rechnung_id)
        if not rechnung:
            return
        self.rechnungsnummer_var.set(rechnung["rechnungsnummer"] or "")
        self.datum_var.set(rechnung["datum"] or "")
        self.stundensatz_var.set(str(rechnung["stundensatz"]))
        self.km_var.set(str(rechnung["km"]))
        self.km_satz_var.set(str(rechnung["km_satz"]))
        self.porto_var.set(str(rechnung["porto"]))
        self.telefon_var.set(str(rechnung["telefon"]))
        self.zeichen_var.set(str(rechnung["zeichen_anzahl"]))
        self.schreibgebuehr_satz_var.set(str(rechnung["schreibgebuehr_satz"]))
        self.kopien_var.set(str(rechnung["kopien_seiten"]))
        self.mwst_var.set(str(rechnung["mwst_satz"]))

        for posten in repo.zeitposten_fuer_rechnung(self.rechnung_id):
            self._zeile_hinzufuegen(posten["bezeichnung"], posten["minuten"], posten["id"])

        for posten in repo.aufwandsposten_fuer_rechnung(self.rechnung_id):
            self._zusatzposten_zeile_hinzufuegen(posten["bezeichnung"], posten["betrag"], posten["id"])

    def _zahl(self, var, standard=0.0):
        return self._text_zu_zahl(var.get(), standard)

    @staticmethod
    def _text_zu_zahl(text, standard=0.0):
        try:
            text = (text or "").strip().replace(",", ".")
            return float(text) if text else standard
        except ValueError:
            return standard

    def _aktuelle_zeitposten(self):
        return [
            {"bezeichnung": z["bezeichnung"].get(), "minuten": int(self._zahl(z["minuten"]))}
            for z in self.zeitposten_zeilen
        ]

    def _aktuelle_zusatzposten(self):
        return [
            {"bezeichnung": z["bezeichnung"].get(), "betrag": self._zahl(z["betrag"])}
            for z in self.zusatzposten_zeilen
        ]

    def _neu_berechnen(self):
        try:
            ergebnis = berechne_rechnung(
                zeitposten=self._aktuelle_zeitposten(),
                stundensatz=self._zahl(self.stundensatz_var, 100),
                km=self._zahl(self.km_var),
                km_satz=self._zahl(self.km_satz_var, 0.42),
                porto=self._zahl(self.porto_var),
                telefon=self._zahl(self.telefon_var),
                zeichen_anzahl=int(self._zahl(self.zeichen_var)),
                schreibgebuehr_satz=self._zahl(self.schreibgebuehr_satz_var, 1.5),
                kopien_seiten=int(self._zahl(self.kopien_var)),
                mwst_satz=self._zahl(self.mwst_var, 19),
                zusatzposten=self._aktuelle_zusatzposten(),
                kopien_grenze=self.kopien_grenze,
                kopien_satz_bis_grenze=self.kopien_satz_bis_grenze,
                kopien_satz_ab_grenze=self.kopien_satz_ab_grenze,
            )
        except Exception:
            return

        text = (
            f"Zeitaufwand:      {ergebnis.minuten_gesamt} Min. = {ergebnis.stunden_exakt:.2f} Std., "
            f"aufgerundet {ergebnis.stunden_aufgerundet} Std. à {ergebnis.stundensatz:.2f} €\n"
            f"Summe 1 (Zeit):   {ergebnis.summe_zeitaufwand:>10.2f} €\n\n"
            f"Reisekosten:      {ergebnis.reisekosten:>10.2f} €\n"
            f"Porto:            {ergebnis.porto:>10.2f} €\n"
            f"Telefon:          {ergebnis.telefon:>10.2f} €\n"
            f"Schreibgebühr:    {ergebnis.schreibgebuehr:>10.2f} € ({ergebnis.schreibgebuehr_einheiten} x angef. 1000 Zeichen)\n"
            f"Kopien:           {ergebnis.kopien_kosten:>10.2f} €\n"
            f"Weitere Pos.:     {ergebnis.zusatzposten_summe:>10.2f} €\n"
            f"Summe 2 (Aufw.):  {ergebnis.summe_aufwendungen:>10.2f} €\n\n"
            f"Summe 1+2:        {ergebnis.zwischensumme:>10.2f} €\n"
            f"MwSt. {ergebnis.mwst_satz:.0f}%:        {ergebnis.mwst_betrag:>10.2f} €\n"
            f"{'GESAMTSUMME:':<18}{ergebnis.gesamtsumme:>10.2f} €\n"
        )
        self.ergebnis_text.config(state="normal")
        self.ergebnis_text.delete("1.0", "end")
        self.ergebnis_text.insert("1.0", text)
        self.ergebnis_text.config(state="disabled")
        self._letztes_ergebnis = ergebnis

    def _rechnung_daten(self):
        return {
            "rechnungsnummer": self.rechnungsnummer_var.get(),
            "datum": self.datum_var.get(),
            "stundensatz": self._zahl(self.stundensatz_var, 100),
            "km": self._zahl(self.km_var),
            "km_satz": self._zahl(self.km_satz_var, 0.42),
            "porto": self._zahl(self.porto_var),
            "telefon": self._zahl(self.telefon_var),
            "zeichen_anzahl": int(self._zahl(self.zeichen_var)),
            "schreibgebuehr_satz": self._zahl(self.schreibgebuehr_satz_var, 1.5),
            "kopien_seiten": int(self._zahl(self.kopien_var)),
            "mwst_satz": self._zahl(self.mwst_var, 19),
        }

    def _speichern(self):
        repo.rechnung_aktualisieren(self.rechnung_id, self._rechnung_daten())

        vorhandene_ids = {z["id"] for z in repo.zeitposten_fuer_rechnung(self.rechnung_id)}
        aktuelle_ids = set()
        for zeile in self.zeitposten_zeilen:
            bez = zeile["bezeichnung"].get()
            minuten = int(self._zahl(zeile["minuten"]))
            if zeile["id"] is None:
                repo.zeitposten_hinzufuegen(self.rechnung_id, bez, minuten)
            else:
                repo.zeitposten_speichern(zeile["id"], bez, minuten)
                aktuelle_ids.add(zeile["id"])
        for entfernte_id in vorhandene_ids - aktuelle_ids:
            repo.zeitposten_loeschen(entfernte_id)

        vorhandene_aufwand_ids = {z["id"] for z in repo.aufwandsposten_fuer_rechnung(self.rechnung_id)}
        aktuelle_aufwand_ids = set()
        for zeile in self.zusatzposten_zeilen:
            bez = zeile["bezeichnung"].get()
            betrag = self._zahl(zeile["betrag"])
            if zeile["id"] is None:
                repo.aufwandsposten_hinzufuegen(self.rechnung_id, bez, betrag)
            else:
                repo.aufwandsposten_speichern(zeile["id"], bez, betrag)
                aktuelle_aufwand_ids.add(zeile["id"])
        for entfernte_id in vorhandene_aufwand_ids - aktuelle_aufwand_ids:
            repo.aufwandsposten_loeschen(entfernte_id)

        messagebox.showinfo("Gespeichert", "Rechnung wurde gespeichert.", parent=self)

    def _exportieren(self):
        self._speichern()
        vorschlag = f"Rechnung_{(self.rechnungsnummer_var.get() or 'neu').replace('/', '-')}.xlsx"
        pfad = filedialog.asksaveasfilename(
            parent=self,
            initialdir=self.dokumente_ordner,
            initialfile=vorschlag,
            defaultextension=".xlsx",
            filetypes=[("Excel-Datei", "*.xlsx")],
        )
        if not pfad:
            return
        from app.db import get_conn
        with get_conn() as conn:
            einstellungen = {r["schluessel"]: r["wert"] for r in conn.execute("SELECT * FROM einstellungen").fetchall()}
        exportiere_rechnung_xlsx(
            pfad, self.fall, repo.rechnung_holen(self.rechnung_id),
            repo.zeitposten_fuer_rechnung(self.rechnung_id), einstellungen,
            zusatzposten=repo.aufwandsposten_fuer_rechnung(self.rechnung_id),
        )
        messagebox.showinfo("Export", f"Rechnung wurde gespeichert unter:\n{pfad}", parent=self)
