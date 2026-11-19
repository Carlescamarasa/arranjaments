"""Simplificar la melodia per nivell: esquelet de notes estructurals, què es treu primer i octaves per frases.

Tot són funcions pures sobre llistes d'`Ev` (la classe de l'arranjador; ací només se'n llig `ini`, `dur`, `alt`).
Les regles venen de les fitxes `referencies/arranjar/simplificar-per-nivell.md`; ací en deixem l'id al costat
(Perricone R11 a R17, Levine VC10, Gould OC-01). Els llindars marcats [inferència] són una proposta nostra i es poden
ajustar tocant les constants de dalt.
"""
from __future__ import annotations

from music21 import pitch
from music21.common.numberTools import opFrac

from . import instruments as inst

_EPS = 1e-6

# ----------------------------------------------------------------------------- dades ajustables

# Límits per nivell [inferència]: figura mínima en negres (0 = sense límit), salt màxim entre notes seguides en
# semitons (None = sense límit) i línies addicionals admeses damunt o davall del pentagrama.
NIVELLS = {
    "elemental": {"figura_minima": 1.0, "salt_max": 7, "linies_addicionals": 2},
    "mitja": {"figura_minima": 0.5, "salt_max": 12, "linies_addicionals": 3},
    "professional": {"figura_minima": 0.0, "salt_max": None, "linies_addicionals": 4},
}
_PARAULES_NIVELL = {
    "elemental": ("elemental", "inicia", "primaria", "basic"),
    "professional": ("professional", "superior", "avancat", "avanzado"),
}
# Puntuació mínima perquè una nota siga estructural (R13) i pesos de cada criteri [inferència]
LLINDAR_ESTRUCTURAL = 2
PES_TEMPS_FORT = {"primer": 3, "mig": 2, "altre": 1}
PES_SINCOPA = 2
PES_DESPRES_SILENCI = 1
PES_EXTREM_FRASE = 3        # primera i última nota de la frase
PES_ALT_BAIX_FRASE = 2      # nota més aguda i més greu de la frase
FRASE_COMPASSOS = 4         # si no hi ha silencis, una frase cada 4 compassos
# Durades que sap escriure l'eina sense figures estranyes (en negres)
DURADES_ESCRIVIBLES = {0.25, 0.375, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0}
# Una frase només canvia d'octava si el salt amb la frase veïna no passa d'això (en semitons)
MAX_TROSSOS_INFORME = 8      # a l'informe, com a molt tants trossos de compassos per línia
SALT_MAX_ENTRE_FRASES = 9
ORDRE_FIGURES = (("semicorxera", 0.25), ("corxera", 0.5), ("negra", 1.0), ("blanca", 2.0))
NOM_PASSADA = {"anticipacio": "anticipacions", "veina": "notes veïnes", "canvi": "notes de canvi",
               "pas": "notes de pas", "salt": "salts a notes curtes"}


def nivell_de(curs: str | None) -> str | None:
    """«elemental», «mitja» o «professional» segons el nom del curs (None si no hi ha curs)."""
    if not curs:
        return None
    t = inst._norm(curs)
    for nom, paraules in _PARAULES_NIVELL.items():
        if any(x in t for x in paraules):
            return nom
    return "mitja"


def figura_minima(permeses: set[str] | None, curs: str | None) -> float:
    """Durada mínima (en negres) que admet el nivell: la del perfil si n'hi ha, i si no la de la taula."""
    if permeses:
        if "fusa" in permeses:        # el perfil admet tot: res a simplificar
            return 0.0
        return next((d for nom, d in ORDRE_FIGURES if nom in permeses), 1.0)
    n = nivell_de(curs)
    return NIVELLS[n]["figura_minima"] if n else 1.0


def figures_del_nivell(curs: str | None) -> set[str] | None:
    """Figures de la taula per nivell (quan no hi ha perfil desat). None si no hi ha curs."""
    n = nivell_de(curs)
    if n is None:
        return None
    q = NIVELLS[n]["figura_minima"]
    return {nom for nom, d in ORDRE_FIGURES if d >= q - _EPS} | {"rodona"} | ({"fusa"} if q <= _EPS else set())


# ----------------------------------------------------------------------------- notes estructurals (R11, R13)

def _compas_de(compassos, t):
    return next((c for c in compassos if c.ini - _EPS <= t < c.fi - _EPS), None)


def _forca_temps(c, t: float) -> int:
    """Pes mètric d'un instant dins del compàs (R11): 3 el primer temps, 2 el temps de mig en compassos de 4 pulsacions,
    1 la resta de pulsacions, 0 fora de pols."""
    pols = c.pols
    llarg = float(c.ts.barDuration.quarterLength)
    pos = t - c.ini
    if c.anacrusi:
        pos = t - (c.fi - llarg)
    k = pos / pols
    if abs(k - round(k)) > 1e-4:
        return 0
    n = int(round(k))
    nb = int(round(llarg / pols))
    if n == 0:
        return PES_TEMPS_FORT["primer"]
    if nb >= 4 and nb % 2 == 0 and n == nb // 2:
        return PES_TEMPS_FORT["mig"]
    return PES_TEMPS_FORT["altre"]


def _creua_pols(c, e) -> bool:
    pols = c.pols
    llarg = float(c.ts.barDuration.quarterLength)
    base = c.ini if not c.anacrusi else c.fi - llarg
    k0 = (e.ini - base) / pols
    k1 = (e.fi - base) / pols
    return int(k1 - 1e-4) > int(k0 + 1e-4) and abs(k0 - round(k0)) > 1e-4


def talls_de_frase(evs, compassos) -> list[float]:
    """Instants on comença una frase: després d'un silenci d'una pulsació o més, i cada FRASE_COMPASSOS compassos."""
    talls = {evs[0].ini} if evs else set()
    for a, b in zip(evs, evs[1:]):
        c = _compas_de(compassos, a.ini)
        pols = c.pols if c else 1.0
        buit = (b.ini - a.fi) if a.alt else a.dur        # silenci (escrit o simplement un forat entre dues notes)
        if b.alt and buit >= pols - _EPS:
            talls.add(b.ini)
    plens = [c for c in compassos if not c.anacrusi]
    for i, c in enumerate(plens):
        if i and i % FRASE_COMPASSOS == 0:
            talls.add(c.ini)
    return sorted(talls)


def importancia(evs, compassos, talls: list[float] | None = None) -> list[int]:
    """Puntuació d'estrès de cada esdeveniment (R11, R13): temps fort, nota llarga, síncopa, després de silenci,
    extrems de frase i nota més aguda o més greu de la frase. Els silencis valen 0."""
    talls = talls if talls is not None else talls_de_frase(evs, compassos)
    imp = [0] * len(evs)
    frases: list[list[int]] = []
    for i, e in enumerate(evs):
        if i == 0 or any(abs(e.ini - t) < _EPS for t in talls):
            frases.append([])
        if e.alt:
            frases[-1].append(i)
    for i, e in enumerate(evs):
        if not e.alt:
            continue
        c = _compas_de(compassos, e.ini)
        if c is None:
            continue
        pols = c.pols
        f = _forca_temps(c, e.ini)
        s = f
        if e.dur >= pols - _EPS:
            s += 1
        if e.dur >= 2 * pols - _EPS:
            s += 1
        if f == 0 and e.dur >= pols / 2 - _EPS and _creua_pols(c, e):
            s += PES_SINCOPA
        if i > 0 and (not evs[i - 1].alt or evs[i - 1].fi < e.ini - _EPS):
            s += PES_DESPRES_SILENCI
        imp[i] = s
    for fr in frases:
        if not fr:
            continue
        imp[fr[0]] += PES_EXTREM_FRASE
        imp[fr[-1]] += PES_EXTREM_FRASE
        altes = [evs[i].alt[0].midi for i in fr]
        imp[fr[altes.index(max(altes))]] += PES_ALT_BAIX_FRASE
        imp[fr[altes.index(min(altes))]] += PES_ALT_BAIX_FRASE
    return imp


# ----------------------------------------------------------------------------- què es treu primer (R14, R15)

def _mid(e) -> int:
    return e.alt[0].midi


def _contigu(a, b) -> bool:
    return a is not None and b is not None and a.alt and b.alt and abs(a.ini + a.dur - b.ini) < _EPS


def _escrivible(d) -> bool:
    return any(abs(float(d) - x) < _EPS for x in DURADES_ESCRIVIBLES)


def _absorbeix(items, i: int, quantes: int = 1) -> bool:
    """Treu `quantes` notes seguides des de la posició i i en reparteix el temps a la nota anterior (o, si no pot, a la
    següent). Retorna si ho ha pogut fer sense deixar una durada que no sabem escriure."""
    treta = items[i:i + quantes]
    total = opFrac(sum(e.dur for e, _ in treta))
    ant = items[i - 1][0] if i > 0 else None
    seg = items[i + quantes][0] if i + quantes < len(items) else None
    if ant is not None and abs(ant.fi - treta[0][0].ini) > _EPS:
        ant = None                       # no hi ha contacte: hi ha un silenci pel mig
    if seg is not None and abs(treta[-1][0].fi - seg.ini) > _EPS:
        seg = None
    if ant is not None and ant.alt and _escrivible(ant.dur + total):
        ant.dur = opFrac(ant.dur + total)
    elif seg is not None and seg.alt and _escrivible(seg.dur + total):
        seg.ini = treta[0][0].ini
        seg.dur = opFrac(seg.dur + total)
    else:
        return False
    del items[i:i + quantes]
    return True


def _candidata(items, i: int, minim: float) -> bool:
    e, est = items[i]
    return bool(e.alt) and not est and e.dur < minim - _EPS


def _passada(items, nom: str, minim: float) -> list[float]:
    """Una passada de l'ordre R14. Retorna els instants (ini) de les notes tretes."""
    tretes: list[float] = []
    i = 1
    while i < len(items):
        if not _candidata(items, i, minim):
            i += 1
            continue
        e = items[i][0]
        ant = items[i - 1][0]
        seg = items[i + 1][0] if i + 1 < len(items) else None
        ok, quantes = False, 1
        if nom == "anticipacio":
            ok = _contigu(e, seg) and _mid(e) == _mid(seg)
        elif nom == "veina":
            ok = (_contigu(ant, e) and _contigu(e, seg) and _mid(ant) == _mid(seg)
                  and 0 < abs(_mid(e) - _mid(ant)) <= 2)
        elif nom == "canvi":
            if (i + 2 < len(items) and _candidata(items, i + 1, minim) and seg is not None):
                dos = items[i + 2][0]
                ok = (_contigu(ant, e) and _contigu(e, seg) and _contigu(seg, dos)
                      and abs(_mid(ant) - _mid(dos)) <= 2 and abs(_mid(e) - _mid(ant)) <= 2
                      and abs(_mid(seg) - _mid(dos)) <= 2)
                quantes = 2
        elif nom == "pas":
            ok = (_contigu(ant, e) and _contigu(e, seg)
                  and abs(_mid(e) - _mid(ant)) <= 2 and abs(_mid(seg) - _mid(e)) <= 2
                  and (_mid(ant) < _mid(e) < _mid(seg) or _mid(ant) > _mid(e) > _mid(seg)))
        elif nom == "salt":
            ok = _contigu(ant, e) and abs(_mid(e) - _mid(ant)) > 2
        if ok:
            ini = e.ini
            if _absorbeix(items, i, quantes):
                tretes.append(ini)
                continue
        i += 1
    return tretes


def _nums(compassos, instants) -> str:
    nums = sorted({c.num for t in instants for c in [_compas_de(compassos, t)] if c})
    parts, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        parts.append(str(nums[i]) if i == j else f"{nums[i]}-{nums[j]}")
        i = j + 1
    if len(parts) > MAX_TROSSOS_INFORME:
        return ", ".join(parts[:MAX_TROSSOS_INFORME]) + " i més"
    return ", ".join(parts)


def simplifica_melodia(evs, compassos, curs: str | None, permeses: set[str] | None = None):
    """Deixa només l'esquelet quan la melodia porta notes més curtes del que admet el nivell.
    Només es toquen les notes NO estructurals i més curtes que la figura mínima; es treuen en l'ordre R14
    (anticipacions, veïnes, canvis, pas, salts a notes curtes) i el temps de cada nota treta passa a l'anterior,
    de manera que la durada total no canvia. Retorna (evs nous, línies d'informe)."""
    minim = figura_minima(permeses, curs)
    if minim <= _EPS or not any(e.alt for e in evs):
        return evs, []
    nous = [type(e)(e.ini, e.dur, list(e.alt)) for e in evs]
    imp = importancia(nous, compassos)
    items = [[e, imp[i] >= LLINDAR_ESTRUCTURAL] for i, e in enumerate(nous)]
    treta: dict[str, list[float]] = {n: [] for n in NOM_PASSADA}
    for _ in range(3):
        quant = 0
        for nom in NOM_PASSADA:
            t = _passada(items, nom, minim)
            treta[nom] += t
            quant += len(t)
        if not quant:
            break
    res = [e for e, _ in items]
    info = []
    parts = [f"{NOM_PASSADA[n]} als compassos {_nums(compassos, ts)}" for n, ts in treta.items() if ts]
    if parts:
        info.append("He simplificat la melodia al nivell (quede l'esquelet de cada frase): " + "; ".join(parts) + ".")
    info += avisos_salts(res, compassos, curs)
    return res, info


def avisos_salts(evs, compassos, curs: str | None) -> list[str]:
    """Avís (R16) dels salts per damunt del que admet el nivell: no els toca, perquè canviarien la melodia."""
    n = nivell_de(curs)
    maxim = NIVELLS[n]["salt_max"] if n else None
    if maxim is None:
        return []
    notes = [e for e in evs if e.alt]
    grans = [b.ini for a, b in zip(notes, notes[1:]) if _contigu(a, b) and abs(_mid(b) - _mid(a)) > maxim]
    if not grans:
        return []
    return [f"La melodia té salts grans per a este nivell als compassos {_nums(compassos, grans)}; no els he tocat."]


# ----------------------------------------------------------------------------- octaves per frases (VC10, OC-01)

def _desplaca(e, octaves: int):
    q = type(e)(e.ini, e.dur, [])
    for p in e.alt:
        r = pitch.Pitch(p.nameWithOctave)
        r.octave = r.implicitOctave + octaves
        q.alt.append(r)
    return q


def talls_d_octava(evs, compassos=None) -> list[int]:
    """Posicions (índex d'esdeveniment) on una frase pot canviar d'octava sense partir un motiu: davant d'un silenci,
    després d'una nota llarga (una pulsació o més) i, si es coneixen els compassos, només a l'inici d'un compàs."""
    res = []
    for i in range(1, len(evs)):
        a, b = evs[i - 1], evs[i]
        if not b.alt and not a.alt:
            continue
        c = _compas_de(compassos, b.ini) if compassos else None
        pols = c.pols if c else 1.0
        silenci = not a.alt or not b.alt or b.ini - a.fi > _EPS
        llarga = a.alt and a.dur >= pols - _EPS
        inici_compas = c is not None and abs(b.ini - c.ini) < _EPS
        if (silenci or llarga) and (c is None or inici_compas or silenci):
            res.append(i)
    return res


def octava_per_frases(evs, lo: int, hi: int, ab_lo: int, ab_hi: int, compassos=None):
    """Mou frases SENCERES una octava quan així cauen dins de la zona còmoda [lo, hi] (en so real) i la frase veïna
    no queda a més de SALT_MAX_ENTRE_FRASES semitons. Mai a mig motiu. Retorna (evs nous, canvis) amb els canvis com
    a llista de (inici, fi, octaves) per a l'informe."""
    ix = [0] + talls_d_octava(evs, compassos) + [len(evs)]
    trams = [(a, b) for a, b in zip(ix, ix[1:]) if b > a]
    if len(trams) < 2:
        return evs, []

    def puntua(tros, sh):
        mids = [_mid(e) + sh for e in tros if e.alt]
        if not mids:
            return (0, 0)
        fora = sum(not ab_lo <= m <= ab_hi for m in mids)
        dins = sum(lo <= m <= hi for m in mids)
        return (-fora, dins)

    res: list = []
    canvis = []
    ultima = None   # última nota (midi) ja col·locada
    for a, b in trams:
        tros = evs[a:b]
        notes = [e for e in tros if e.alt]
        if not notes:
            res += tros
            continue
        millor = 0
        base = puntua(tros, 0)
        for sh in (12, -12):
            cand = puntua(tros, sh)
            if cand > puntua(tros, millor):
                millor = sh
        if millor != 0 and puntua(tros, millor) <= base:
            millor = 0
        if millor and ultima is not None and abs(_mid(notes[0]) + millor - ultima) > SALT_MAX_ENTRE_FRASES \
                and abs(_mid(notes[0]) - ultima) <= SALT_MAX_ENTRE_FRASES:
            millor = 0
        if millor:
            tros = [_desplaca(e, millor // 12) for e in tros]
            canvis.append((tros[0].ini, tros[-1].fi, millor // 12))
        res += tros
        ultima = next((_mid(e) for e in reversed(tros) if e.alt), ultima)
    return res, canvis


def text_octaves(canvis, compassos) -> list[str]:
    """Una línia d'informe per als canvis d'octava per frases."""
    if not canvis:
        return []
    parts = []
    for ini, fi, o in canvis:
        c0, c1 = _compas_de(compassos, ini), _compas_de(compassos, fi - _EPS)
        if c0 is None or c1 is None:
            continue
        lloc = f"compàs {c0.num}" if c0.num == c1.num else f"compassos {c0.num}-{c1.num}"
        parts.append(f"{lloc} {'una octava amunt' if o > 0 else 'una octava avall'}")
    return ["He canviat d'octava frases senceres perquè càpiguen a la zona còmoda: " + "; ".join(parts) + "."] if parts else []


def canvis_octava(orig, res, sh: int) -> list[tuple[float, float, int]]:
    """Els trams on `res` té una octava diferent de la de tota la melodia desplaçada `sh` semitons (els canvis per
    frase): (inici, fi, octaves de més). Per a l'informe."""
    trams: list[list] = []
    for a, b in zip(orig, res):
        if not a.alt or not b.alt:
            continue
        extra = (_mid(b) - _mid(a) - sh) // 12
        if extra == 0:
            continue
        if trams and trams[-1][2] == extra and abs(trams[-1][1] - b.ini) < 4:
            trams[-1][1] = b.fi
        else:
            trams.append([b.ini, b.fi, extra])
    return [tuple(t) for t in trams]
