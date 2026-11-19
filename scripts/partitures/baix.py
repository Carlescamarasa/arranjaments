"""Baix amb personalitat: inversions per grau conjunt, aproximació a l'acord següent i baix caminant.

Lògica del paquet 5. `arranjador.rol_baix_viu` la crida i només embolica el resultat en `Ev`. Aquest mòdul no
importa `arranjador` (evita cicles) i treballa amb números MIDI: `linia(...)` torna `(inici, durada, midi)`.

Què fa, segons el nivell del curs:
  elemental   no s'usa (el baix senzill de sempre: arrel i quinta)
  mitjà       inversions quan milloren la línia (3a, i 5a només cadencial, de pas o després de IV), aproximació
              diatònica a l'acord següent, baix caminant en swing amb notes de l'acord
  avançat     a més: 7a al baix en acords de sèptima, aproximació cromàtica, caminant amb notes de pas de l'escala

Fonts (ids dels resums): Herrera BAX-01 a BAX-03, Perricone R65 i R66, Zamacois Q07, EN01 i HA09 (baix per grau
conjunt, 6/4 limitat), Levine BX06 (símbol amb barra).
El baix caminant no el desenvolupa cap dels llibres (Levine BX01 ho avisa): és [inferència] a partir del
esbós de Herrera BAX-01 (arrel, 3a, 5a, aproximació). Vegeu `referencies/arranjar/baix-que-camina.md`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from music21 import pitch
from music21.common.numberTools import opFrac

from . import instruments as inst

_EPS = 1e-6

# --------------------------------------------------------------------------- paràmetres ajustables ([inferència])

# cost d'un salt del baix: (semitons com a màxim, cost). Els graus conjunts (fins a 2 semitons) no costen res.
COST_SALT = ((2, 0.0), (4, 1.0), (7, 2.5), (12, 5.0))
COST_SALT_GRAN = 9.0
COST_SALT_OCTAVA_CADENCIA = 0.5     # salt d'octava just en una cadència dominant a tònica
PES_FUNCIO = {"R": 0.0, "3": 1.2, "5": 2.0, "7": 2.5}      # preferència per l'arrel, després la 3a, 5a i 7a
COST_INVERSIO_LLARGA = 3.0          # inversió en un acord de més d'un compàs
COST_INVERSIO_REPETIDA = 8.0        # dues inversions seguides a la mateixa inversió (BAX-03)
COST_TERCERA_A_LA_MELODIA = 10.0    # la 3a al baix quan la melodia ja hi és (BAX-03)
COST_MOVIMENT_CONTRARI = -0.8       # premi si baix i melodia van en sentit contrari (R65)
COST_MOVIMENT_PARAL = 0.4
COST_PARAL_LLELES = 1.5             # 5a o 8a entre baix i melodia movent-se en paral·lel
COST_REGISTRE = 0.15                # per semitò per damunt de la sisena més greu: el baix prefereix el greu (BAX-04)
COST_MATEIXA_NOTA = 0.5             # el mateix so en dos acords diferents (HA09)
COST_REPETIDA_CAMINANT = 6.0        # dos temps seguits a la mateixa nota en el caminant
COST_ANADA_TORNADA = 1.5            # F A F: tornar a la nota de dos temps abans
COST_CANVI_DIRECCIO = 0.6           # la línia prefereix continuar en el mateix sentit
PROIBIT = 1e6

ESTILS_AMB_INVERSIONS = ("ragtime", "marxa", "pop", "vals", "classic")
ESTILS_CAMINANTS = ("swing",)


# --------------------------------------------------------------------------- nivell

def nivell(curs: str | None) -> str:
    """«elemental», «mitja» (sense curs o curs mitjà) o «avancat» (professional, superior)."""
    t = inst._norm(curs or "")
    if any(x in t for x in ("elemental", "inicia", "primaria", "basic")):
        return "elemental"
    if any(x in t for x in ("professional", "superior", "avanc")):
        return "avancat"
    return "mitja"


# --------------------------------------------------------------------------- l'acord, nota per nota

@dataclass
class Pas:
    seg: object
    arrel: int
    tons: dict            # funció ("R", "3", "5", "7") -> classe d'altura
    barra: int | None     # classe d'altura del baix d'un símbol amb barra (C/E), si n'hi ha
    es_dom: bool = False


_RE_BARRA = re.compile(r"/([A-G][#b\-]*)$")


def _tons(acord) -> dict:
    pcs = tuple(acord.pcs)
    r = pcs[0]
    iv = {(p - r) % 12: p for p in pcs}
    tons = {"R": r}
    t = iv.get(3, iv.get(4))
    if t is not None:
        tons["3"] = t
    q = iv.get(7, iv.get(6, iv.get(8)))
    if q is not None:
        tons["5"] = q
    if len(pcs) >= 4:
        s = iv.get(10, iv.get(11, iv.get(9)))
        if s is not None:
            tons["7"] = s
    return tons


def _barra(acord) -> int | None:
    m = _RE_BARRA.search(acord.figura or "")
    if not m:
        return None
    try:
        return pitch.Pitch(m.group(1).replace("b", "-")).pitchClass
    except Exception:
        return None


def _veu(pc: int, lo: int, prev: int | None, marge: int) -> int:
    opcions = [m for m in range(lo, lo + marge) if m % 12 == pc]
    if not opcions:
        opcions = [lo + ((pc - lo) % 12)]
    if prev is None:
        return opcions[0]
    return min(opcions, key=lambda m: (abs(m - prev), m))


def _cost_salt(d: int, octava_cadencia: bool = False) -> float:
    d = abs(d)
    if d == 12 and octava_cadencia:
        return COST_SALT_OCTAVA_CADENCIA
    for maxim, cost in COST_SALT:
        if d <= maxim:
            return cost
    return COST_SALT_GRAN


# --------------------------------------------------------------------------- tria d'inversions (programació dinàmica)

def _sis_quatre_permes(pas: list[Pas], i: int, estil: str, tonica: int) -> bool:
    """El 6/4 només és cadencial (I abans de V), de pas, o després de IV en pop i ragtime (Q07, BAX-03)."""
    p = pas[i]
    dom, sub = (tonica + 7) % 12, (tonica + 5) % 12
    prev = pas[i - 1] if i > 0 else None
    seg = pas[i + 1] if i + 1 < len(pas) else None
    if p.arrel == tonica and seg is not None and seg.arrel == dom:
        return True
    if estil in ("pop", "ragtime") and p.arrel == tonica and prev is not None and prev.arrel == sub:
        return True
    q = p.tons.get("5")
    if q is not None and prev is not None and seg is not None:
        a, b = (q - prev.arrel) % 12, (seg.arrel - q) % 12
        c, d = (prev.arrel - q) % 12, (q - seg.arrel) % 12
        if (a in (1, 2) and b in (1, 2)) or (c in (1, 2) and d in (1, 2)):
            return True
    return False


def _candidats(pas: list[Pas], i: int, estil: str, niv: str, tonica: int, lo: int, marge: int,
               ultim: bool, melodia_pc) -> list[tuple[int, str]]:
    """Notes possibles al baix d'aquest acord: (midi, funció)."""
    p = pas[i]
    dom = (tonica + 7) % 12
    funcions = ["R"]
    if p.barra is not None:                 # símbol amb barra: el baix el mana (Levine BX06)
        funcions = [f for f, pc in p.tons.items() if pc == p.barra] or ["B"]
    elif i > 0 and not ultim and estil in ESTILS_AMB_INVERSIONS:
        seg = pas[i + 1] if i + 1 < len(pas) else None
        cadencia_dom = p.arrel == dom and seg is not None and seg.arrel == tonica
        cadencia_tonica = p.arrel == tonica and pas[i - 1].arrel == dom
        if not (cadencia_dom or cadencia_tonica):    # la cadència V-I, sempre en estat fonamental
            if "3" in p.tons:
                funcions.append("3")
            if "5" in p.tons and _sis_quatre_permes(pas, i, estil, tonica):
                funcions.append("5")
            if niv == "avancat" and "7" in p.tons:
                funcions.append("7")
    res = []
    for f in funcions:
        pc = p.barra if f == "B" else p.tons[f]
        for m in range(lo, lo + marge):
            if m % 12 == pc:
                res.append((m, f))
    if not res:
        res = [(_veu(p.tons["R"], lo, None, marge), "R")]
    return res


def _registre(midi: int, lo: int) -> float:
    return COST_REGISTRE * max(0, midi - (lo + 8))


def _cost_unari(pas: list[Pas], i: int, f: str, midi: int, melodia_pc) -> float:
    c = PES_FUNCIO.get(f, 0.0)
    s = pas[i].seg
    if f != "R" and s.fi - s.ini > s.compas.dur + _EPS:
        c += COST_INVERSIO_LLARGA        # un acord que dura més d'un compàs, millor en estat fonamental
    mel = melodia_pc(pas[i].seg.ini) if melodia_pc else None
    if f == "3" and mel is not None and mel % 12 == midi % 12:
        c += COST_TERCERA_A_LA_MELODIA
    return c


def _cost_parell(pas: list[Pas], i: int, a: tuple[int, str], b: tuple[int, str], melodia_midi,
                 tonica: int) -> float:
    """Cost de passar del baix `a` (acord i-1) al baix `b` (acord i)."""
    d = b[0] - a[0]
    cadencia = pas[i - 1].arrel == (tonica + 7) % 12 and pas[i].arrel == tonica
    c = _cost_salt(d, octava_cadencia=cadencia)
    if a[1] == b[1] and a[1] != "R":
        c += COST_INVERSIO_REPETIDA
    if d == 0 and pas[i - 1].arrel != pas[i].arrel:
        c += COST_MATEIXA_NOTA
    if melodia_midi:
        m0, m1 = melodia_midi(pas[i - 1].seg.ini), melodia_midi(pas[i].seg.ini)
        if m0 is not None and m1 is not None and m1 != m0 and d != 0:
            if (m1 - m0) * d < 0:
                c += COST_MOVIMENT_CONTRARI
            else:
                c += COST_MOVIMENT_PARAL
                if (m0 - a[0]) % 12 in (0, 7) and (m1 - b[0]) % 12 in (0, 7):
                    c += COST_PARAL_LLELES
    return c


def tria_inversions(pas: list[Pas], estil: str, niv: str, tonica: int, lo: int, marge: int,
                    melodia_midi=None) -> list[tuple[int, str]]:
    """Per a cada acord, el baix (midi, funció) que dona la línia més suau. Determinista."""
    mel_pc = melodia_midi
    n = len(pas)
    cands = [_candidats(pas, i, estil, niv, tonica, lo, marge, i == n - 1, mel_pc) for i in range(n)]
    cost = [[_cost_unari(pas, 0, f, m, mel_pc) + _registre(m, lo) for m, f in cands[0]]]
    enrere: list[list[int]] = [[]]
    for i in range(1, n):
        fila, ref = [], []
        for b in cands[i]:
            millor = min(range(len(cands[i - 1])),
                         key=lambda j: (cost[i - 1][j] + _cost_parell(pas, i, cands[i - 1][j], b, melodia_midi, tonica), j))
            fila.append(cost[i - 1][millor] + _cost_parell(pas, i, cands[i - 1][millor], b, melodia_midi, tonica)
                        + _cost_unari(pas, i, b[1], b[0], mel_pc) + _registre(b[0], lo))
            ref.append(millor)
        cost.append(fila)
        enrere.append(ref)
    j = min(range(len(cands[-1])), key=lambda x: (cost[-1][x], x))
    tria = [None] * n
    for i in range(n - 1, -1, -1):
        tria[i] = cands[i][j]
        if i:
            j = enrere[i][j]
    return tria


# --------------------------------------------------------------------------- notes dins de cada acord

def _aproximacio(objectiu: int, prev: int, niv: str, escala: set[int], lo: int, hi: int) -> int:
    """Nota a un semitò (avançat) o a un grau de l'escala (mitjà) per damunt o per davall de l'objectiu."""
    if niv == "avancat":
        opts = [objectiu - 1, objectiu + 1]
    else:
        opts = [next((objectiu - d for d in (1, 2) if (objectiu - d) % 12 in escala), objectiu - 1),
                next((objectiu + d for d in (1, 2) if (objectiu + d) % 12 in escala), objectiu + 1)]
    opts = [o for o in opts if lo <= o <= hi] or opts
    return min(opts, key=lambda m: (abs(m - prev), m))


def _caminant_mig(inici: int, fi: int, nbeats: int, pcs_forts: set[int], pcs_febles: set[int],
                  lo: int, hi: int) -> list[int]:
    """Notes dels temps entre el primer (`inici`) i l'aproximació (`fi`): la ruta més suau i amb direcció.
    `nbeats` = temps del mig. Programació dinàmica de segon ordre per evitar l'anada i tornada (F A F A)."""
    if nbeats <= 0:
        return []
    pools = []
    for b in range(1, nbeats + 1):
        pcs = pcs_forts if b % 2 == 0 else (pcs_forts | pcs_febles)      # el temps 3 (b=2) només notes de l'acord
        pools.append([m for m in range(lo, hi + 1) if m % 12 in pcs] or [inici])

    def pas(a2, a1, m):
        c = _cost_salt(m - a1) + (COST_REPETIDA_CAMINANT if m == a1 else 0.0)
        if a2 is not None and m == a2:
            c += COST_ANADA_TORNADA
        elif a2 is not None and (a1 - a2) * (m - a1) < 0:
            c += COST_CANVI_DIRECCIO
        return c

    estats = {(None, inici): 0.0}
    enrere: list[dict] = []
    for pool in pools:
        nous: dict = {}
        ref: dict = {}
        for est, c0 in sorted(estats.items(), key=lambda x: (x[0][0] is not None, x[0])):
            for m in pool:
                c = c0 + pas(est[0], est[1], m)
                nou_est = (est[1], m)
                if nou_est not in nous or c < nous[nou_est] - 1e-9:
                    nous[nou_est] = c
                    ref[nou_est] = est
        estats = nous
        enrere.append(ref)
    est = min(estats, key=lambda e: (estats[e] + pas(e[0], e[1], fi), e))
    ruta = []
    for ref in reversed(enrere):
        ruta.append(est[1])
        est = ref[est]
    return ruta[::-1]


def _complement(t: str, base: str, tons: dict) -> str:
    """El so «altre» dins l'acord: la 5a (o la 3a) si el baix no ho és ja; si ho és, l'arrel."""
    if t == "5":
        return "5" if base in ("R", "3") and "5" in tons else "R"
    if t == "3":
        return "3" if base != "3" and "3" in tons else "R"
    return "R"


# --------------------------------------------------------------------------- la línia sencera

@dataclass
class Tram:
    """Uns quants segments consecutius amb el mateix acord, tractats com un de sol (el baix hi camina de debò)."""
    ini: float
    fi: float
    compas: object
    acord: object


def _agrupa(actius: list) -> list[Tram]:
    """Ajunta els segments contigus amb el mateix acord (les partitures els parteixen per mig compàs).
    L'últim segment queda sol: és la nota final."""
    trams: list[Tram] = []
    for idx, s in enumerate(actius):
        darrer = idx == len(actius) - 1
        if (trams and not darrer and abs(trams[-1].fi - s.ini) < _EPS and trams[-1].acord.figura == s.acord.figura
                and trams[-1].compas.pols == s.compas.pols and trams[-1].fi < s.fi):
            trams[-1].fi = s.fi
        else:
            trams.append(Tram(s.ini, s.fi, s.compas, s.acord))
    return trams


def linia(segs: list, estil: str, curs: str | None, lo: int, hi: int, marge: int, tonica: int, escala: set[int],
          melodia_midi=None, pols_a_corxeres: bool = False):
    """Baix amb inversions i aproximació. `segs` són els `Segment` de l'arranjador (amb `.acord`, `.compas`).

    Torna una llista de `(inici, durada, midi)`, o None si aquest estil/nivell no el fa servir (cal el baix de sempre).
    """
    niv = nivell(curs)
    if niv == "elemental" or estil == "rock":
        return None
    actius = _agrupa([s for s in segs if s.acord is not None and not s.compas.anacrusi])
    if not actius:
        return None
    pas = [Pas(s, s.acord.pcs[0], _tons(s.acord), _barra(s.acord)) for s in actius]
    cami = estil in ESTILS_CAMINANTS
    if cami:                                    # el caminant comença cada acord per l'arrel (BAX-01)
        pas_inv = [Pas(p.seg, p.arrel, p.tons, p.barra) for p in pas]
        estil_inv = "swing"
    else:
        pas_inv, estil_inv = pas, estil
    base = tria_inversions(pas_inv, estil_inv, niv, tonica, lo, marge, melodia_midi)
    res: list[tuple[float, float, int]] = []
    ultim = actius[-1]
    for j, s in enumerate(actius):
        p = pas[j]
        mid, fun = base[j]
        pols = s.compas.pols
        dur = opFrac(s.fi - s.ini)
        n = int(round(dur / pols))
        seg = actius[j + 1] if j + 1 < len(actius) and abs(actius[j + 1].ini - s.fi) < _EPS else None
        if s is ultim:
            res.append((s.ini, pols, mid))
            continue
        if n < 2 or abs(n * pols - dur) > _EPS:
            res.append((s.ini, dur, mid))
            continue
        canvi = seg is not None and pas[j + 1].arrel != p.arrel
        objectiu = base[j + 1][0] if seg is not None else None
        notes = _notes_del_segment(s, p, mid, fun, n, estil, niv, canvi, objectiu, pas, j, tonica, escala,
                                   lo, lo + marge - 1, marge, hi, pols)
        for b, m in enumerate(notes):
            res.append((opFrac(s.ini + b * pols), pols, m))
    return res


def _notes_del_segment(s, p, mid, fun, n, estil, niv, canvi, objectiu, pas, j, tonica, escala, lo, hi_eff,
                       marge, hi, pols) -> list[int]:
    tons = p.tons
    prev = mid
    notes = [mid]
    cadencia = p.arrel == (tonica + 7) % 12 and j + 1 < len(pas) and pas[j + 1].arrel == tonica

    def to(f):
        return _veu(tons[f] if f in tons else tons["R"], lo, prev, marge)

    if estil in ESTILS_CAMINANTS and abs(pols - 1.0) < _EPS and n >= 2:
        # baix caminant [inferència]: arrel, notes de l'acord o de pas, i aproximació a l'arrel següent
        if n == 2:
            notes.append(_aproximacio(objectiu, mid, niv, escala, lo, hi_eff) if canvi and objectiu is not None
                         else to("5"))
            return notes
        forts = {tons[f] for f in ("R", "3", "5", "7") if f in tons}
        febles = set(escala)           # notes de pas de l'escala, només als temps febles
        # l'últim temps s'aproxima sempre a l'arrel següent (també si l'acord no canvia: dona impuls a la línia)
        fi = _aproximacio(objectiu, mid, niv, escala, lo, hi_eff) if objectiu is not None else to("5")
        mig = _caminant_mig(mid, fi, n - 2, forts, febles, lo, hi_eff)
        return notes + mig + [fi]
    tipus: list[str]
    if estil in ("ragtime", "marxa"):
        tipus = ["R" if b % 2 == 0 else "5" for b in range(n)]
        if estil == "ragtime" and canvi:
            tipus[-1] = "A"
        if estil == "marxa" and cadencia and n >= 2:
            tipus[-1] = "8"
    elif estil == "swing":
        tipus = ["R"] + [("3", "5")[(b - 1) % 2] for b in range(1, n - 1)] + ["A" if canvi else "5"]
    elif estil == "pop":
        tipus = {2: ["R", "5"], 3: ["R", "5", "R"]}.get(n) or [("R", "R", "5", "R")[b % 4] for b in range(n)]
        if canvi:
            tipus[-1] = "A"
    elif estil == "vals":
        tipus = [("R", "5", "3")[b % 3] for b in range(n)]
    else:
        tipus = [("R", "5", "3", "5")[b % 4] for b in range(n)]
    for t in tipus[1:]:
        if t == "A" and objectiu is not None:
            x = _aproximacio(objectiu, prev, niv, escala, lo, hi_eff)
        elif t == "8":
            opts = [y for y in (mid - 12, mid + 12) if lo <= y <= hi]
            x = min(opts, key=lambda y: (abs(y - objectiu) if objectiu is not None else 0, y)) if opts else mid
        elif t == "R":
            # el baix torna a la seua nota (oom-pah), llevat que quede a més d'una quinta de l'última nota
            x = mid if abs(mid - prev) <= 7 else _veu(p.barra if fun == "B" else tons[fun], lo, prev, marge)
        else:
            f = _complement(t, fun, tons)
            x = _veu(tons.get(f, tons["R"]), lo, prev, marge)
        notes.append(x)
        prev = x
    return notes
