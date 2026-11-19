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

from music21 import (bar, chord, clef, harmony, instrument as m21i, key, layout, metadata, meter, note, percussion,
                     pitch, roman, stream, tempo, tie)
from music21.common.numberTools import opFrac

from . import instruments as inst
from . import musica
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


def harmonitzar(evs: list[Ev], segs: list[Segment], k: key.Key, estil: str) -> None:
    """Harmonització per regles amb programació dinàmica (sempre el mateix resultat)."""
    cands = _candidats_diatonics(k, "harmonitzat")
    jazz = estil in ("ragtime", "swing", "pop")
    actius = [i for i, s in enumerate(segs) if not s.compas.anacrusi]
    if not actius:
        return
    ordre_comp = {cid: n for n, (cid, _) in enumerate(sorted({id(segs[i].compas): segs[i].compas.ini
                                                              for i in actius}.items(), key=lambda x: x[1]))}

    def local(j, a: Acord) -> float:
        s = segs[actius[j]]
        val = 0.0
        for e, x, y in _notes_entre(evs, s.ini, s.fi):
            w = _pes(e, x, y, s)
            val += w if e.alt[0].pitchClass in a.pcs else -0.6 * w
        g = _grau(a, k)
        if a.te_septima:
            val += 0.2 if jazz else -0.2
        if j == 0 and g == 1 and not a.te_septima:
            val += 1.0
        if j == len(actius) - 1:
            val += 5.0 if (g == 1 and not a.te_septima) else -5.0
        if j == len(actius) - 2 and g == 5:
            val += 1.5
        n = ordre_comp[id(s.compas)]
        primer_del_compas = abs(s.ini - s.compas.ini) < _EPS
        if primer_del_compas and n % 8 == 7 and g == 1 and not a.te_septima:
            val += 0.8
        if n % 8 == 3 and g == 5 and not primer_del_compas:
            val += 0.5
        return val

    def trans(a: Acord, b: Acord) -> float:
        ga, gb = _grau(a, k), _grau(b, k)
        if a.figura == b.figura:
            return 0.1
        return _TRANSICIONS.get((ga, gb), 0.0)

    n = len(actius)
    punt = [[local(0, c) for c in cands]]
    enrere = [[None] * len(cands)]
    for j in range(1, n):
        fila, ptr = [], []
        for ci, c in enumerate(cands):
            loc = local(j, c)
            millor = max(range(len(cands)), key=lambda pi: (punt[-1][pi] + trans(cands[pi], c), -pi))
            fila.append(punt[-1][millor] + trans(cands[millor], c) + loc)
            ptr.append(millor)
        punt.append(fila)
        enrere.append(ptr)
    ci = max(range(len(cands)), key=lambda i: (punt[-1][i], -i))
    for j in range(n - 1, -1, -1):
        segs[actius[j]].acord = copy.copy(cands[ci])
        ci = enrere[j][ci] if enrere[j][ci] is not None else ci


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


_PATRONS = {
    # per cada estil: llista de tipus de pols per a 2, 3 i 4 temps. B=baix, C=acord, A=arpegi, c=acord en corxeres,
    # L=acord llarg (tot el segment)
    "ragtime": {2: "BC", 3: "BCC", 4: "BCBC"},
    "swing": {2: "BC", 3: "BCC", 4: "BCBC"},
    "marxa": {2: "BC", 3: "BCC", 4: "BCBC"},
    "vals": {2: "BC", 3: "BCC", 4: "BCCC"},
    "pop": {2: "AA", 3: "AAA", 4: "AAAA"},
    "rock": {2: "cc", 3: "ccc", 4: "cccc"},
    "classic": {2: "L-", 3: "L--", 4: "L-L-"},
}


def _veu_baixa(pc: int, lo: int, prev: int | None, marge: int = 12) -> int:
    opcions = [m for m in range(lo, lo + marge) if m % 12 == pc]
    if not opcions:
        opcions = [lo + ((pc - lo) % 12)]
    if prev is None:
        return opcions[0]
    return min(opcions, key=lambda m: (abs(m - prev), m))


def _disposicio(acord: Acord, n: int, lo: int, hi: int, prev: list[int] | None) -> list[int]:
    """Notes de l'acord per a la mà dreta (o les dues baquetes): tercera i quinta, o tercera i sèptima."""
    if n <= 1:
        pcs = [acord.pcs[1] if len(acord.pcs) > 1 else acord.pcs[0]]
    elif n == 2:
        pcs = [acord.pcs[1], acord.pcs[3]] if acord.te_septima else [acord.pcs[1], acord.pcs[2]]
    else:
        pcs = [acord.pcs[1], acord.pcs[3], acord.pcs[0]] if acord.te_septima else list(acord.pcs[:3])
    opcions = []
    for base in range(lo, hi + 1):
        if base % 12 not in pcs:
            continue
        nots = [base]
        for pc in pcs:
            if pc == base % 12:
                continue
            x = nots[-1] + 1
            while x % 12 != pc:
                x += 1
            nots.append(x)
        nots = sorted(nots)
        if nots[-1] <= hi and nots[-1] - nots[0] <= 9:
            opcions.append(nots)
    if not opcions:
        return [lo + ((pcs[0] - lo) % 12)]
    if prev is None:
        mig = (lo + hi) / 2
        return min(opcions, key=lambda v: (abs(sum(v) / len(v) - mig), v))
    return min(opcions, key=lambda v: (sum(abs(a - b) for a, b in zip(v, prev)) + abs(len(v) - len(prev)) * 3, v))


def rol_acompanyament(segs: list[Segment], instr: inst.Instrument, curs: str | None, estil: str, k: key.Key,
                      bordo: bool = False) -> tuple[list[Ev], list[Ev]]:
    """Patró de l'estil sobre els acords. Retorna (acompanyament, línia de baix que hi ha dins)."""
    lo, hi = _rang_concert(instr, curs)
    lo = min(max(lo, 43), hi - 12)
    hi = min(hi, lo + 30)
    n = _veus_acomp(instr)
    corxeres = _permet_corxeres(instr, curs)
    zona_baix_hi = lo + 11
    res: list[Ev] = []
    baixos: list[Ev] = []
    prev_v = None
    prev_b = None
    ultim = max((s.compas.ini for s in segs if s.acord), default=None)
    per_compas: dict[int, list[Segment]] = {}
    ordre = []
    for s in segs:
        if id(s.compas) not in per_compas:
            ordre.append(s.compas)
        per_compas.setdefault(id(s.compas), []).append(s)
    for c in ordre:
        meus = per_compas[id(c)]
        if c.anacrusi or all(s.acord is None for s in meus):
            continue
        n_pols = max(1, int(round(c.dur / c.pols)))
        if bordo:
            t = k.tonic.pitchClass
            ton = _veu_baixa(t, lo, None)
            v = [ton, ton + 7] if ton + 7 <= hi else [ton - 5, ton]
            res.append(Ev(c.ini, c.dur, [pitch.Pitch(midi=x) for x in v]))
            continue
        final = abs(c.ini - ultim) < _EPS
        patro = _PATRONS.get(estil, _PATRONS["pop"]).get(n_pols, "BC" * (n_pols // 2) + "B" * (n_pols % 2))
        if final:
            patro = "F" + "-" * (n_pols - 1)
        for b in range(n_pols):
            t = opFrac(c.ini + b * c.pols)
            s = next((x for x in meus if x.ini <= t + _EPS < x.fi), None)
            if s is None or s.acord is None:
                continue
            a = s.acord
            tipus = patro[b] if b < len(patro) else "-"
            if tipus == "-":
                continue
            primer_del_segment = abs(t - s.ini) < _EPS
            if tipus == "B":
                pc = a.pcs[0] if primer_del_segment or len(a.pcs) < 3 else a.pcs[2]
                prev_b = _veu_baixa(pc, lo, prev_b)
                res.append(Ev(t, c.pols, [pitch.Pitch(midi=prev_b)]))
                baixos.append(Ev(t, c.pols, [pitch.Pitch(midi=prev_b)]))
            elif tipus in ("C", "c", "L", "F"):
                v = _disposicio(a, n, max(lo, zona_baix_hi - 2, 60 if instr.clau == "piano" else 0) if n > 1 else lo,
                                hi, prev_v)
                prev_v = v
                if tipus == "L":
                    dur = opFrac(s.fi - t)
                    if n >= 3:
                        prev_b = _veu_baixa(a.pcs[0], lo, prev_b)
                        v = sorted(set([prev_b] + v))
                        baixos.append(Ev(t, dur, [pitch.Pitch(midi=prev_b)]))
                    res.append(Ev(t, dur, [pitch.Pitch(midi=x) for x in v]))
                elif tipus == "F":
                    prev_b = _veu_baixa(a.pcs[0], lo, prev_b)
                    tot = sorted(set(([prev_b] if n != 2 else []) + v))
                    res.append(Ev(t, c.pols, [pitch.Pitch(midi=x) for x in tot]))
                    baixos.append(Ev(t, c.pols, [pitch.Pitch(midi=prev_b)]))
                elif tipus == "c" and corxeres:
                    mig = opFrac(c.pols / 2)
                    res.append(Ev(t, mig, [pitch.Pitch(midi=x) for x in v]))
                    res.append(Ev(opFrac(t + mig), mig, [pitch.Pitch(midi=x) for x in v]))
                else:
                    res.append(Ev(t, c.pols, [pitch.Pitch(midi=x) for x in v]))
            elif tipus == "A":
                arp = [a.pcs[0], a.pcs[2] if len(a.pcs) > 2 else a.pcs[0], a.pcs[1], a.pcs[2] if len(a.pcs) > 2 else a.pcs[0]]
                if primer_del_segment:
                    prev_b = _veu_baixa(a.pcs[0], lo, prev_b)
                    baixos.append(Ev(t, c.pols, [pitch.Pitch(midi=prev_b)]))
                base = prev_b if prev_b is not None else _veu_baixa(a.pcs[0], lo, None)
                rel = int(round((t - s.ini) / c.pols))
                if corxeres and c.pols >= 1:
                    mig = opFrac(c.pols / 2)
                    for h, pc in enumerate(arp[(rel * 2) % 4:(rel * 2) % 4 + 2]):
                        x = base + ((pc - base) % 12) + (12 if h and pc == arp[0] else 0)
                        while x > hi:
                            x -= 12
                        res.append(Ev(opFrac(t + h * mig), mig, [pitch.Pitch(midi=x)]))
                else:
                    pc = arp[rel % 4]
                    x = base + ((pc - base) % 12)
                    res.append(Ev(t, c.pols, [pitch.Pitch(midi=x)]))
    return _ortografia(res, k, segs), _ortografia(baixos, k, segs)


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
                _ajunta_silencis(v)
            m.insert(0, v1)
            m.insert(0, v2)
        else:
            # caixa o percussió: una sola línia, a tots els temps (o als forts per a la percussió menuda)
            for b in range(n_pols):
                toca = (b == 0) if final else (instr.clau == "caixa" or b % 2 == 0 or n_pols <= 2)
                m.append(grup({"SN"}, c.pols) if toca else note.Rest(quarterLength=c.pols))
            _ajunta_silencis(m)
        part.append(m)
    return part


def _ajunta_silencis(v) -> None:
    """Silencis seguits en un de sol (més fàcil de llegir)."""
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
            if a > t + _EPS:
                m.append(note.Rest(quarterLength=opFrac(a - t)))
            if len(e.alt) == 1:
                x = note.Note(copy.deepcopy(e.alt[0]))
            else:
                x = chord.Chord([copy.deepcopy(q) for q in e.alt])
            x.quarterLength = opFrac(b - a)
            ve = e.ini < c.ini - _EPS
            va = e.fi > c.fi + _EPS
            if ve or va:
                x.tie = tie.Tie("continue" if ve and va else "stop" if ve else "start")
            m.append(x)
            t = b
        if t < c.fi - _EPS:
            m.append(note.Rest(quarterLength=opFrac(c.fi - t)))
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


ORDRE_FAMILIES = ["flauti", "flauta", "oboe", "corn-angles", "clarinet-sib", "clarinet-la", "clarinet-baix",
                  "clarinet-contrabaix", "saxo-soprano", "saxo-alt", "saxo-tenor", "saxo-bari", "fagot", "contrafagot",
                  "trompa-fa", "trompeta-sib", "trompeta-do", "fliscorn-sib", "trombo", "trombo-baix", "bombardi", "tuba",
                  "carillo", "xilofon", "xilofon-orff", "metalofon", "vibrafon", "marimba", "bateria", "caixa",
                  "percussio", "violi", "viola", "violoncel", "contrabaix", "guitarra", "piano"]


def _ordre(r: Rol) -> tuple:
    try:
        return (ORDRE_FAMILIES.index(r.instr.clau), ROLS.index(r.rol))
    except ValueError:
        return (len(ORDRE_FAMILIES), ROLS.index(r.rol))


# --------------------------------------------------------------------------- comprovacions

def paral_leles(a: list[Ev], b: list[Ev], compassos: list[Compas]) -> list[tuple[int, str]]:
    """Quintes i octaves paral·leles entre dues línies (en so real). Retorna (compàs, tipus)."""
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
                    c = next((c for c in compassos if c.ini <= t + _EPS < c.fi), None)
                    res.append((c.num if c else 0, "octaves" if i1 == 0 else "quintes"))
        ant = (x, y)
    return res


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


# --------------------------------------------------------------------------- ordre principal

def arranjar(score: stream.Score, rols: list[Rol], estil: str | None = None, curs: str | None = None,
             compassos_sel: tuple[int, int] | None = None, melodia_part: int | None = None,
             a_tonalitat: str | None = None, simplifica: bool = False, bordo: bool = False) -> tuple[stream.Score, list[str]]:
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
        harmonitzar(evs, segs, k, estil)
        font = "de la melodia sola (harmonització per regles: I, ii, IV, V, vi i cadència V-I)"

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
    for r in rols:
        if r.rol == "melodia":
            e, sh = rol_melodia(evs, r.instr, curs)
            linies.setdefault("melodia", e)
            if sh:
                informe.append(f"{r.instr.nom}: melodia {abs(sh) // 12} octava{'es' if abs(sh) > 12 else ''} "
                               f"{'amunt' if sh > 0 else 'avall'} perquè caiga en la zona còmoda.")
            construides.append((r, [part_des_de_evs(e, compassos)], e))
    baix_ev = None
    acomp_rol = next((r for r in rols if r.rol == "acompanyament"), None)
    for r in rols:
        if r.rol == "baix":
            e = rol_baix(segs, r.instr, curs, estil, k)
            baix_ev = baix_ev or e
            construides.append((r, [part_des_de_evs(e, compassos)], e))
    for r in rols:
        if r.rol == "acompanyament":
            e, baixos = rol_acompanyament(segs, r.instr, curs, estil, k, bordo)
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
            construides.append((r, [part_des_de_evs(e, compassos)], e))
    for r in rols:
        if r.rol == "percussio":
            construides.append((r, [rol_percussio(compassos, segs, r.instr, curs, estil)], None))

    construides.sort(key=lambda x: _ordre(x[0]))
    res = stream.Score()
    res.metadata = metadata.Metadata()
    res.metadata.title = f"{titol} (esborrany d'arranjament)"
    res.metadata.movementName = res.metadata.title
    res.metadata.composer = compositor or ""
    tempos = list(score.recurse().getElementsByClass(tempo.MetronomeMark))
    # els acords van damunt de la (primera) melodia, posats en so real ABANS d'escriure la part: si l'instrument
    # transporta, es transporten amb les notes (Fa -> Sol per a la trompeta en Sib, Fa -> Do per a la trompa en Fa)
    mel_simbols = next(r for r, _, _ in construides if r.rol == "melodia")
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
        for p in pp:
            ult = p.getElementsByClass(stream.Measure).last()
            if ult.rightBarline is None:
                ult.rightBarline = bar.Barline("final")
            res.insert(0, p)
        if len(pp) > 1:
            res.insert(0, layout.StaffGroup(pp, name=r.instr.nom, abbreviation=r.instr.abreviatura, symbol="brace"))

    # ----- informe
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
    primer_acord = next((s.compas.num for s in segs if s.acord is not None and not s.compas.anacrusi), None)
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
