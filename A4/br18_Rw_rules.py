"""BR18: regelbaseret klassifikation af krav til luftlydisolation i undervisningsbygninger.

Kilder (BR18, vejledning til undervisningsbygninger):
- Afsnit 3.1: Definitioner af rumtyper
  https://www.bygningsreglementet.dk/tekniske-bestemmelser/17/vejledninger/undervisningsbygninger/definitioner-af-rumtyper-for-undervisningsbygninger/
- Afsnit 3.2: Lydisolation, tabel 3.1
  https://www.bygningsreglementet.dk/tekniske-bestemmelser/17/vejledninger/undervisningsbygninger/lydisolation-for-undervisningsbygninger/

Vigtigt: Beregner det KRÆVEDE R'w, ikke den faktiske lydisolation i en konstruktion.
Dørforbindelse betyder en direkte dørforbindelse mellem de to aktuelle rum.
Andre åbninger/gennemføringer giver ikke automatisk lempeligere krav.
Visse specialtilfælde skal vurderes af en akustisk rådgiver.

Python 3.10+. Ingen eksterne pakker.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Rumtype(str, Enum):
    UNDERVISNING = "undervisning"
    FAELLES = "faelles"
    SLOEJD = "sloejd"
    MUSIK = "musik"
    AABENT = "aabent_undervisningsomraade"
    EKSTERN = "ekstern_enhed_eller_institution"
    UKENDT = "ukendt"


# Udvid selv ordbogen efter gennemgang af rumfunktionerne fra IFC/Revit.
# Ukendte navne gætter vi ikke på; de sendes til manuel vurdering.
RUMTYPER = {
    "undervisning": Rumtype.UNDERVISNING,
    "undervisningsrum": Rumtype.UNDERVISNING,
    "teaching room": Rumtype.UNDERVISNING,
    "sløjdundervisningsrum": Rumtype.SLOEJD,
    "woodworking classroom": Rumtype.SLOEJD,
    "sang- og musikundervisningsrum": Rumtype.MUSIK,
    "music and singing classroom": Rumtype.MUSIK,
    "ekstern enhed/institution": Rumtype.EKSTERN,
    "external unit/institution": Rumtype.EKSTERN,
    "klasseværelse": Rumtype.UNDERVISNING,
    "klasselokale": Rumtype.UNDERVISNING,
    "faglokale": Rumtype.UNDERVISNING,
    "grupperum": Rumtype.UNDERVISNING,
    "auditorium": Rumtype.UNDERVISNING,
    "gymnastiksal": Rumtype.UNDERVISNING,
    "bibliotek": Rumtype.UNDERVISNING,
    "kontor": Rumtype.UNDERVISNING,
    "forberedelsesrum": Rumtype.UNDERVISNING,
    "personalerum": Rumtype.UNDERVISNING,
    "fælles": Rumtype.FAELLES,
    "fællesrum": Rumtype.FAELLES,
    "common area": Rumtype.FAELLES,
    "gang": Rumtype.FAELLES,
    "gangareal": Rumtype.FAELLES,
    "korridor": Rumtype.FAELLES,
    "trapperum": Rumtype.FAELLES,
    "aula": Rumtype.FAELLES,
    "kantine": Rumtype.FAELLES,
    "toilet": Rumtype.FAELLES,
    "toiletrum": Rumtype.FAELLES,
    "teknikrum": Rumtype.FAELLES,
    "sløjd": Rumtype.SLOEJD,
    "sløjdlokale": Rumtype.SLOEJD,
    "musik": Rumtype.MUSIK,
    "musiklokale": Rumtype.MUSIK,
    "sang": Rumtype.MUSIK,
    "sanglokale": Rumtype.MUSIK,
    "sang og musik": Rumtype.MUSIK,
    "åbent undervisningsområde": Rumtype.AABENT,
    "åbne undervisningsområder": Rumtype.AABENT,
    "open-plan teaching areas": Rumtype.AABENT,
    "ekstern": Rumtype.EKSTERN,
    "anden institution": Rumtype.EKSTERN,
    "anden undervisningsinstitution": Rumtype.EKSTERN,
    "anden daginstitution": Rumtype.EKSTERN,
    "erhvervsenhed": Rumtype.EKSTERN,
}


def rumtype(tekst: str | Rumtype) -> Rumtype:
    if isinstance(tekst, Rumtype):
        return tekst
    return RUMTYPER.get(tekst.strip().casefold(), Rumtype.UKENDT)


@dataclass(frozen=True)
class Rum:
    navn: str
    funktion: str | Rumtype


@dataclass(frozen=True)
class Rumpar:
    a: Rum
    b: Rum
    retning: str = "horisontal"  # 'horisontal' = side om side, 'vertikal' = over/under
    doerforbindelse: bool = False  # Direkte mellem rum A og B
    fleksibel_adskillelse: bool = False  # Kun i åbent undervisningsområde
    ekstern_saerlig_stoej: bool | None = None  # Kun relevant ved 'ekstern'
    gennemfoeringer: bool = False  # Fx ventilationskanal: krav sænkes IKKE


@dataclass(frozen=True)
class Resultat:
    krav_db: int | None
    regel: str
    forklaring: str
    status: str  # 'bestemt' eller 'manuel_vurdering'
    bemaerkning: str = ""


def bestem_lydisolation(par: Rumpar) -> Resultat:
    """Bestem vejledende BR18 minimumskrav R'w for den samlede rumadskillelse."""
    t1, t2 = rumtype(par.a.funktion), rumtype(par.b.funktion)
    typer = {t1, t2}
    retning = par.retning.strip().casefold()
    if retning not in {"horisontal", "vertikal"}:
        raise ValueError("direction must be 'horisontal' or 'vertikal'")

    noter = []
    if par.gennemfoeringer:
        noter.append("Service penetrations and other openings must be considered in acoustic design; the requirement is not automatically reduced.")
    if any(str(r.funktion).strip().casefold() in {"aula", "kantine", "auditorium", "gymnastiksal"} for r in (par.a, par.b)):
        noter.append("Large or specialized rooms may require separate acoustic design (BR18 Section 3.1).")

    def svar(db: int | None, regel: str, forklaring: str) -> Resultat:
        return Resultat(
            krav_db=db,
            regel=regel,
            forklaring=forklaring,
            status="bestemt" if db is not None else "manuel_vurdering",
            bemaerkning=" ".join(noter),
        )

    if Rumtype.UKENDT in typer:
        return svar(None, "UKENDT_RUMTYPE", "At least one room type is unknown; classify the room function first.")

    if retning == "vertikal" and par.doerforbindelse:
        return svar(None, "UKLAR_DOR_VERTIKALT", "A direct door connection across a vertical separation is not a standard case in Table 3.1.")

    # Tabel 3.1: det deklarerede valg om fleksibel rumadskillelse er afgørende.
    # Reglen om R'w >= 20 dB er ikke betinget af dørforbindelse.
    # Dørforbindelse skal derfor ikke blokere dette særtilfælde.
    if par.fleksibel_adskillelse:
        if retning == "horisontal" and typer == {Rumtype.AABENT}:
            noter.append("Section 3.1 requires separate acoustic design of open-plan teaching areas.")
            return svar(20, "T3.1_FLEKSIBEL", "Flexible partition within an open-plan teaching area.")
        return svar(None, "UKLAR_FLEKSIBEL", "The 20 dB rule only applies to flexible partitions in open-plan teaching areas.")
    if Rumtype.AABENT in typer:
        return svar(None, "AABENT_OMRAADE", "An open-plan teaching area without a specified flexible partition requires a separate assessment.")

    # Rum uden for denne undervisningsbygning: 60 dB er betinget af særlig støj.
    if Rumtype.EKSTERN in typer:
        anden = t2 if t1 == Rumtype.EKSTERN else t1
        if anden != Rumtype.UNDERVISNING:
            return svar(None, "EKSTERN_SPECIAL", "This combination with an external unit is not unambiguously covered by the standard rule.")
        if par.ekstern_saerlig_stoej is True:
            return svar(60, "T3.1_EKSTERN_STOEJ", "Teaching room adjacent to an external unit/institution with particularly disturbing noise.")
        return svar(None, "EKSTERN_VURDERING", "The 60 dB rule for external units requires particularly disturbing noise; determine the requirement through acoustic design.")

    # Hvis sløjd og musik mødes, kan særreglerne overlappe.
    if Rumtype.MUSIK in typer and Rumtype.SLOEJD in typer:
        if par.doerforbindelse:
            return svar(None, "MUSIK_SLOEJD_DOR", "Music and woodworking rooms with a direct door connection: special rules may overlap; professional assessment is required.")
        return svar(65, "T3.1_MUSIK", "Music room adjacent to woodworking room: the 65 dB music requirement is stricter than the 60 dB woodworking requirement.")

    # Musik: 65 dB uden dør, særskilte 55/50 dB-værdier med dør.
    if Rumtype.MUSIK in typer:
        if par.doerforbindelse:
            if Rumtype.FAELLES in typer:
                return svar(50, "T3.1_MUSIK_FAELLES_DOR", "Music room and common area with a direct door connection.")
            return svar(55, "T3.1_MUSIK_DOR", "Music room and teaching/music room with a direct door connection.")
        return svar(65, "T3.1_MUSIK", "Music room adjacent to another music room, teaching room, or common area.")

    # Sløjd: 60 dB uden dør; en udtrykkelig undtagelse på 44 dB mod fællesrum med dør.
    if Rumtype.SLOEJD in typer:
        if par.doerforbindelse:
            if Rumtype.FAELLES in typer:
                return svar(44, "T3.1_SLOEJD_FAELLES_DOR", "Woodworking room and common area with a direct door connection.")
            return svar(None, "SLOEJD_UNDERVISNING_DOR", "Woodworking room with a door to a teaching/woodworking room: Table 3.1 has no specific door rule for this pair; interpretation requires review.")
        return svar(60, "T3.1_SLOEJD", "Woodworking room adjacent to another teaching room or common area.")

    # Almindelige undervisningsrum og fællesrum.
    if typer == {Rumtype.FAELLES}:
        return svar(None, "FAELLES_FAELLES", "The table does not specify a general R'w requirement between two common areas.")

    if typer <= {Rumtype.UNDERVISNING, Rumtype.FAELLES} and Rumtype.UNDERVISNING in typer:
        if par.doerforbindelse:
            if Rumtype.FAELLES in typer:
                return svar(36, "T3.1_UND_FAELLES_DOR", "Teaching room and common area with a direct door connection.")
            return svar(44, "T3.1_UND_UND_DOR", "Teaching rooms with a direct door connection.")
        if retning == "vertikal":
            return svar(51, "T3.1_ALMINDELIG_VERTIKAL", "Teaching room above or below another teaching room or common area.")
        return svar(48, "T3.1_ALMINDELIG_HORISONTAL", "Teaching room adjacent to another teaching room or common area.")

    return svar(None, "IKKE_DAEKKET", "No unambiguous BR18 Table 3.1 rule applies to this room pair.")


def _valgfri_bool(v: str | None) -> bool | None:
    if v is None or str(v).strip() == "":
        return None
    lav = str(v).strip().casefold()
    if lav in {"1", "ja", "true", "yes"}:
        return True
    if lav in {"0", "nej", "false", "no"}:
        return False
    raise ValueError(f"Invalid Boolean value: {v!r} (use yes/no)")


def behandl_csv(input_fil: str, output_fil: str) -> None:
    """Indlæs CSV med rumpar (fx fra BIM) og skriv krav + regel + begrundelse."""
    with Path(input_fil).open("r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        # Accepterer både komma og semikolon (typisk dansk Excel).
        separator = ";" if sample.splitlines() and sample.splitlines()[0].count(";") > sample.splitlines()[0].count(",") else ","
        raekker = list(csv.DictReader(f, delimiter=separator))

    resultater = []
    for i, r in enumerate(raekker, start=2):
        try:
            par = Rumpar(
                a=Rum(r["rum_a"], r["type_a"]),
                b=Rum(r["rum_b"], r["type_b"]),
                retning=r.get("retning") or "horisontal",
                doerforbindelse=_valgfri_bool(r.get("doerforbindelse")) or False,
                fleksibel_adskillelse=_valgfri_bool(r.get("fleksibel_adskillelse")) or False,
                ekstern_saerlig_stoej=_valgfri_bool(r.get("ekstern_saerlig_stoej")),
                gennemfoeringer=_valgfri_bool(r.get("gennemfoeringer")) or False,
            )
            res = bestem_lydisolation(par)
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Fejl i CSV-linje {i}: {exc}") from exc
        resultater.append({
            **r,
            "krav_Rw_db": "" if res.krav_db is None else res.krav_db,
            "status": res.status,
            "regel": res.regel,
            "forklaring": res.forklaring,
            "bemaerkning": res.bemaerkning,
        })

    kolonner = list(dict.fromkeys(
        (list(raekker[0]) if raekker else ["rum_a", "type_a", "rum_b", "type_b"])
        + ["krav_Rw_db", "status", "regel", "forklaring", "bemaerkning"]
    ))
    with Path(output_fil).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=kolonner, delimiter=";")
        writer.writeheader()
        writer.writerows(resultater)


if __name__ == "__main__":
    # Eksempler: brug disse rumpar, eller kald behandl_csv(...)
    eksempler = [
        Rumpar(Rum("101", "klasselokale"), Rum("102", "klasselokale")),
        Rumpar(Rum("101", "klasselokale"), Rum("Gang", "gang"), doerforbindelse=True),
        Rumpar(Rum("Musik", "musik"), Rum("101", "klasselokale")),
        Rumpar(Rum("Sløjd", "sløjd"), Rum("Gang", "gang"), doerforbindelse=True),
        Rumpar(Rum("101", "klasselokale"), Rum("201", "klasselokale"), retning="vertikal"),
        Rumpar(Rum("Gang 1", "gang"), Rum("Gang 2", "gang")),
    ]
    for par in eksempler:
        res = bestem_lydisolation(par)
        krav = f"R'w ≥ {res.krav_db} dB" if res.krav_db is not None else "MANUAL ASSESSMENT"
        print(f"{par.a.navn} ↔ {par.b.navn}: {krav} ({res.regel})")
        if res.krav_db is None:
            print(f"  Explanation: {res.forklaring}")
