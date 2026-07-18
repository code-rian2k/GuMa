"""
Rechnungslogik - bildet exakt die bisherige Excel-Berechnung nach:

1. Zeitaufwand: Summe aller Minuten-Posten -> Stunden -> aufgerundet auf volle
   Stunde -> x Stundensatz
2. Aufwendungen:
   - Reisekosten: km x km-Satz
   - Porto (freier Betrag)
   - Telefon (freier Betrag)
   - Schreibgebühr: je angefangene 1000 Zeichen x Satz (aufgerundet)
   - Kopien: gestaffelt - erste 50 Seiten x 0,50 €, jede weitere Seite x 0,15 €
3. Summe 1 (Zeitaufwand) + Summe 2 (Aufwendungen) = Zwischensumme
4. MwSt auf Zwischensumme
5. Gesamtsumme
"""
import math
from dataclasses import dataclass, field


KOPIEN_GRENZE = 50
KOPIEN_SATZ_BIS_GRENZE = 0.50
KOPIEN_SATZ_AB_GRENZE = 0.15


@dataclass
class RechnungsErgebnis:
    minuten_gesamt: int
    stunden_exakt: float
    stunden_aufgerundet: int
    stundensatz: float
    summe_zeitaufwand: float

    reisekosten: float
    porto: float
    telefon: float
    schreibgebuehr: float
    schreibgebuehr_einheiten: int
    kopien_kosten: float
    summe_aufwendungen: float

    zwischensumme: float
    mwst_satz: float
    mwst_betrag: float
    gesamtsumme: float


def berechne_kopien_kosten(seiten: int) -> float:
    if seiten <= 0:
        return 0.0
    if seiten <= KOPIEN_GRENZE:
        return round(seiten * KOPIEN_SATZ_BIS_GRENZE, 2)
    return round(
        KOPIEN_GRENZE * KOPIEN_SATZ_BIS_GRENZE
        + (seiten - KOPIEN_GRENZE) * KOPIEN_SATZ_AB_GRENZE,
        2,
    )


def berechne_schreibgebuehr(zeichen_anzahl: int, satz: float):
    """Je angefangene 1000 Zeichen wird aufgerundet."""
    if zeichen_anzahl <= 0:
        return 0, 0.0
    einheiten = math.ceil(zeichen_anzahl / 1000)
    return einheiten, round(einheiten * satz, 2)


def berechne_rechnung(
    zeitposten: list,   # Liste von dicts mit "minuten"
    stundensatz: float,
    km: float,
    km_satz: float,
    porto: float,
    telefon: float,
    zeichen_anzahl: int,
    schreibgebuehr_satz: float,
    kopien_seiten: int,
    mwst_satz: float,
) -> RechnungsErgebnis:
    minuten_gesamt = sum(int(p.get("minuten", 0) or 0) for p in zeitposten)
    stunden_exakt = minuten_gesamt / 60
    stunden_aufgerundet = math.ceil(stunden_exakt) if minuten_gesamt > 0 else 0
    summe_zeitaufwand = round(stunden_aufgerundet * stundensatz, 2)

    reisekosten = round((km or 0) * (km_satz or 0), 2)
    schreibgebuehr_einheiten, schreibgebuehr = berechne_schreibgebuehr(
        zeichen_anzahl or 0, schreibgebuehr_satz or 0
    )
    kopien_kosten = berechne_kopien_kosten(kopien_seiten or 0)

    summe_aufwendungen = round(
        reisekosten + (porto or 0) + (telefon or 0) + schreibgebuehr + kopien_kosten, 2
    )

    zwischensumme = round(summe_zeitaufwand + summe_aufwendungen, 2)
    mwst_betrag = round(zwischensumme * (mwst_satz or 0) / 100, 2)
    gesamtsumme = round(zwischensumme + mwst_betrag, 2)

    return RechnungsErgebnis(
        minuten_gesamt=minuten_gesamt,
        stunden_exakt=stunden_exakt,
        stunden_aufgerundet=stunden_aufgerundet,
        stundensatz=stundensatz,
        summe_zeitaufwand=summe_zeitaufwand,
        reisekosten=reisekosten,
        porto=porto or 0,
        telefon=telefon or 0,
        schreibgebuehr=schreibgebuehr,
        schreibgebuehr_einheiten=schreibgebuehr_einheiten,
        kopien_kosten=kopien_kosten,
        summe_aufwendungen=summe_aufwendungen,
        zwischensumme=zwischensumme,
        mwst_satz=mwst_satz,
        mwst_betrag=mwst_betrag,
        gesamtsumme=gesamtsumme,
    )
