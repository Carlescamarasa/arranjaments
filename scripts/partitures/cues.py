"""Cues (paquet 12): notes petites que ajuden l'alumne a no perdre el compte i que cobreixen un instrument absent.

- Cues d'orientació (Gould PRT-10, PRT-11): després d'un silenci llarg, els dos últims compassos del silenci
  porten una línia que l'alumne pot sentir (de qui toca al seu voltant), en notes petites, amb el nom de
  l'instrument («+ Fl.»). Es posen ABANS de passar a altura escrita, així queden transposades a l'instrument que les llig.
- Cues d'instrument absent (Gould LAY-16, BND-04): el baix o el contracant, en notes petites, a l'instrument de
  registre més pròxim, només on este calla, amb l'avís «Toqueu les notes petites si falta ...».
- `silencia_cues_xml`: marca les notes petites com a `<cue/>` al MusicXML perquè MuseScore no les reproduïsca.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from pathlib import Path

from music21 import expressions, note, stream

# Llindars [inferència] ajustables. PRT-10: «> ~4-8 compassos; elemental >= 4».
MIN_SILENCI_ELEMENTAL = 4
MIN_SILENCI_GENERAL = 8
COMPASSOS_CUE = 2                    # PRT-10: 1 a 2 compassos, acabant un compàs abans de l'entrada
MIN_COMPASSOS_ABSENTS = 2            # un tros d'instrument absent més curt no val la pena
PES_ROL = {"melodia": 3.0, "contracant": 2.5, "suport": 1.0, "baix": 1.0, "pad": 0.2, "acompanyament": 0.0}
PES_PORTADOR = 4.0                   # qui porta la melodia en eixa frase és el millor candidat
FUNCIONS_ABSENTS = ("contracant", "baix", "suport")
MIDA_CUE = "cue"


@dataclass
class CueInfo:
    tipus: str            # "orientacio" o "absent"
    receptor: str
    origen: str
    compassos: list[int]  # números de compàs
    transposicio: int = 0   # semitons d'octava aplicats


# --------------------------------------------------------------------------- utilitats

def _mesures(part: stream.Part) -> list[stream.Measure]:
    return list(part.getElementsByClass(stream.Measure))


def _buit(m: stream.Measure) -> bool:
    return not any(True for _ in m.recurse().notes)


def _runs_buits(ms: list[stream.Measure]) -> list[tuple[int, int]]:
    runs, ini = [], None
    for i, m in enumerate(ms):
        if _buit(m):
            if ini is None:
                ini = i
        elif ini is not None:
            runs.append((ini, i - 1))
            ini = None
    if ini is not None:
        runs.append((ini, len(ms) - 1))
    return runs


def _notes_simples(m: stream.Measure):
    """Notes soles (sense acords ni notes de adorn) d'un compàs, o None si no és una línia simple."""
    res = []
    for e in m.notes:
        if e.isChord or e.duration.isGrace:
            return None
        res.append(e)
    # veus encavalcades: no és una línia
    fi = 0.0
    for e in sorted(res, key=lambda x: x.offset):
        if e.offset < fi - 1e-6:
            return None
        fi = e.offset + e.quarterLength
    return sorted(res, key=lambda x: x.offset)


def _cap_dins(notes, lo: int, hi: int, despl: int) -> bool:
    return all(lo <= n.pitch.midi + despl <= hi for n in notes)


def _desplaçament(notes, lo: int, hi: int) -> int | None:
    """Desplaçament d'octava (el mínim) perquè totes les notes càpiguen al registre del receptor."""
    for d in (0, -12, 12, -24, 24):
        if _cap_dins(notes, lo, hi, d):
            return d
    return None


def _escriu_cue(m: stream.Measure, origen: list, despl: int) -> None:
    """Reemplaça els silencis d'un compàs buit per les notes petites (copiades) amb els silencis de farciment."""
    for r in list(m.getElementsByClass(note.Rest)):
        m.remove(r)
    dur = m.barDuration.quarterLength
    t = 0.0
    for e in origen:
        if e.offset + e.quarterLength > dur + 1e-6:
            break
        if e.offset > t + 1e-6:
            m.insert(t, note.Rest(quarterLength=e.offset - t))
        n = note.Note()
        n.pitch = copy.deepcopy(e.pitch)
        if despl:
            n.pitch.octave = e.pitch.octave + despl // 12     # només octaves: l'escriptura (sostinguts o bemolls) es manté
        n.quarterLength = e.quarterLength
        n.style.noteSize = MIDA_CUE
        m.insert(e.offset, n)
        t = e.offset + e.quarterLength
    if t < dur - 1e-6:
        m.insert(t, note.Rest(quarterLength=dur - t))


def _etiqueta(m: stream.Measure, text: str) -> None:
    te = expressions.TextExpression(text)
    te.placement = "above"
    m.insert(0, te)


def _unitats_aptes(construides):
    """Les parts d'una sola pauta amb altura: receptors i orígens possibles."""
    return [(i, r, pp[0]) for i, (r, pp, _e) in enumerate(construides) if len(pp) == 1 and not r.instr.percussio]


# --------------------------------------------------------------------------- cues d'orientació

def cues_orientacio(construides, rang, elemental: bool, seccions=None, rols=None) -> list[CueInfo]:
    """Per a cada silenci prou llarg, dos compassos de cue abans de l'entrada. `rang(instr)` dona el registre
    (concert) on pot tocar un instrument. `seccions` i `rols` (opcionals) permeten preferir qui porta la melodia."""
    minim = MIN_SILENCI_ELEMENTAL if elemental else MIN_SILENCI_GENERAL
    aptes = _unitats_aptes(construides)
    mesures = {i: _mesures(p) for i, _r, p in aptes}
    # silencis de TOTES les parts calculats abans de posar res (una cue no ha de crear silencis nous ni tapar-ne)
    runs = {i: _runs_buits(mesures[i]) for i, _r, _p in aptes}
    posades: list[CueInfo] = []
    for i, r, _p in aptes:
        ms = mesures[i]
        for a, b in runs[i]:
            if b - a + 1 < minim or b + 1 >= len(ms):
                continue
            c0 = b - COMPASSOS_CUE + 1
            millor = _tria_origen(i, c0, b, aptes, mesures, rang, r, seccions, rols)
            if millor is None:
                continue
            j, rj, origen, despl = millor
            for k in range(c0, b + 1):
                _escriu_cue(ms[k], origen[k - c0], despl)
            _etiqueta(ms[c0], f"+ {rj.instr.abreviatura}")
            posades.append(CueInfo("orientacio", r.instr.nom, rj.instr.nom, [_num(ms[k], k) for k in range(c0, b + 1)],
                                   despl))
    return posades


def _num(m: stream.Measure, k: int) -> int:
    return m.number if m.number is not None else k + 1


def _tria_origen(i, c0, c1, aptes, mesures, rang, r_rec, seccions, rols):
    """La millor part per a copiar-ne els compassos c0..c1: línia simple amb notes en l'últim compàs, el més
    melòdica possible, i que càpiga al registre del receptor."""
    lo, hi = rang(r_rec.instr)
    millor = None
    for j, rj, pj in aptes:
        if j == i:
            continue
        mj = mesures[j]
        trams = [_notes_simples(mj[k]) for k in range(c0, c1 + 1)]
        if any(t is None for t in trams) or not trams[-1] or sum(len(t) for t in trams) < 2:
            continue
        notes = [n for t in trams for n in t]
        d = _desplaçament(notes, lo, hi)
        if d is None:
            continue
        pes = PES_ROL.get(rj.rol, 0.0)
        ix = _index(rols, rj)
        if seccions and ix is not None:
            for s in seccions:
                if s.i0 <= c1 < s.i1 and s.portador == ix:
                    pes += PES_PORTADOR
        pes -= abs(d) / 24.0
        if millor is None or pes > millor[0]:
            millor = (pes, j, rj, trams, d)
    if millor is None:
        return None
    return millor[1], millor[2], millor[3], millor[4]


# --------------------------------------------------------------------------- cues d'instrument absent

def cues_absents(construides, rang, seccions=None, rols=None, article=None) -> list[CueInfo]:
    """Posa el baix i el contracant (en notes petites) a l'instrument de registre més pròxim, als compassos on
    este calla. `article(instr)` dona el nom amb article («el trombó») per a l'avís."""
    aptes = _unitats_aptes(construides)
    mesures = {i: _mesures(p) for i, _r, p in aptes}
    posades: list[CueInfo] = []
    ja_avisat: set[int] = set()

    def registre(j):
        mids = [n.pitch.midi for m in mesures[j] for n in m.notes if not n.isChord]
        return sum(mids) / len(mids) if mids else None

    for ia, ra, _pa in aptes:
        if ra.rol not in ("baix", "contracant"):
            continue
        mia = registre(ia)
        if mia is None:
            continue
        # candidats per registre pròxim
        cands = sorted((abs((registre(j) or mia) - mia), j) for j, rj, _p in aptes
                       if j != ia and rj.instr.clau != ra.instr.clau)
        n_comp = len(mesures[ia])
        actius = [False] * n_comp
        for k, m in enumerate(mesures[ia]):
            actius[k] = (not _buit(m)) and _funcio(seccions, rols, ra, k) in FUNCIONS_ABSENTS
        for _d, j in cands:
            if any(c.origen == ra.instr.nom and c.tipus == "absent" for c in posades):
                break        # un sol instrument de reemplaçament per línia: el de registre més pròxim que la pot tocar
            rj = next(r for jj, r, _p in aptes if jj == j)
            lo, hi = rang(rj.instr)
            mj = mesures[j]
            k = 0
            while k < n_comp:
                if not (actius[k] and _buit(mj[k])):
                    k += 1
                    continue
                k0 = k
                while k < n_comp and actius[k] and _buit(mj[k]):
                    k += 1
                if k - k0 < MIN_COMPASSOS_ABSENTS:
                    continue
                trams = [_notes_simples(mesures[ia][x]) for x in range(k0, k)]
                if any(t is None for t in trams):
                    continue
                notes = [n for t in trams for n in t]
                d = _desplaçament(notes, lo, hi)
                if d is None:
                    continue
                for x in range(k0, k):
                    _escriu_cue(mj[x], trams[x - k0], d)
                    actius[x] = False   # ja cobert: un altre candidat no el repeteix
                nom = article(ra.instr) if article else ra.instr.nom
                _etiqueta(mj[k0], ("Toqueu les notes petites si falta " if j not in ja_avisat else "Si falta ") + nom)
                ja_avisat.add(j)
                posades.append(CueInfo("absent", rj.instr.nom, ra.instr.nom, [_num(mj[x], x) for x in range(k0, k)], d))
    return posades


def _funcio(seccions, rols, r, k) -> str:
    """Funció del rol en el compàs k (índex): la de la frase si hi ha rotació, o la del rol."""
    ix = _index(rols, r)
    if seccions and ix is not None:
        for s in seccions:
            if s.i0 <= k < s.i1 and ix in s.funcions:
                return s.funcions[ix]
    return r.rol


def _index(rols, r):
    """Posició d'un rol a la llista (per identitat: dos rols iguals no es confonen)."""
    return next((i for i, x in enumerate(rols or ()) if x is r), None)


# --------------------------------------------------------------------------- informe i MusicXML

def text_cues(cues: list[CueInfo]) -> list[str]:
    res = []
    for c in cues:
        comp = f"compàs {c.compassos[0]}" if len(c.compassos) == 1 else f"compassos {c.compassos[0]} a {c.compassos[-1]}"
        if c.tipus == "orientacio":
            res.append(f"  Cue d'orientació a {c.receptor} ({comp}), de {c.origen}.")
        else:
            res.append(f"  Cue de {c.origen} a {c.receptor} ({comp}), per si falta.")
    return res


_RE_NOTA = re.compile(r"<note(?P<a>[^>]*)>(?P<cos>.*?)</note>", re.S)


def silencia_cues_xml(ruta: str | Path) -> int:
    """Afig `<cue />` a les notes petites d'un MusicXML (MuseScore les dibuixa petites i no les reprodueix).
    Retorna quantes n'ha marcat. Si no n'hi ha cap, no toca el fitxer."""
    ruta = Path(ruta)
    t = ruta.read_text(encoding="utf-8")
    if 'size="cue"' not in t:
        return 0
    n = 0

    def canvia(m):
        nonlocal n
        cos = m.group("cos")
        if 'size="cue"' not in cos or "<cue" in cos or "<rest" in cos:
            return m.group(0)
        n += 1
        return f"<note{m.group('a')}><cue />{cos}</note>"

    nou = _RE_NOTA.sub(canvia, t)
    if n:
        ruta.write_text(nou, encoding="utf-8")
    return n
