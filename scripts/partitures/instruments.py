"""Catàleg d'instruments: transposició, clau i tessitura.

Les tessitures estan expressades en altura ESCRITA (la que llig l'intèrpret).
Són valors ORIENTATIUS de manual, pensats per a avisar d'alguna cosa que pot ser
incòmoda; no substitueixen el criteri del professor o professora d'instrument.
"abast" = els extrems pràctics; "comoda" = la zona on sona bé sense patir.
Per a canviar-los, edita aquest fitxer (cada línia és un instrument).
Els noms de nota internes són els de music21 (C4 = do central).
"""
import re
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
    clef: str = "treble"  # clau habitual: treble, bass, alto o auto (la tria music21 segons les notes)

    def semitons(self) -> int:
        return interval.Interval(self.transposicio).semitones if self.transposicio != "P1" else 0


CATALEG: list[Instrument] = [
    Instrument("trompeta-sib", "Trompeta en Si bemoll", "Trumpet", "M-2", ("F#3", "C6"), ("G3", "G5"),
               ("trumpet", "trompeta", "cornet", "corneta", "trompeta en sib", "trompeta en si bemoll",
                "trompeta si bemoll", "trompeta sib", "trumpet in bb")),
    Instrument("trompeta-do", "Trompeta en Do", "Trumpet", "P1", ("F#3", "C6"), ("G3", "G5"),
               ("trumpet in c", "trompeta en do", "trompeta do")),
    Instrument("fliscorn-sib", "Fliscorn en Si bemoll", "Trumpet", "M-2", ("F#3", "B-5"), ("G3", "F5"),
               ("flugelhorn", "fliscorn", "fliscorno")),
    Instrument("trompa-fa", "Trompa en Fa", "Horn", "P-5", ("F#2", "C6"), ("C3", "F5"),
               ("horn", "trompa", "french horn", "corno", "horn in f", "trompa en fa")),
    Instrument("corn-angles", "Corn anglès en Fa", "EnglishHorn", "P-5", ("B3", "G6"), ("C4", "D6"),
               ("english horn", "corn angles", "corno inglese", "corno ingles", "cor angles", "cor anglais")),
    Instrument("trombo", "Trombó", "Trombone", "P1", ("E2", "F5"), ("F2", "B-4"),
               ("trombone", "trombo", "trombon", "tenor trombone"), "bass"),
    Instrument("trombo-baix", "Trombó baix", "BassTrombone", "P1", ("B-1", "D5"), ("C2", "A4"),
               ("bass trombone", "trombo baix", "trombon bajo"), "bass"),
    Instrument("bombardi", "Bombardí (eufoni) en Si bemoll, escrit en clau de Fa", "Euphonium", "P1",
               ("E2", "F5"), ("A2", "B-4"),
               ("euphonium", "bombardi", "bombardino", "eufoni", "eufonio", "baritone horn"), "bass"),
    Instrument("tuba", "Tuba", "Tuba", "P1", ("D1", "F4"), ("F1", "B-3"), ("tuba", "bombardon"), "bass"),
    Instrument("flauti", "Flautí", "Piccolo", "P8", ("D4", "C7"), ("G4", "A6"),
               ("piccolo", "flauti", "flautin", "ottavino")),
    Instrument("flauta", "Flauta", "Flute", "P1", ("C4", "C7"), ("D4", "G6"), ("flute", "flauta")),
    Instrument("oboe", "Oboè", "Oboe", "P1", ("B-3", "G6"), ("C4", "D6"), ("oboe", "oboè")),
    Instrument("clarinet-sib", "Clarinet en Si bemoll", "Clarinet", "M-2", ("E3", "C7"), ("E3", "G6"),
               ("clarinet", "clarinete", "clarinet en sib", "clarinet in bb")),
    Instrument("clarinet-la", "Clarinet en La", "Clarinet", "m-3", ("E3", "C7"), ("E3", "G6"),
               ("clarinet in a", "clarinet en la", "clarinete en la")),
    Instrument("clarinet-baix", "Clarinet baix en Si bemoll", "BassClarinet", "M-9", ("E3", "G6"), ("E3", "D6"),
               ("bass clarinet", "clarinet baix", "clarinete bajo", "clarinet bajo")),
    Instrument("clarinet-contrabaix", "Clarinet contrabaix en Si bemoll", "ContrabassClarinet", "M-16",
               ("E3", "C6"), ("E3", "G5"),
               ("contrabass clarinet", "clarinet contrabaix", "clarinete contrabajo")),
    Instrument("saxo-soprano", "Saxo soprano en Si bemoll", "SopranoSaxophone", "M-2", ("B-3", "F6"),
               ("B-3", "D6"), ("soprano sax", "saxo soprano", "saxofon soprano", "saxofo soprano",
                               "soprano saxophone")),
    Instrument("saxo-alt", "Saxo alt en Mi bemoll", "AltoSaxophone", "M-6", ("B-3", "F6"), ("B-3", "D6"),
               ("alto sax", "saxo alt", "saxofon alto", "saxofo alt", "saxo alto", "alto saxophone", "saxo",
                "sax", "saxofon", "saxofo", "saxophone")),
    Instrument("saxo-tenor", "Saxo tenor en Si bemoll", "TenorSaxophone", "M-9", ("B-3", "F6"), ("B-3", "D6"),
               ("tenor sax", "saxo tenor", "saxofon tenor", "saxofo tenor", "tenor saxophone")),
    Instrument("saxo-bari", "Saxo baríton en Mi bemoll", "BaritoneSaxophone", "M-13", ("B-3", "F6"),
               ("B-3", "D6"), ("baritone sax", "saxo baritono", "saxo bariton", "saxofon baritono",
                               "saxofo bariton", "baritone saxophone")),
    Instrument("fagot", "Fagot", "Bassoon", "P1", ("B-1", "E-5"), ("C2", "B-4"), ("bassoon", "fagot"), "bass"),
    Instrument("contrafagot", "Contrafagot", "Contrabassoon", "P-8", ("B-1", "G4"), ("C2", "C4"),
               ("contrabassoon", "contrafagot", "contrafagot"), "bass"),
    Instrument("guitarra", "Guitarra", "Guitar", "P-8",
               ("E3", "C6"), ("E3", "A5"), ("guitar", "guitarra", "guitare", "chitarra")),
    Instrument("violi", "Violí", "Violin", "P1", ("G3", "E7"), ("G3", "A6"), ("violin", "violi")),
    Instrument("viola", "Viola", "Viola", "P1", ("C3", "E6"), ("C3", "A5"), ("viola",), "alto"),
    Instrument("violoncel", "Violoncel", "Violoncello", "P1", ("C2", "A5"), ("C2", "E5"),
               ("cello", "violoncel", "violonchelo", "violoncello"), "bass"),
    Instrument("contrabaix", "Contrabaix", "Contrabass", "P-8", ("E2", "G4"), ("E2", "D4"),
               ("double bass", "contrabass", "contrabaix", "contrabajo"), "bass"),
    Instrument("piano", "Piano", "Piano", "P1", ("A0", "C8"), ("A0", "C8"), ("piano", "klavier"), "auto"),
]

_PER_CLAU = {i.clau: i for i in CATALEG}


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn").strip()


def _paraules(text: str) -> str:
    """Text normalitzat només amb lletres, xifres i espais simples (per a cercar paraules senceres)."""
    return " " + re.sub(r"[^a-z0-9#]+", " ", _norm(text)).strip() + " "


def _coincidencies(text: str) -> list[tuple[int, Instrument]]:
    t = _paraules(text)
    res = []
    for inst in CATALEG:
        llargada = 0
        for a in inst.alies + (inst.clau,):
            na = _paraules(a)
            if na in t:
                llargada = max(llargada, len(na))
        if llargada:
            res.append((llargada, inst))
    res.sort(key=lambda x: -x[0])
    return res


def obtenir(text: str) -> Instrument:
    """Accepta la clau exacta o un nom habitual: «trompeta», «Trompeta en Sib», «trombon», «saxo»..."""
    n = _norm(text).replace(" ", "-").replace("_", "-")
    if n in _PER_CLAU:
        return _PER_CLAU[n]
    trobades = _coincidencies(text)
    if trobades:
        return trobades[0][1]
    suggeriments = ", ".join(i.clau for i in CATALEG)
    raise ErrorUsuari(f"No conec l'instrument «{text}». Els que conec són: {suggeriments}.")


def detectar(nom_text: str, semitons_transposicio: int | None) -> Instrument | None:
    """Intenta endevinar l'instrument d'una part a partir del seu nom."""
    if not _norm(nom_text or ""):
        return None
    candidats = _coincidencies(nom_text)
    if not candidats:
        return None
    millor = candidats[0][0]
    millors = [i for longitud, i in candidats if longitud == millor]
    if semitons_transposicio is not None:
        for i in millors:
            if i.semitons() == semitons_transposicio:
                return i
    return millors[0]


def crear_objecte_music21(inst: Instrument):
    classe = getattr(m21i, inst.classe, m21i.Instrument)  # si music21 no la coneix, instrument genèric
    obj = classe()
    obj.instrumentName = inst.nom
    obj.partName = inst.nom
    obj.transposition = interval.Interval(inst.transposicio) if inst.transposicio != "P1" else None
    return obj


def rang_midi(rang: tuple) -> tuple[int, int]:
    return pitch.Pitch(rang[0]).midi, pitch.Pitch(rang[1]).midi
