"""
Wiederverwendbares Datumsfeld mit Kalender-Auswahl (tkcalendar) anstelle
freier Texteingabe, inklusive roter Markierung der in den Einstellungen
hinterlegten "festen Tage" (Wochentage, die grundsätzlich frei- oder
verplant sind, z.B. jeden Freitag oder das ganze Wochenende).
"""
import calendar as _calendar_modul
import datetime

WOCHENTAGE_KUERZEL = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
GESPERRTER_TAG_TAG = "gesperrter_tag"


def gesperrte_wochentage_lesen(einstellungen: dict) -> set:
    """Liest die in den Einstellungen hinterlegten festen Wochentage aus
    (0=Montag ... 6=Sonntag, wie datetime.date.weekday())."""
    text = (einstellungen.get("gesperrte_wochentage") or "").strip()
    if not text:
        return set()
    return {int(t) for t in text.split(",") if t.strip().isdigit()}


def gesperrte_wochentage_schreiben(wochentage: set) -> str:
    return ",".join(str(i) for i in sorted(wochentage))


def ist_gesperrter_tag(datum_text: str, gesperrte_wochentage: set) -> bool:
    """datum_text im Format TT.MM.JJJJ. Nicht auswertbare Daten gelten als
    nicht gesperrt, damit unklare Eingaben nicht fälschlich eine Warnung
    auslösen."""
    try:
        datum = datetime.datetime.strptime(datum_text or "", "%d.%m.%Y").date()
    except ValueError:
        return False
    return datum.weekday() in gesperrte_wochentage


def _gesperrte_tage_markieren(kalender, gesperrte_wochentage: set):
    """Färbt im aktuell im Kalender-Widget angezeigten Monat alle Tage rot,
    deren Wochentag als 'fest' hinterlegt ist. Wird bei jedem Monatswechsel
    erneut aufgerufen (siehe <<CalendarMonthChanged>>), da sich der
    angezeigte Monat sonst nicht automatisch aktualisieren würde."""
    kalender.calevent_remove(tag=GESPERRTER_TAG_TAG)
    if not gesperrte_wochentage:
        return
    monat, jahr = kalender.get_displayed_month()
    anzahl_tage = _calendar_modul.monthrange(jahr, monat)[1]
    for tag in range(1, anzahl_tage + 1):
        datum = datetime.date(jahr, monat, tag)
        if datum.weekday() in gesperrte_wochentage:
            kalender.calevent_create(datum, "fester Tag", GESPERRTER_TAG_TAG)
    kalender.tag_config(GESPERRTER_TAG_TAG, background="#F8D7DA", foreground="#7A1F1F")


def datumsfeld_erstellen(parent, textvariable, einstellungen: dict, **kw):
    """Erstellt ein Kalender-Datumsfeld (Format TT.MM.JJJJ, kompatibel zum
    bisherigen Text-Format), das die in den Einstellungen hinterlegten
    festen Wochentage im Kalender-Popup rot markiert."""
    # Erst hier statt am Dateianfang importiert: so bleiben die reinen
    # Datums-/Logikfunktionen oben (gesperrte_wochentage_lesen usw.) auch
    # ohne installiertes tkcalendar/Tk-GUI-Toolkit importier- und testbar.
    from tkcalendar import DateEntry

    # DateEntry ignoriert beim Erzeugen den evtl. schon gesetzten Wert von
    # textvariable und initialisiert sich sonst immer auf das heutige Datum
    # (wichtig z.B. beim Öffnen einer bestehenden Rechnung mit eigenem
    # Datum) - deshalb hier explizit als year/month/day übergeben.
    anfangsdatum = {}
    try:
        geparst = datetime.datetime.strptime(textvariable.get(), "%d.%m.%Y").date()
        anfangsdatum = {"year": geparst.year, "month": geparst.month, "day": geparst.day}
    except ValueError:
        pass

    kw.setdefault("locale", "de_DE")
    feld = DateEntry(parent, textvariable=textvariable, date_pattern="dd.mm.yyyy", **anfangsdatum, **kw)
    gesperrte_wochentage = gesperrte_wochentage_lesen(einstellungen)

    def _neu_markieren(_event=None):
        _gesperrte_tage_markieren(feld._calendar, gesperrte_wochentage)

    feld._calendar.bind("<<CalendarMonthChanged>>", _neu_markieren)
    _neu_markieren()
    return feld
