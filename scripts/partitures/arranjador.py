"""Arranjador determinista: crea parts noves (melodia, contracant, acompanyament, baix, percussió) a partir d'una melodia.

El resultat és un ESBORRANY que el professorat revisa amb MuseScore. Tot és per regles simples i sempre dona el mateix
resultat per a la mateixa entrada (cap atzar):

1. Anàlisi: s'extrau la melodia (veu superior d'una part) i l'harmonia (símbols d'acord si n'hi ha; si no, s'infereix de
   les altres veus; si només hi ha melodia, s'harmonitza amb I, ii, IV, V(7) i vi i cadència V-I al final).
2. Cada rol és una funció: `melodia`, `contracant`, `acompanyament`, `baix`, `percussio`.
3. Es construeix en so real (concert) i després cada part s'escriu a l'altura que llig l'intèrpret.
4. Comprovacions automàtiques: quintes i octaves paral·leles del contracant, tessitures, compassos buits i nivell.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field

from music21 import (bar, chord, clef, expressions, harmony, instrument as m21i, key, layout, metadata, meter, note,
                     percussion, pitch, roman, stream, tempo, tie)
from music21.common.numberTools import opFrac

from . import gravat
from . import instruments as inst
from . import cues, musica
from . import parts as _parts
from .errors import ErrorUsuari

ESTILS = ("ragtime", "swing", "pop", "rock", "marxa", "vals", "classic")
ROLS = ("melodia", "contracant", "acompanyament", "baix", "percussio")
_ALIES_ROL = {
    "melodia": "melodia", "melodía": "melodia", "tema": "melodia",
    "contracant": "contracant", "contramelodia": "contracant", "contracanto": "contracant", "segona veu": "contracant",
    "acompanyament": "acompanyament", "acompanament": "acompanyament", "acompanamiento": "acompanyament",
    "acomp": "acompanyament", "acords": "acompanyament",
    "baix": "baix", "baixos": "baix", "bajo": "baix", "bass": "baix",
    "percussio": "percussio", "percusion": "percussio", "ritme": "percussio",
}
_EPS = 1e-6


# --------------------------------------------------------------------------- dades bàsiques

@dataclass
class Ev:
    """Un esdeveniment en so real: inici i durada (en negres) i les altures (buit = silenci)."""
    ini: float
    dur: float
    alt: list = field(default_factory=list)   # pitch.Pitch

    @property
    def fi(self):
        return opFrac(self.ini + self.dur)


@dataclass
class Acord:
    arrel: pitch.Pitch
    pcs: tuple            # classes d'altura: arrel, tercera, quinta (i sèptima)
    figura: str           # figura de music21 (F, C7, Dm, B-...)
    origen: str = "partitura"   # partitura, inferit, harmonitzat, proposat
    noms: dict = field(default_factory=dict)   # classe d'altura -> nom de la nota dins de l'acord (Re#, no Mib)

    @property
    def te_septima(self):
        return len(self.pcs) >= 4

    def nom(self) -> str:
        """Nom en solfeig: Fa, Do7, Sib, Rem..."""
        m = re.match(r"^([A-G])([-#b]*)(.*)$", self.figura)
        if not m:
            return self.figura
        alt = m.group(2).replace("-", "b")
        return musica._SOLFEIG[m.group(1)] + alt + m.group(3)

    def lletra(self) -> str:
        return self.figura.replace("-", "b")


def _acord_de_simbol(cs: harmony.ChordSymbol, origen="partitura") -> Acord:
    r = cs.root()
    ints = sorted({(p.pitchClass - r.pitchClass) % 12 for p in cs.pitches})
    return Acord(pitch.Pitch(r.name), tuple((r.pitchClass + i) % 12 for i in ints), cs.figure, origen,
                 {p.pitchClass: p.name for p in cs.pitches})


_SUFIX = {"major": "", "minor": "m", "diminished": "dim", "augmented": "+"}


def _acord_de_roman(fig: str, k: key.Key, origen="harmonitzat") -> Acord:
    rn = roman.RomanNumeral(fig, k)
    r = rn.root()
    if rn.isDominantSeventh():
        suf = "7"
    elif rn.seventh is not None:
        suf = "7" if rn.quality == "major" else "m7"
    else:
        suf = _SUFIX.get(rn.quality, "")
    ints = sorted({(p.pitchClass - r.pitchClass) % 12 for p in rn.pitches})
    return Acord(pitch.Pitch(r.name), tuple((r.pitchClass + i) % 12 for i in ints), r.name + suf, origen,
                 {p.pitchClass: p.name for p in rn.pitches})


@dataclass
class Compas:
    num: int
    ini: float
    dur: float
    ts: meter.TimeSignature
    anacrusi: bool = False
    canvi_ts: bool = False
    barra_esq: object = None
    barra_dre: object = None

    @property
    def fi(self):
        return opFrac(self.ini + self.dur)

    @property
    def pols(self) -> float:
        return float(self.ts.beatDuration.quarterLength)


@dataclass
class Segment:
    ini: float
    fi: float
    compas: Compas
    acord: Acord | None


@dataclass
class Rol:
    rol: str
    instr: inst.Instrument


# --------------------------------------------------------------------------- arguments

def parse_rols(text: str) -> list[Rol]:
    if not text or not text.strip():
        raise ErrorUsuari("Digues quin rol fa cada instrument, per exemple: "
                          "--rols \"melodia=trompeta-sib,contracant=flauta,acompanyament=xilofon,percussio=bateria\".")
    res = []
    avisos = []
    for tros in re.split(r"[,;]\s*", text.strip()):
        if not tros.strip():
            continue
        if "=" not in tros:
            raise ErrorUsuari(f"No entenc «{tros}». El format és rol=instrument, per exemple melodia=trompeta-sib. "
                              f"Rols: {', '.join(ROLS)}.")
        r, i = (x.strip() for x in tros.split("=", 1))
        rol = _ALIES_ROL.get(inst._norm(r).replace("-", " "))
        if rol is None:
            raise ErrorUsuari(f"No conec el rol «{r}». Rols possibles: {', '.join(ROLS)}.")
        ins = inst.obtenir(i)
        grup = inst.grup(i)
        if grup:
            avisos.append(f"«{i}» és un grup d'instruments ({', '.join(x.nom for x in grup)}): he triat {ins.nom}. "
                          f"Si en vols un altre, escriu el seu nom ({', '.join(x.clau for x in grup)}).")
        if rol == "percussio" and not ins.percussio:
            raise ErrorUsuari(f"{ins.nom} té altura: no pot fer el rol de percussió. Per a percussió: bateria, caixa o percussio.")
        if rol != "percussio" and ins.percussio:
            raise ErrorUsuari(f"{ins.nom} és percussió sense altura: només pot fer el rol «percussio».")
        res.append(Rol(rol, ins))
    if not any(r.rol == "melodia" for r in res):
        raise ErrorUsuari("Cal almenys un instrument amb el rol «melodia».")
    parse_rols.avisos = avisos
    return res


parse_rols.avisos = []


_SOLF_PC = {"do": "C", "re": "D", "mi": "E", "fa": "F", "sol": "G", "la": "A", "si": "B"}


def parse_tonalitat(text: str) -> key.Key:
    t = inst._norm(text).replace("bemoll", "b").replace("sostingut", "#").replace("sostenit", "#").replace("menor", "m")
    t = t.replace("major", "").replace("mayor", "").strip()
    m = re.match(r"^(do|re|mi|fa|sol|la|si|[a-g])\s*(#|b)?\s*(m)?$", t)
    if not m:
        raise ErrorUsuari(f"No entenc la tonalitat «{text}». Exemples: «Sol major», «Fa», «Re menor», «Sib major».")
    lletra = _SOLF_PC.get(m.group(1), m.group(1).upper())
    alt = {"#": "#", "b": "-"}.get(m.group(2) or "", "")
    return key.Key(lletra + alt, "minor" if m.group(3) else "major")


def parse_compassos(text: str | None) -> tuple[int, int] | None:
    if not text:
        return None
    m = re.match(r"^\s*(\d+)\s*[-–a]\s*(\d+)\s*$", text)
    if not m:
        raise ErrorUsuari(f"No entenc «{text}». Escriu els compassos així: 1-16.")
    a, b = int(m.group(1)), int(m.group(2))
    if a < 0 or b < a:
        raise ErrorUsuari("El primer compàs ha de ser menor que l'últim (per exemple 1-16).")
    return a, b


# --------------------------------------------------------------------------- anàlisi de l'entrada

def _parts_amb_altura(score: stream.Score) -> list[int]:
    return [k for k, p in enumerate(score.parts) if musica.notes_reals(p)]


def _triar_melodia(score: stream.Score, num: int | None) -> int:
    """Índex del pentagrama d'on surt la melodia: el de dalt de la part triada, o el de la part més aguda."""
    us = musica.unitats(score)
    if num is not None:
        if not 1 <= num <= len(us):
            raise ErrorUsuari(f"La part {num} no existeix: la partitura en té {len(us)}.")
        return us[num - 1][0]
    millor, alt = None, None
    for u in us:
        mids = sorted(p.midi for p in musica.altures(musica.part_sonora(score.parts[u[0]])))
        if not mids:
            continue
        mediana = mids[len(mids) // 2]
        if alt is None or mediana > alt:
            millor, alt = u[0], mediana
    if millor is None:
        raise ErrorUsuari("La partitura no té cap nota amb altura: no hi ha melodia per a arranjar.")
    return millor


def _compassos(part: stream.Part) -> list[Compas]:
    ms = list(part.getElementsByClass(stream.Measure))
    if not ms:
        part = part.makeMeasures()
        ms = list(part.getElementsByClass(stream.Measure))
    res = []
    ts = None
    for i, m in enumerate(ms):
        canvi = m.timeSignature is not None
        if canvi:
            ts = m.timeSignature
        if ts is None:
            ts = meter.TimeSignature("4/4")
            canvi = True
        ple = opFrac(ts.barDuration.quarterLength)
        dur = opFrac(m.duration.quarterLength) or ple
        anac = (i == 0 and (m.paddingLeft or 0) > 0) or (i == 0 and dur < ple - _EPS)
        if not anac and dur < ple - _EPS and i < len(ms) - 1:
            dur = ple
        res.append(Compas(m.number, opFrac(m.offset), dur, ts, anac, canvi, m.leftBarline, m.rightBarline))
    return res


def _linia_superior(staff: stream.Part) -> list[Ev]:
    """Veu superior d'un pentagrama (si hi ha acords o veus, la nota més aguda de cada moment)."""
    c = copy.deepcopy(musica.part_sonora(staff))
    for h in list(c.recurse().getElementsByClass((harmony.Harmony, note.Unpitched))):
        h.activeSite.remove(h)
    atacs = {(opFrac(n.offset), p.midi) for n in c.flatten().notes if n.quarterLength > 0
             and (n.tie is None or n.tie.type == "start") for p in n.pitches}
    evs: list[Ev] = []
    for n in c.chordify().flatten().notes:
        if n.quarterLength <= 0:
            continue
        p = max(n.pitches, key=lambda x: x.ps)
        ini = opFrac(n.offset)
        ant = evs[-1] if evs else None
        if (ant and ant.alt and abs(ant.fi - ini) < _EPS and ant.alt[0].midi == p.midi
                and (ini, p.midi) not in atacs):
            ant.dur = opFrac(ant.dur + n.quarterLength)
            continue
        evs.append(Ev(ini, opFrac(n.quarterLength), [pitch.Pitch(p.nameWithOctave)]))
    return evs


def _simbols(score: stream.Score) -> list[tuple[float, harmony.ChordSymbol]]:
    res = {}
    for p in score.parts:
        for cs in p.flatten().getElementsByClass(harmony.ChordSymbol):
            if isinstance(cs, harmony.NoChord) or not cs.pitches:
                continue
            res.setdefault(opFrac(cs.offset), cs)
    return sorted(res.items(), key=lambda x: x[0])


def _segments(compassos: list[Compas], talls: list[float]) -> list[Segment]:
    segs = []
    for c in compassos:
        if c.anacrusi:
            punts = [c.ini]
        else:
            r = c.ts.ratioString
            mig = c.dur / 2 if r in ("4/4", "2/2", "12/8", "4/2") else None
            punts = [c.ini] + ([opFrac(c.ini + mig)] if mig else [])
        punts += [t for t in talls if c.ini + _EPS < t < c.fi - _EPS]
        punts = sorted(set(opFrac(x) for x in punts))
        for a, b in zip(punts, punts[1:] + [c.fi]):
            segs.append(Segment(a, b, c, None))
    return segs


def _notes_entre(evs: list[Ev], a: float, b: float) -> list[tuple[Ev, float, float]]:
    """Notes de la melodia que sonen entre a i b, amb el tros que hi cau."""
    res = []
    for e in evs:
        if e.alt and e.ini < b - _EPS and e.fi > a + _EPS:
            res.append((e, max(e.ini, a), min(e.fi, b)))
    return res


def _pes(e: Ev, ini_tros: float, fi_tros: float, seg: Segment) -> float:
    d = fi_tros - ini_tros
    rel = (ini_tros - seg.compas.ini) / seg.compas.pols
    fort = abs(ini_tros - seg.ini) < _EPS or abs(rel - round(rel)) < _EPS and round(rel) % 2 == 0
    return d * (1.5 if fort else 1.0)


def encaix(acord: Acord, evs: list[Ev], seg: Segment) -> float | None:
    """Proporció (ponderada) de la melodia del segment que són notes de l'acord. None si no hi ha melodia."""
    tot = dins = 0.0
    for e, a, b in _notes_entre(evs, seg.ini, seg.fi):
        w = _pes(e, a, b, seg)
        tot += w
        if e.alt[0].pitchClass in acord.pcs:
            dins += w
    return dins / tot if tot else None


def _candidats_diatonics(k: key.Key, origen: str) -> list[Acord]:
    figs = ["I", "IV", "V", "V7", "ii", "vi"] if k.mode == "major" else ["i", "iv", "V", "V7", "VI", "III"]
    return [_acord_de_roman(f, k, origen) for f in figs]


def _grau(a: Acord, k: key.Key) -> int | None:
    sc = [p.pitchClass for p in k.getScale().getPitches()[:7]]
    return sc.index(a.arrel.pitchClass) + 1 if a.arrel.pitchClass in sc else None


_TRANSICIONS = {(5, 1): 1.0, (4, 5): 0.6, (2, 5): 0.8, (1, 4): 0.4, (1, 5): 0.3, (6, 2): 0.5, (6, 4): 0.5,
                (1, 6): 0.3, (5, 6): 0.3, (5, 4): -0.8, (2, 1): -0.5, (4, 1): 0.3, (3, 6): 0.4}


def harmonitzar(evs: list[Ev], segs: list[Segment], k: key.Key, estil: str, curs: str | None = None,
                mode: str = "auto") -> str | None:
    """Harmonització per regles amb programació dinàmica (sempre el mateix resultat). La lògica és a
    `harmonitzacio.py` (ritme harmònic i vocabulari per nivell, mode modal); torna una frase per a l'informe."""
    from . import harmonitzacio
    return harmonitzacio.harmonitza(evs, segs, k, estil, curs, mode)


def _nom_arrel(pc: int, k: key.Key) -> str:
    for p in k.getScale().getPitches()[:7]:
        if p.pitchClass == pc:
            return p.name
    p = pitch.Pitch(pc)
    if k.sharps < 0 and p.accidental is not None and p.accidental.name == "sharp":
        p = p.getEnharmonic()
    return p.name


_TIPUS = {"": (0, 4, 7), "m": (0, 3, 7), "7": (0, 4, 7, 10), "dim": (0, 3, 6)}


def inferir_de_veus(score: stream.Score, segs: list[Segment], k: key.Key) -> None:
    """Tria, per a cada segment, l'acord que millor explica totes les notes (amb preferència pel baix com a arrel)."""
    sons = []
    for p in score.parts:
        for n in musica.notes_reals(musica.part_sonora(p)):
            ini = opFrac(n.getOffsetInHierarchy(p)) if n.activeSite is not None else 0
            sons.append((ini, opFrac(ini + n.quarterLength), [x.midi for x in n.pitches]))
    escala = {p.pitchClass for p in k.getScale().getPitches()[:7]}
    anterior = None
    for s in segs:
        if s.compas.anacrusi:
            continue
        pes = [0.0] * 12
        baix = None
        for a, b, mids in sons:
            if a < s.fi - _EPS and b > s.ini + _EPS:
                d = min(b, s.fi) - max(a, s.ini)
                for m in mids:
                    pes[m % 12] += d * (1.5 if abs(a - s.ini) < _EPS else 1.0)
                if abs(a - s.ini) < _EPS or a <= s.ini:
                    lo = min(mids)
                    baix = lo if baix is None else min(baix, lo)
        if sum(pes) == 0:
            s.acord = anterior
            continue
        millor = None
        for arrel in range(12):
            for suf, ints in _TIPUS.items():
                pcs = tuple((arrel + i) % 12 for i in ints)
                v = sum(pes[x] for x in pcs) - 0.7 * sum(pes[x] for x in range(12) if x not in pcs)
                if not set(pcs) <= escala:
                    v -= 0.15 * sum(pes)
                if suf == "7":
                    v -= 0.05 * sum(pes)
                if baix is not None and baix % 12 == arrel:
                    v += 0.3 * sum(pes)
                cand = (v, -arrel, suf)
                if millor is None or cand > millor[0]:
                    millor = (cand, arrel, suf, pcs)
        _, arrel, suf, pcs = millor
        fig = _nom_arrel(arrel, k) + suf
        s.acord = Acord(pitch.Pitch(_nom_arrel(arrel, k)), pcs, fig, "inferit",
                        {p.pitchClass: p.name for p in harmony.ChordSymbol(fig).pitches})
        anterior = s.acord


def acords_de_simbols(simbols, segs: list[Segment], evs: list[Ev], k: key.Key, avisos: list[str]) -> None:
    """Els acords escrits es respecten. En compassos sense cap símbol (l'acord ve d'abans) es revisa si encaixa."""
    for s in segs:
        actiu = None
        for t, cs in simbols:
            if t <= s.ini + _EPS:
                actiu = cs
            else:
                break
        s.acord = _acord_de_simbol(actiu) if actiu is not None else None
    explicits = {opFrac(t) for t, _ in simbols}
    per_compas: dict[int, list[Segment]] = {}
    for s in segs:
        per_compas.setdefault(id(s.compas), []).append(s)
    firmes = {}
    vistos = []
    for s in segs:
        c = s.compas
        if id(c) in [id(x) for x in vistos]:
            continue
        vistos.append(c)
        meus = per_compas[id(c)]
        firma = tuple((opFrac(e.ini - c.ini), e.dur, e.alt[0].midi) for e, _, _ in _notes_entre(evs, c.ini, c.fi))
        te_simbol = any(c.ini - _EPS <= t < c.fi - _EPS for t in explicits)
        if not te_simbol and meus[0].acord is not None and firma and firma in firmes:
            model = firmes[firma]
            if [x.acord.figura if x.acord else None for x in model] != [x.acord.figura if x.acord else None for x in meus] \
                    and len(model) == len(meus):
                for x, y in zip(meus, model):
                    x.acord = copy.copy(y.acord)
                    if x.acord:
                        x.acord.origen = "proposat"
                avisos.append(f"Compàs {c.num}: no hi havia acord escrit i la melodia és igual que en el compàs "
                              f"{model[0].compas.num}: hi he posat el mateix ({' '.join(x.acord.nom() for x in meus if x.acord)}).")
        elif not te_simbol and meus[0].acord is not None:
            e = _encaix_compas(meus, evs)
            if e is not None and e < 0.34:
                anterior = None
                for y in reversed(segs[:segs.index(meus[0])]):
                    if y.acord is not None:
                        anterior = y.acord.figura
                        break
                vell = " ".join(dict.fromkeys(x.acord.nom() for x in meus))
                for x in meus:
                    cands = _candidats_diatonics(k, "proposat")
                    millor = max(cands, key=lambda q: ((encaix(q, evs, x) or 0), q.figura == anterior,
                                                       -cands.index(q)))
                    if (encaix(millor, evs, x) or 0) >= 0.5:
                        x.acord = millor
                        anterior = millor.figura
                nous = " ".join(dict.fromkeys(x.acord.nom() for x in meus))
                if nous != vell:
                    avisos.append(f"Compàs {c.num}: l'acord {vell} venia d'abans i no encaixa amb la melodia: "
                                  f"proposo {nous}.")
        if firma and firma not in firmes and meus[0].acord is not None:
            firmes[firma] = meus
    for c in vistos:
        meus = per_compas[id(c)]
        if not any(c.ini - _EPS <= t < c.fi - _EPS for t in explicits):
            continue
        e = _encaix_compas(meus, evs)
        if e is not None and e < 0.25:
            noms = " ".join(dict.fromkeys(x.acord.nom() for x in meus if x.acord))
            avisos.append(f"Compàs {c.num}: l'acord escrit ({noms}) quasi no té notes de la melodia. Mira si és correcte.")


def _encaix_compas(meus: list[Segment], evs: list[Ev]) -> float | None:
    """Encaix de tot un compàs amb els seus acords (les notes de pas curtes pesen poc)."""
    tot = dins = 0.0
    for x in meus:
        if x.acord is None:
            continue
        for e, a, b in _notes_entre(evs, x.ini, x.fi):
            w = _pes(e, a, b, x)
            tot += w
            if e.alt[0].pitchClass in x.acord.pcs:
                dins += w
    return dins / tot if tot else None


def analitzar_tonalitat(evs: list[Ev], segs: list[Segment], score: stream.Score, fonts_acords: bool) -> key.Key:
    st = stream.Stream()
    for e in evs:
        if e.alt:
            st.insert(e.ini, note.Note(e.alt[0], quarterLength=e.dur))
    if fonts_acords:
        for s in segs:
            if s.acord:
                st.insert(s.ini, chord.Chord([pitch.Pitch(pc + 60) for pc in s.acord.pcs], quarterLength=s.fi - s.ini))
    else:
        for p in score.parts:
            for n in musica.notes_reals(musica.part_sonora(p)):
                st.insert(n.getOffsetInHierarchy(p), copy.deepcopy(n))
    k = st.analyze("key")
    if fonts_acords:
        # el primer acord d'una cançó sol ser el de la tònica: si és una interpretació quasi igual de bona, la triem
        primer = next((s.acord for s in segs if s.acord), None)
        if primer is not None and primer.arrel.pitchClass != k.tonic.pitchClass:
            mode = "minor" if (primer.pcs[1] - primer.pcs[0]) % 12 == 3 else "major"
            for alt in k.alternateInterpretations[:6]:
                if (alt.tonic.pitchClass == primer.arrel.pitchClass and alt.mode == mode
                        and alt.correlationCoefficient >= k.correlationCoefficient - 0.15):
                    return alt
        return k
    # la nota final de la melodia sol ser la tònica: desempat entre relatiu major i menor
    finals = [e for e in evs if e.alt]
    if finals:
        ult = finals[-1].alt[0].pitchClass
        rel = k.relative
        if ult == rel.tonic.pitchClass and ult != k.tonic.pitchClass:
            k = rel
    return k


# --------------------------------------------------------------------------- rangs i nivell

def _perfil(instr: inst.Instrument, curs: str | None):
    if not curs:
        return None
    from . import nivells
    return nivells.perfil(instr.clau, curs)


def rang_comode(instr: inst.Instrument, curs: str | None) -> tuple[tuple[int, int], str]:
    """Zona còmoda ESCRITA en MIDI i d'on ve (perfil del nivell o catàleg)."""
    p = _perfil(instr, curs)
    if p and p.get("tessitura"):
        from . import nivells
        return nivells.rang_midi(p["tessitura"]), f"perfil de {curs}"
    lo, hi = inst.rang_midi(instr.comoda)
    if es_elemental(curs):
        return (lo, lo + -(-(hi - lo) * 7 // 10)), "catàleg, limitada per a elemental"
    return (lo, hi), "catàleg"


def es_elemental(curs: str | None) -> bool:
    """Cursos d'iniciació o d'elemental: sense perfil, la zona còmoda es limita als dos terços de baix."""
    t = inst._norm(curs or "")
    return any(x in t for x in ("elemental", "inicia", "primaria", "basic"))


def _figures_permeses(instr: inst.Instrument, curs: str | None) -> set[str] | None:
    p = _perfil(instr, curs)
    if p and p.get("figures"):
        from . import nivells
        return {nivells.normalitza_figura(f) for f in p["figures"]}
    return None


def _permet_corxeres(instr, curs) -> bool:
    f = _figures_permeses(instr, curs)
    return f is None or "corxera" in f or "semicorxera" in f


def _rang_concert(instr, curs):
    (lo, hi), _ = rang_comode(instr, curs)
    t = instr.semitons()
    return lo + t, hi + t


# --------------------------------------------------------------------------- rols

def rol_melodia(evs: list[Ev], instr: inst.Instrument, curs: str | None) -> tuple[list[Ev], int]:
    """La melodia, a l'octava on més notes cauen dins de la zona còmoda de l'instrument."""
    lo, hi = _rang_concert(instr, curs)
    ab_lo, ab_hi = (x + instr.semitons() for x in inst.rang_midi(instr.abast))
    mids = [e.alt[0].midi for e in evs if e.alt]
    if not mids:
        return evs, 0
    centre = (lo + hi) / 2
    mitja = sum(mids) / len(mids)

    def nota(sh):
        dins = sum(lo <= m + sh <= hi for m in mids)
        fora = sum(not ab_lo <= m + sh <= ab_hi for m in mids)
        return (-fora, dins, -abs(mitja + sh - centre), sh == 0)   # mai fora d'abast per a guanyar zona còmoda

    sh = max((-24, -12, 0, 12, 24), key=nota)
    return [Ev(e.ini, e.dur, [_octava(x, sh // 12) for x in e.alt]) for e in evs], sh


def _octava(p: pitch.Pitch, n: int) -> pitch.Pitch:
    """Canvi d'octava que conserva el nom de la nota (Sol# continua sent Sol#)."""
    q = copy.deepcopy(p)
    q.octave = q.implicitOctave + n
    return q


def simplificar_ritme(evs: list[Ev], compassos: list[Compas], permeses: set[str]) -> tuple[list[Ev], int]:
    """Cada nota més curta que la figura mínima del nivell s'ajunta: queda la nota que sona a cada pols mínim."""
    ordre = [("semicorxera", 0.25), ("corxera", 0.5), ("negra", 1.0), ("blanca", 2.0)]
    q = next((d for nom, d in ordre if nom in permeses), 1.0)
    canvis = 0
    res: list[Ev] = []
    for c in compassos:
        t = c.ini
        while t < c.fi - _EPS:
            fi = min(opFrac(t + q), c.fi)
            sona = next((e for e in evs if e.ini <= t + _EPS and e.fi > t + _EPS), None)
            dins = [e for e in evs if t - _EPS <= e.ini < fi - _EPS]
            if sona is None and dins:
                sona = dins[0]
            if len([e for e in dins if e.alt]) > 1 or (dins and abs(dins[0].ini - t) > _EPS):
                canvis += 1
            alt = list(sona.alt) if sona else []
            ant = res[-1] if res else None
            continua = ant is not None and sona is not None and ant.alt == alt and sona.ini < t - _EPS
            if continua or (ant is not None and not alt and not ant.alt):
                ant.dur = opFrac(ant.dur + (fi - t))
            else:
                res.append(Ev(t, opFrac(fi - t), alt))
            t = fi
    return res, canvis


def _sonant(evs: list[Ev], t: float):
    for e in evs:
        if e.ini <= t + _EPS and e.fi > t + _EPS:
            return e.alt[0].midi if e.alt else None
    return None


def _escala_pcs(k: key.Key) -> set[int]:
    return {p.pitchClass for p in k.getScale().getPitches()[:7]}


def rol_contracant(evs_mel: list[Ev], segs: list[Segment], instr: inst.Instrument, curs: str | None,
                   k: key.Key, baix: list[Ev] | None) -> list[Ev]:
    """Notes llargues de l'acord, per graus conjunts si es pot, a distància de 3a o 6a de la melodia,
    sense quintes ni octaves paral·leles. On la melodia s'atura (nota llarga o silenci), un petit farciment."""
    lo, hi = _rang_concert(instr, curs)
    mids = [e.alt[0].midi for e in evs_mel if e.alt]
    med_mel = sorted(mids)[len(mids) // 2] if mids else (lo + hi) // 2
    damunt = (lo + hi) / 2 >= med_mel
    centre = lo + 0.4 * (hi - lo)       # la zona mitjana-baixa de l'instrument és la més segura
    sostre = lo + 0.7 * (hi - lo)       # per damunt, cada semitò costa més
    actius = [i for i, s in enumerate(segs) if s.acord is not None]
    if not actius:
        return []

    def mel(s):
        m = _sonant(evs_mel, s.ini)
        if m is None:
            dins = _notes_entre(evs_mel, s.ini, s.fi)
            m = dins[0][0].alt[0].midi if dins else None
        return m

    def bx(s):
        if baix:
            return _sonant(baix, s.ini)
        return s.acord.arrel.pitchClass if s.acord else None

    cands = []
    for i in actius:
        s = segs[i]
        cs = [p for p in range(lo, hi + 1) if p % 12 in s.acord.pcs]
        cands.append(cs or [lo])

    def local(i, p):
        s = segs[i]
        m = mel(s)
        c = 0.12 * abs(p - centre) + 0.4 * max(0, p - sostre)
        if m is not None:
            iv = p - m
            if (damunt and iv <= 0) or (not damunt and iv >= 0):
                c += 4
            a = abs(iv)
            ic = a % 12
            if a == 0:
                c += 8
            elif ic in (3, 4, 8, 9):
                c -= 2
            elif ic == 0:
                c += 3
            elif ic in (5, 7):
                c += 1
            else:
                c += 5
            if a > 16:
                c += (a - 16) * 0.5
        for e, x, _ in _notes_entre(evs_mel, s.ini, s.fi):
            if x > s.ini + _EPS and e.dur >= 1 and (abs(p - e.alt[0].midi) % 12) in (1, 2, 6, 10, 11):
                c += 1.5
        pc = p % 12
        a = s.acord
        if len(a.pcs) > 1 and pc == a.pcs[1]:
            c -= 0.5
        if a.te_septima and pc == a.pcs[-1]:
            c -= 0.5
        return c

    def trans(i0, p0, i1, p1):
        s0, s1 = segs[i0], segs[i1]
        d = abs(p1 - p0)
        c = {0: 0.3, 1: -1, 2: -1, 3: 0, 4: 0.3}.get(d, 1 if d <= 7 else 3 + 0.3 * (d - 7))
        if abs(s1.ini - s0.fi) > _EPS:
            return 0
        m0, m1 = mel(s0), mel(s1)
        if m0 is not None and m1 is not None and m0 != m1 and p0 != p1:
            if (p0 - m0) % 12 == (p1 - m1) % 12 and (p1 - m1) % 12 in (0, 7):
                c += 10
        b0, b1 = bx(s0), bx(s1)
        if b0 is not None and b1 is not None and b0 % 12 != b1 % 12 and p0 != p1:
            if (p0 - b0) % 12 == (p1 - b1) % 12 and (p1 - b1) % 12 in (0, 7):
                c += 6
        return c

    # Viterbi
    cost = [[local(actius[0], p) for p in cands[0]]]
    ptr = [[0] * len(cands[0])]
    for j in range(1, len(actius)):
        fila, pt = [], []
        for p in cands[j]:
            loc = local(actius[j], p)
            millor = min(range(len(cands[j - 1])),
                         key=lambda q: (cost[-1][q] + trans(actius[j - 1], cands[j - 1][q], actius[j], p), q))
            fila.append(cost[-1][millor] + trans(actius[j - 1], cands[j - 1][millor], actius[j], p) + loc)
            pt.append(millor)
        cost.append(fila)
        ptr.append(pt)
    q = min(range(len(cands[-1])), key=lambda x: (cost[-1][x], x))
    tria = [0] * len(actius)
    for j in range(len(actius) - 1, -1, -1):
        tria[j] = cands[j][q]
        q = ptr[j][q]

    escala = _escala_pcs(k)
    res: list[Ev] = []
    ultim_compas = segs[actius[-1]].compas
    for j, i in enumerate(actius):
        s = segs[i]
        t = tria[j]
        if s.compas is ultim_compas:
            # final: una nota de l'acord al primer temps fort, com la resta del conjunt
            if abs(s.ini - s.compas.ini) < _EPS:
                res.append(Ev(s.ini, opFrac(min(s.fi - s.ini, s.compas.pols * 2)), [pitch.Pitch(midi=t)]))
            continue
        seguent = tria[j + 1] if j + 1 < len(actius) and abs(segs[actius[j + 1]].ini - s.fi) < _EPS else None
        pols = s.compas.pols
        n_pols = int(round((s.fi - s.ini) / pols))
        atacs = [e for e, x, _ in _notes_entre(evs_mel, s.ini, s.fi) if e.ini > s.ini + _EPS]
        quieta = not atacs and n_pols >= 2 and abs(n_pols * pols - (s.fi - s.ini)) < _EPS
        if not quieta or seguent is None:
            res.append(Ev(s.ini, opFrac(s.fi - s.ini), [pitch.Pitch(midi=t)]))
            continue
        # farciment: graus conjunts cap a la nota següent
        bons = sorted(escala | set(s.acord.pcs))
        pas = []
        x = t
        dirc = 1 if seguent > t else -1 if seguent < t else 1
        while len(pas) < n_pols - 1:
            x += dirc
            while x % 12 not in bons:
                x += dirc
            if x == seguent or not lo <= x <= hi:
                break
            pas.append(x)
        notes = [t] + pas
        mel_ara = _sonant(evs_mel, s.ini)
        netes = [notes[0]]
        for x in notes[1:]:
            if mel_ara is not None and abs(x - mel_ara) % 12 in (1, 6, 11):
                break
            netes.append(x)
        notes = netes
        durs = [pols] * len(notes)
        durs[0] = opFrac((s.fi - s.ini) - pols * (len(notes) - 1))
        tt = s.ini
        for x, d in zip(notes, durs):
            res.append(Ev(tt, opFrac(d), [pitch.Pitch(midi=x)]))
            tt = opFrac(tt + d)
    return _ajunta_repetides(_ortografia(res, k, segs), sorted({segs[i].compas.ini for i in actius}))


def _ortografia(evs: list[Ev], k: key.Key, segs: list[Segment] | None = None) -> list[Ev]:
    """Escriu cada nota amb el nom que li toca: primer el de l'acord (Re# en Si7), després el de l'escala
    (Sib i no La# en Fa major) i, si no, sostinguts o bemolls segons l'armadura."""
    escala = {p.pitchClass: p.name for p in k.getScale().getPitches()[:7]}
    for e in evs:
        noms = dict(escala)
        if segs:
            s = next((x for x in segs if x.ini <= e.ini + _EPS < x.fi), None)
            if s is not None and s.acord is not None:
                noms.update(s.acord.noms)
        nous = []
        for p in e.alt:
            nom = noms.get(p.pitchClass)
            if nom is None:
                q = pitch.Pitch(midi=p.midi)
                if q.accidental is not None:
                    if (k.sharps < 0) != (q.accidental.name == "flat"):
                        q = q.getEnharmonic()
                nous.append(q)
            else:
                q = pitch.Pitch(nom)
                q.octave = 4
                q.octave += (p.midi - q.midi) // 12
                nous.append(q)
        e.alt = nous
    return evs


def _ajunta_repetides(evs: list[Ev], inicis_compas: list[float]) -> list[Ev]:
    """Dues notes iguals seguides dins del mateix compàs queden com una nota llarga (mai lligades d'un compàs a
    l'altre: és més fàcil de llegir i no hi ha lligadures que travessen una repetició)."""
    import bisect
    res: list[Ev] = []
    for e in evs:
        ant = res[-1] if res else None
        mateix = ant is not None and (bisect.bisect_right(inicis_compas, ant.ini + _EPS)
                                      == bisect.bisect_right(inicis_compas, e.ini + _EPS))
        if (ant and mateix and ant.alt and e.alt and [p.midi for p in ant.alt] == [p.midi for p in e.alt]
                and abs(ant.fi - e.ini) < _EPS):
            ant.dur = opFrac(ant.dur + e.dur)
        else:
            res.append(e)
    return res


def _veus_acomp(instr: inst.Instrument) -> int:
    if instr.clau in ("piano", "guitarra", "marimba"):
        return 3
    if instr.lamina:
        return 2
    return 1


# Patrons, ritmes i motius: vegeu acompanyament.py (dades per estil i nivell). Alias per compatibilitat.
from . import acompanyament as _acomp   # noqa: E402
from . import voicing as _voicing        # noqa: E402

_PATRONS = _acomp.PATRONS


def _veu_baixa(pc: int, lo: int, prev: int | None, marge: int = 12) -> int:
    opcions = [m for m in range(lo, lo + marge) if m % 12 == pc]
    if not opcions:
        opcions = [lo + ((pc - lo) % 12)]
    if prev is None:
        return opcions[0]
    return min(opcions, key=lambda m: (abs(m - prev), m))


def _disposicio(acord: Acord, n: int, lo: int, hi: int, prev: list[int] | None, estil: str = "classic",
                nivell: str = "mitja", **mes) -> list[int]:
    """Notes de l'acord per a la mà dreta (o les dues baquetes). La lògica és a voicing.py (clàssic i jazz)."""
    return _voicing.disposicio(acord, n, lo, hi, prev, estil, nivell, **mes)


def rol_acompanyament(segs: list[Segment], instr: inst.Instrument, curs: str | None, estil: str, k: key.Key,
                      bordo: bool = False, melodia: list[Ev] | None = None, fi_frases: list[float] | None = None,
                      amb_baix: bool = False) -> tuple[list[Ev], list[Ev]]:
    """Acompanyament de l'estil sobre els acords (tipus i motiu: acompanyament.py). Retorna (acompanyament, baix)."""
    return _acomp.genera(segs, instr, curs, estil, k, bordo, melodia, fi_frases, amb_baix)


def rol_baix(segs: list[Segment], instr: inst.Instrument, curs: str | None, estil: str, k: key.Key) -> list[Ev]:
    """Fonamentals (i quintes en els estils de dos temps) en la zona greu de l'instrument."""
    lo, hi = _rang_concert(instr, curs)
    lo = min(max(lo, 36), hi - 12)
    res: list[Ev] = []
    prev = None
    ultim = max((s.ini for s in segs if s.acord), default=None)
    for s in segs:
        if s.acord is None or s.compas.anacrusi:
            continue
        a = s.acord
        dur = opFrac(s.fi - s.ini)
        prev = _veu_baixa(a.pcs[0], lo, prev, marge=min(19, max(12, hi - lo)))
        if abs(s.ini - ultim) < _EPS:
            res.append(Ev(s.ini, s.compas.pols, [pitch.Pitch(midi=prev)]))
            continue
        pols = s.compas.pols
        n_pols = int(round(dur / pols))
        if estil in ("pop", "rock") and n_pols >= 2:
            for b in range(n_pols):
                res.append(Ev(opFrac(s.ini + b * pols), pols, [pitch.Pitch(midi=prev)]))
        elif estil in ("ragtime", "swing", "marxa") and n_pols >= 2 and len(a.pcs) >= 3 and dur >= s.compas.dur - _EPS:
            mig = opFrac(dur / 2) if n_pols % 2 == 0 else pols
            res.append(Ev(s.ini, mig, [pitch.Pitch(midi=prev)]))
            q = _veu_baixa(a.pcs[2], lo, prev, marge=min(19, max(12, hi - lo)))
            res.append(Ev(opFrac(s.ini + mig), opFrac(dur - mig), [pitch.Pitch(midi=q)]))
        else:
            res.append(Ev(s.ini, dur, [pitch.Pitch(midi=prev)]))
    return _ortografia(res, k, segs)


# --------------------------------------------------------------------------- percussió

_POS = {"BD": ("F", 4, None), "SN": ("C", 5, None), "HH": ("G", 5, "x"), "CR": ("A", 5, "x")}


def _patro_bateria(estil: str, n_pols: int, subdiv_compost: bool, corxeres: bool) -> list[list[set]]:
    """Per a cada pols, una llista de subdivisions; cada una, el conjunt d'instruments que sonen."""
    res = []
    for b in range(n_pols):
        fort = b % 2 == 0
        if estil == "vals" and n_pols == 3:
            res.append([{"BD", "HH"}] if b == 0 else [{"SN", "HH"}])
            continue
        if subdiv_compost:
            if corxeres:
                res.append([{"HH", "BD"} if fort else {"HH", "SN"}, {"HH"}, {"HH"}])
            else:
                res.append([{"HH", "BD"} if fort else {"HH", "SN"}])
            continue
        if estil in ("pop", "rock") and corxeres:
            extra = {"BD"} if (estil == "rock" and b == 2) else set()
            res.append([({"HH", "BD"} if fort else {"HH", "SN"}), {"HH"} | extra])
        else:
            res.append([{"HH", "BD"} if fort else {"HH", "SN"}])
    return res


def rol_percussio(compassos: list[Compas], segs: list[Segment], instr: inst.Instrument, curs: str | None,
                  estil: str) -> stream.Part:
    corxeres = _permet_corxeres(instr, curs)
    sonen = {id(s.compas) for s in segs if s.acord is not None}
    ultim = max((c.ini for c in compassos if id(c) in sonen), default=None)
    part = stream.Part()
    ins = m21i.UnpitchedPercussion()
    ins.instrumentName = instr.nom
    ins.partName = instr.nom
    ins.midiChannel = 9
    part.insert(0, ins)
    part.partName = instr.nom
    part.partAbbreviation = instr.nom

    def un(nom, ql):
        step, octv, cap = _POS[nom]
        u = note.Unpitched()
        u.displayStep, u.displayOctave = step, octv
        if cap:
            u.notehead = cap
        u.quarterLength = ql
        return u

    def grup(noms, ql, amunt=True):
        noms = sorted(noms)
        if len(noms) == 1:
            x = un(noms[0], ql)
        else:
            x = percussion.PercussionChord([un(nm, ql) for nm in noms])
            x.quarterLength = ql
        x.stemDirection = "up" if amunt else "down"
        return x

    for n, c in enumerate(compassos):
        m = _compas_buit(c, n == 0)
        if n == 0:
            m.insert(0, clef.PercussionClef())
        n_pols = max(1, int(round(c.dur / c.pols)))
        actiu = id(c) in sonen and not c.anacrusi
        if not actiu:
            m.append(note.Rest(quarterLength=c.dur))
            part.append(m)
            continue
        final = abs(c.ini - ultim) < _EPS
        if instr.clau == "bateria":
            if final:
                pat = [[{"CR", "BD"}]] + [[set()] for _ in range(n_pols - 1)]
            else:
                pat = _patro_bateria(estil, n_pols, c.ts.numerator in (6, 9, 12) and c.ts.denominator == 8, corxeres)
            v1, v2 = stream.Voice(id="1"), stream.Voice(id="2")
            for subs in pat:
                ql = opFrac(c.pols / len(subs))
                for s in subs:
                    dalt = s - {"BD"}
                    v1.append(grup(dalt, ql) if dalt else note.Rest(quarterLength=ql))
                    v2.append(grup({"BD"}, ql, amunt=False) if "BD" in s else note.Rest(quarterLength=ql))
            for v in (v1, v2):
                _ajunta_silencis(v, c.ts)
            m.insert(0, v1)
            m.insert(0, v2)
        else:
            # caixa o percussió: una sola línia, a tots els temps (o als forts per a la percussió menuda)
            for b in range(n_pols):
                toca = (b == 0) if final else (instr.clau == "caixa" or b % 2 == 0 or n_pols <= 2)
                m.append(grup({"SN"}, c.pols) if toca else note.Rest(quarterLength=c.pols))
            _ajunta_silencis(m, c.ts)
        part.append(m)
    return part


def _ajunta_silencis(v, ts=None) -> None:
    """Silencis seguits en un de sol (més fàcil de llegir). Amb el compàs (`ts`), agrupats per pulsació."""
    if ts is not None:
        gravat.agrupa_silencis(v, ts)
        return
    els = list(v.notesAndRests)
    i = 0
    while i < len(els) - 1:
        a, b = els[i], els[i + 1]
        if a.isRest and b.isRest and a.quarterLength + b.quarterLength in (1.0, 2.0, 3.0, 4.0) \
                and (a.offset % (a.quarterLength + b.quarterLength) == 0 or a.quarterLength + b.quarterLength == 3.0
                     and a.offset == 0):
            a.quarterLength = a.quarterLength + b.quarterLength
            v.remove(b)
            els.pop(i + 1)
        else:
            i += 1


# --------------------------------------------------------------------------- escriptura

def _compas_buit(c: Compas, primer: bool) -> stream.Measure:
    m = stream.Measure(number=c.num)
    if primer or c.canvi_ts:
        m.timeSignature = copy.deepcopy(c.ts)
    if primer and c.anacrusi:
        m.paddingLeft = opFrac(c.ts.barDuration.quarterLength - c.dur)
    if c.barra_esq is not None:
        m.leftBarline = copy.deepcopy(c.barra_esq)
    if c.barra_dre is not None:
        m.rightBarline = copy.deepcopy(c.barra_dre)
    return m


def part_des_de_evs(evs: list[Ev], compassos: list[Compas], classe=stream.Part) -> stream.Part:
    p = classe()
    for n, c in enumerate(compassos):
        m = _compas_buit(c, n == 0)
        t = c.ini
        for e in evs:
            if not e.alt or e.fi <= c.ini + _EPS or e.ini >= c.fi - _EPS:
                continue
            a, b = max(e.ini, c.ini), min(e.fi, c.fi)
            pad = opFrac(c.ts.barDuration.quarterLength - c.dur) if c.anacrusi else 0   # compàs de l'anacrusi
            if a > t + _EPS:
                for r in gravat.silencis(t - c.ini + pad, a - t, c.ts):
                    m.append(r)
            if len(e.alt) == 1:
                x = note.Note(copy.deepcopy(e.alt[0]))
            else:
                x = chord.Chord([copy.deepcopy(q) for q in e.alt])
            ve = e.ini < c.ini - _EPS
            va = e.fi > c.fi + _EPS
            for y in gravat.talla_nota(x, a - c.ini + pad, b - a, c.ts, ve, va):
                m.append(y)
            t = b
        if t < c.fi - _EPS:
            pad = opFrac(c.ts.barDuration.quarterLength - c.dur) if c.anacrusi else 0
            for r in gravat.silencis(t - c.ini + pad, c.fi - t, c.ts):
                m.append(r)
        if not m.notesAndRests:
            m.append(note.Rest(quarterLength=c.dur))
        p.append(m)
    return p


def _vestir(part: stream.Part, instr: inst.Instrument, k_escrit, ks_concert: key.KeySignature | None) -> stream.Part:
    """Posa instrument, clau i armadura, i passa de so real a altura escrita."""
    obj = inst.crear_objecte_music21(instr)
    part.insert(0, obj)
    part.partName = instr.nom
    part.partAbbreviation = instr.abreviatura
    primer = part.getElementsByClass(stream.Measure).first()
    if ks_concert is not None:
        primer.insert(0, copy.deepcopy(ks_concert))
    part.atSoundingPitch = True
    if obj.transposition is not None:
        part.toWrittenPitch(inPlace=True)
        for n in part.recurse().notes:
            for p in getattr(n, "pitches", ()):
                if p.accidental is not None and abs(p.accidental.alter) >= 2:
                    q = p.simplifyEnharmonic()
                    p.step, p.accidental, p.octave = q.step, q.accidental, q.octave
    musica._posar_clau(part, instr)
    part.makeAccidentals(inPlace=True, overrideStatus=True, cautionaryNotImmediateRepeat=False)
    return part


# Ordre del guió segons Gould SCO-04: fusta, metall, percussió i làmines, guitarra i teclat, cordes al final.
ORDRE_FAMILIES = ["flauti", "flauta", "oboe", "corn-angles", "clarinet-sib", "clarinet-la", "clarinet-baix",
                  "clarinet-contrabaix", "saxo-soprano", "saxo-alt", "saxo-tenor", "saxo-bari", "fagot", "contrafagot",
                  "trompa-fa", "trompeta-sib", "trompeta-do", "fliscorn-sib", "trombo", "trombo-baix", "bombardi", "tuba",
                  "carillo", "xilofon", "xilofon-orff", "metalofon", "vibrafon", "marimba", "bateria", "caixa",
                  "percussio", "guitarra", "piano", "violi", "viola", "violoncel", "contrabaix"]


def _ordre(r: Rol) -> tuple:
    try:
        return (ORDRE_FAMILIES.index(r.instr.clau), ROLS.index(r.rol))
    except ValueError:
        return (len(ORDRE_FAMILIES), ROLS.index(r.rol))


# --------------------------------------------------------------------------- comprovacions

def _paral_temps(a: list[Ev], b: list[Ev]) -> list[tuple[float, str]]:
    """Instants (i tipus) de les quintes i octaves paral·leles entre dues línies (en so real)."""
    temps = sorted({e.ini for e in a if e.alt} | {e.ini for e in b if e.alt})
    res = []
    ant = None
    for t in temps:
        x, y = _sonant(a, t), _sonant(b, t)
        if x is None or y is None:
            ant = None
            continue
        if ant is not None:
            x0, y0 = ant
            if x0 != x and y0 != y:
                i0, i1 = (x0 - y0) % 12, (x - y) % 12
                if i0 == i1 and i1 in (0, 7):
                    res.append((t, "octaves" if i1 == 0 else "quintes"))
        ant = (x, y)
    return res


def paral_leles(a: list[Ev], b: list[Ev], compassos: list[Compas]) -> list[tuple[int, str]]:
    """Quintes i octaves paral·leles entre dues línies (en so real). Retorna (compàs, tipus)."""
    res = []
    for t, tipus in _paral_temps(a, b):
        c = next((c for c in compassos if c.ini <= t + _EPS < c.fi), None)
        res.append((c.num if c else 0, tipus))
    return res


def _repara_paral(e: list[Ev], mel: list[Ev], baix: list[Ev] | None, segs: list[Segment], lo: int, hi: int,
                  k: key.Key) -> list[Ev]:
    """Si una nota del contracant fa quintes o octaves paral·leles amb la melodia o el baix, la canvia per una altra
    nota de l'acord (la més propera) que les evite sense crear-ne de noves."""
    def total(x):
        return len(_paral_temps(x, mel)) + (len(_paral_temps(x, baix)) if baix else 0)

    for _ in range(4):
        ts = {t for t, _ in _paral_temps(e, mel)} | ({t for t, _ in _paral_temps(e, baix)} if baix else set())
        if not ts:
            break
        canviat = False
        for t in sorted(ts):
            ev = next((x for x in e if abs(x.ini - t) < _EPS and x.alt), None)
            if ev is None:
                continue
            a = _acord_en(segs, t)
            orig = ev.alt[0]
            m = _sonant(mel, t)
            ara = total(e)
            cands = sorted((p for p in range(max(lo, orig.midi - 6), min(hi, orig.midi + 6) + 1)
                            if p != orig.midi and (a is None or p % 12 in a.pcs)
                            and (m is None or (p - m) % 12 not in (0, 1, 6, 11))), key=lambda p: (abs(p - orig.midi), p))
            for p in cands:
                ev.alt = [pitch.Pitch(midi=p)]
                if total(e) < ara:
                    canviat = True
                    break
                ev.alt = [orig]
        if not canviat:
            break
    return _ortografia(e, k, segs)


def _rang_text(parts: list[stream.Part], instr: inst.Instrument, curs: str | None) -> list[str]:
    (lo, hi), font = rang_comode(instr, curs)
    ab_lo, ab_hi = inst.rang_midi(instr.abast)
    escrits = []
    fora, incom = [], []
    for n in (x for part in parts for x in part.flatten().notes):
        if isinstance(n, harmony.Harmony) or not getattr(n, "pitches", None) or isinstance(n, note.Unpitched):
            continue
        cnum = n.getContextByClass(stream.Measure)
        for p in n.pitches:
            escrits.append(p.midi)
            if not ab_lo <= p.midi <= ab_hi:
                fora.append(cnum.number if cnum else 0)
            elif not lo <= p.midi <= hi:
                incom.append(cnum.number if cnum else 0)
    if not escrits:
        return ["   Sense notes."]
    ll = [f"   Escrit de {musica.nom_nota(min(escrits))} a {musica.nom_nota(max(escrits))} "
          f"(zona còmoda {musica.nom_nota(lo)}-{musica.nom_nota(hi)}, segons el {font})."]
    if fora:
        ll.append(f"   FORA d'abast als compassos {_llista_nums(fora)}.")
    if incom:
        ll.append(f"   Fora de la zona còmoda als compassos {_llista_nums(incom)}.")
    return ll


def _llista_nums(nums) -> str:
    u = sorted(set(nums))
    return ", ".join(str(x) for x in u[:12]) + (f" i {len(u) - 12} més" if len(u) > 12 else "")


def compassos_buits(part: stream.Part) -> list[int]:
    return [m.number for m in part.getElementsByClass(stream.Measure) if not any(
        not n.isRest for n in m.recurse().notesAndRests)]


def compassos_incomplets(part: stream.Part, compassos: list[Compas]) -> list[int]:
    res = []
    for m, c in zip(part.getElementsByClass(stream.Measure), compassos):
        veus = list(m.voices) or [m]
        for v in veus:
            tot = sum(n.quarterLength for n in v.notesAndRests)
            if abs(tot - c.dur) > 1e-3:
                res.append(m.number)
                break
    return res


# --------------------------------------------------------------------------- repartiment de la melodia (rotació)

@dataclass
class Seccio:
    """Una frase de la peça (de compàs a compàs) i qui fa què en ella."""
    i0: int                 # índex del primer compàs
    i1: int                 # índex del compàs següent a l'últim
    ini: float
    fi: float
    num0: int               # número del primer i l'últim compàs (per a l'informe)
    num1: int
    portador: int = 0       # índex (a la llista de rols) de qui porta la melodia
    funcions: dict = field(default_factory=dict)   # índex de rol -> funció en esta frase
    repeteix: int | None = None
    tutti: bool = False
    tipus: str = "irregular"   # sentencia, periode, irregular (forma.py); intro i coda per a les afegides
    tancada: bool = False      # la frase acaba en la tònica (frase tancada, Perricone R04)
    marca: float = 0.0         # punts de final de frase detectats al final (0 = tallada per la llargada ideal)


def _es_barra_forta(b) -> bool:
    return b is not None and (isinstance(b, bar.Repeat) or getattr(b, "type", "") in
                              ("double", "final", "light-light", "light-heavy"))


def _puntua_tall(b: int, ideal: int, compassos: list[Compas], evs: list[Ev], segs: list[Segment], k) -> float:
    """Com de bon lloc és el compàs b per a començar una frase: doble barra, nota llarga o silenci i cadència."""
    c0, c1 = compassos[b - 1], compassos[b]
    sc = -1.0 * abs(b - ideal)
    if _es_barra_forta(c0.barra_dre):
        sc += 2.5
    ant = [e for e in evs if e.alt and e.ini < c1.ini - _EPS]
    if ant:
        u = ant[-1]
        if u.dur >= 2 - _EPS or u.fi > c1.ini + _EPS:
            sc += 1.5
        elif u.fi <= c1.ini - c0.pols + _EPS:
            sc += 1.5
    a0 = next((s.acord for s in reversed(segs) if s.compas is c0 and s.acord), None)
    a1 = next((s.acord for s in segs if s.compas is c1 and s.acord), None)
    if a0 is not None and a1 is not None:
        g0, g1 = _grau(a0, k), _grau(a1, k)
        if g1 == 1 and g0 == 5:
            sc += 1.5
        elif g1 == 1 and g0 == 4:
            sc += 0.5
    from . import forma
    return sc + forma.marques_extra(b, compassos, evs, segs, k)


def dividir_seccions(compassos: list[Compas], evs: list[Ev], segs: list[Segment], k, bpm: float | None = None) -> list[Seccio]:
    """Frases tallades per cadències i repeticions de material (forma.py): la llargada ideal depèn de la mètrica i del
    tempo (4 compassos en simple, 2 en compost) i només mana quan no es detecta cap final de frase."""
    from . import forma
    f = 1 if compassos[0].anacrusi else 0
    res = []
    for a, b, tipus, marca in forma.divideix(compassos, evs, segs, k, bpm):
        n0 = compassos[a + (1 if a == 0 and f else 0)].num
        res.append(Seccio(a, b, compassos[a].ini, compassos[b - 1].fi, n0, compassos[b - 1].num, tipus=tipus,
                          marca=marca))
    forma.etiqueta(res, compassos, evs, k)
    # repeticions: frases amb el mateix material de melodia
    def signatura(s):
        ref = compassos[s.i0 + (1 if s.i0 == 0 and f else 0)].ini
        ns = [e for e in evs if e.alt and s.ini - _EPS <= e.ini < s.fi - _EPS]
        if not ns:
            return set()
        p0 = ns[0].alt[0].midi
        return {(round(e.ini - ref, 3), e.dur, e.alt[0].midi - p0) for e in ns}
    sigs = [signatura(s) for s in res]
    for i in range(1, len(res)):
        for j in range(i):
            if sigs[i] and sigs[j] and len(sigs[i] & sigs[j]) / max(len(sigs[i]), len(sigs[j])) >= 0.6:
                res[i].repeteix = j
                break
    return res


def _retalla(evs: list[Ev], a: float, b: float) -> list[Ev]:
    res = []
    for e in evs:
        if e.fi <= a + _EPS or e.ini >= b - _EPS:
            continue
        x, y = max(e.ini, a), min(e.fi, b)
        res.append(Ev(opFrac(x), opFrac(y - x), list(e.alt)))
    return res


def _substitueix(evs: list[Ev], a: float, b: float, nous: list[Ev]) -> list[Ev]:
    res = []
    for e in evs:
        if e.fi <= a + _EPS or e.ini >= b - _EPS:
            res.append(e)
            continue
        if e.ini < a - _EPS:
            res.append(Ev(e.ini, opFrac(a - e.ini), list(e.alt)))
        if e.fi > b + _EPS:
            res.append(Ev(opFrac(b), opFrac(e.fi - b), list(e.alt)))
    return sorted(res + nous, key=lambda e: e.ini)


def _encaix_melodia(evs_sec: list[Ev], instr: inst.Instrument, curs: str | None):
    """(cap, evs, desplaçament, proporció dins la zona còmoda): la melodia d'una frase a l'octava de l'instrument."""
    if not any(e.alt for e in evs_sec):
        return False, evs_sec, 0, 0.0
    e, sh = rol_melodia(evs_sec, instr, curs)
    lo, hi = _rang_concert(instr, curs)
    ab_lo, ab_hi = (x + instr.semitons() for x in inst.rang_midi(instr.abast))
    mids = [x.alt[0].midi for x in e if x.alt]
    fora = sum(not ab_lo <= m <= ab_hi for m in mids)
    frac = sum(lo <= m <= hi for m in mids) / len(mids)
    return fora == 0 and frac >= 0.85, e, sh, frac


def _pot_portar(instr: inst.Instrument) -> bool:
    return not instr.percussio and instr.clau not in ("piano", "guitarra")


def _funcions_seccio(rols: list[Rol], ld: dict, x: int, curs: str | None, tutti: bool = False) -> dict:
    """Qui fa què quan l'instrument x porta la melodia (els altres canvien de funció el mínim possible)."""
    f = {i: r.rol for i, r in enumerate(rols)}
    m, c, a, b = ld["melodia"], ld.get("contracant"), ld.get("acompanyament"), ld.get("baix")
    if x == m:
        if tutti and c is not None:
            f[c] = "melodia"
        return f
    f[x] = "melodia"
    if x == c:
        f[m] = "contracant"
    elif x == a:
        f[m] = "contracant"
        if c is not None:
            f[c] = "pad"
    elif x == b:
        cand = [i for i in (m, c) if i is not None]
        y = min(cand, key=lambda i: (sum(_rang_concert(rols[i].instr, curs)) / 2, i))
        f[y] = "suport"
        if y == c:
            f[m] = "contracant"
    return f


ROTACIO_MIN_COMPASSOS = 12   # per sota d'això la melodia no es reparteix, encara que hi haja tres frases curtes
FRAGMENT_REL = 0.6   # una frase més curta que això (respecte de la mediana) no canvia de portador [inferència]


def planificar(rols: list[Rol], seccions: list[Seccio], evs: list[Ev], curs: str | None,
               tutti_final: bool = False) -> list[str]:
    """Tria qui porta la melodia a cada frase. Retorna notes per a l'informe."""
    notes: list[str] = []
    ld: dict = {}
    for i, r in enumerate(rols):
        if not r.instr.percussio:
            ld.setdefault(r.rol, i)
    m = ld["melodia"]
    for s in seccions:
        s.portador = m
        s.tutti = False
    n = len(seccions)
    if sum(r.rol == "melodia" for r in rols) > 1:
        notes.append("Hi ha dos instruments amb la melodia: no la repartisc entre veus.")
    elif n < 3 or sum(x.i1 - x.i0 for x in seccions) < ROTACIO_MIN_COMPASSOS:
        notes.append("La peça és massa curta per a repartir la melodia entre veus (menys de tres frases).")
    else:
        cands = [i for i in (ld.get("contracant"), ld.get("baix"), ld.get("acompanyament")) if i is not None
                 and _pot_portar(rols[i].instr)]
        if ld.get("acompanyament") in cands and ld.get("baix") is None and ld.get("contracant") is None:
            cands.remove(ld["acompanyament"])
        cache: dict = {}

        def encaix(si, i):
            if (si, i) not in cache:
                s = seccions[si]
                cache[(si, i)] = _encaix_melodia(_retalla(evs, s.ini, s.fi), rols[i].instr, curs)
            return cache[(si, i)]

        pos = 0
        llarg = sorted(x.i1 - x.i0 for x in seccions)[n // 2]
        for si in range(1, n - 1):
            ant = seccions[si - 1].portador
            if seccions[si].i1 - seccions[si].i0 < FRAGMENT_REL * llarg and seccions[si].repeteix is None:
                seccions[si].portador = ant     # un tros de frase no canvia de veu: continua el portador anterior
                continue
            opcions = [cands[(pos + o) % len(cands)] for o in range(len(cands))] if cands else []
            opcions = [i for i in opcions if i != ant and encaix(si, i)[0]]
            rep = seccions[si].repeteix
            if rep is not None and len(opcions) > 1 and seccions[rep].portador == opcions[0]:
                opcions = opcions[1:] + opcions[:1]
            if opcions:
                seccions[si].portador = opcions[0]
                pos = (cands.index(opcions[0]) + 1) % len(cands)
        b = ld.get("baix")
        if b in cands and not any(s.portador == b for s in seccions):
            bons = [si for si in range(1, n - 1) if encaix(si, b)[0]]
            if bons:
                si = max(bons, key=lambda q: (encaix(q, b)[3], -abs(q - n / 2), -q))
                seccions[si].portador = b
        if b is not None and not any(s.portador == b for s in seccions):
            notes.append(f"{_nom_curt(rols[b].instr).capitalize()} no porta la melodia: no hi cap a la seua zona còmoda.")
        if tutti_final and ld.get("contracant") is not None and _pot_portar(rols[ld["contracant"]].instr):
            ult = seccions[-1]
            if _encaix_melodia(_retalla(evs, ult.ini, ult.fi), rols[ld["contracant"]].instr, curs)[0]:
                ult.tutti = True
    for s in seccions:
        s.funcions = _funcions_seccio(rols, ld, s.portador, curs, s.tutti)
    return notes


_FEMENINS = ("trompeta", "flauta", "trompa", "tuba", "viola", "guitarra", "marimba", "caixa", "bateria", "percussio",
             "percussió")


def _nom_curt(instr: inst.Instrument) -> str:
    t = instr.nom.lower()
    for sep in (" en ", " (", ","):
        t = t.split(sep)[0]
    return t.strip()


def _amb_article(instr: inst.Instrument) -> str:
    n = _nom_curt(instr)
    if n[0] in "aeiouàèéíòóú":
        return "l'" + n
    return ("la " if n.split()[0] in _FEMENINS else "el ") + n


def text_pla(rols: list[Rol], seccions: list[Seccio], notes: list[str]) -> list[str]:
    trossos = []
    for s in seccions:
        extra = []
        if s.tutti:
            extra.append("tot el conjunt amb la melodia")
        for i, f in s.funcions.items():
            if f == "suport":
                extra.append(f"{_amb_article(rols[i].instr)} fa el baix")
            elif f == "pad":
                extra.append(f"{_amb_article(rols[i].instr)} fa els acords de fons")
        t = f"c. {s.num0}-{s.num1} {_nom_curt(rols[s.portador].instr)}"
        trossos.append(t + (f" ({'; '.join(extra)})" if extra else ""))
    ll = ["Repartiment de la melodia (canvia de veu cada frase; amb --sense-rotacio es queda sempre en el mateix instrument):",
          "  Qui porta la melodia: " + "; ".join(trossos) + "."]
    ll += [f"  {x}" for x in notes]
    return ll


def _acord_en(segs: list[Segment], t: float):
    for s in segs:
        if s.ini <= t + _EPS < s.fi:
            return s.acord
    return None


def _quantitza(d: float, minim: float) -> float:
    return min((x for x in (0.5, 1.0, 1.5, 2.0) if x >= minim - _EPS), key=lambda x: (abs(x - d), x))


def _cadena(ts: list[float], signes: list[int], pool: list[int], p0: int, mel_at, acord, anterior=None):
    """Una nota per instant, per graus conjunts del conjunt `pool`, seguint el contorn `signes`; cada nota evita els
    xocs amb la melodia (unísó, segona menor, tritó, sèptima major) i les quintes i octaves paral·leles. L'última, nota
    de l'acord. None si no hi ha manera."""
    if not pool:
        return None
    pool = sorted(pool)

    def valida(p, t, prev_p):
        m = mel_at(t) if mel_at else None
        if m is None:
            return True
        if (p - m) % 12 in (0, 1, 6, 11):
            return False
        if prev_p is not None and prev_p[0] != p and prev_p[1] != m:
            i0, i1 = (prev_p[0] - prev_p[1]) % 12, (p - m) % 12
            if i0 == i1 and i1 in (0, 7):
                return False
        return True

    def tria(desitjat_idx, t, prev_p):
        for d in (0, 1, -1, 2, -2):
            q = desitjat_idx + d
            if 0 <= q < len(pool) and valida(pool[q], t, prev_p):
                return q
        return None

    idx0 = min(range(len(pool)), key=lambda q: (abs(pool[q] - p0), q))
    q = tria(idx0, ts[0], anterior)
    if q is None:
        return None
    res = [pool[q]]
    for j, sg in enumerate(signes):
        prev_p = (res[-1], mel_at(ts[j]) if mel_at else None)
        q = tria(max(0, min(len(pool) - 1, q + sg)), ts[j + 1], prev_p)
        if q is None:
            return None
        res.append(pool[q])
    if acord is not None and res[-1] % 12 not in acord.pcs:
        prev_p = (res[-2], mel_at(ts[-2])) if len(res) > 1 and mel_at else anterior
        bons = [x for x in pool if x % 12 in acord.pcs and abs(x - res[-1]) <= 4 and valida(x, ts[-1], prev_p)]
        if not bons:
            return None
        res[-1] = min(bons, key=lambda x: (abs(x - res[-1]), x))
    return res


def _motiu(evs_mel: list[Ev], c: Compas, maxim: int = 4):
    """Els atacs de la melodia d'un compàs: (inici relatiu, durada, signe del moviment cap a la nota següent)."""
    at = [e for e in evs_mel if e.alt and c.ini - _EPS <= e.ini < c.fi - _EPS][:maxim]
    return [(opFrac(e.ini - c.ini), min(e.dur, opFrac(c.fi - e.ini)), e.alt[0].midi) for e in at]


def _finestres_resposta(evs_mel: list[Ev], compassos: list[Compas], seccions: list[Seccio]):
    """Finals de frase on la melodia manté una nota llarga o descansa: (inici, fi, compàs on comença la frase)."""
    res = []
    f0 = 1 if compassos[0].anacrusi else 0
    for s in seccions:
        for ci in range(s.i0, s.i1):
            c = compassos[ci]
            if c.anacrusi or ci >= len(compassos) - 1:
                continue
            local = ci - s.i0 - (f0 if s.i0 == 0 else 0)
            if not ((local + 1) % 4 == 0 or ci == s.i1 - 1):
                continue
            at = [e for e in evs_mel if e.alt and c.ini - _EPS <= e.ini < c.fi - _EPS]
            if at:
                u = at[-1]
                w0 = c.ini + (int((u.ini - c.ini) / c.pols + _EPS) + 1) * c.pols
            else:
                w0 = c.ini + c.pols
            w0 = max(opFrac(w0), opFrac(c.fi - 2 * c.pols))
            if c.fi - w0 >= c.pols - _EPS:
                res.append((w0, c.fi, ci - local % 4, ci))
    return res


def _farciments(linia: list[Ev], evs_mel: list[Ev], segs: list[Segment], compassos: list[Compas],
                seccions: list[Seccio], lo: int, hi: int, k, curs_corxeres: bool, melodic: bool) -> list[Ev]:
    """Respostes curtes (2-4 notes amb el ritme de la melodia) on la melodia manté una nota llarga o descansa."""
    minim = 0.5 if curs_corxeres else 1.0
    escala = _escala_pcs(k)
    for w0, w1, g, ci in _finestres_resposta(evs_mel, compassos, seccions):
        mot = []
        for j in list(range(g, ci + 1)) + list(range(g - 1, max(g - 5, -1), -1)):
            mot = _motiu(evs_mel, compassos[j])
            if len(mot) >= 2:
                break
        if len(mot) < 2:
            continue
        durs, mids, tt = [], [], w0
        for rel, d, m in mot:
            d = _quantitza(d, minim)
            if tt + d > w1 + _EPS:
                break
            durs.append(d)
            mids.append(m)
            tt = opFrac(tt + d)
        if len(durs) < 2:
            continue
        ts = []
        t = w0
        for d in durs:
            ts.append(t)
            t = opFrac(t + d)
        signes = [(mids[j + 1] > mids[j]) - (mids[j + 1] < mids[j]) for j in range(len(mids) - 1)]
        a = _acord_en(segs, w0)
        if a is None:
            continue
        ref = _sonant(linia, w0)
        if ref is None:
            ref = _sonant(linia, w0 - _EPS) or (lo + hi) // 2
        pcs = set(a.pcs)
        pool = [p for p in range(lo, hi + 1) if p % 12 in (pcs if not melodic else pcs | escala)]
        p0 = min((p for p in pool if p % 12 in pcs), key=lambda p: (abs(p - ref), p), default=None)
        if p0 is None:
            continue
        mel_at = (lambda x: _sonant(evs_mel, x)) if melodic else None
        notes = _cadena(ts, signes, pool, p0, mel_at, a, None)
        if notes is None:
            continue
        nous = [Ev(t, d, [pitch.Pitch(midi=x)]) for t, d, x in zip(ts, durs, notes)]
        linia = _substitueix(linia, w0, ts[-1] + durs[-1], _ortografia(nous, k, segs))
    return linia


def _imitacions(linia: list[Ev], evs_mel: list[Ev], segs: list[Segment], compassos: list[Compas],
                seccions: list[Seccio], lo: int, hi: int, k, curs_corxeres: bool) -> list[Ev]:
    """De tant en tant, el contracant repeteix el ritme (i el contorn) de la melodia del compàs anterior."""
    minim = 0.5 if curs_corxeres else 1.0
    escala = _escala_pcs(k)
    f0 = 1 if compassos[0].anacrusi else 0
    for s in seccions:
        for ci in range(s.i0 + (f0 if s.i0 == 0 else 0), s.i1):
            local = ci - s.i0 - (f0 if s.i0 == 0 else 0)
            g, pos = divmod(local, 4)
            if pos != 1 or g % 2 == 0 or ci >= len(compassos) - 2:
                continue
            c0, c = compassos[ci - 1], compassos[ci]
            mot = [x for x in _motiu(evs_mel, c0) if x[0] < 2 * c0.pols - _EPS]
            if len(mot) < 2:
                continue
            if len(_motiu(evs_mel, c, 8)) > 3 or len([e for e in linia if c.ini - _EPS <= e.ini < c.fi - _EPS]) > 2:
                continue
            t = opFrac(c.ini + round(mot[0][0] * 2) / 2)
            ts, durs, mids = [], [], []
            for _, d, m in mot:
                d = _quantitza(d, minim)
                if t + d > c.ini + 2 * c.pols + _EPS:
                    break
                ts.append(t)
                durs.append(d)
                mids.append(m)
                t = opFrac(t + d)
            if len(ts) < 2:
                continue
            fin = opFrac(ts[-1] + durs[-1])
            signes = [(mids[j + 1] > mids[j]) - (mids[j + 1] < mids[j]) for j in range(len(mids) - 1)]
            a = _acord_en(segs, ts[0])
            ref = _sonant(linia, ts[0])
            if a is None or ref is None or ref % 12 not in a.pcs:
                continue
            pool = [p for p in range(lo, hi + 1) if p % 12 in (set(a.pcs) | escala)]
            prev = _sonant(linia, ts[0] - 0.01)
            m0 = _sonant(evs_mel, ts[0] - 0.01)
            anterior = (prev, m0) if prev is not None and m0 is not None else None
            notes = _cadena(ts, signes, pool, ref, lambda x: _sonant(evs_mel, x), a, anterior)
            if notes is None:
                continue
            nous = [Ev(t, d, [pitch.Pitch(midi=x)]) for t, d, x in zip(ts, durs, notes)]
            linia = _substitueix(linia, ts[0], fin, _ortografia(nous, k, segs))
    return linia


def rol_baix_viu(segs: list[Segment], instr: inst.Instrument, curs: str | None, estil: str, k: key.Key,
                 melodia: list[Ev] | None = None) -> list[Ev]:
    """Baix amb patró d'estil: arrel i quinta (ragtime, marxa), passant per graus (swing), arpegi (vals, clàssic).
    A partir del nivell mitjà, amb inversions, aproximació i caminant (`baix.py`)."""
    lo, hi = _rang_concert(instr, curs)
    lo = min(max(lo, 36), hi - 12)
    marge = min(19, max(12, hi - lo))
    from . import baix as _baix
    personal = _baix.linia(segs, estil, curs, lo, hi, marge, k.tonic.pitchClass, _escala_pcs(k),
                           (lambda t: _sonant(melodia, t)) if melodia else None)
    if personal is not None:
        return _ortografia([Ev(i, d, [pitch.Pitch(midi=m)]) for i, d, m in personal], k, segs)
    corxeres = _permet_corxeres(instr, curs)
    escala = _escala_pcs(k)
    actius = [s for s in segs if s.acord is not None and not s.compas.anacrusi]
    ultim = max((s.ini for s in actius), default=None)
    res: list[Ev] = []
    prev = None
    for j, s in enumerate(actius):
        a = s.acord
        dur = opFrac(s.fi - s.ini)
        pols = s.compas.pols
        n = int(round(dur / pols))
        seg = actius[j + 1] if j + 1 < len(actius) and abs(actius[j + 1].ini - s.fi) < _EPS else None
        arrel = _veu_baixa(a.pcs[0], lo, prev, marge)
        if abs(s.ini - ultim) < _EPS:
            res.append(Ev(s.ini, pols, [pitch.Pitch(midi=arrel)]))
            prev = arrel
            continue
        if n < 2 or abs(n * pols - dur) > _EPS:
            res.append(Ev(s.ini, dur, [pitch.Pitch(midi=arrel)]))
            prev = arrel
            continue
        canvi = seg is not None and seg.acord.pcs[0] != a.pcs[0]
        if estil in ("ragtime", "marxa"):
            tipus = ["R" if b % 2 == 0 else "5" for b in range(n)]
            if estil == "ragtime" and canvi:
                tipus[-1] = "A"
        elif estil == "swing":
            tipus = ["R"] + [("3", "5")[(b - 1) % 2] for b in range(1, n - 1)] + ["A" if canvi else "5"]
        elif estil in ("pop", "rock"):
            tipus = {2: ["R", "5"], 3: ["R", "5", "R"]}.get(n) or [("R", "R", "5", "R")[b % 4] for b in range(n)]
        elif estil == "vals":
            tipus = [("R", "5", "3")[b % 3] for b in range(n)]
        else:
            tipus = [("R", "5", "3", "5")[b % 4] for b in range(n)]
        for b, t in enumerate(tipus):
            ini = opFrac(s.ini + b * pols)
            if t == "R":
                x = _veu_baixa(a.pcs[0], lo, prev, marge)
            elif t == "5":
                x = _veu_baixa(a.pcs[2] if len(a.pcs) > 2 else a.pcs[0], lo, prev, marge)
            elif t == "3":
                x = _veu_baixa(a.pcs[1] if len(a.pcs) > 1 else a.pcs[0], lo, prev, marge)
            else:   # approximació a l'arrel de l'acord següent
                pn = seg.acord.pcs[0]
                if estil == "swing":
                    pcs = [(pn - 1) % 12, (pn + 1) % 12]
                else:
                    sc = sorted(escala)
                    pcs = [next(((pn - d) % 12 for d in range(1, 12) if (pn - d) % 12 in sc), pn),
                           next(((pn + d) % 12 for d in range(1, 12) if (pn + d) % 12 in sc), pn)]
                opts = [_veu_baixa(pc, lo, prev, marge) for pc in pcs]
                x = min(opts, key=lambda m: (abs(m - prev) if prev is not None else 0, m))
            if estil == "rock" and corxeres and pols >= 1 and t == "R":
                mig = opFrac(pols / 2)
                res.append(Ev(ini, mig, [pitch.Pitch(midi=x)]))
                res.append(Ev(opFrac(ini + mig), mig, [pitch.Pitch(midi=x)]))
            else:
                res.append(Ev(ini, pols, [pitch.Pitch(midi=x)]))
            prev = x
    return _ortografia(res, k, segs)


def _pad(evs: list[Ev], instr: inst.Instrument, curs: str | None) -> list[Ev]:
    """Fons d'acords per a un instrument d'una sola veu: una nota llarga de l'acord, en la part baixa de la seua zona."""
    lo, hi = _rang_concert(instr, curs)
    tope = lo + 0.75 * (hi - lo)
    res = []
    for e in evs:
        if not e.alt:
            continue
        p = max(e.alt, key=lambda x: x.ps)
        q = pitch.Pitch(p.nameWithOctave)
        while q.midi > tope and q.midi - 12 >= lo:
            q.octave -= 1
        res.append(Ev(e.ini, e.dur, [q]))
    return res


def _construir_rotacio(rols, seccions, segs, compassos, evs, curs, estil, k, bordo, informe):
    """Les parts amb la melodia repartida entre veus. Retorna (construides, linies, baix_ref)."""
    idx_mel = next(i for i, r in enumerate(rols) if r.rol == "melodia")
    e_m, sh = rol_melodia(evs, rols[idx_mel].instr, curs)
    if sh:
        informe.append(f"{rols[idx_mel].instr.nom}: melodia {abs(sh) // 12} octava{'es' if abs(sh) > 12 else ''} "
                       f"{'amunt' if sh > 0 else 'avall'} perquè caiga en la zona còmoda.")
    n = len(seccions)
    mel_sec: dict = {}
    comp_mel: list[Ev] = []
    for si, s in enumerate(seccions):
        for i, f in s.funcions.items():
            if f != "melodia":
                continue
            if i == idx_mel:
                mel_sec[(si, i)] = _retalla(e_m, s.ini, s.fi)
            else:
                mel_sec[(si, i)] = _encaix_melodia(_retalla(evs, s.ini, s.fi), rols[i].instr, curs)[1]
        comp_mel += mel_sec[(si, s.portador)]
    cache: dict = {}
    baixos_acomp: dict = {}

    def linia(i, f):
        if (i, f) in cache:
            return cache[(i, f)]
        instr = rols[i].instr
        lo, hi = _rang_concert(instr, curs)
        corx = _permet_corxeres(instr, curs)
        if f == "baix":
            e = rol_baix_viu(segs, instr, curs, estil, k, comp_mel)
            blo = min(max(lo, 36), hi - 12)
            e = _farciments(e, comp_mel, segs, compassos, seccions, blo, min(hi, blo + 12), k, corx, False)
        elif f == "suport":
            e = rol_baix(segs, instr, curs, "classic", k)
        elif f == "acompanyament":
            e, baixos_acomp[i] = rol_acompanyament(segs, instr, curs, estil, k, bordo, comp_mel, [x.fi for x in seccions],
                                                   any(r.rol == "baix" for r in rols))
        elif f == "pad":
            e = _pad(rol_acompanyament(segs, instr, curs, "coral", k)[0], instr, curs)
        elif f == "contracant":
            e = rol_contracant(comp_mel, segs, instr, curs, k, baix_ref or None)
            e = _imitacions(e, comp_mel, segs, compassos, seccions, lo, hi, k, corx)
            e = _farciments(e, comp_mel, segs, compassos, seccions, lo, hi, k, corx, True)
            e = _repara_paral(e, comp_mel, baix_ref or None, segs, lo, hi, k)
        else:
            raise ValueError(f)
        cache[(i, f)] = e
        return e

    baix_ref: list[Ev] = []
    for s in seccions:
        tit = next((i for i, f in s.funcions.items() if f in ("baix", "suport")), None)
        if tit is not None:
            baix_ref += _retalla(linia(tit, s.funcions[tit]), s.ini, s.fi)
    if not baix_ref:
        for i, r in enumerate(rols):
            if r.rol == "acompanyament":
                linia(i, "acompanyament")
                baix_ref = list(baixos_acomp.get(i, []))
                break
    else:
        # seccions sense titular de baix: els baixos de l'acompanyament
        sense = [s for s in seccions if not any(f in ("baix", "suport") for f in s.funcions.values())]
        if sense:
            for i, r in enumerate(rols):
                if r.rol == "acompanyament":
                    linia(i, "acompanyament")
                    for s in sense:
                        baix_ref += _retalla(baixos_acomp.get(i, []), s.ini, s.fi)
                    baix_ref.sort(key=lambda e: e.ini)
                    break
    cont_comp: list[Ev] = []
    for s in seccions:
        tit = next((i for i, f in s.funcions.items() if f == "contracant"), None)
        if tit is not None:
            cont_comp += _retalla(linia(tit, "contracant"), s.ini, s.fi)
    linies = {"melodia": comp_mel}
    if cont_comp:
        linies["contracant"] = cont_comp

    construides = []
    for i, r in enumerate(rols):
        if r.instr.percussio:
            construides.append((r, [rol_percussio(compassos, segs, r.instr, curs, estil)], None))
            continue
        evs_i: list[Ev] = []
        marques = []
        si = 0
        while si < n:
            f = seccions[si].funcions[i]
            sj = si
            while sj + 1 < n and seccions[sj + 1].funcions[i] == f:
                sj += 1
            a, b = seccions[si].ini, seccions[sj].fi
            if f == "melodia":
                if i == idx_mel:
                    evs_i += _retalla(e_m, a, b)
                else:
                    for q in range(si, sj + 1):
                        evs_i += mel_sec[(q, i)]
                if si > 0:
                    marques.append(seccions[si].i0)
            else:
                evs_i += _retalla(linia(i, f), a, b)
            si = sj + 1
        evs_i.sort(key=lambda e: e.ini)
        evs_i, resp = gravat.respiracions(evs_i, [(q.ini, q.fi, q.funcions[i]) for q in seccions], r.instr,
                                          compassos, es_elemental(curs), _permet_corxeres(r.instr, curs))
        if r.instr.clau == "piano":
            dreta = [Ev(x.ini, x.dur, [p for p in x.alt if p.midi >= 60]) for x in evs_i]
            esquerra = [Ev(x.ini, x.dur, [p for p in x.alt if p.midi < 60]) for x in evs_i]
            construides.append((r, [part_des_de_evs(dreta, compassos, stream.PartStaff),
                                    part_des_de_evs(esquerra, compassos, stream.PartStaff)], evs_i))
            continue
        part = part_des_de_evs(evs_i, compassos)
        gravat.marca_respiracions(part, resp)
        ms = list(part.getElementsByClass(stream.Measure))
        for ci in marques:
            te = expressions.TextExpression("melodia")
            te.placement = "above"
            te.style.fontStyle = "italic"
            ms[ci].insert(0, te)
        construides.append((r, [part], evs_i))
    return construides, linies, baix_ref


def _construir_fix(rols, segs, compassos, evs, curs, estil, k, bordo, informe):
    """Les parts amb cada rol sempre en el mateix instrument (el comportament de sempre, amb --sense-rotacio)."""
    construides: list = []
    linies: dict[str, list[Ev]] = {}
    frases = dividir_seccions(compassos, evs, segs, k)    # per a les respiracions dels vents
    elem = es_elemental(curs)
    for r in rols:
        if r.rol == "melodia":
            e, sh = rol_melodia(evs, r.instr, curs)
            linies.setdefault("melodia", e)
            e, resp = gravat.respiracions(e, [(q.ini, q.fi, "melodia") for q in frases], r.instr, compassos, elem,
                                          _permet_corxeres(r.instr, curs))
            if sh:
                informe.append(f"{r.instr.nom}: melodia {abs(sh) // 12} octava{'es' if abs(sh) > 12 else ''} "
                               f"{'amunt' if sh > 0 else 'avall'} perquè caiga en la zona còmoda.")
            pm = part_des_de_evs(e, compassos)
            gravat.marca_respiracions(pm, resp)
            construides.append((r, [pm], e))
    baix_ev = None
    acomp_rol = next((r for r in rols if r.rol == "acompanyament"), None)
    for r in rols:
        if r.rol == "baix":
            e = rol_baix(segs, r.instr, curs, estil, k)
            baix_ev = baix_ev or e
            construides.append((r, [part_des_de_evs(e, compassos)], e))
    for r in rols:
        if r.rol == "acompanyament":
            e, baixos = rol_acompanyament(segs, r.instr, curs, estil, k, bordo, linies.get("melodia"), None,
                                          baix_ev is not None)
            if baix_ev is None and baixos and r is acomp_rol:
                baix_ev = baixos
            if r.instr.clau == "piano":
                # piano en dos pentagrames: mà dreta (de Do3 amunt) i mà esquerra
                dreta = [Ev(x.ini, x.dur, [p for p in x.alt if p.midi >= 60]) for x in e]
                esquerra = [Ev(x.ini, x.dur, [p for p in x.alt if p.midi < 60]) for x in e]
                construides.append((r, [part_des_de_evs(dreta, compassos, stream.PartStaff),
                                        part_des_de_evs(esquerra, compassos, stream.PartStaff)], e))
            else:
                construides.append((r, [part_des_de_evs(e, compassos)], e))
    for r in rols:
        if r.rol == "contracant":
            e = rol_contracant(linies["melodia"], segs, r.instr, curs, k, baix_ev)
            linies.setdefault("contracant", e)
            e, resp = gravat.respiracions(e, [(q.ini, q.fi, "contracant") for q in frases], r.instr, compassos, elem,
                                          _permet_corxeres(r.instr, curs))
            pc = part_des_de_evs(e, compassos)
            gravat.marca_respiracions(pc, resp)
            construides.append((r, [pc], e))
    for r in rols:
        if r.rol == "percussio":
            construides.append((r, [rol_percussio(compassos, segs, r.instr, curs, estil)], None))
    return construides, linies, baix_ev


# --------------------------------------------------------------------------- ordre principal

def _posar_cues(construides, curs, seccions, rols, absents: bool = False) -> list:
    """Cues d'orientació i, si es demana, d'instrument absent (paquet 12). La lògica és a `cues.py`.
    Les d'instrument absent omplin molts silencis: només amb `--cues-absents` (conjunt incomplet)."""
    rang = lambda instr: _rang_concert(instr, curs)
    fetes = cues.cues_orientacio(construides, rang, es_elemental(curs), seccions, rols)
    if absents:
        fetes += cues.cues_absents(construides, rang, seccions, rols, article=_amb_article)
    return fetes


def arranjar(score: stream.Score, rols: list[Rol], estil: str | None = None, curs: str | None = None,
             compassos_sel: tuple[int, int] | None = None, melodia_part: int | None = None,
             a_tonalitat: str | None = None, simplifica: bool = False, bordo: bool = False,
             rotacio: bool = True, tutti_final: bool = False, intro: bool = False,
             coda: bool = False, harmonia: str = "auto",
             cues_absents: bool = False) -> tuple[stream.Score, list[str]]:
    informe: list[str] = []
    avisos_acords: list[str] = []
    md0 = score.metadata
    titol = (md0.title or md0.movementName if md0 else None) or "Arranjament"
    compositor = score.metadata.composer if score.metadata else None
    if compassos_sel:
        a, b = compassos_sel
        nums = [m.number for m in score.parts[0].getElementsByClass(stream.Measure)]
        if nums and (a > max(nums) or b < min(nums)):
            raise ErrorUsuari(f"La partitura va del compàs {min(nums)} al {max(nums)}: els compassos {a}-{b} no hi són.")
        score = score.measures(a, b)
    idx_mel = _triar_melodia(score, melodia_part)
    staff = score.parts[idx_mel]
    compassos = _compassos(staff)
    if not compassos:
        raise ErrorUsuari("No trobe compassos en la partitura.")
    if a_tonalitat:
        desti = parse_tonalitat(a_tonalitat)
        evs0 = _linia_superior(staff)
        segs0 = _segments(compassos, [])
        simb0 = _simbols(score)
        if simb0:
            acords_de_simbols(simb0, segs0, evs0, key.Key("C"), [])
        ara = analitzar_tonalitat(evs0, segs0, score, bool(simb0))
        if ara.mode != desti.mode:
            raise ErrorUsuari(f"La peça està en mode {musica._MODES.get(ara.mode, ara.mode)} "
                              f"({musica.nom_alteracio(ara.tonic)}); tria una tonalitat del mateix mode.")
        st = (desti.tonic.pitchClass - ara.tonic.pitchClass) % 12
        st = st - 12 if st > 6 else st
        if st:
            score = musica.transportar(score, semitons=st)
            staff = score.parts[idx_mel]
            compassos = _compassos(staff)
            informe.append(f"He transportat {st:+d} semitons (de {_nom_k(ara)} a {_nom_k(desti)}).")
    evs = _linia_superior(staff)
    if not any(e.alt for e in evs):
        raise ErrorUsuari("La part triada com a melodia no té notes en estos compassos.")
    if estil is None:
        estil = "vals" if compassos[0].ts.ratioString == "3/4" else "marxa" if compassos[0].ts.ratioString in ("2/4", "6/8") else "pop"
        informe.append(f"Estil: {estil} (no l'has dit; el trie pel compàs).")
    elif estil not in ESTILS:
        raise ErrorUsuari(f"No conec l'estil «{estil}». Estils: {', '.join(ESTILS)}.")
    else:
        informe.append(f"Estil: {estil}.")

    simbols = _simbols(score)
    segs = _segments(compassos, [t for t, _ in simbols])
    altres = [k for k in _parts_amb_altura(score) if k != idx_mel] or any(
        len(n.pitches) > 1 for n in musica.notes_reals(staff))
    if simbols:
        acords_de_simbols(simbols, segs, evs, key.Key("C"), [])
        k = analitzar_tonalitat(evs, segs, score, True)
        acords_de_simbols(simbols, segs, evs, k, avisos_acords)
        font = "dels símbols d'acord de la partitura"
    elif altres:
        k = analitzar_tonalitat(evs, segs, score, False)
        inferir_de_veus(score, segs, k)
        font = "de les notes de totes les veus (acords deduïts)"
    else:
        k = analitzar_tonalitat(evs, segs, score, False)
        descripcio = harmonitzar(evs, segs, k, estil, curs, harmonia)
        font = f"de la melodia sola ({descripcio})"

    ks_orig = next(iter(staff.recurse().getElementsByClass(key.KeySignature)), None)
    ks_concert = key.KeySignature(k.sharps)
    if ks_orig is not None and ks_orig.sharps != k.sharps:
        informe.append(f"Tonalitat: {_nom_k(k)}. L'armadura original no hi quadra ({_alts(ks_orig.sharps)}): "
                       f"he posat la de {_nom_k(k)} ({_alts(k.sharps)}).")
    else:
        informe.append(f"Tonalitat: {_nom_k(k)}.")
    informe.append(f"Harmonia: ve {font}.")

    # ----- melodia de partida i nivell
    mel_rols = [r for r in rols if r.rol == "melodia"]
    if simplifica:
        f_ok = _figures_permeses(mel_rols[0].instr, curs)
        if f_ok is None:
            informe.append("No he simplificat el ritme: no sé quines figures toca este nivell "
                           f"({mel_rols[0].instr.clau}, {curs or 'sense curs'}). Desa-les amb «partitures nivell desa».")
        else:
            evs, canvis = simplificar_ritme(evs, compassos, f_ok)
            informe.append(f"He simplificat el ritme de la melodia a les figures del nivell ({canvis} llocs).")

    # ----- construcció
    construides: list[tuple[Rol, stream.Part, list[Ev] | None]] = []
    linies: dict[str, list[Ev]] = {}
    baix_ev = None
    pla: list[str] = []
    from . import forma
    extrems = None
    if rotacio:
        seccions = dividir_seccions(compassos, evs, segs, k, forma.bpm_de_la_partitura(score))
        notes_pla = planificar(rols, seccions, evs, curs, tutti_final)
        if intro or coda:
            extrems = forma.afegeix_extrems(compassos, segs, evs, k, intro, coda, seccions, rols, curs)
            informe += extrems["notes"]
        pla = text_pla(rols, seccions, notes_pla) + forma.text_frases(seccions)
        arranjar.pla = seccions
        construides, linies, baix_ev = _construir_rotacio(rols, seccions, segs, compassos, evs, curs, estil, k, bordo,
                                                          informe)
    else:
        arranjar.pla = []
        seccions = dividir_seccions(compassos, evs, segs, k, forma.bpm_de_la_partitura(score))   # per a les lletres d'assaig
        if intro or coda:
            extrems = forma.afegeix_extrems(compassos, segs, evs, k, intro, coda, seccions, rols, curs)
            informe += extrems["notes"]
        construides, linies, baix_ev = _construir_fix(rols, segs, compassos, evs, curs, estil, k, bordo, informe)

    construides.sort(key=lambda x: _ordre(x[0]))
    if extrems and extrems["i_coda"] is not None:
        forma.decora_coda(construides, extrems["i_coda"])
    matisos = gravat.posa_matisos_i_articulacions(construides, rols, arranjar.pla, compassos, estil, es_elemental(curs))
    res = stream.Score()
    res.metadata = metadata.Metadata()
    res.metadata.title = f"{titol} (esborrany d'arranjament)"
    res.metadata.movementName = res.metadata.title
    res.metadata.composer = compositor or ""
    tempos = list(score.recurse().getElementsByClass(tempo.MetronomeMark))
    # els acords van damunt de la (primera) melodia, posats en so real ABANS d'escriure la part: si l'instrument
    # transporta, es transporten amb les notes (Fa -> Sol per a la trompeta en Sib, Fa -> Do per a la trompa en Fa)
    mel_simbols = next(r for r, _, _ in construides if r.rol == "melodia")
    cues_fetes = _posar_cues(construides, curs, seccions, rols, cues_absents)   # en so real: es transposen al vestir cada part
    for n, (r, pp, _) in enumerate(construides):
        if not r.instr.percussio:
            if r is mel_simbols:
                _posar_simbols(pp[0], segs, compassos)
            for p in pp:
                _vestir(p, r.instr, None, ks_concert)
            if len(pp) == 2:
                for p, cl in zip(pp, (clef.TrebleClef(), clef.BassClef())):
                    for c in list(p.recurse().getElementsByClass(clef.Clef)):
                        c.activeSite.remove(c)
                    p.getElementsByClass(stream.Measure).first().insert(0, cl)
        if n == 0 and tempos:
            pp[0].getElementsByClass(stream.Measure).first().insert(0, copy.deepcopy(tempos[0]))
        elif n == 0:
            pp[0].getElementsByClass(stream.Measure).first().insert(0, gravat.tempo_estil(estil, compassos[0].ts))
            informe.append(gravat.text_tempo(estil, compassos[0].ts))
        for p in pp:
            ult = p.getElementsByClass(stream.Measure).last()
            if ult.rightBarline is None:
                ult.rightBarline = bar.Barline("final")
            res.insert(0, p)
        if len(pp) > 1:
            res.insert(0, layout.StaffGroup(pp, name=r.instr.nom, abbreviation=r.instr.abreviatura, symbol="brace"))
    lletres = _parts.posar_lletres(construides[0][1][0], _parts.inicis_seccio(seccions), compassos[0].anacrusi)
    _parts.posar_claudators(res, _parts.grups_claudators([(r.instr.clau, pp) for r, pp, _ in construides]))
    _parts.desa_nivell(res, curs)

    # ----- informe
    informe += pla
    if lletres:
        informe.append(_parts.text_lletres(lletres, compassos))
    if cues_fetes:
        informe.append("Cues (notes petites):")
        informe += cues.text_cues(cues_fetes)
    informe += _text_acords(segs, compassos)
    informe += avisos_acords
    informe.append("Parts:")
    for r, pp, _ in construides:
        informe.append(f"  {r.instr.nom} ({_NOM_ROL[r.rol]})")
        if r.instr.percussio:
            informe.append("   Percussió sense altura: " + _desc_percussio(r.instr, estil))
        else:
            informe += _rang_text(pp, r.instr, curs)
        if curs:
            from . import nivells
            if _perfil(r.instr, curs) is None and r.instr.percussio:
                informe.append(f"   No tinc el perfil de {r.instr.clau} a {curs}: he usat figures senzilles (negres, i "
                               "corxeres només en pop i rock).")
            elif _perfil(r.instr, curs) is None:
                informe.append(f"   No tinc el perfil de {r.instr.clau} a {curs}: he usat una zona còmoda orientativa. "
                               f"Es pot desar amb «partitures nivell desa --instrument {r.instr.clau} --curs \"{curs}\" ...».")
            else:
                c = nivells.comprova(r.instr, curs, pp)
                informe += nivells.text_comprovacio(c)
    if not curs:
        informe.append("Sense nivell: he usat les zones còmodes del catàleg (orientatives).")
    elif es_elemental(curs) and any(_perfil(r.instr, curs) is None for r, _, _ in construides if not r.instr.percussio):
        informe.append(f"Sense perfil de «{curs}»: per prudència he limitat la zona còmoda de cada instrument als dos "
                       "terços de baix de la del catàleg. És orientatiu: desa el perfil real amb «partitures nivell desa».")
    informe.append("Comprovacions:")
    par = []
    if "contracant" in linies:
        par += [(c, t, "melodia") for c, t in paral_leles(linies["contracant"], linies["melodia"], compassos)]
        if baix_ev:
            par += [(c, t, "baix") for c, t in paral_leles(linies["contracant"], baix_ev, compassos)]
    if par:
        informe.append("  Quintes o octaves paral·leles del contracant: " + "; ".join(
            f"compàs {c} ({t} amb {amb})" for c, t, amb in sorted(set(par))[:12]))
    elif "contracant" in linies:
        informe.append("  Quintes o octaves paral·leles del contracant: cap.")
    buits = []
    primer_acord = next((s.compas.num for s in segs if s.acord is not None and not s.compas.anacrusi
                         and s.acord.origen != "forma"), None)
    inici = sorted({c.num for c in compassos if primer_acord is not None and c.num < primer_acord})
    for r, pp, _ in construides:
        b = sorted(set.intersection(*[set(compassos_buits(p)) for p in pp]) - set(inici))
        inc = sorted({x for p in pp for x in compassos_incomplets(p, compassos)})
        if inc:
            buits.append(f"{r.instr.nom}: compassos incomplets {_llista_nums(inc)}")
        if b:
            buits.append(f"{r.instr.nom} en silenci als compassos {_llista_nums(b)}")
    informe.append("  Compassos buits o incomplets: " + ("; ".join(buits) if buits else "cap."))
    if inici:
        informe.append(f"  Abans del primer acord (compàs {_llista_nums(inici)}) només toca la melodia.")
    informe.append("Revisa-ho amb MuseScore: és un esborrany.")
    return res, informe


arranjar.pla = []   # les frases (Seccio) de l'última crida: qui porta la melodia a cadascuna

_NOM_ROL = {"melodia": "melodia", "contracant": "contracant", "acompanyament": "acompanyament", "baix": "baix",
            "percussio": "percussió"}


def _desc_percussio(instr, estil) -> str:
    if instr.clau == "bateria":
        return ("bombo (espai de baix), caixa (tercer espai) i charles (creu damunt del pentagrama); "
                f"patró senzill d'estil {estil}, i plat i bombo a l'últim compàs.")
    if instr.clau == "caixa":
        return "caixa a cada temps."
    return "un cop als temps forts."


def _nom_k(k: key.Key) -> str:
    return f"{musica.nom_alteracio(k.tonic)} {musica._MODES.get(k.mode, k.mode)}"


def _alts(n: int) -> str:
    if n == 0:
        return "sense alteracions"
    return f"{abs(n)} {'sostingut' if n > 0 else 'bemoll'}{'s' if abs(n) > 1 else ''}"


def _posar_simbols(part: stream.Part, segs: list[Segment], compassos: list[Compas]) -> None:
    ant = None
    ms = list(part.getElementsByClass(stream.Measure))
    for s in segs:
        if s.acord is None:
            continue
        if ant is not None and ant == s.acord.figura and abs(s.ini - s.compas.ini) > _EPS:
            continue
        if ant == s.acord.figura and abs(s.ini - s.compas.ini) < _EPS:
            ant = s.acord.figura
            continue
        i = compassos.index(s.compas)
        cs = harmony.ChordSymbol(s.acord.figura)
        cs.writeAsChord = False
        ms[i].insert(opFrac(s.ini - s.compas.ini), cs)
        ant = s.acord.figura


def _text_acords(segs: list[Segment], compassos: list[Compas]) -> list[str]:
    ll = ["Acords (* = proposat o deduït per l'eina; en la partitura van en lletres: C=Do, D=Re, E=Mi, F=Fa, "
          "G=Sol, A=La, B=Si, b=bemoll):"]
    per = []
    for c in compassos:
        meus = [s for s in segs if s.compas is c]
        noms = []
        for s in meus:
            if s.acord is None:
                noms.append("-")
            else:
                noms.append(s.acord.nom() + ("*" if s.acord.origen != "partitura" else ""))
        # mig compàs repetit: un sol nom
        if len(noms) == 2 and noms[0] == noms[1]:
            noms = noms[:1]
        per.append((c.num, " ".join(noms)))
    for i in range(0, len(per), 4):
        grup = per[i:i + 4]
        ll.append(f"  c. {grup[0][0]}-{grup[-1][0]}: " + " | ".join(x[1] for x in grup))
    return ll
