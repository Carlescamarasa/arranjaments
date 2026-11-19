"""Gravat: com s'escriuen les parts perquè es lligen bé (durades i silencis per la mètrica, matisos,
articulacions i respiracions).

Què fa MuseScore sol i què ha de portar el MusicXML (comprovat amb MuseScore 4.7 sobre una exportació real):
- Barres: les respecta tal com arriben (les posa music21 per la mètrica) i les corxeres en 4/4 queden per pulsacions.
- Durades i silencis: MuseScore NO els parteix. Una blanca que travessa el mig del compàs, o un silenci de dues
  negres en 3/4, s'escriuen tal qual. Per això ho decidim ací, abans d'escriure el MusicXML.
- Matisos: han de ser objectes de compàs (Dynamic dins del Measure). Un matís penjat de la nota es perd.
- Articulacions (staccato, accent) i marca de respiració: passen bé i MuseScore les ix com a signes (la
  respiració, com una coma).
- Text d'estil + metrònom: s'escriuen en negreta damunt de la pauta superior.

Regles (ids dels digests): Gould A BM-06, BM-06b, RS-04, SU-01, SU-02, SY-01, DY-01, DY-04, AR-01, WW-01, WW-02;
Herrera ENG-01, ENG-03, ENG-04; Zamacois III Z5-15; Schoenberg AC-14.
Els valors marcats [orientatiu] són decisions de l'eina, no dels llibres: es poden canviar ací.
"""
from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass

from music21 import articulations, duration, dynamics, harmony, note, stream, tempo
from music21.common.numberTools import opFrac

_EPS = 1e-6

# --------------------------------------------------------------------------- constants ajustables

# Durades que es poden escriure amb una sola figura (amb un punt com a màxim), en negres.
FIGURES = (6.0, 4.0, 3.0, 2.0, 1.5, 1.0, 0.75, 0.5, 0.375, 0.25, 0.1875, 0.125)

# Herrera ENG-01: en 4/4 (i compassos de 4 pulsacions) cap valor travessa el mig del compàs sense lligadura,
# llevat d'estes combinacions (inici, durada) en pulsacions. [Herrera mana sobre Gould: és més estricte]
EXCEPCIONS_4_PULSACIONS = ((0, 4), (0, 3), (1, 2), (1, 3))

# Estil -> (text, negres per minut). [orientatiu] És un suggeriment: l'informe ho diu.
TEMPO_PER_ESTIL = {"ragtime": ("Ragtime", 100), "swing": ("Swing", 120), "pop": ("Pop", 100),
                   "rock": ("Rock", 120), "marxa": ("Marxa", 112), "vals": ("Vals", 120),
                   "classic": ("Moderato", 96)}

# Escala de matisos i quins es permeten en nivell elemental (el digest MA-01 de la teoria: pp p mf f ff).
ESCALA_MATISOS = ("pp", "p", "mp", "mf", "f", "ff")
MATISOS_ELEMENTAL = ("p", "mf", "f")
# Matís de la melodia per estil [orientatiu]. L'acompanyament sempre un graó per sota (Z5-15, AC-14).
MATIS_MELODIA = {"ragtime": "mf", "swing": "mf", "pop": "mf", "rock": "f", "marxa": "f", "vals": "mp",
                 "classic": "mf"}
FUNCIONS_SUAUS = ("contracant", "acompanyament", "baix", "suport", "pad", "percussio")
# Torna a escriure el matís després d'un silenci llarg (DY-04: 4 compassos o més).
COMPASSOS_RECORDATORI = 4

# Respiracions (WW-02). Funcions en què un vent fa frase i necessita respirar.
FUNCIONS_AMB_FRASE = ("melodia", "contracant", "pad", "suport")
COMPASSOS_ENTRE_RESPIRACIONS_ELEMENTAL = 2     # en nivell elemental, cada 2 compassos si no hi ha silenci
MIN_NEGRES_ENTRE_RESPIRACIONS = 3.9
SILENCI_LLARG = 2.0     # nota de 2 negres o més: la respiració li lleva una negra
SILENCI_CURT = 0.5      # nota d'entre 1 i 2 negres: li lleva una corxera. Més curta: no hi ha respiració

CLASSES_VENT = {"AltoSaxophone", "BaritoneSaxophone", "SopranoSaxophone", "TenorSaxophone", "BassClarinet",
                "BassTrombone", "Bassoon", "Clarinet", "ContrabassClarinet", "Contrabassoon", "EnglishHorn",
                "Euphonium", "Flute", "Horn", "Oboe", "Piccolo", "Trombone", "Trumpet", "Tuba"}


# --------------------------------------------------------------------------- mètrica

@dataclass(frozen=True)
class Metrica:
    barra: float
    limits: tuple            # límits de pulsació (o de grup), de 0 fins a la barra
    forts: tuple             # límits forts interiors (el mig del compàs)
    composta: bool           # compost o irregular: només es creuen pulsacions senceres
    pulsacio: float
    excepcions: tuple        # (inici, durada) que poden travessar un límit fort


def _grups_irregulars(n: int) -> tuple:
    """Agrupació d'un compàs irregular de n unitats (3+2, 2+2+3...). [orientatiu] Gould BM-06b."""
    taula = {5: (3, 2), 7: (2, 2, 3), 8: (3, 3, 2), 10: (3, 3, 2, 2), 11: (3, 3, 3, 2)}
    if n in taula:
        return taula[n]
    return (3,) * (n // 3) + ((n % 3,) if n % 3 else ())


def metrica(ts) -> Metrica:
    """L'estructura de pulsacions d'un compàs (music21 TimeSignature)."""
    num, den = ts.numerator, ts.denominator
    unitat = 4.0 / den
    barra = num * unitat
    if den >= 8:
        if num == 3 or (num % 3 == 0 and num >= 6):
            grup = 3 * unitat
            limits = tuple(opFrac(i * grup) for i in range(num // 3 + 1))
            forts = (opFrac(2 * grup),) if num == 12 else ()
            return Metrica(barra, limits, forts, True, grup, ((0, barra),))
        if num in (2, 4):
            limits = tuple(opFrac(i * unitat) for i in range(num + 1))
            return Metrica(barra, limits, (), False, unitat, ((0, barra),))
        pos, limits = 0.0, [0.0]
        for g in _grups_irregulars(num):
            pos += g * unitat
            limits.append(opFrac(pos))
        return Metrica(barra, tuple(limits), (), True, unitat * 3, ((0, barra),))
    pols = unitat
    limits = tuple(opFrac(i * pols) for i in range(num + 1))
    if num == 4:
        return Metrica(barra, limits, (opFrac(2 * pols),), False, pols,
                       tuple((opFrac(a * pols), opFrac(b * pols)) for a, b in EXCEPCIONS_4_PULSACIONS))
    forts = (opFrac(3 * pols),) if num == 6 else ()
    return Metrica(barra, limits, forts, False, pols, ((0, barra),))


def _iguals(a, b) -> bool:
    return abs(a - b) < _EPS


def _representable(d: float) -> bool:
    return any(_iguals(d, f) for f in FIGURES)


def _dyadic(*valors) -> bool:
    return all(abs(v * 16 - round(v * 16)) < 1e-4 for v in valors)


def _legal(a: float, b: float, m: Metrica) -> bool:
    """Pot escriure's [a,b) amb una sola figura sense amagar la pulsació?"""
    prev = max(l for l in m.limits if l <= a + _EPS)
    seg = [l for l in m.limits if l > a + _EPS]
    seg_next = min(seg) if seg else m.barra
    if m.composta:
        a_en_limit = any(_iguals(a, l) for l in m.limits)
        b_en_limit = any(_iguals(b, l) for l in m.limits)
        return (a_en_limit and b_en_limit) or b <= seg_next + _EPS
    if _iguals(a, prev):
        return True
    if b <= seg_next + _EPS:
        return True
    # la negra a contratemps (corxera-negra-corxera): l'única que travessa una pulsació en simple
    return _iguals(a - prev, m.pulsacio / 2) and _iguals(b - a, m.pulsacio)


def _binari(d: float) -> list[float]:
    """Descomposició d'una durada en figures, de la més llarga a la més curta."""
    res, resta = [], d
    while resta > _EPS:
        f = next((x for x in FIGURES if x <= resta + _EPS), None)
        if f is None:
            res.append(resta)
            break
        res.append(f)
        resta -= f
    return res


def _tros(a: float, b: float, m: Metrica) -> list[tuple[float, float]]:
    if b - a < _EPS:
        return []
    forts = [f for f in m.forts if a + _EPS < f < b - _EPS]
    exempt = any(_iguals(a, i) and _iguals(b - a, d) for i, d in m.excepcions)
    if forts and not exempt:
        f = forts[0]
        return _tros(a, f, m) + _tros(f, b, m)
    if _legal(a, b, m) and _representable(b - a):
        return [(a, b)]
    dins = [l for l in m.limits if a + _EPS < l < b - _EPS]
    if dins:
        return _tros(a, dins[0], m) + _tros(dins[0], b, m)
    res, p = [], a
    for d in _binari(b - a):
        res.append((p, p + d))
        p += d
    return res


def parteix_durada(inici: float, dur: float, ts) -> list[float]:
    """Una nota que comença a `inici` (dins del compàs, en negres) i dura `dur`: les figures lligades que
    la porten segons la mètrica (Herrera ENG-01 per a 4/4, Gould SU-01 i SU-02 per a la resta).
    Les durades irregulars (tresets...) es deixen com arriben."""
    m = metrica(ts)
    inici, dur = float(inici), float(dur)
    if not _dyadic(inici, dur) or inici + dur > m.barra + _EPS or dur < _EPS:
        return [opFrac(dur)]
    return [opFrac(b - a) for a, b in _tros(inici, inici + dur, m)]


def parteix_silenci(inici: float, dur: float, ts) -> list[float]:
    """Un silenci agrupat per pulsacions (Gould RS-04): mai travessa la pulsació, en 4/4 només es veu la meitat
    del compàs, en 3/4 sempre per pulsació, i el compàs sencer és un sol silenci."""
    m = metrica(ts)
    inici, dur = float(inici), float(dur)
    fi = inici + dur
    if not _dyadic(inici, dur) or fi > m.barra + _EPS or dur < _EPS:
        return [opFrac(dur)]
    if _iguals(inici, 0) and _iguals(dur, m.barra):
        return [opFrac(dur)]
    meitats, ext = [], [0.0, *m.forts, m.barra]
    if m.forts:
        meitats = list(zip(ext[:-1], ext[1:]))
    grups = list(zip(m.limits[:-1], m.limits[1:]))
    res, p = [], inici
    while p < fi - _EPS:
        pas = next(((h0, h1) for h0, h1 in meitats if _iguals(p, h0) and h1 <= fi + _EPS), None)
        if pas is None:
            pas = next(((g0, g1) for g0, g1 in grups if _iguals(p, g0) and g1 <= fi + _EPS), None)
        if pas is not None:
            res.append(opFrac(pas[1] - pas[0]))
            p = pas[1]
            continue
        g0, g1 = next((g0, g1) for g0, g1 in grups if g0 - _EPS <= p < g1 - _EPS)
        lim = min(fi, g1)
        for L in (1.0, 0.5, 0.25, 0.125):
            q = (p - g0) / L
            if abs(q - round(q)) < 1e-6 and p + L <= lim + _EPS:
                res.append(opFrac(L))
                p += L
                break
        else:
            res.append(opFrac(fi - p))
            break
    return res


# --------------------------------------------------------------------------- escriptura de notes i silencis

def talla_nota(x, inici: float, dur: float, ts, ve: bool = False, va: bool = False) -> list:
    """`x` és una nota o un acord ja creat (sense lligadura). Torna la cadena de notes lligades que el
    representen. `ve`/`va`: ja ve lligada del compàs anterior / continua en el següent."""
    from music21 import tie
    trossos = parteix_durada(inici, dur, ts)
    res = []
    for i, q in enumerate(trossos):
        y = copy.deepcopy(x) if i else x
        y.quarterLength = q
        entra = ve if i == 0 else True
        ix = va if i == len(trossos) - 1 else True
        if entra and ix:
            y.tie = tie.Tie("continue")
        elif ix:
            y.tie = tie.Tie("start")
        elif entra:
            y.tie = tie.Tie("stop")
        res.append(y)
    return res


def silencis(inici: float, dur: float, ts) -> list:
    return [note.Rest(quarterLength=q) for q in parteix_silenci(inici, dur, ts)]


def agrupa_silencis(cont, ts) -> None:
    """Torna a escriure els silencis seguits d'un compàs (o veu) agrupats per la mètrica."""
    elements = list(cont.notesAndRests)
    runs, actual = [], []
    for e in elements:
        if e.isRest and (not actual or _iguals(actual[-1].offset + actual[-1].quarterLength, e.offset)):
            actual.append(e)
            continue
        if actual:
            runs.append(actual)
        actual = [e] if e.isRest else []
    if actual:
        runs.append(actual)
    for run in runs:
        ini = float(run[0].offset)
        total = float(sum(r.quarterLength for r in run))
        for r in run:
            cont.remove(r)
        p = ini
        for q in parteix_silenci(ini, total, ts):
            cont.insert(opFrac(p), note.Rest(quarterLength=q))
            p += float(q)


def regrafia_part(part: stream.Stream) -> int:
    """Per a peces importades: torna a escriure les durades i els silencis de cada compàs segons la mètrica.
    Treballa compàs a compàs i només en compassos senzills (una sola veu, sense tresets). Torna quants
    compassos ha canviat."""
    canviats = 0
    ts = None
    for m in part.getElementsByClass(stream.Measure):
        if m.timeSignature is not None:
            ts = m.timeSignature
        if ts is None or m.getElementsByClass(stream.Voice) or m.duration.quarterLength > ts.barDuration.quarterLength + _EPS:
            continue
        elems = list(m.notesAndRests)
        if not elems or any(not _dyadic(float(e.offset), float(e.quarterLength)) or e.duration.tuplets for e in elems):
            continue
        antes = [(float(e.offset), float(e.quarterLength)) for e in elems]
        fets, i = [], 0
        while i < len(elems):
            e = elems[i]
            if e.isRest:
                j = i
                while j + 1 < len(elems) and elems[j + 1].isRest:
                    j += 1
                fets.append(("r", float(e.offset), float(elems[j].offset + elems[j].quarterLength) - float(e.offset), e))
                i = j + 1
                continue
            j = i
            if e.tie is not None and e.tie.type == "start":
                while (j + 1 < len(elems) and not elems[j + 1].isRest and elems[j + 1].tie is not None
                       and elems[j + 1].tie.type in ("continue", "stop") and _mateixes(e, elems[j + 1])
                       and elems[j].tie.type in ("start", "continue")):
                    j += 1
                    if elems[j].tie.type == "stop":
                        break
            ve = e.tie is not None and e.tie.type in ("stop", "continue")
            va = elems[j].tie is not None and elems[j].tie.type in ("start", "continue")
            fets.append(("n", float(e.offset), float(elems[j].offset + elems[j].quarterLength) - float(e.offset),
                         (e, ve, va)))
            i = j + 1
        nous = []
        for tipus, off, d, dada in fets:
            if tipus == "r":
                nous += [(off + sum(float(q) for q in parteix_silenci(off, d, ts)[:k]), r)
                         for k, r in enumerate(silencis(off, d, ts))]
            else:
                e, ve, va = dada
                base = copy.deepcopy(e)
                base.tie = None
                for k, y in enumerate(talla_nota(base, off, d, ts, ve, va)):
                    nous.append((off + sum(float(q) for q in parteix_durada(off, d, ts)[:k]), y))
        despres = [(o, float(y.quarterLength)) for o, y in nous]
        if despres == antes:
            continue
        for e in elems:
            m.remove(e)
        for o, y in nous:
            m.insert(opFrac(o), y)
        canviats += 1
    return canviats


def _mateixes(a, b) -> bool:
    return sorted(p.nameWithOctave for p in getattr(a, "pitches", ())) == \
        sorted(p.nameWithOctave for p in getattr(b, "pitches", ()))


# --------------------------------------------------------------------------- tempo d'estil

def tempo_estil(estil: str, ts):
    """Marca de tempo (text d'estil + metrònom) per a una peça que no en porta. [orientatiu]"""
    text, negres = TEMPO_PER_ESTIL[estil]
    if ts.denominator >= 8 and ts.numerator % 3 == 0 and ts.numerator >= 6:
        return tempo.MetronomeMark(text=text, number=round(negres * 2 / 3), referent=duration.Duration(1.5))
    return tempo.MetronomeMark(text=text, number=negres, referent=duration.Duration(1.0))


def text_tempo(estil: str, ts) -> str:
    mm = tempo_estil(estil, ts)
    unitat = "negra amb punt" if mm.referent.quarterLength == 1.5 else "negra"
    return (f"He posat el tempo «{mm.text}» amb {unitat} = {int(mm.number)}: la peça no en duia. "
            "És un suggeriment, ajusta'l al grup.")


# --------------------------------------------------------------------------- matisos

def _permesos(elemental: bool) -> tuple:
    return MATISOS_ELEMENTAL if elemental else ESCALA_MATISOS


def nivell_matis(estil: str, funcio: str, elemental: bool) -> str:
    """El matís d'una funció: la melodia el de l'estil; la resta, un graó per sota entre els permesos."""
    permesos = _permesos(elemental)
    idx = ESCALA_MATISOS.index(MATIS_MELODIA.get(estil, "mf"))
    cand = sorted(permesos, key=lambda n: (abs(ESCALA_MATISOS.index(n) - idx), -ESCALA_MATISOS.index(n)))
    mel = cand[0]
    if funcio not in FUNCIONS_SUAUS:
        return mel
    baix = [n for n in permesos if ESCALA_MATISOS.index(n) < ESCALA_MATISOS.index(mel)]
    return baix[-1] if baix else mel


def _notes_amb_temps(part) -> list:
    """(inici absolut, nota) de cada nota sonora de la part, ordenades."""
    res = []
    for m in part.getElementsByClass(stream.Measure):
        for n in m.recurse().notes:
            if isinstance(n, (note.Rest, harmony.Harmony)) or not hasattr(n, "articulations"):
                continue
            res.append((float(m.offset) + float(n.getOffsetInHierarchy(m)), n, m))
    res.sort(key=lambda x: x[0])
    return res


def _es_continuacio(n) -> bool:
    return n.tie is not None and n.tie.type in ("stop", "continue")


def _beat_feble(off_metric: float, m: Metrica) -> bool:
    """Temps feble (2 i 4 en 4/4, 2 en 2/4...): la pulsació de sentit senar."""
    k = int(round(off_metric / m.pulsacio)) if abs(off_metric / m.pulsacio - round(off_metric / m.pulsacio)) < 1e-6 else None
    return k is not None and k % 2 == 1


def _contratemps(off_metric: float, m: Metrica) -> bool:
    """Atac fora de la pulsació (per exemple la segona corxera d'un temps)."""
    q = off_metric / m.pulsacio
    return abs(q - round(q)) > 1e-6


def posa_matisos_i_articulacions(construides, rols, seccions, compassos, estil: str, elemental: bool) -> dict:
    """Matisos coherents per funció (la melodia un graó per damunt de la resta) i articulacions per estil.
    `construides`: llista (Rol, [parts], ...) en so real. `seccions`: les Seccio de la rotació (o buida:
    cada rol fa sempre el mateix). Torna un resum: {nom de part: [matisos posats]}."""
    resum: dict = {}
    if not compassos:
        return resum
    fi_total = compassos[-1].fi
    barres = {}
    for r, pp, _ in construides:
        idx = next((i for i, x in enumerate(rols) if x is r), None)
        if seccions and idx is not None:
            talls = [(s.ini, s.fi, s.funcions.get(idx, r.rol)) for s in seccions]
        else:
            talls = [(compassos[0].ini, fi_total, r.rol)]
        nom = r.instr.nom
        posats = resum.setdefault(nom, [])
        notes_parts = [_notes_amb_temps(p) for p in pp]
        ultim_nivell, fi_anterior = None, None
        for ini, fi, funcio in talls:
            nivell = nivell_matis(estil, funcio, elemental)
            # el piano de dos pentagrames: el matís va al pentagrama de baix si hi sona, i si no al d'alt
            triat = None
            for lli in reversed(notes_parts):
                triat = next((x for x in lli if ini - _EPS <= x[0] < fi - _EPS and not _es_continuacio(x[1])), None)
                if triat:
                    break
            if triat is None:
                continue
            recordatori = fi_anterior is not None and (triat[0] - fi_anterior) >= COMPASSOS_RECORDATORI * \
                float(compassos[0].ts.barDuration.quarterLength)
            if nivell != ultim_nivell or recordatori:
                triat[2].insert(opFrac(float(triat[1].getOffsetInHierarchy(triat[2]))), dynamics.Dynamic(nivell))
                posats.append(nivell)
                ultim_nivell = nivell
            ult = [x for lli in notes_parts for x in lli if ini - _EPS <= x[0] < fi - _EPS]
            if ult:
                fi_anterior = max(x[0] + float(x[1].quarterLength) for x in ult)
            if r.instr.percussio:
                continue
            for lli in notes_parts:
                for t, n, mes in lli:
                    if not (ini - _EPS <= t < fi - _EPS) or _es_continuacio(n):
                        continue
                    c = next((c for c in compassos if c.ini - _EPS <= t < c.fi - _EPS), None)
                    if c is None:
                        continue
                    pad = float(c.ts.barDuration.quarterLength - c.dur) if c.anacrusi else 0.0
                    off = t - c.ini + pad
                    barres[id(c)] = metrica(c.ts)
                    _articula(n, estil, funcio, off, float(n.quarterLength), barres[id(c)])
    return resum


def _articula(n, estil: str, funcio: str, off: float, dur: float, m: Metrica) -> None:
    """Articulació per estil i funció (Herrera ENG-03, Gould AR-01, Schoenberg AC-14). Només notes curtes:
    una nota llarga no es posa en staccato."""
    curta = dur <= m.pulsacio + _EPS
    feble = _beat_feble(off, m)
    if estil == "marxa" and funcio in ("baix", "suport", "acompanyament") and curta:
        n.articulations.append(articulations.Staccato())
    elif estil == "ragtime":
        if funcio == "baix" and curta:
            n.articulations.append(articulations.Staccato())
        elif funcio == "acompanyament" and feble and curta:
            n.articulations.append(articulations.Staccato())
    elif estil == "swing" and funcio == "acompanyament" and curta and (feble or _contratemps(off, m)):
        # el comping de swing toca avançat mig temps (Levine CP01): l'accent va també al contratemps
        n.articulations.append(articulations.Accent())
    elif estil == "vals" and funcio in ("baix", "suport") and _iguals(off, 0.0):
        n.articulations.append(articulations.Accent())


# --------------------------------------------------------------------------- respiracions

def es_vent(instr) -> bool:
    return getattr(instr, "classe", None) in CLASSES_VENT


def respiracions(evs: list, talls: list, instr, compassos: list, elemental: bool, corxeres: bool = True):
    """Per a un vent: on respira. Torna (evs nous, instants on acaba la nota que respira).
    `talls`: [(inici, fi, funcio)] de cada frase. Respira al final de cada frase en què fa de melodia, contracant
    o pad, i en elemental també cada 2 compassos si no hi ha cap silenci. La nota anterior s'escurça (WW-02):
    el temps de la respiració es resta d'ella (`corxeres` fals: mai un silenci menor que la negra). Si ja hi ha un silenci, no cal marca (el silenci no implica respiració)."""
    if not es_vent(instr):
        return evs, []
    fi_peca = compassos[-1].fi if compassos else 0
    punts = []
    for ini, fi, funcio in talls:
        if funcio not in FUNCIONS_AMB_FRASE:
            continue
        if elemental:
            cs = [c for c in compassos if ini - _EPS <= c.ini < fi - _EPS]
            for k in range(COMPASSOS_ENTRE_RESPIRACIONS_ELEMENTAL, len(cs), COMPASSOS_ENTRE_RESPIRACIONS_ELEMENTAL):
                punts.append((cs[k].ini, cs[k - COMPASSOS_ENTRE_RESPIRACIONS_ELEMENTAL].ini))
        if fi < fi_peca - _EPS:
            punts.append((fi, ini))
    sonores = [e for e in evs if e.alt]
    nous = list(evs)
    marques, ultima = [], None
    for t, des_de in sorted(set(punts)):
        prev = next((e for e in sonores if _iguals(e.fi, t)), None)
        seg = next((e for e in sonores if _iguals(e.ini, t)), None)
        if prev is None or seg is None:
            continue
        if ultima is not None and t - ultima < MIN_NEGRES_ENTRE_RESPIRACIONS:
            continue
        finestra = [e for e in sonores if des_de - _EPS <= e.ini < t - _EPS]
        if any(b.ini - a.fi >= 0.5 - _EPS for a, b in zip(finestra, finestra[1:])):
            continue
        gap = SILENCI_LLARG / 2 if prev.dur >= SILENCI_LLARG - _EPS else SILENCI_CURT if prev.dur >= 1.0 - _EPS else None
        if gap is not None and not corxeres and gap < 1.0:
            gap = None      # el nivell no té corxeres: no es pot deixar un silenci més curt que la negra
        if gap is None:
            continue
        nou = dataclasses.replace(prev, dur=opFrac(prev.dur - gap))
        nous = [nou if e is prev else e for e in nous]
        sonores = [nou if e is prev else e for e in sonores]
        marques.append(nou.fi)
        ultima = t
    return nous, marques


def marca_respiracions(part: stream.Stream, marques: list) -> None:
    """Posa la marca de respiració a la nota que acaba a cada instant de `marques`."""
    if not marques:
        return
    for t, n, _ in _notes_amb_temps(part):
        fi = t + float(n.quarterLength)
        if any(_iguals(fi, q) for q in marques) and not any(isinstance(a, articulations.BreathMark)
                                                            for a in n.articulations):
            n.articulations.append(articulations.BreathMark())
