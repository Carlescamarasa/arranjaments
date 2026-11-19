"""Harmonització de la melodia sola (paquet 10).

Quan la melodia no porta acords ni hi ha altres veus, l'eina els proposa per regles i programació dinàmica
(sempre el mateix resultat). Tres coses canvien segons el nivell i el tipus de melodia:

* Vocabulari d'acords: elemental només I, IV, V i vi; mitjà afegeix ii, iii i V7; avançat afegeix dominants
  secundaris (V7/V...), bVII i iv (intercanvi modal). Herrera NIV-01, REH-25, TEN-03, TEN-09.
* Ritme harmònic: un acord per compàs en elemental, el que dona el segment (dos en 4/4) en mitjà i avançat.
  Herrera INF-09, INF-11; un acord no canvia nota a nota, i una dominant no cau en part més feble que la
  seua resolució (HAR-03).
* Melodies modals i pentatòniques (sense sensible): no hi ha V7 ni cadència forçada; s'usen I, bVII, IV i v
  (Zamacois III, Z5-25 i Z5-26). Les notes de pas i de més durada curta pesen menys que les principals (INF-01)
  i un semitò entre la melodia i una nota de l'acord es castiga (INF-05).

Els paràmetres numèrics (pesos, llindars) són dades al capdamunt per a poder ajustar-los.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

from music21 import key, roman

from . import instruments as inst

NIVELLS = ("elemental", "mitja", "avancat")
MODES = ("auto", "simple", "modal")

# Vocabulari clàssic per mode de la tonalitat i nivell. Les llistes són cumulatives.
_MIT_MAJOR = ["I", "ii", "iii", "IV", "V", "V7", "vi"]
_MIT_MENOR = ["i", "iv", "V", "V7", "VI", "III", "VII"]
VOCABULARI = {
    "major": {"elemental": ["I", "IV", "V", "vi"], "mitja": _MIT_MAJOR,
              "avancat": _MIT_MAJOR + ["V7/V", "V7/ii", "V7/vi", "V7/IV", "bVII", "iv"]},
    "minor": {"elemental": ["i", "iv", "V", "VI"], "mitja": _MIT_MENOR,
              "avancat": _MIT_MENOR + ["V7/III", "V7/iv", "V7/VI"]},
}
# Vocabulari modal (sense sensible): I, bVII, IV i v (dòric i mixolidi), i VI, VII en menor natural.
VOCABULARI_MODAL = {"major": ["I", "IV", "bVII", "v"], "minor": ["i", "iv", "v", "VI", "VII", "III"]}
VOCABULARI_PENTATONIC = {"major": ["I", "IV", "V", "vi"], "minor": ["i", "iv", "v", "VI", "VII"]}
VOCABULARI_SIMPLE = {"major": ["I", "IV", "V"], "minor": ["i", "iv", "V"]}

# Cost fix de triar un acord poc habitual (REH-25: com més lluny de la tonalitat, més ha de valdre la pena)
COST_ACORD = {"iii": -0.5, "bVII": -0.4, "iv": -0.4, "III": -0.2, "VII": -0.3,
              "V7/V": -0.3, "V7/ii": -0.4, "V7/vi": -0.4, "V7/IV": -0.4, "V7/III": -0.4, "V7/iv": -0.4,
              "V7/VI": -0.4}
HOLD = {"elemental": 0.3, "mitja": 0.1, "avancat": 0.1}   # bonus per mantenir l'acord (no canviar nota a nota)
PES_SECUNDARIA = 0.4        # una nota curta fora de temps pesa menys que una principal (INF-01)
PENAL_FORA_FORT = 2.5       # nota principal de la melodia que no és de l'acord (en elemental i mitjà)
PENAL_FORA_FORT_AVANCAT = 1.5   # en avançat les tensions (2a i 6a sobre l'arrel) són més tolerables
PENAL_SEMITO = 1.5          # nota de la melodia a un semitò per damunt d'una nota de l'acord (INF-05)
PREMI_SENSIBLE = 1.5        # premi si la melodia porta una nota cromàtica d'un dominant secundari (la sensible)
PENAL_SENSE_SENSIBLE = 2.5  # penalització si no la porta (per tant, V7/x només amb eixa nota)
PENAL_DOMINANT_FEBLE = 1.0  # dominant en part més forta que la seua resolució (HAR-03)
FRASE_CADA = 4              # si no es veu cap final de frase, se suposa cada 4 compassos


@dataclass
class Cand:
    fig: str         # figura romana (V7/V, bVII...)
    acord: object    # arranjador.Acord
    tipus: str       # d diatònic, s dominant secundari, b préstec modal
    grau: int | None   # grau de l'arrel (diatònic) o del grau objectiu (secundari)
    cromatiques: frozenset = frozenset()   # notes de l'acord fora de l'escala: la melodia n'ha de portar alguna


def nivell_harmonic(curs: str | None) -> str:
    """elemental, mitja o avancat a partir del text del curs (sense curs: mitjà, el comportament de sempre)."""
    if not curs:
        return "mitja"
    from .arranjador import es_elemental
    t = inst._norm(curs)
    if es_elemental(curs):
        return "elemental"
    if any(x in t for x in ("professional", "superior", "avancat")):
        return "avancat"
    return "mitja"


def detecta_mode(evs, k: key.Key) -> str:
    """classic, modal (sense sensible i amb sèptima natural) o pentatonic (cinc notes) per la durada de cada nota."""
    pes: dict[int, float] = {}
    for e in evs:
        if e.alt:
            pc = e.alt[0].pitchClass
            pes[pc] = pes.get(pc, 0.0) + e.dur
    t = k.tonic.pitchClass
    if not pes:
        return "classic"
    sensible = pes.get((t - 1) % 12, 0) > 0
    sep_natural = pes.get((t + 10) % 12, 0) > 0
    if not sensible and sep_natural:
        return "modal"
    pent = {0, 2, 4, 7, 9} if k.mode == "major" else {0, 3, 5, 7, 10}
    if len(pes) >= 3 and {(pc - t) % 12 for pc in pes} <= pent:
        return "pentatonic"
    return "classic"


def _vocabulari(k: key.Key, nivell: str, mode: str, detectat: str) -> tuple[list[str], str]:
    """Llista de figures i nom del vocabulari triat."""
    m = "major" if k.mode == "major" else "minor"
    if mode == "simple":
        return VOCABULARI_SIMPLE[m], "simple"
    if mode == "modal" or detectat == "modal":
        return VOCABULARI_MODAL[m], "modal"
    if detectat == "pentatonic":
        return VOCABULARI_PENTATONIC[m], "pentatonic"
    return VOCABULARI[m][nivell], "classic"


def _candidats(k: key.Key, figs: list[str], origen: str, A) -> list[Cand]:
    res = []
    escala = [p.pitchClass for p in k.getScale().getPitches()[:7]]
    for f in figs:
        ac = A._acord_de_roman(f, k, origen)
        if f.startswith("V7/"):
            objectiu = f.split("/")[1]
            arrel = roman.RomanNumeral(objectiu, k).root().pitchClass
            grau = escala.index(arrel) + 1 if arrel in escala else None
            res.append(Cand(f, ac, "s", grau, frozenset(set(ac.pcs) - set(escala))))
        elif k.mode == "major" and f in ("bVII", "iv", "v"):
            res.append(Cand(f, ac, "b", None, frozenset(set(ac.pcs) - set(escala))))
        else:
            g = escala.index(ac.arrel.pitchClass) + 1 if ac.arrel.pitchClass in escala else None
            res.append(Cand(f, ac, "d", g))
    return res


_TRANS_MODAL = {(7, 1): 0.8, (4, 1): 0.6, (1, 7): 0.4, (5, 1): 0.4, (1, 4): 0.4, (7, 4): 0.5, (4, 7): 0.3,
                (6, 7): 0.4, (1, 5): 0.3, (7, 6): 0.3, (1, 6): 0.3, (5, 4): 0.2, (3, 7): 0.3}


def _finals_de_frase(evs, unitats, A) -> set[int]:
    """Índex (de la llista d'unitats) on acaba una frase: nota llarga, silenci posterior o cada FRASE_CADA compassos."""
    finals = set()
    notes = [e for e in evs if e.alt]
    for u, unitat in enumerate(unitats):
        s = unitat[-1]
        if abs(s.fi - (s.compas.ini + s.compas.dur)) >= A._EPS:   # no és l'últim segment del compàs
            continue
        dins = [e for e in notes if e.ini < s.fi - A._EPS and e.fi > s.ini + A._EPS]
        if not dins:
            continue
        ult = max(dins, key=lambda e: e.ini)
        seg_ini = min((e.ini for e in notes if e.ini >= s.fi - A._EPS), default=None)
        silenci = seg_ini is not None and seg_ini - ult.fi >= s.compas.pols / 2 - A._EPS
        llarga = ult.dur >= 2 * s.compas.pols - A._EPS and ult.fi >= s.fi - A._EPS
        if silenci or llarga:
            finals.add(u)
    return finals


def harmonitza(evs, segs, k: key.Key, estil: str, curs: str | None = None, mode: str = "auto") -> str | None:
    """Posa `seg.acord` a cada segment (menys l'anacrusi). Torna una frase que descriu què s'ha fet (per a l'informe)."""
    from . import arranjador as A
    if mode not in MODES:
        raise ValueError(f"mode d'harmonització desconegut: {mode}")
    nivell = "elemental" if mode == "simple" else nivell_harmonic(curs)
    actius = [i for i, s in enumerate(segs) if not s.compas.anacrusi]
    if not actius:
        return None
    detectat = detecta_mode(evs, k)
    figs, vocab = _vocabulari(k, nivell, mode, detectat)
    modal = vocab in ("modal", "pentatonic")
    cands = _candidats(k, figs, "harmonitzat", A)
    jazz = estil in ("ragtime", "swing", "pop")

    # unitats: en elemental (i simple) un acord per compàs; si no, un per segment
    if nivell == "elemental":
        grups: dict[int, list] = {}
        for i in actius:
            grups.setdefault(id(segs[i].compas), []).append(i)
        unitats_idx = sorted(grups.values(), key=lambda g: segs[g[0]].ini)
    else:
        unitats_idx = [[i] for i in actius]
    unitats = [[segs[i] for i in g] for g in unitats_idx]
    ordre_comp = {cid: n for n, (cid, _) in enumerate(sorted({id(s.compas): s.compas.ini for u in unitats for s in u}
                                                             .items(), key=lambda x: x[1]))}
    finals = _finals_de_frase(evs, unitats, A)
    fins_compassos = {ordre_comp[id(unitats[u][-1].compas)] for u in finals}
    n_u = len(unitats)
    tonica = k.tonic.pitchClass

    def notes_de(s):
        res = []
        for e, x, y in A._notes_entre(evs, s.ini, s.fi):
            w = A._pes(e, x, y, s)
            principal = A._pes(e, x, y, s) > (y - x) * 1.2 or (y - x) >= 1.5 * s.compas.pols - A._EPS
            res.append((e.alt[0].pitchClass, w if principal else w * PES_SECUNDARIA, principal))
        return res

    def melodia(s, c: Cand) -> float:
        a = c.acord
        val = 0.0
        presents = set()
        for pc, w, principal in notes_de(s):
            presents.add(pc)
            if pc in a.pcs:
                val += w
                continue
            val -= 0.6 * w
            if principal:
                tensio = (pc - a.arrel.pitchClass) % 12 in (2, 9)
                val -= w * (PENAL_FORA_FORT_AVANCAT if nivell == "avancat" and tensio else PENAL_FORA_FORT)
                if (pc - 1) % 12 in a.pcs:
                    val -= w * PENAL_SEMITO
            elif (pc - 1) % 12 in a.pcs:
                val -= w * PENAL_SEMITO * 0.3
        if c.tipus in ("s", "b") and c.cromatiques:
            val += PREMI_SENSIBLE if presents & c.cromatiques else -PENAL_SENSE_SENSIBLE
        return val

    def tonica_simple(c: Cand) -> bool:
        return c.grau == 1 and c.tipus == "d" and not c.acord.te_septima

    def local(u: int, c: Cand) -> float:
        unitat = unitats[u]
        val = sum(melodia(s, c) for s in unitat) + COST_ACORD.get(c.fig, 0.0)
        if c.acord.te_septima:
            val += 0.2 if jazz else -0.2
        s0 = unitat[0]
        if u == 0 and tonica_simple(c):
            val += 1.0
        if u == n_u - 1:
            val += 5.0 if tonica_simple(c) else -5.0
        if u == n_u - 2 and c.grau == 5 and c.tipus == "d" and not modal:
            val += 1.5
        n = ordre_comp[id(s0.compas)]
        primer = abs(s0.ini - s0.compas.ini) < A._EPS
        if primer and n % 8 == 7 and tonica_simple(c):
            val += 0.8
        if n % 8 == 3 and c.grau == 5 and c.tipus == "d" and not primer and not modal:
            val += 0.5
        if u in finals and u < n_u - 1 and not modal:
            ult = [pc for pc, _, p in notes_de(unitat[-1]) if p]
            if ult and ult[-1] in c.acord.pcs and c.tipus == "d" and c.grau in (1, 5):
                val += 0.6
        return val

    primers = [abs(unitats[u][0].ini - unitats[u][0].compas.ini) < A._EPS for u in range(n_u)]
    compas_de = [id(unitats[u][0].compas) for u in range(n_u)]

    def trans(u: int, a: Cand, b: Cand) -> float:
        """Cost d'anar de l'acord a (unitat u-1) al b (unitat u)."""
        if a.fig == b.fig:
            return HOLD[nivell]
        if a.tipus == "s":
            return 1.0 if (b.tipus == "d" and b.grau == a.grau) else -3.0
        v = 0.2 if b.tipus in ("s", "b") else 0.0
        if a.tipus == "b":
            v += 0.6 if (b.tipus == "d" and b.grau in (1, 5)) else 0.0
        elif b.tipus != "s" and b.tipus != "b":
            v += (_TRANS_MODAL if modal else A._TRANSICIONS).get((a.grau, b.grau), 0.0)
        dominant = a.tipus == "d" and a.grau == 5 and not modal
        if dominant and b.grau in (1, 6) and primers[u - 1] and not primers[u] and compas_de[u] == compas_de[u - 1]:
            v -= PENAL_DOMINANT_FEBLE
        return v

    punt = [[local(0, c) for c in cands]]
    enrere = [[None] * len(cands)]
    for j in range(1, n_u):
        fila, ptr = [], []
        for ci, c in enumerate(cands):
            loc = local(j, c)
            millor = max(range(len(cands)), key=lambda pi: (punt[-1][pi] + trans(j, cands[pi], c), -pi))
            fila.append(punt[-1][millor] + trans(j, cands[millor], c) + loc)
            ptr.append(millor)
        punt.append(fila)
        enrere.append(ptr)
    ci = max(range(len(cands)), key=lambda i: (punt[-1][i], -i))
    triats = []
    for j in range(n_u - 1, -1, -1):
        for i in unitats_idx[j]:
            segs[i].acord = copy.copy(cands[ci].acord)
        triats.append(cands[ci].fig)
        ci = enrere[j][ci] if enrere[j][ci] is not None else ci
    usats = [f for f in figs if f in triats]
    nom_nivell = {"elemental": "elemental", "mitja": "mitjà", "avancat": "avançat"}[nivell]
    if vocab == "modal":
        return (f"harmonització per regles, melodia modal (sense sensible): acords {', '.join(usats)}, "
                "sense V7 ni cadència forçada")
    if vocab == "pentatonic":
        return (f"harmonització per regles, melodia pentatònica: acords {', '.join(usats)}; "
                "un bordó (arrel i quinta) hi queda bé, prova --bordo")
    if vocab == "simple":
        return f"harmonització per regles, simple: un acord per compàs ({', '.join(usats)})"
    ritme = "un acord per compàs" if nivell == "elemental" else "fins a un acord per mig compàs"
    return f"harmonització per regles, nivell {nom_nivell} ({ritme}): acords {', '.join(usats)} i cadència V-I"
