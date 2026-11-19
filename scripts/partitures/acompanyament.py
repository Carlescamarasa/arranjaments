"""Tipus d'acompanyament per estil i nivell: quin ritme i quin motiu fa cada instrument d'acompanyament.

Les dades (`PATRONS`) diuen, per a cada estil i nivell, què es toca a cada pols del compàs. El codi (`genera`) les aplica
sobre els acords, tria les notes amb `voicing.py` i manté el mateix motiu tota la peça: només el canvia a les cadències
(últim compàs de frase i compàs final) i quan la melodia no el necessita.

Fonts (només ids, el text no es copia): Schoenberg AC-01 a AC-15 (tipus d'acompanyament i caràcter), Levine ST01 i ST02
(stride i dècimes), CP01 i CP02 (acords curts avançats mig temps), CP04 (més densitat quan el solista descansa),
Herrera ENG-01 i EST-01, Perricone R58 (punts morts). Els terminis i llindars marcats [inferència] són ajustables.

Tipus de pols dins un patró:
  R   arrel al baix (sempre l'arrel; stride i comping de jazz)
  B   baix de dos temps: arrel al primer cop del segment i 5a després (marxa, vals)
  D   dècima: arrel greu amb la 3a una dècima amunt (stride avançat; si no hi ha lloc, com R)
  C   acord curt (una pulsació)
  c   acord en corxeres (dues per pulsació, tres en compassos compostos)
  Q   acord curt avançat mig temps: porta l'acord que arriba mig temps després (Levine CP01)
  L   acord llarg, fins que canvie l'acord (o la durada indicada)
  A   arpegi (pop), una nota per pulsació o dues en corxeres
  AL  Alberti: nota baixa, alta, mitjana, alta
"""
from __future__ import annotations

from music21 import pitch
from music21.common.numberTools import opFrac

from . import voicing

NIVELLS = ("elemental", "mitja", "avançat")

# --- paràmetres ajustables ([inferència]: no vénen literalment dels llibres)
MAX_ATACS_MELODIA_OMISSIO = 1     # elemental: compàs amb com a molt tants atacs de melodia i un sol acord = només baix
ESTILS_AMB_OMISSIO = ("classic", "pop")   # en marxa, vals, ragtime, swing i rock el pols no s'omet (caràcter, AC-14)
ESTILS_CADENCIA = ("classic", "pop")      # estils on l'últim compàs de frase canvia de motiu
PULSACIONS_COMPLEMENT = 2         # swing avançat: es reforça cada 2 pulsacions (temps 1 i 3) si la melodia calla
DURADA_COMPLEMENT = 0.5           # negres: acord curt de complement
SEQ_ALBERTI = (0, 2, 1, 2)        # baix, alt, mig, alt
SEQ_ARPEGI = ("arrel", "quinta", "tercera", "quinta")
TOPE_PIANO_ESQUERRA = 59          # l'Alberti del piano intenta quedar-se a la mà esquerra
MAXIM_DECIMA = 16                 # distància màxima (semitons) arrel a 3a que una mà abasta amb dècima

_E = 1e-6


def nivell_de(curs: str | None) -> str:
    """«elemental», «mitja» o «avançat» a partir del text del curs. Sense curs o desconegut: «mitja»."""
    from . import instruments as inst
    t = inst._norm(curs or "")
    if any(x in t for x in ("elemental", "inicia", "primaria", "basic")):
        return "elemental"
    if any(x in t for x in ("avan", "profession", "superior", "esg", "jazz")):
        return "avançat"
    return "mitja"


# --------------------------------------------------------------------------- dades dels patrons

def _per_pulsacio(tipus: str, n: int, dur: float = 1.0):
    return [(float(i), tipus, dur) for i in range(n)]


_DANSA = {  # R/B als temps forts i acord als febles
    2: [(0.0, "B", 1.0), (1.0, "C", 1.0)],
    3: [(0.0, "B", 1.0), (1.0, "C", 1.0), (2.0, "C", 1.0)],
    4: [(0.0, "B", 1.0), (1.0, "C", 1.0), (2.0, "B", 1.0), (3.0, "C", 1.0)],
}
_VALS = {
    2: _DANSA[2],
    3: _DANSA[3],
    4: [(0.0, "B", 1.0), (1.0, "C", 1.0), (2.0, "C", 1.0), (3.0, "C", 1.0)],
}
_STRIDE = {  # Levine ST01: arrel als temps 1 i 3, acord als 2 i 4
    2: [(0.0, "R", 1.0), (1.0, "C", 1.0)],
    3: [(0.0, "R", 1.0), (1.0, "C", 1.0), (2.0, "C", 1.0)],
    4: [(0.0, "R", 1.0), (1.0, "C", 1.0), (2.0, "R", 1.0), (3.0, "C", 1.0)],
}
_STRIDE_DECIMES = {  # avançat: dècima en lloc d'arrel (ST01, ST02)
    2: [(0.0, "D", 1.0), (1.0, "C", 1.0)],
    3: [(0.0, "D", 1.0), (1.0, "C", 1.0), (2.0, "C", 1.0)],
    4: [(0.0, "D", 1.0), (1.0, "C", 1.0), (2.0, "D", 1.0), (3.0, "C", 1.0)],
}
_COMPING = {  # Levine CP01: acords curts una corxera abans del temps on arriba l'acord (& del 2 i & del 4)
    2: [(0.0, "R", 1.0), (1.5, "Q", 0.5)],
    3: [(0.0, "R", 1.0), (1.5, "Q", 0.5)],
    4: [(0.0, "R", 1.0), (1.5, "Q", 0.5), (2.0, "R", 1.0), (3.5, "Q", 0.5)],
}
_UN_PER_COMPAS = {2: [(0.0, "L", None)], 3: [(0.0, "L", None)], 4: [(0.0, "L", None)]}
_MITJOS_COMPASSOS = {2: [(0.0, "L", None)], 3: [(0.0, "L", None)], 4: [(0.0, "L", None), (2.0, "L", None)]}

PATRONS: dict[str, dict[str, dict[int, list]]] = {
    "ragtime": {"elemental": _STRIDE, "mitja": _STRIDE, "avançat": _STRIDE_DECIMES},
    "swing": {"elemental": _STRIDE, "mitja": _COMPING, "avançat": _COMPING},
    "marxa": {"elemental": _DANSA, "mitja": _DANSA, "avançat": _DANSA},
    "vals": {"elemental": _VALS, "mitja": _VALS, "avançat": _VALS},
    "pop": {n: {k: _per_pulsacio("A", k) for k in (2, 3, 4)} for n in NIVELLS},
    "rock": {"elemental": {k: _per_pulsacio("C", k) for k in (2, 3, 4)},
             "mitja": {k: _per_pulsacio("c", k) for k in (2, 3, 4)},
             "avançat": {k: _per_pulsacio("c", k) for k in (2, 3, 4)}},
    # clàssic: intermitent a elemental (AC-08), Alberti de mitjà en amunt (AC-05)
    "classic": {"elemental": _UN_PER_COMPAS, "mitja": {k: _per_pulsacio("AL", k) for k in (2, 3, 4)},
                "avançat": {k: _per_pulsacio("AL", k) for k in (2, 3, 4)}},
    # coral: acords sostinguts (AC-04); és el que fan els pads
    "coral": {n: _MITJOS_COMPASSOS for n in NIVELLS},
}


def patro(estil: str, nivell: str, n_pols: int) -> list:
    """Llista (posició en pulsacions, tipus, durada en pulsacions o None) per a un compàs de `n_pols` pulsacions."""
    taula = PATRONS.get(estil, PATRONS["pop"]).get(nivell) or PATRONS["pop"]["mitja"]
    if n_pols in taula:
        return list(taula[n_pols])
    for gran in (4, 3, 2):
        if n_pols % gran == 0:
            return [(o + b * gran, t, d) for b in range(n_pols // gran) for (o, t, d) in taula[gran]]
    base = taula[3] if n_pols >= 3 else taula[2]
    return list(base)


# --------------------------------------------------------------------------- generador

def genera(segs, instr, curs, estil, k, bordo=False, melodia=None, fi_frases=None, amb_baix=False):
    """Acompanyament d'un instrument sobre els acords. Retorna (acompanyament, línia de baix que hi ha dins).

    melodia: esdeveniments de la melodia en so real (per a no xocar-hi, ometre en elemental i omplir els buits).
    fi_frases: instants (en negres) on acaba cada frase; l'últim compàs de la frase canvia de motiu (AC-03).
    amb_baix: hi ha un altre instrument fent el baix; el comping de swing no hi posa arrels (Levine CP01).
    """
    from . import arranjador as A
    Ev = A.Ev
    nivell = nivell_de(curs)
    lo, hi = A._rang_concert(instr, curs)
    lo = min(max(lo, 43), hi - 12)
    hi = min(hi, lo + 30)
    n = A._veus_acomp(instr)
    corxeres = A._permet_corxeres(instr, curs) and nivell != "elemental"
    zona_baix_hi = lo + 11
    pis_acord = max(lo, zona_baix_hi - 2, 60 if instr.clau == "piano" else 0) if n > 1 else lo
    res: list = []
    baixos: list = []
    st = {"prev_v": None, "prev_b": None, "cur": None, "prev_ac": None, "slot": 0, "alb": None}
    ultim = max((s.compas.ini for s in segs if s.acord), default=None)
    fi_frases = sorted(fi_frases or [])
    mel = [e for e in (melodia or []) if e.alt]
    per_compas: dict = {}
    ordre = []
    for s in segs:
        if id(s.compas) not in per_compas:
            ordre.append(s.compas)
        per_compas.setdefault(id(s.compas), []).append(s)
    amb_baix_swing = amb_baix and estil == "swing"

    def seg_a(t):
        return next((x for x in segs if x.ini <= t + _E < x.fi), None)

    def mel_ataca(a, b):
        return any(a - _E <= e.ini < b - _E for e in mel)

    def atacs_melodia(a, b):
        return sum(1 for e in mel if a - _E <= e.ini < b - _E)

    def mel_a(t):
        sona = [x.midi for e in mel if e.ini - _E <= t < e.fi - _E for x in e.alt]
        return max(sona) if sona else None

    def notes_acord(a, t, final_dom=False, tipus_estil=None):
        if a is not st["cur"]:
            st["prev_ac"], st["cur"] = st["cur"], a
        v = voicing.disposicio(a, n, pis_acord, hi, st["prev_v"], tipus_estil or estil, nivell, mel_a(t),
                               st["prev_b"] if n > 1 and not amb_baix_swing else None, st["prev_ac"], final_dom)
        st["prev_v"] = v
        return v

    def P(midis):
        return [pitch.Pitch(midi=x) for x in midis]

    def baix_ev(t, dur, midi):
        baixos.append(Ev(t, dur, [pitch.Pitch(midi=midi)]))

    def es_v_i(a):
        p = st["cur"]
        return (p is not None and p is not a and len(p.pcs) >= 2 and (p.pcs[1] - p.pcs[0]) % 12 == 4
                and (p.pcs[0] - a.pcs[0]) % 12 == 7)

    for c in ordre:
        meus = per_compas[id(c)]
        if c.anacrusi or all(s.acord is None for s in meus):
            continue
        n_pols = max(1, int(round(c.dur / c.pols)))
        if bordo:
            t = k.tonic.pitchClass
            ton = A._veu_baixa(t, lo, None)
            v = [ton, ton + 7] if ton + 7 <= hi else [ton - 5, ton]
            res.append(Ev(c.ini, c.dur, P(v)))
            continue
        final = abs(c.ini - ultim) < _E
        cadencia = (not final and estil in ESTILS_CADENCIA and nivell != "elemental" and len(meus) == 1
                    and any(abs(c.fi - f) < _E for f in fi_frases))
        mat = patro("coral" if estil == "coral" else estil, nivell, n_pols)
        if final or cadencia:
            mat = [(0.0, "F", None)]
        elif (estil in ESTILS_AMB_OMISSIO and nivell == "elemental" and mel and len(meus) == 1
              and atacs_melodia(c.ini, c.fi) <= MAX_ATACS_MELODIA_OMISSIO):
            mat = [(0.0, "O", None)]       # melodia quieta i un sol acord: només el baix (AC-02)
        compound = abs(c.pols - 1.5) < _E
        n_sub = (3 if compound else 2) if (corxeres and c.pols >= 1) else 1
        mida_sub = opFrac(c.pols / n_sub)
        emesos_acord: list[float] = []
        tipus_L = False
        st["slot"] = 0          # l'Alberti comença cada compàs (i cada acord nou) per la nota baixa

        for (off, tipus, dur_p) in mat:
            t = opFrac(c.ini + off * c.pols)
            if t >= c.fi - _E:
                continue
            if tipus == "Q":
                s = seg_a(opFrac(t + 0.5))      # l'acord que arriba mig temps després
                if s is None or s.acord is None:
                    continue
            else:
                s = next((x for x in meus if x.ini <= t + _E < x.fi), None)
            if s is None or s.acord is None:
                continue
            a = s.acord
            dur = opFrac(min(dur_p * c.pols, c.fi - t)) if dur_p is not None else None
            primer = abs(t - s.ini) < _E
            if tipus in ("R", "B", "D"):
                if amb_baix_swing:
                    continue
                if tipus == "R" or primer or len(a.pcs) < 3:
                    pc = a.pcs[0]
                else:
                    pc = a.pcs[2]
                b = A._veu_baixa(pc, lo, st["prev_b"])
                st["prev_b"] = b
                notes = [b]
                if tipus == "D" and n >= 3 and len(a.pcs) > 1:
                    alta = b + ((a.pcs[1] - b) % 12) + 12
                    if alta - b <= MAXIM_DECIMA and alta <= hi:
                        notes = [b, alta]
                res.append(Ev(t, dur, P(notes)))
                baix_ev(t, dur, b)
            elif tipus in ("C", "c", "Q"):
                v = notes_acord(a, t)
                if tipus == "c" and n_sub > 1:
                    for h in range(n_sub):
                        res.append(Ev(opFrac(t + h * mida_sub), mida_sub, P(v)))
                else:
                    res.append(Ev(t, dur, P(v)))
                emesos_acord.append(t)
            elif tipus == "L":
                tipus_L = True
                fi_l = opFrac(min(s.fi, c.fi)) if dur_p is None else opFrac(min(t + dur, c.fi))
                v = notes_acord(a, t)
                if n >= 3:
                    st["prev_b"] = A._veu_baixa(a.pcs[0], lo, st["prev_b"])
                    v = sorted(set([st["prev_b"]] + v))
                    baix_ev(t, opFrac(fi_l - t), st["prev_b"])
                res.append(Ev(t, opFrac(fi_l - t), P(v)))
                emesos_acord.append(t)
            elif tipus == "O":
                b = A._veu_baixa(a.pcs[0], lo, st["prev_b"])
                st["prev_b"] = b
                res.append(Ev(c.ini, c.dur, P([b])))
                baix_ev(c.ini, c.dur, b)
                break
            elif tipus == "F":
                fdom = final and es_v_i(a)
                v = notes_acord(a, t, fdom)
                b = A._veu_baixa(a.pcs[0], lo, st["prev_b"])
                st["prev_b"] = b
                llarg = estil in ("classic", "coral", "pop", "vals", "marxa") or cadencia
                dur_f = c.dur if llarg else c.pols
                if dur_f > c.dur:
                    dur_f = c.dur
                tot = sorted(set(([b] if n != 2 else []) + v))
                res.append(Ev(t, dur_f, P(tot)))
                baix_ev(t, dur_f, b)
                emesos_acord.append(t)
            elif tipus == "AL":
                if st["alb"] is None or st["alb"][0] is not a:
                    base = A._veu_baixa(a.pcs[0], lo, st["prev_b"])
                    if instr.clau == "piano" and base + 7 > TOPE_PIANO_ESQUERRA and base - 12 >= 36:
                        base -= 12
                    st["prev_b"] = base
                    alt_pc = a.pcs[3] if (nivell == "avançat" and len(a.pcs) > 3) else (
                        a.pcs[2] if len(a.pcs) > 2 else a.pcs[0])
                    mig_pc = a.pcs[1] if len(a.pcs) > 1 else a.pcs[0]
                    st["alb"] = (a, [base, base + ((mig_pc - base) % 12), base + ((alt_pc - base) % 12)])
                    st["slot"] = 0
                    nou_alb = True
                else:
                    nou_alb = False
                if nou_alb or off == 0:
                    baix_ev(t, c.pols, st["alb"][1][0])
                notes_alb = st["alb"][1]
                for h in range(n_sub):
                    x = notes_alb[SEQ_ALBERTI[st["slot"] % len(SEQ_ALBERTI)]]
                    while x > hi:
                        x -= 12
                    res.append(Ev(opFrac(t + h * mida_sub), mida_sub, P([x])))
                    st["slot"] += 1
            elif tipus == "A":
                arp_pcs = {"arrel": a.pcs[0], "quinta": a.pcs[2] if len(a.pcs) > 2 else a.pcs[0], "tercera": a.pcs[1]
                           if len(a.pcs) > 1 else a.pcs[0]}
                arp = [arp_pcs[x] for x in SEQ_ARPEGI]
                if nivell == "avançat" and len(a.pcs) > 3:
                    arp[2] = a.pcs[3]
                if primer:
                    st["prev_b"] = A._veu_baixa(a.pcs[0], lo, st["prev_b"])
                    baix_ev(t, c.pols, st["prev_b"])
                base = st["prev_b"] if st["prev_b"] is not None else A._veu_baixa(a.pcs[0], lo, None)
                rel = int(round((t - s.ini) / c.pols))
                if n_sub > 1:
                    for h in range(n_sub):
                        pc = arp[(rel * n_sub + h) % 4]
                        x = base + ((pc - base) % 12) + (12 if h and pc == arp[0] else 0)
                        while x > hi:
                            x -= 12
                        res.append(Ev(opFrac(t + h * mida_sub), mida_sub, P([x])))
                else:
                    pc = arp[rel % 4]
                    x = base + ((pc - base) % 12)
                    res.append(Ev(t, c.pols, P([x])))
        # una nota llarga o intermitent no ha de deixar un canvi d'acord sense acord (AC-08)
        if tipus_L:
            for s in meus:
                if s.acord is not None and s.ini > c.ini + _E and all(abs(s.ini - x) > _E for x in emesos_acord):
                    v = notes_acord(s.acord, s.ini)
                    if n >= 3:
                        st["prev_b"] = A._veu_baixa(s.acord.pcs[0], lo, st["prev_b"])
                        v = sorted(set([st["prev_b"]] + v))
                        baix_ev(s.ini, opFrac(s.fi - s.ini), st["prev_b"])
                    res.append(Ev(s.ini, opFrac(min(s.fi, c.fi) - s.ini), P(v)))
        # complementari (AC-09, CP04): si la melodia calla en un temps fort, un acord curt omple el buit
        if estil == "swing" and nivell == "avançat" and mel and not final:
            for b in range(0, n_pols, PULSACIONS_COMPLEMENT):
                t = opFrac(c.ini + b * c.pols)
                s = next((x for x in meus if x.ini <= t + _E < x.fi), None)
                if s is None or s.acord is None or mel_ataca(t, t + c.pols):
                    continue
                if any(t - _E <= x < t + c.pols - _E for x in emesos_acord):
                    continue
                v = notes_acord(s.acord, t)
                res.append(Ev(t, DURADA_COMPLEMENT, P(v)))
    res.sort(key=lambda e: (e.ini, -len(e.alt)))
    return A._ortografia(res, k, segs), A._ortografia(baixos, k, segs)
