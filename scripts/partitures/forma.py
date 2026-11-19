"""Frases i forma: on acaba cada frase, de quin tipus és (sentència, període o irregular) i, si es demana, una
introducció i una coda curtes fetes amb material de la pròpia melodia.

Tot és determinista. Regles de referència (ids dels digests): Schoenberg FR-01 a FR-14 (llargada, marques de final,
període, sentència), IN-01, CD-01 a CD-03 (introducció i coda); Perricone R04 a R07 (frase oberta o tancada per la nota
final), R48 i R76 (introducció amb un fragment de la melodia); Herrera INF-12 (cadències i puntuació).

Els llindars marcats [inferència] no surten d'un llibre: són ajustables i es poden calibrar amb peces reals.
"""
from __future__ import annotations

import copy
import difflib
from bisect import bisect_right

from music21 import expressions, key, pitch
from music21.common.numberTools import opFrac

_EPS = 1e-6

# --------------------------------------------------------------------------- constants ajustables
BPM_DEFECTE = 100.0           # negres per minut quan la partitura no diu el tempo [inferència]
COMPAS_RAPID_S = 1.5          # un compàs més curt que això (segons) fa les frases el doble de llargues [inferència]
COMPAS_LENT_S = 4.0           # un compàs més llarg que això fa les frases la meitat de llargues [inferència]
BASE_SIMPLE = 4               # compassos d'una frase en compàs simple (FR-01)
BASE_COMPOST = 2              # compassos d'una frase en compàs compost (FR-01)
LLINDAR_TALL = 2.0            # punts de marques perquè un final de frase conte com a «detectat» (FR-02) [inferència]
SIM_RITME = 0.85              # similitud rítmica per a «la mateixa idea» (FR-12) [inferència]
SIM_CONTORN = 0.70            # similitud de contorn melòdic (FR-12) [inferència]
BONUS_FORMA = 2.5             # punts a una frase que és sentència o període [inferència]
BONUS_REPETICIO = 1.0         # punts si el compàs següent comença com una frase anterior (repetició de material)
PES_REDUCCIO = 1.0            # el ritme s'asserena al final de la frase (FR-02)
PES_BAIXADA = 0.5             # la línia baixa al final
PES_GRAUS = 0.5               # l'últim interval és de grau conjunt
PES_TONICA = 1.0              # la frase acaba en la tònica amb cadència V-I
PES_SEMICADENCIA = 1.0        # la frase acaba en una nota del V i el compàs següent canvia d'acord
PENALITZACIO_CURTA = 1.2      # per compàs que falta respecte de la llargada ideal
PENALITZACIO_LLARGA = 0.5     # per compàs que passa de la llargada ideal
PENALITZACIO_DOBLE = 0.5      # una frase del doble de llargada (període o sentència de 8)
PECA_LLARGA = 6               # a partir de tantes frases ideals, les frases s'agrupen de dues en dues (com abans: 8 en 4/4)
GRUP_MIN = 1.5                # una secció agrupada té almenys tantes vegades la llargada ideal
FINAL_PECA = 3.0              # el final de la peça sempre és final de frase

INTRO_MAX_COMPASSOS = 4
NOTES_CEL_LA_MIN = 3          # un compàs amb tantes notes o més és una cèl·lula d'un sol compàs


def _arr():
    from . import arranjador
    return arranjador


# --------------------------------------------------------------------------- llargada de la frase
def es_compost(ts) -> bool:
    return ts.numerator in (6, 9, 12) and ts.denominator in (8, 16)


def llargada_frase(ts, bpm: float | None = None) -> int:
    """Compassos d'una frase segons la mètrica i el tempo: 4 en simple, 2 en compost, el doble si el compàs és molt
    ràpid i la meitat si és molt lent (FR-01)."""
    base = BASE_COMPOST if es_compost(ts) else BASE_SIMPLE
    segons = float(ts.barDuration.quarterLength) * 60.0 / (bpm or BPM_DEFECTE)
    if segons < COMPAS_RAPID_S:
        base *= 2
    elif segons > COMPAS_LENT_S and base > 2:
        base //= 2
    return base


def bpm_de_la_partitura(score) -> float | None:
    """Negres per minut de la primera marca de tempo (None si no n'hi ha)."""
    from music21 import tempo
    for m in score.recurse().getElementsByClass(tempo.MetronomeMark):
        try:
            q = m.getQuarterBPM()
        except Exception:
            q = None
        if q:
            return float(q)
    return None


# --------------------------------------------------------------------------- anàlisi de la melodia per compassos
class _Mel:
    """Les notes de la melodia repartides per compassos."""

    def __init__(self, compassos, evs, k):
        self.c = compassos
        self.k = k
        self.tonica = k.tonic.pitchClass
        ini = [c.ini for c in compassos]
        self.notes = [[] for _ in compassos]
        for e in evs:
            if not e.alt:
                continue
            i = bisect_right(ini, e.ini + _EPS) - 1
            if 0 <= i and e.ini < compassos[i].fi - _EPS:
                self.notes[i].append(e)

    def sig(self, a: int, b: int):
        """(inici relatiu, durada, altura) de les notes dels compassos [a, b)."""
        ref = self.c[a].ini
        return [(round(float(e.ini - ref), 3), float(e.dur), e.alt[0].midi)
                for i in range(a, b) for e in self.notes[i]]

    def ultima(self, a: int, b: int):
        for i in range(b - 1, a - 1, -1):
            if self.notes[i]:
                return self.notes[i][-1]
        return None


def _simil_ritme(x, y) -> float:
    sx, sy = {(r, d) for r, d, _ in x}, {(r, d) for r, d, _ in y}
    if not sx or not sy:
        return 0.0
    return len(sx & sy) / max(len(sx), len(sy))


def _signes(x):
    m = [p for _, _, p in x]
    return [(q > p) - (q < p) for p, q in zip(m, m[1:])]


def _simil_contorn(x, y) -> float:
    if not x or not y:
        return 0.0
    sx, sy = _signes(x), _signes(y)
    if not sx and not sy:
        return 1.0
    return difflib.SequenceMatcher(None, sx, sy).ratio()


def _iguals(mel: _Mel, a0: int, a1: int, ln: int) -> bool:
    x, y = mel.sig(a0, a0 + ln), mel.sig(a1, a1 + ln)
    return _simil_ritme(x, y) >= SIM_RITME and _simil_contorn(x, y) >= SIM_CONTORN


def tancada(mel: _Mel, a: int, b: int) -> bool:
    """Frase tancada: l'última nota és la tònica (R04); si no, oberta."""
    u = mel.ultima(a, b)
    return u is not None and u.alt[0].pitchClass == mel.tonica


def classifica(mel: _Mel, a: int, b: int) -> str:
    """`sentencia`, `periode` o `irregular` per a la frase dels compassos [a, b) (FR-12)."""
    n = b - a
    if n >= 4 and n % 4 == 0:
        u = n // 4
        if _iguals(mel, a, a + u, u):
            cont = mel.sig(a + 2 * u, a + 3 * u)
            if _simil_ritme(mel.sig(a, a + u), cont) < SIM_RITME:
                return "sentencia"
    if n >= 4 and n % 2 == 0:
        mig = n // 2
        u = max(1, mig // 2)
        if _iguals(mel, a, a + mig, u) and not tancada(mel, a, a + mig) and tancada(mel, a + mig, b):
            return "periode"
    return "irregular"


# --------------------------------------------------------------------------- marques de final de frase
def marques_extra(b: int, compassos, evs, segs, k) -> float:
    """Punts de final de frase abans del compàs b que no estan a `_puntua_tall`: ritme que s'asserena, línia que
    baixa, grau conjunt, tònica amb cadència i semicadència (FR-02, INF-12)."""
    c0, c1 = compassos[b - 1], compassos[b]
    ant = [e for e in evs if e.alt and e.ini < c1.ini - _EPS]
    sc = 0.0
    if not ant:
        return sc
    u = ant[-1]
    dins = [e for e in ant if e.ini >= c0.ini - _EPS]
    prev = [e for e in ant if compassos[max(b - 2, 0)].ini - _EPS <= e.ini < c0.ini - _EPS] if b >= 2 else []
    if prev and len(dins) < len(prev):
        sc += PES_REDUCCIO
    if len(ant) >= 2 and ant[-2].alt and u.alt[0].midi < ant[-2].alt[0].midi:
        sc += PES_BAIXADA
    if len(ant) >= 2 and ant[-2].alt and 0 < abs(u.alt[0].midi - ant[-2].alt[0].midi) <= 2:
        sc += PES_GRAUS
    a0 = next((s.acord for s in reversed(segs) if s.compas is c0 and s.acord), None)
    a1 = next((s.acord for s in segs if s.compas is c1 and s.acord), None)
    if a0 is not None and a1 is not None:
        arr = _arr()
        g0, g1 = arr._grau(a0, k), arr._grau(a1, k)
        pc = u.alt[0].pitchClass
        if g0 == 5 and g1 == 1 and pc == k.tonic.pitchClass:
            sc += PES_TONICA
        elif g0 == 5 and g1 != 5 and pc in a0.pcs:
            sc += PES_SEMICADENCIA
    return sc


def _marques(compassos, evs, segs, k, mel: _Mel, f: int, L: int) -> dict[int, float]:
    arr = _arr()
    n = len(compassos)
    res = {}
    for b in range(f + 2, n - 1):
        sc = arr._puntua_tall(b, b, compassos, evs, segs, k)
        for d in (L, 2 * L):
            if b - d >= f and _iguals(mel, b, b - d, 1):
                sc += BONUS_REPETICIO
                break
        res[b] = sc
    return res


def _penalitza(ln: int, L: int) -> float:
    if ln == L:
        return 0.0
    if ln == 2 * L:
        return PENALITZACIO_DOBLE
    if ln < L:
        return PENALITZACIO_CURTA * (L - ln)
    if ln < 2 * L:
        return PENALITZACIO_LLARGA * (ln - L) + 0.5
    return PENALITZACIO_DOBLE + 2.0 * (ln - 2 * L)


def divideix(compassos, evs, segs, k, bpm: float | None = None):
    """Talls de frases. Retorna una llista de (a, b, tipus, marca) amb compassos [a, b) i la nota de com de clar és el
    final. Si no hi ha marques, la llargada ideal mana (pla B)."""
    n = len(compassos)
    f = 1 if compassos[0].anacrusi else 0
    L = llargada_frase(compassos[f if f < n else 0].ts, bpm)
    plens = n - f
    mel = _Mel(compassos, evs, k)
    if plens < 2 * L or plens < 4:
        return [(0, n, classifica(mel, f, n), 0.0)]
    marca = _marques(compassos, evs, segs, k, mel, f, L)
    marca[n] = FINAL_PECA
    maxl = 2 * L + 2
    forma_cache: dict = {}

    def forma(a, b):
        if (a, b) not in forma_cache:
            forma_cache[(a, b)] = classifica(mel, a, b)
        return forma_cache[(a, b)]

    millor = {f: (0.0, None)}
    for b in range(f + 2, n + 1):
        cand = None
        for a in range(max(f, b - maxl), b - 1):
            if a not in millor:
                continue
            ln = b - a
            val = millor[a][0] + marca.get(b, 0.0) - _penalitza(ln, L)
            if forma(a, b) != "irregular":
                val += BONUS_FORMA
            key_ = (val, -abs(ln - L), -a)
            if cand is None or key_ > cand[0]:
                cand = (key_, a)
        if cand is not None:
            millor[b] = (cand[0][0], cand[1])
    if n not in millor:
        return [(0, n, classifica(mel, f, n), 0.0)]
    talls = []
    b = n
    while b != f:
        a = millor[b][1]
        talls.append((a, b))
        b = a
    talls.reverse()
    res = []
    for i, (a, b) in enumerate(talls):
        res.append((0 if i == 0 else a, b, forma(a, b), round(marca.get(b, 0.0), 2)))
    res = _uneix_periodes(res, mel, f)
    if plens >= PECA_LLARGA * L:
        res = _agrupa_frases(res, mel, f, L)
    return res


def _agrupa_frases(res, mel: _Mel, f: int, L: int):
    """En peces llargues, frases consecutives s'ajunten fins a tindre ~2 frases ideals (8 compassos en 4/4): és la
    unitat de rotació de la melodia i de lletra d'assaig. Els talls continuen sent finals de frase detectats."""
    out = []
    cur = None
    for a, b, t, m in res:
        if cur is None:
            cur = [a, b, t, m]
        else:
            cur[1], cur[3] = b, m
            cur[2] = None
        if cur[1] - max(cur[0], f) >= GRUP_MIN * L:
            out.append(cur)
            cur = None
    if cur is not None:
        if out and cur[1] - cur[0] < L:
            out[-1][1], out[-1][3], out[-1][2] = cur[1], cur[3], None
        else:
            out.append(cur)
    return [(a, b, t or classifica(mel, max(a, f), b), m) for a, b, t, m in out]


def _uneix_periodes(res, mel: _Mel, f: int):
    """Dues frases consecutives de la mateixa llargada que formen un període (la segona comença com la primera, la
    primera queda oberta i la segona tancada) passen a ser una sola secció: la melodia canvia de portador als talls
    de període, no a la meitat (Schoenberg FR-04)."""
    out = []
    i = 0
    while i < len(res):
        if i + 1 < len(res):
            a1, b1, _, _ = res[i]
            a2, b2, _, m2 = res[i + 1]
            if b1 - max(a1, f) == b2 - a2 and classifica(mel, max(a1, f), b2) == "periode":
                out.append((a1, b2, "periode", m2))
                i += 2
                continue
        out.append(res[i])
        i += 1
    return out


def etiqueta(seccions, compassos, evs, k) -> None:
    """Posa `tancada` a cada secció (nota final estable, R04)."""
    mel = _Mel(compassos, evs, k)
    f = 1 if compassos[0].anacrusi else 0
    for s in seccions:
        s.tancada = tancada(mel, max(s.i0, f), s.i1)


_NOM_TIPUS = {"sentencia": "sentència", "periode": "període", "irregular": "irregular", "intro": "introducció",
              "coda": "coda"}


def text_frases(seccions) -> list[str]:
    trossos = []
    for s in seccions:
        t = f"c. {s.num0}-{s.num1} {_NOM_TIPUS.get(s.tipus, s.tipus)}"
        if s.tipus not in ("intro", "coda"):
            t += " (tancada)" if s.tancada else " (oberta)"
        trossos.append(t)
    return ["Frases: " + "; ".join(trossos) + "."]


# --------------------------------------------------------------------------- introducció i coda
def _escala_midis(k: key.Key) -> list[int]:
    pcs = {p.pitchClass for p in k.getScale().getPitches()[:7]}
    return [m for m in range(0, 128) if m % 12 in pcs]


def desplaca_diatonic(midi: int, graus: int, k: key.Key) -> int:
    """Mou una altura `graus` graus de l'escala de la tonalitat (una nota fora d'escala compta com la de baix)."""
    esc = _escala_midis(k)
    i = max(0, bisect_right(esc, midi) - 1)
    return esc[min(max(i + graus, 0), len(esc) - 1)]


def _cost(evs_cel, graus: int, k, acord_en) -> float:
    c = 0.0
    for t, d, m in evs_cel:
        a = acord_en(t)
        if a is None:
            continue
        if desplaca_diatonic(m, graus, k) % 12 not in a.pcs:
            c += float(d)
    return c


def _tria_desplacament(cel, k, acord_en, preferit: int) -> int:
    """El desplaçament diatònic (de -7 a 7 graus) que deixa menys notes fora de l'acord; prefereix el més proper
    a `preferit`."""
    millor = min(range(-7, 8), key=lambda g: (round(_cost(cel, g, k, acord_en), 3), abs(g - preferit), g))
    return millor


def _cel(compassos, evs, i0: int, longitud: int):
    """Les notes dels compassos [i0, i0+longitud) com a (inici relatiu, durada, altura), retallades al compàs."""
    res = []
    ref = compassos[i0].ini
    fi = compassos[i0 + longitud - 1].fi
    for e in evs:
        if not e.alt or e.ini < ref - _EPS or e.ini >= fi - _EPS:
            continue
        res.append((opFrac(e.ini - ref), opFrac(min(e.fi, fi) - e.ini), e.alt[0].midi))
    return res


def _evs_de_cel(cel, ini: float, graus: int, k, Ev):
    return [Ev(opFrac(ini + t), d, [pitch.Pitch(midi=desplaca_diatonic(m, graus, k))]) for t, d, m in cel]


def _busca_cel(mel: _Mel, i_ini: int, f: int) -> int:
    """Compàs de l'últim tros de melodia amb notes: el primer de l'última frase que en tinga, o el més proper abans."""
    n = len(mel.c)
    for i in list(range(i_ini, n)) + list(range(i_ini - 1, f - 1, -1)):
        if len(mel.notes[i]) >= 2:
            return i
    return next((i for i in range(f, n) if mel.notes[i]), f)


def _compas_nou(model, ini: float, num: int):
    arr = _arr()
    return arr.Compas(num, opFrac(ini), opFrac(model.ts.barDuration.quarterLength), model.ts)


def _acords_dels_segs(segs_nous, figures: list[str], k, arr):
    """Posa un acord (figura romana) a cada segment nou: reparteix les figures de manera uniforme."""
    n = len(segs_nous)
    for i, s in enumerate(segs_nous):
        s.acord = arr._acord_de_roman(figures[min(len(figures) - 1, i * len(figures) // n)], k, "forma")


def _tonica_propera(k, midi_ref: int) -> int:
    t = k.tonic.pitchClass
    return min((m for m in range(midi_ref - 12, midi_ref + 13) if m % 12 == t), key=lambda m: (abs(m - midi_ref), m))


def afegeix_extrems(compassos, segs, evs, k, intro: bool, coda: bool, seccions=None, rols=None, curs=None) -> dict:
    """Afegeix una introducció i/o una coda (modifica les llistes al lloc). Retorna {"notes": [...], "n_intro", "n_coda",
    "i_coda"} amb el que s'ha fet. Els compassos de la peça es renumeren perquè la numeració siga contínua."""
    arr = _arr()
    Ev, Compas, Seccio = arr.Ev, arr.Compas, arr.Seccio
    info = {"notes": [], "n_intro": 0, "n_coda": 0, "i_coda": None}
    f = 1 if compassos[0].anacrusi else 0
    pleno = [c for c in compassos[f:]]
    if len(pleno) < 4 or not any(e.alt for e in evs):
        if intro or coda:
            info["notes"].append("No he afegit introducció ni coda: la peça és massa curta.")
        return info
    major = k.mode == "major"
    I = "I" if major else "i"
    IV = "IV" if major else "iv"
    nuc_ini = compassos[0].ini
    model = compassos[f]
    ult = compassos[-1]
    nous_c, nous_s, nous_e = [], [], []
    coda_c, coda_s, coda_e = [], [], []
    mi = _Mel(compassos, evs, k)

    # ---- coda (es construeix primer: usa la melodia i el final de la peça tal com són)
    if coda:
        bar = float(ult.ts.barDuration.quarterLength)
        n_seg = len(arr._segments([_compas_nou(ult, 0, 0)], []))
        n_cad = 1 if n_seg >= 2 else 2
        t0 = ult.fi
        cs = [_compas_nou(ult, t0 + j * bar, ult.num + 1 + j) for j in range(n_cad + 1)]
        ss = []
        for j, c in enumerate(cs):
            ss += arr._segments([c], [])
        if n_seg >= 2:
            nfig = [IV] * (n_seg // 2) + ["V"] * (n_seg - n_seg // 2)
            for i, s in enumerate(ss[:n_seg]):
                s.acord = arr._acord_de_roman(nfig[i], k, "forma")
        else:
            ss[0].acord = arr._acord_de_roman(IV, k, "forma")
            ss[1].acord = arr._acord_de_roman("V", k, "forma")
        for s in ss[n_cad * n_seg:]:
            s.acord = arr._acord_de_roman(I, k, "forma")

        def acord_coda(t):
            return next((s.acord for s in ss if s.ini - _EPS <= t < s.fi - _EPS), None)

        # material: la primera cèl·lula de l'última frase (un compàs)
        i_ult = max(f, seccions[-1].i0 if seccions else len(compassos) - 4)
        i_cel = _busca_cel(mi, i_ult, f)
        cel = _cel(compassos, evs, i_cel, 1)
        for j in range(n_cad):
            tj = t0 + j * bar
            ac = lambda t, tj=tj: acord_coda(tj + t)
            g = _tria_desplacament(cel, k, ac, 0 if j == 0 else -1)
            coda_e += _evs_de_cel(cel, tj, g, k, Ev)
        ref = mi.ultima(0, len(compassos))
        tonica = _tonica_propera(k, ref.alt[0].midi if ref else 60)
        coda_e.append(Ev(opFrac(t0 + n_cad * bar), opFrac(bar), [pitch.Pitch(midi=tonica)]))
        coda_c, coda_s = cs, ss
        info["n_coda"] = len(cs)
        info["notes"].append(f"Coda de {len(cs)} compassos: fragment de la melodia (c. {compassos[i_cel].num}) sobre "
                             f"{'IV-V' if n_seg >= 2 else 'IV, V'} i tònica llarga al final amb calderó.")

    # ---- introducció
    if intro:
        i_cel = f
        long_cel = 1 if len(mi.notes[f]) >= NOTES_CEL_LA_MIN or len(pleno) < 6 else 2
        bar = float(model.ts.barDuration.quarterLength)
        n_in = 2 * long_cel
        n_in = min(n_in, INTRO_MAX_COMPASSOS)
        ini0 = nuc_ini - n_in * bar
        cs = [_compas_nou(model, ini0 + j * bar, 1 + j) for j in range(n_in)]
        ss = []
        for c in cs:
            ss += arr._segments([c], [])
        per_compas = len(ss) // n_in
        for j in range(n_in):
            for s in ss[j * per_compas:(j + 1) * per_compas]:
                s.acord = arr._acord_de_roman(I if j < long_cel else "V", k, "forma")
        cel = _cel(compassos, evs, i_cel, long_cel)

        def acord_in(t, ini_bloc):
            return next((s.acord for s in ss if s.ini - _EPS <= ini_bloc + t < s.fi - _EPS), None)

        ev_in = []
        for bloc in range(2):
            ini_b = ini0 + bloc * long_cel * bar
            g = 0 if bloc == 0 else _tria_desplacament(cel, k, lambda t, ib=ini_b: acord_in(t, ib), 4)
            ev_in += _evs_de_cel(cel, ini_b, g, k, Ev)
        nous_c, nous_s, nous_e = cs, ss, ev_in
        info["n_intro"] = n_in
        info["notes"].append(f"Introducció de {n_in} compassos: el motiu del compàs {compassos[i_cel].num}"
                             f"{'-' + str(compassos[i_cel + long_cel - 1].num) if long_cel > 1 else ''} sobre la "
                             f"tònica i després, en seqüència, sobre la dominant.")

    # ---- inserció, numeració i seccions
    n_i, n_c = info["n_intro"], info["n_coda"]
    desp = n_i + (1 if (n_i and compassos[0].anacrusi and compassos[0].num == 0) else 0)
    if desp:
        for c in compassos:
            c.num += desp
    if n_i and nous_c and compassos[0].ts.ratioString == nous_c[0].ts.ratioString:
        compassos[0].canvi_ts = False
    if n_c:
        if arr._es_barra_forta(ult.barra_dre):
            ult.barra_dre = None
        for j, c in enumerate(coda_c):
            c.num = ult.num + 1 + j
    n_abans = len(compassos)
    compassos[:0] = nous_c
    segs[:0] = nous_s
    evs[:0] = nous_e
    compassos.extend(coda_c)
    segs.extend(coda_s)
    evs.extend(coda_e)
    evs.sort(key=lambda e: e.ini)
    info["i_coda"] = (n_i + n_abans) if n_c else None
    if seccions is not None:
        ld = {}
        for i, r in enumerate(rols):
            if not r.instr.percussio:
                ld.setdefault(r.rol, i)
        m = ld["melodia"]
        for s in seccions:
            s.i0 += n_i
            s.i1 += n_i
            s.num0 += desp
            s.num1 += desp
            if s.repeteix is not None and n_i:
                s.repeteix += 1
        if n_i:
            si = Seccio(0, n_i, nous_c[0].ini, nuc_ini, 1, n_i, m, tipus="intro", tancada=False)
            si.funcions = arr._funcions_seccio(rols, ld, m, curs, False)
            seccions.insert(0, si)
        if n_c:
            sc = Seccio(n_i + n_abans, n_i + n_abans + n_c, coda_c[0].ini, coda_c[-1].fi, coda_c[0].num, coda_c[-1].num,
                        m, tipus="coda", tancada=True)
            sc.funcions = arr._funcions_seccio(rols, ld, m, curs, False)
            seccions.append(sc)
    return info


def decora_coda(construides, i_coda: int | None) -> None:
    """Ritardando al primer compàs de la coda (a la part de la melodia) i calderó a l'última nota de cada part."""
    if i_coda is None or not construides:
        return
    from music21 import note, stream
    primer = True
    for r, pp, _ in construides:
        if r.instr.percussio:
            continue
        for p in pp:
            ms = list(p.getElementsByClass(stream.Measure))
            if primer and i_coda < len(ms):
                te = expressions.TextExpression("rit.")
                te.placement = "above"
                te.style.fontStyle = "italic"
                ms[i_coda].insert(0, te)
                primer = False
            ult = ms[-1]
            ns = [x for x in ult.notes]
            if ns:
                ns[-1].expressions.append(expressions.Fermata())
