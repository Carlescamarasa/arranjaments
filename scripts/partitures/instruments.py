"""Catàleg d'instruments: transposició i tessitura.

Les tessitures estan expressades en altura ESCRITA (la que llig l'intèrpret).
Són valors orientatius de manual, pensats per a avisar d'alguna cosa que pot ser
incòmoda; no substitueixen el criteri del professor o professora d'instrument.
"abast" = els extrems pràctics; "comoda" = la zona on sona bé sense patir.
Per a canviar-los, edita aquest fitxer (cada línia és un instrument).
"""
import unicodedata
from dataclasses import dataclass

from music21 import instrument as m21i
from music21 import interval, pitch

from .errors import ErrorUsuari


@dataclass(frozen=True)
class Instrument:
    clau: str            # nom curt per a l'ordre de línia (sense accents)
    nom: str             # nom per a mostrar
    classe: str          # classe de music21
    transposicio: str    # interval de l'escrit al real (p. ex. "M-2" = una segona major cap avall)
    abast: tuple         # (nota més greu, nota més aguda) escrites
    comoda: tuple
    alies: tuple = ()
    clau_clef: str = "auto"

    def semitons(self) -> int:
        return interval.Interval(self.transposicio).semitones if self.transposicio != "P1" else 0


CATALEG: list[Instrument] = [
    Instrument("trompeta-sib", "Trompeta en Si bemoll", "Trumpet", "M-2", ("F#3", "C6"), ("G3", "G5"),
               ("trumpet", "trompeta", "cornet", "corneta")),
    Instrument("trompeta-do", "Trompeta en Do", "Trumpet", "P1", ("F#3", "C6"), ("G3", "G5"),
               ("trumpet in c", "trompeta en do", "trompeta do")),
    Instrument("fliscorn-sib", "Fliscorn en Si bemoll", "Trumpet", "M-2", ("F#3", "B-5"), ("G3", "F5"),
               ("flugelhorn", "fliscorn", "fliscorno")),
    Instrument("trompa-fa", "Trompa en Fa", "Horn", "P-5", ("F#2", "C6"), ("C3", "F5"),
               ("horn", "trompa", "french horn", "corno")),
    Instrument("trombo", "Trombó", "Trombone", "P1", ("E2", "F5"), ("F2", "B-4"),
               ("trombone", "trombo", "trombon", "tenor trombone")),
    Instrument("trombo-baix", "Trombó baix", "BassTrombone", "P1", ("B-1", "D5"), ("C2", "A4"),
               ("bass trombone", "trombo baix", "trombon bajo")),
    Instrument("tuba", "Tuba", "Tuba", "P1", ("D1", "F4"), ("F1", "B-3"), ("tuba", "bombardino", "bombardon")),
    Instrument("flauta", "Flauta", "Flute", "P1", ("C4", "C7"), ("D4", "G6"), ("flute", "flauta")),
    Instrument("oboe", "Oboè", "Oboe", "P1", ("B-3", "G6"), ("C4", "D6"), ("oboe", "oboè")),
    Instrument("clarinet-sib", "Clarinet en Si bemoll", "Clarinet", "M-2", ("E3", "C7"), ("E3", "G6"),
               ("clarinet", "clarinete")),
    Instrument("clarinet-la", "Clarinet en La", "Clarinet", "m-3", ("E3", "C7"), ("E3", "G6"),
               ("clarinet in a", "clarinet en la")),
    Instrument("saxo-soprano", "Saxo soprano en Si bemoll", "SopranoSaxophone", "M-2", ("B-3", "F6"),
               ("B-3", "D6"), ("soprano sax", "saxo soprano", "saxofon soprano")),
    Instrument("saxo-alt", "Saxo alt en Mi bemoll", "AltoSaxophone", "M-6", ("B-3", "F6"), ("B-3", "D6"),
               ("alto sax", "saxo alt", "saxofon alto")),
    Instrument("saxo-tenor", "Saxo tenor en Si bemoll", "TenorSaxophone", "M-9", ("B-3", "F6"), ("B-3", "D6"),
               ("tenor sax", "saxo tenor", "saxofon tenor")),
    Instrument("saxo-bari", "Saxo baríton en Mi bemoll", "BaritoneSaxophone", "M-13", ("B-3", "F6"),
               ("B-3", "D6"), ("baritone sax", "saxo baríton", "saxofon baritono")),
    Instrument("fagot", "Fagot", "Bassoon", "P1", ("B-1", "E-5"), ("C2", "B-4"), ("bassoon", "fagot", "fagot")),
    Instrument("violi", "Violí", "Violin", "P1", ("G3", "E7"), ("G3", "A6"), ("violin", "violí", "violin")),
    Instrument("viola", "Viola", "Viola", "P1", ("C3", "E6"), ("C3", "A5"), ("viola",)),
    Instrument("violoncel", "Violoncel", "Violoncello", "P1", ("C2", "A5"), ("C2", "E5"),
               ("cello", "violoncel", "violonchelo")),
    Instrument("contrabaix", "Contrabaix", "Contrabass", "P-8", ("E2", "G4"), ("E2", "D4"),
               ("double bass", "contrabass", "contrabaix", "contrabajo")),
    Instrument("piano", "Piano", "Piano", "P1", ("A0", "C8"), ("A0", "C8"), ("piano", "klavier")),
]

_PER_CLAU = {i.clau: i for i in CATALEG}


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn").strip()


def obtenir(clau: str) -> Instrument:
    n = _norm(clau).replace(" ", "-").replace("_", "-")
    if n in _PER_CLAU:
        return _PER_CLAU[n]
    # tolerància: "trompeta" a soles → si només hi ha una opció que comença així
    opcions = [i for i in CATALEG if i.clau.startswith(n)]
    if len(opcions) == 1:
        return opcions[0]
    suggeriments = ", ".join(i.clau for i in CATALEG)
    raise ErrorUsuari(
        f"No conec l'instrument «{clau}». Els que conec són: {suggeriments}."
    )


def detectar(nom_text: str, semitons_transposicio: int | None) -> Instrument | None:
    """Intenta endevinar l'instrument d'una part a partir del seu nom."""
    t = _norm(nom_text or "")
    if not t:
        return None
    candidats = []
    for inst in CATALEG:
        llargada = max((len(_norm(a)) for a in inst.alies if _norm(a) in t), default=0)
        if llargada:
            candidats.append((llargada, inst))
    if not candidats:
        return None
    candidats.sort(key=lambda x: -x[0])
    millor = candidats[0][0]
    millors = [i for l, i in candidats if l == millor]
    if semitons_transposicio is not None:
        for i in millors:
            if i.semitons() == semitons_transposicio:
                return i
    return millors[0]


def crear_objecte_music21(inst: Instrument):
    classe = getattr(m21i, inst.classe)
    obj = classe()
    obj.instrumentName = inst.nom
    obj.partName = inst.nom
    obj.transposition = interval.Interval(inst.transposicio) if inst.transposicio != "P1" else None
    return obj


def rang_midi(rang: tuple) -> tuple[int, int]:
    return pitch.Pitch(rang[0]).midi, pitch.Pitch(rang[1]).midi
