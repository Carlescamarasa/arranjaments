"""Contracant per nivell: terceres i sextes, contorn complementari o notes guia, i fàcil de tocar.

Tres maneres de fer el contracant, segons el curs (veges la fitxa `referencies/arranjar/contracant-facil.md`):

- `terceres` (elemental): la melodia a distància de tercera o sexta (Zamacois Z5-17), canviant d'un interval a l'altre
  com a molt cada 4 notes, sense quintes ni octaves paral·leles. Només les notes de pols; les ràpides no es dupliquen.
- `complementari` (mitjà): notes llargues de l'acord que fan el contorn contrari al de la frase (Perricone R39 i R40)
  i entren després de la melodia perquè no coincidisquen més de la meitat dels atacs (Z5-16).
- `guia` (professional): igual que l'anterior, però en els acords de sèptima només amb les notes guia, 3a i 7a (Herrera CON-01).

Als forats de la melodia (nota llarga o silenci, Perricone R58) hi van els farciments de l'arranjador; per a nivell
elemental amb notes de l'escala pentatònica de l'acord (Levine HR09, Herrera TEN-14), que són cinc i no sonen mai malament.

Les funcions treballen en so real (concert) i criden l'arranjador només quan fa falta (import tardà, per no fer cercles).
"""
from __future__ import annotations

from music21 import pitch
from music21.common.numberTools import opFrac

from . import simplificar

_EPS = 1e-6

# ----------------------------------------------------------------------------- dades ajustables [inferència]

NIVELL_A_MODE = {"elemental": "terceres", "mitja": "complementari", "professional": "guia"}
COINCIDENCIA_MAXIMA = 0.5       # Z5-16: part dels atacs del contracant que poden coincidir amb els de la melodia
MAX_NOTES_MATEIX_INTERVAL = 4   # Z5-17: canviar de tercera a sexta (o al revés) com a molt cada 4 notes
SALT_MAX_ELEMENTAL = 9          # semitons entre dues notes del contracant en elemental (una sexta major)
PES_OBJECTIU = 0.8              # com de fort va el contorn cap a la línia objectiu (cost per semitò)
DISTANCIA_MAXIMA_OBJECTIU = 5   # semitons: més lluny de l'objectiu no costa més (així mai guanya a evitar paral·leles)
AMPLITUD_CONTORN = 6            # semitons que puja o baixa el contorn objectiu dins d'una frase
PENALITZACIO_PARAL = 50.0       # una quinta o octava paral·lela no es dona mai si es pot evitar
PENTATONICA_MAJOR = (0, 2, 4, 7, 9)
PENTATONICA_MENOR = (0, 3, 5, 7, 10)
CONTORN_OPOSAT = {"ascendent": "descendent", "descendent": "ascendent", "arc": "arc_invertit",
                  "arc_invertit": "arc", "estacionari": "arc"}


def mode_contracant(curs: str | None) -> str:
    """`terceres`, `complementari` o `guia` segons el curs. Sense curs, el del mig."""
    return NIVELL_A_MODE.get(simplificar.nivell_de(curs) or "mitja", "complementari")


# ----------------------------------------------------------------------------- peces petites

def pentatonica(acord) -> set[int]:
    """Classes d'altura de la pentatònica de l'acord (major sobre majors i dominants, menor sobre menors) més les
    notes de l'acord. Els acords disminuïts només tenen les seues notes."""
    pcs = set(acord.pcs)
    arrel = acord.arrel.pitchClass
    tercera = (acord.pcs[1] - acord.pcs[0]) % 12 if len(acord.pcs) > 1 else 4
    quinta = (acord.pcs[2] - acord.pcs[0]) % 12 if len(acord.pcs) > 2 else 7
    if quinta != 7:
        return pcs
    forma = PENTATONICA_MENOR if tercera == 3 else PENTATONICA_MAJOR
    return pcs | {(arrel + x) % 12 for x in forma}


def pool_farciment(curs: str | None):
    """Funció que dona les notes dels farciments per a este curs: la pentatònica en elemental, None (l'escala) si no."""
    return pentatonica if simplificar.nivell_de(curs) == "elemental" else None


def notes_guia(acord) -> set[int]:
    """Les notes que defineixen l'acord: tercera i sèptima quan hi ha sèptima. En una tríada no hi ha sèptima i
    la línia usa les tres notes de l'acord (només amb tercera i quinta no tindria on moure's)."""
    if len(acord.pcs) >= 4:
        return {acord.pcs[1], acord.pcs[-1]}
    return set(acord.pcs)


def classifica_contorn(vals: list[int]) -> str:
    """Contorn d'una frase (Perricone R39): ascendent, descendent, arc, arc_invertit o estacionari."""
    if len(vals) < 2 or max(vals) - min(vals) < 3:
        return "estacionari"
    n = len(vals)
    imax, imin = vals.index(max(vals)), vals.index(min(vals))
    interior = lambda i: 0.2 * (n - 1) <= i <= 0.8 * (n - 1)       # noqa: E731
    if n >= 3 and interior(imax) and vals[0] < vals[imax] - 2 and vals[-1] < vals[imax] - 2:
        return "arc"
    if n >= 3 and interior(imin) and vals[0] > vals[imin] + 2 and vals[-1] > vals[imin] + 2:
        return "arc_invertit"
    return "ascendent" if vals[-1] >= vals[0] else "descendent"


def _forma(contorn: str, u: float) -> float:
    """Forma de la línia objectiu entre -1 i 1, amb u de 0 a 1 dins de la frase."""
    if contorn == "ascendent":
        return 2 * u - 1
    if contorn == "descendent":
        return 1 - 2 * u
    arc = (1 - 4 * (u - 0.5) ** 2) * 2 - 1       # -1 als extrems i 1 al mig
    return arc if contorn == "arc" else -arc


def _compassos_de(segs):
    res = []
    for s in segs:
        if not res or res[-1] is not s.compas:
            res.append(s.compas)
    return res


def objectiu_contorn(evs_mel, segs, lo: int, hi: int) -> dict[int, float]:
    """Altura objectiu del contracant a cada segment: el contorn oposat al de la frase de la melodia (R40).
    Clau: índex del segment a `segs`."""
    from . import arranjador as arr
    compassos = _compassos_de(segs)
    talls = simplificar.talls_de_frase([e for e in evs_mel], compassos) if evs_mel else [0.0]
    centre = lo + 0.4 * (hi - lo)
    res: dict[int, float] = {}
    for a, b in zip(talls, talls[1:] + [float("inf")]):
        idx = [i for i, s in enumerate(segs) if s.acord is not None and a - _EPS <= s.ini < b - _EPS]
        if not idx:
            continue
        vals = []
        for i in idx:
            m = arr._sonant(evs_mel, segs[i].ini)
            if m is None:
                dins = arr._notes_entre(evs_mel, segs[i].ini, segs[i].fi)
                m = dins[0][0].alt[0].midi if dins else None
            if m is not None:
                vals.append(m)
        contorn = CONTORN_OPOSAT[classifica_contorn(vals)]
        for j, i in enumerate(idx):
            u = j / (len(idx) - 1) if len(idx) > 1 else 0.5
            res[i] = centre + AMPLITUD_CONTORN * _forma(contorn, u)
    return res


# ----------------------------------------------------------------------------- coincidència d'atacs (Z5-16)

def coincidencia_atacs(linia, evs_mel) -> float:
    """Part dels atacs del contracant que cauen justament on la melodia ataca (0 a 1)."""
    atacs = {opFrac(e.ini) for e in evs_mel if e.alt}
    meus = [e for e in linia if e.alt]
    if not meus:
        return 0.0
    return sum(opFrac(e.ini) in atacs for e in meus) / len(meus)


def desplaca_entrades(linia, evs_mel, segs, maxim: float = COINCIDENCIA_MAXIMA, baix=None):
    """Si el contracant coincideix massa amb la melodia, algunes notes llargues entren una pulsació (o mitja pulsació)
    més tard, com una resposta. Mai l'última nota, ni quan la nota quedaria més curta que mitja pulsació, ni quan la
    nova entrada tornaria a coincidir amb un atac de la melodia o crearia quintes i octaves paral·leles noves."""
    from . import arranjador as arr
    if coincidencia_atacs(linia, evs_mel) <= maxim:
        return linia

    def paral(x):
        return len(arr._paral_temps(x, evs_mel)) + (len(arr._paral_temps(x, baix)) if baix else 0)

    linia = [type(e)(e.ini, e.dur, list(e.alt)) for e in linia]
    atacs = {opFrac(e.ini) for e in evs_mel if e.alt}
    ultim = max((e.ini for e in linia if e.alt), default=None)
    candidats = []
    for n, e in enumerate(linia):
        if not e.alt or e.ini == ultim or opFrac(e.ini) not in atacs:
            continue
        c = next((s.compas for s in segs if s.ini - _EPS <= e.ini < s.fi - _EPS), None)
        if c is not None:
            candidats.append((n, c.pols))
    for n, pols in candidats[::2] + candidats[1::2]:
        if coincidencia_atacs(linia, evs_mel) <= maxim:
            break
        e = linia[n]
        for retard in (pols, pols / 2):
            nova = opFrac(e.ini + retard)
            resta = opFrac(e.dur - retard)
            if opFrac(nova) in atacs or resta < pols / 2 - _EPS or not simplificar._escrivible(resta):
                continue
            abans = paral(linia)
            e.ini, e.dur = nova, resta
            if paral(linia) > abans:
                e.ini, e.dur = opFrac(nova - retard), opFrac(resta + retard)
                continue
            break
    return linia


# ----------------------------------------------------------------------------- mode terceres (Z5-17)

def _ancoratges(evs_mel, segs):
    """Les notes de la melodia que el contracant seguirà: les de pols, les llargues i les que venen després d'un silenci.
    Cada una amb el final fins on arriba el seu ritme (les notes ràpides del mig no es dupliquen). (ini, fi, midi)."""
    notes = [e for e in evs_mel if e.alt]
    res = []
    for e in notes:
        c = next((s.compas for s in segs if s.ini - _EPS <= e.ini < s.fi - _EPS), None)
        if c is None:
            continue
        llarg = float(c.ts.barDuration.quarterLength)
        base = c.fi - llarg if c.anacrusi else c.ini
        k = (e.ini - base) / c.pols
        en_pols = abs(k - round(k)) < 1e-4
        ant = next((x for x in reversed(evs_mel) if x.ini < e.ini - _EPS), None)
        despres_silenci = ant is None or not ant.alt or ant.fi < e.ini - _EPS
        if en_pols or e.dur >= c.pols - _EPS or despres_silenci:
            res.append([e.ini, e.fi, e.alt[0].midi])
    for a, b in zip(res, res[1:] + [[float('inf'), 0, 0]]):
        if b[0] > a[1] + _EPS:
            # entre les dues hi ha notes ràpides o un silenci: s'arriba fins on la melodia no para
            cont = [x for x in notes if a[1] - _EPS <= x.ini < b[0] - _EPS]
            fi = a[1]
            for x in cont:
                if abs(x.ini - fi) < _EPS:
                    fi = x.fi
            a[1] = fi
    res = [(a, b, m) for a, b, m in res]
    # durades que sap escriure l'eina
    sortida = []
    for a, b, m in res:
        d = opFrac(b - a)
        if not simplificar._escrivible(d):
            d = max((x for x in simplificar.DURADES_ESCRIVIBLES if x <= d + _EPS), default=None)
            if d is None:
                continue
        sortida.append((a, opFrac(a + d), m))
    return sortida


def _pas_escala(m: int, n: int, sentit: int, escala: set[int]) -> int:
    """La nota que queda a `n` graus de l'escala de `m` (cap amunt si sentit=1, cap avall si -1)."""
    p, fet = m, 0
    while fet < n:
        p += sentit
        if p % 12 in escala:
            fet += 1
    return p


def linia_terceres(evs_mel, segs, instr_lo: int, instr_hi: int, k, curs=None):
    """Contracant en terceres i sextes diatòniques de la melodia, només amb les notes de pols (Z5-17)."""
    from . import arranjador as arr
    anc = _ancoratges(evs_mel, segs)
    if not anc:
        return None
    escala = arr._escala_pcs(k)
    mids = [e.alt[0].midi for e in evs_mel if e.alt]
    med = sorted(mids)[len(mids) // 2]
    damunt = (instr_lo + instr_hi) / 2 >= med
    sentit = 1 if damunt else -1
    centre = instr_lo + 0.4 * (instr_hi - instr_lo)
    salt_max = SALT_MAX_ELEMENTAL if simplificar.nivell_de(curs) == "elemental" else 12
    ultim = len(anc) - 1

    def cap_a_rang(p):
        for _ in range(4):
            if p > instr_hi:
                p -= 12
            elif p < instr_lo:
                p += 12
        return p, instr_lo <= p <= instr_hi

    cands = []
    for j, (ini, fi, m) in enumerate(anc):
        acord = arr._acord_en(segs, ini)
        fila = []
        for tipus, graus in ((3, 2), (6, 5)):
            p, dins = cap_a_rang(_pas_escala(m, graus, sentit, escala))
            c = 0.04 * abs(p - centre) + (0 if dins else 20)
            if acord is not None and p % 12 not in acord.pcs:
                c += 3 if j == ultim else 0.5
            if abs(p - m) % 12 not in (3, 4, 8, 9):
                c += 5
            fila.append((tipus, p, c))
        cands.append(fila)

    # programació dinàmica: estat = (tipus, quantes notes seguides del mateix tipus)
    INF = float("inf")
    cost = [{(t, 1): c for t, p, c in cands[0]}]
    ptr = [{}]
    for j in range(1, len(anc)):
        nou, pt = {}, {}
        contigu = abs(anc[j - 1][1] - anc[j][0]) < _EPS
        for t, p, loc in cands[j]:
            for (t0, r0), c0 in cost[-1].items():
                r = r0 + 1 if t == t0 else 1
                if r > MAX_NOTES_MATEIX_INTERVAL:
                    continue
                p0 = next(pp for tt, pp, _ in cands[j - 1] if tt == t0)
                m0, m1 = anc[j - 1][2], anc[j][2]
                c = c0 + loc + (0.3 if t != t0 else 0)
                salt = abs(p - p0)
                c += 6 if salt > salt_max else 0.15 * max(0, salt - 2)
                if contigu and p != p0 and m0 != m1:
                    i0, i1 = (p0 - m0) % 12, (p - m1) % 12
                    if i0 == i1 and i1 in (0, 7):
                        c += PENALITZACIO_PARAL
                if c < nou.get((t, r), INF):
                    nou[(t, r)] = c
                    pt[(t, r)] = (t0, r0)
        if not nou:      # no hi ha manera de complir el límit: es deixa lliure
            return None
        cost.append(nou)
        ptr.append(pt)
    estat = min(cost[-1], key=lambda e: (cost[-1][e], e))
    triats = [None] * len(anc)
    for j in range(len(anc) - 1, -1, -1):
        triats[j] = estat[0]
        estat = ptr[j].get(estat) if j else None
    evs = []
    for j, (ini, fi, m) in enumerate(anc):
        p = next(pp for tt, pp, _ in cands[j] if tt == triats[j])
        evs.append(arr.Ev(ini, opFrac(fi - ini), [pitch.Pitch(midi=p)]))
    return arr._ortografia(evs, k, segs)


# ----------------------------------------------------------------------------- entrada des de l'arranjador

def linia(evs_mel, segs, instr, curs, k, baix):
    """El contracant de tota la peça segons el curs. L'arranjador el crida en lloc de `rol_contracant`."""
    from . import arranjador as arr
    lo, hi = arr._rang_concert(instr, curs)
    mode = mode_contracant(curs)
    if mode == "terceres":
        res = linia_terceres(evs_mel, segs, lo, hi, k, curs)
        if res:
            return res
        mode = "complementari"
    objectiu = objectiu_contorn(evs_mel, segs, lo, hi)
    res = arr.rol_contracant(evs_mel, segs, instr, curs, k, baix, objectiu=objectiu,
                             filtre_pcs=notes_guia if mode == "guia" else None)
    return arr._ortografia(desplaca_entrades(res, evs_mel, segs, baix=baix), k, segs)


def comprovacions(linies: dict, curs: str | None) -> list[str]:
    """Línies d'informe sobre la independència del contracant (Z5-16). Buit si tot és com cal."""
    if "contracant" not in linies or "melodia" not in linies:
        return []
    mode = mode_contracant(curs)
    c = coincidencia_atacs(linies["contracant"], linies["melodia"])
    if mode == "terceres":
        return [f"  Contracant en terceres i sextes (nivell elemental): cada nota va amb una de la melodia "
                f"({round(c * 100)}% dels atacs coincideixen; és el que toca en este mode)."]
    if c > COINCIDENCIA_MAXIMA + _EPS:
        return [f"  Contracant: el {round(c * 100)}% dels atacs coincideix amb la melodia; "
                "la peça no deixa gaire lloc perquè entre més tard."]
    return [f"  Contracant: només el {round(c * 100)}% dels atacs coincideix amb la melodia."]
