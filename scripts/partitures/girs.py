"""Girs de pàgina de les particel·les (paquet 12, Gould PRT-05, PRT-06 i LAY-08).

MuseScore no optimitza els girs. Com ho fa este mòdul (comprovat amb MuseScore 4.7):
1. Es genera la particel·la i es demana a MuseScore la posició de cada compàs (`-o fitxer.mpos`, que diu en quina
   pàgina cau cada «caixa» de lectura). Un silenci multicompàs és una sola caixa (vegeu `parts.unitats_de_lectura`).
2. Si la part té més d'una pàgina, primer es prova de fer-la càpiga en una sola (PRT-06) amb una pauta un graó més xicoteta.
3. Si no, es comprova que cada gir cau en un silenci d'almenys 4 segons (5 el contrabaix). Si no, es força un salt de
   pàgina (`<print new-page>`) just després del silenci llarg més proper per darrere, i es torna a comprovar.
4. Si no hi ha cap silenci prou llarg, es deixa com està i es diu a l'informe.

Tot depèn de saber a quina pàgina cau cada compàs. Si el nombre de caixes que ha donat MuseScore no quadra amb el que
calcula el codi, no s'adivina res: es renuncia als girs d'eixa part i es diu a l'informe.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from music21 import layout, stream

from . import parts as _parts

SEGONS_GIR = 4.0                  # PRT-05
SEGONS_GIR_CONTRABAIX = 5.0
BPM_PER_DEFECTE = 100.0           # [inferència] si la partitura no porta tempo
MAX_ITERACIONS = 4
OMPLERT_MINIM = 0.5               # [inferència] un salt forçat ha de deixar la pàgina plena almenys a la meitat


@dataclass
class Gir:
    compas_nou: int       # índex del primer compàs de la pàgina següent
    pagina_nova: int      # número de pàgina (1 = primera)
    segons: float         # silenci disponible al voltant del gir
    be: bool


def segons_minims(clau_instrument: str) -> float:
    return SEGONS_GIR_CONTRABAIX if clau_instrument == "contrabaix" else SEGONS_GIR


def pagines_de_mpos(text: str) -> list[int]:
    """Pàgina (0 = primera) de cada element de lectura, en l'ordre en què MuseScore els dona."""
    return [int(p) for p in re.findall(r'<element\b[^>]*\bpage="(\d+)"', text)]


def _segons_compas(m: stream.Measure, bpm: float) -> float:
    return float(m.barDuration.quarterLength) * 60.0 / bpm


def pagines_per_compas(part: stream.Part, pagines: list[int]) -> list[int] | None:
    """Pàgina de cada compàs, o None si el que diu MuseScore no quadra amb les caixes calculades."""
    unitats = _parts.unitats_de_lectura(part)
    if len(unitats) != len(pagines):
        return None
    n = len(list(part.getElementsByClass(stream.Measure)))
    res = [0] * n
    for (a, b), p in zip(unitats, pagines):
        for i in range(a, b + 1):
            res[i] = p
    if any(y < x for x, y in zip(res, res[1:])):
        return None
    return res


def nombre_pagines(pagines: list[int]) -> int:
    return (max(pagines) + 1) if pagines else 1


def _buits_voltant(ms: list, e: int) -> tuple[int, int]:
    """Compassos buits consecutius que acaben en e, i que comencen en e+1."""
    abans = 0
    i = e
    while i >= 0 and _parts.es_buit(ms[i]):
        abans += 1
        i -= 1
    despres = 0
    i = e + 1
    while i < len(ms) and _parts.es_buit(ms[i]):
        despres += 1
        i += 1
    return abans, despres


def avalua_girs(part: stream.Part, pag_compas: list[int], bpm: float, minim: float) -> list[Gir]:
    ms = list(part.getElementsByClass(stream.Measure))
    girs = []
    for i in range(1, len(ms)):
        if pag_compas[i] == pag_compas[i - 1]:
            continue
        abans, despres = _buits_voltant(ms, i - 1)
        segons = (abans + despres) * _segons_compas(ms[i - 1], bpm)
        girs.append(Gir(i, pag_compas[i] + 1, segons, abans >= 1 and segons >= minim))
    return girs


def proposa_salt(part: stream.Part, gir: Gir, pag_compas: list[int], bpm: float, minim: float) -> int | None:
    """Índex del compàs que ha de començar la pàgina nova per a que el gir caiga en un silenci llarg: el silenci
    llarg més pròxim per darrere del gir, dins de la mateixa pàgina. None si no n'hi ha cap."""
    ms = list(part.getElementsByClass(stream.Measure))
    pagina = pag_compas[gir.compas_nou - 1]
    inici = min(i for i, p in enumerate(pag_compas) if p == pagina)
    millor = None
    i = 0
    while i < len(ms):
        if not _parts.es_buit(ms[i]):
            i += 1
            continue
        a = i
        while i < len(ms) and _parts.es_buit(ms[i]):
            i += 1
        b = i - 1
        nou = b + 1
        if nou >= len(ms) or nou >= gir.compas_nou or pag_compas[a] != pagina:
            continue
        if (b - a + 1) * _segons_compas(ms[a], bpm) < minim:
            continue
        if nou - inici < OMPLERT_MINIM * (gir.compas_nou - inici):
            continue        # deixaria la pàgina quasi buida
        if ms[nou].getElementsByClass(layout.PageLayout):
            continue
        millor = nou          # l'últim (el més proper al gir) guanya
    return millor


def posa_salt_pagina(part: stream.Part, index: int) -> None:
    """Salt de pàgina abans del compàs `index` (substitueix un salt de sistema, que ja va inclòs)."""
    m = list(part.getElementsByClass(stream.Measure))[index]
    for s in list(m.getElementsByClass(layout.SystemLayout)):
        m.remove(s)
    m.insert(0, layout.PageLayout(isNew=True))


def bpm_de(score: stream.Score) -> tuple[float, bool]:
    """(negres per minut, si és el valor per defecte)."""
    from music21 import tempo
    for mm in score.recurse().getElementsByClass(tempo.MetronomeMark):
        try:
            v = mm.getQuarterBPM()
        except Exception:
            v = None
        if v:
            return float(v), False
    return BPM_PER_DEFECTE, True
