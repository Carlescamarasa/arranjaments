"""Parts llegibles (paquet 3): lletres d'assaig, silencis multicompàs, números de compàs, mida de pauta,
salts de sistema i claudàtors per família.

Què fa el codi i què fa MuseScore (comprovat amb MuseScore 4.7 des de la línia d'ordres):
- Les lletres d'assaig, els salts de sistema i els claudàtors van dins del MusicXML (el fa este mòdul).
- La mida de pauta, els silencis multicompàs i els números de compàs són ESTIL de MuseScore, no MusicXML.
  L'opció `-S estil.mss` de MuseScore aplica la mida de pauta, però NO activa els silencis multicompàs.
  Per això l'estil s'escriu directament dins del fitxer .mscz (que és un zip amb `score_style.mss`).
- Regles de referència (ids de les fitxes): Gould B LAY-02, LAY-04, LAY-05, LAY-07, PRT-01, PRT-02, PRT-03, PRT-09,
  SCO-04, SCO-06.
"""
from __future__ import annotations

import shutil
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from music21 import expressions, layout, metadata, stream

from .errors import ErrorUsuari

# --------------------------------------------------------------------------- perfils de pàgina
# Mida de pauta en mm de "spatium" (= alçada de la pauta dividida per 4). LAY-02 i PRT-01: alumne petit 8 a 9 mm,
# normal 6,7 a 7 mm, guió 5 a 6 mm. El digest dona 2,3 mm (9,2 mm) per a l'alumne petit; ací s'usa 2,1 (8,4 mm),
# dins de la forqueta, perquè la part càpiga millor en una pàgina (PRT-06). [inferència: ajustable]
PERFILS_PAGINA = {
    "elemental": {"spatium": 2.1, "reduccions": (1.95, 1.8, 1.675)},
    "normal": {"spatium": 1.675, "reduccions": (1.6, 1.5)},
    "guio": {"spatium": 1.375, "reduccions": ()},
}
MIN_BUITS_MULTICOMPAS = 2          # PRT-09: a partir de 2 compassos de silenci s'agrupen
COMPASSOS_PER_SISTEMA_ELEMENTAL = 4   # LAY-07
# Més espai entre sistemes a les parts (PRT-02), en espais de pauta
DISTANCIA_SISTEMES_PART = {"minSystemDistance": 10.0, "maxSystemDistance": 20.0}


def perfil(clau: str) -> dict:
    return PERFILS_PAGINA[clau]


def estil_part(spatium: float, nom_instrument: str = "") -> dict:
    """Claus d'estil de MuseScore per a una particel·la."""
    claus = {
        "spatium": f"{spatium:g}",
        "createMultiMeasureRests": "1",
        "minEmptyMeasures": str(MIN_BUITS_MULTICOMPAS),
        "showMeasureNumber": "1",
        "showMeasureNumberOne": "0",
        "measureNumberSystem": "1",          # número a l'inici de cada sistema, no cada N compassos (LAY-04)
        "measureNumberInterval": "5",
    }
    claus.update({k: f"{v:g}" for k, v in DISTANCIA_SISTEMES_PART.items()})
    if nom_instrument:
        # PRT-03: a partir de la pàgina 2, el nom de l'instrument a dalt al mig; la pàgina 1 ja el porta al marge
        claus.update({"showHeader": "1", "headerFirstPage": "0", "headerOddEven": "1",
                      "oddHeaderC": nom_instrument, "evenHeaderC": nom_instrument})
    return claus


def estil_guio(spatium: float | None = None) -> dict:
    """Claus d'estil per al guió: sense silencis multicompàs (PRT-09) i mida petita (LAY-02)."""
    return {
        "spatium": f"{spatium or PERFILS_PAGINA['guio']['spatium']:g}",
        "createMultiMeasureRests": "0",
        "showMeasureNumber": "1",
        "showMeasureNumberOne": "0",
        "measureNumberSystem": "1",
    }


# --------------------------------------------------------------------------- estil dins del .mscz

def aplica_estil_mscz(mscz: str | Path, claus: dict) -> None:
    """Escriu les claus d'estil dins de `score_style.mss` del .mscz (que és un zip). Atòmic: mai deixa mig escrit."""
    mscz = Path(mscz)
    try:
        with zipfile.ZipFile(mscz) as z:
            noms = z.namelist()
            dades = {n: z.read(n) for n in noms}
    except (OSError, zipfile.BadZipFile) as e:
        raise ErrorUsuari(f"No puc llegir el fitxer de MuseScore «{mscz.name}» per a posar-hi l'estil.") from e
    nom_estil = next((n for n in noms if n.endswith("score_style.mss")), None)
    if nom_estil is None:
        raise ErrorUsuari(f"El fitxer «{mscz.name}» no porta estil; no puc aplicar la mida de pauta.")
    arrel = ET.fromstring(dades[nom_estil])
    estil = arrel.find("Style")
    if estil is None:
        estil = ET.SubElement(arrel, "Style")
    for clau, valor in claus.items():
        el = estil.find(clau)
        if el is None:
            el = ET.SubElement(estil, clau)
        el.text = str(valor)
    dades[nom_estil] = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(arrel, encoding="utf-8")
    with tempfile.TemporaryDirectory(dir=mscz.parent, prefix=".tmp-estil-") as tmp:
        nou = Path(tmp) / mscz.name
        with zipfile.ZipFile(nou, "w", zipfile.ZIP_DEFLATED) as z:
            for n in noms:
                z.writestr(n, dades[n])
        shutil.move(str(nou), str(mscz))


def llig_estil_mscz(mscz: str | Path) -> dict:
    """Les claus d'estil d'un .mscz (per a comprovar-les en proves)."""
    with zipfile.ZipFile(mscz) as z:
        nom = next(n for n in z.namelist() if n.endswith("score_style.mss"))
        arrel = ET.fromstring(z.read(nom))
    estil = arrel.find("Style")
    return {el.tag: (el.text or "") for el in estil} if estil is not None else {}


# --------------------------------------------------------------------------- nivell dins del MusicXML
# L'ordre «exportar» només rep un fitxer; el nivell (curs) viaja dins del MusicXML com a camp personalitzat,
# que MuseScore ignora. Així «exportar» sap si la part és d'alumne petit (mida gran, 4 compassos per sistema).

CAMP_NIVELL = "arranjaments-nivell"


def desa_nivell(score: stream.Score, curs: str | None) -> None:
    if not curs:
        return
    if score.metadata is None:
        score.metadata = metadata.Metadata()
    score.metadata.addCustom(CAMP_NIVELL, curs)


def nivell_de(score: stream.Score) -> str | None:
    try:
        v = score.metadata.getCustom(CAMP_NIVELL) if score.metadata else ()
    except Exception:
        return None
    return str(v[0]) if v else None


# --------------------------------------------------------------------------- lletres d'assaig (LAY-05)

def lletra_assaig(i: int) -> str:
    """A, B, C... Z, AA, BB, CC... (després de Z es dobla la lletra, com diu Gould)."""
    return chr(65 + i % 26) * (i // 26 + 1)


def inicis_seccio(seccions) -> list[int]:
    """Índexs (0 = primer compàs) on comença cada secció. Només llig `Seccio.i0` de `dividir_seccions`."""
    return sorted({s.i0 for s in seccions})


def posar_lletres(part: stream.Part, inicis: list[int], anacrusi: bool = False) -> list[tuple[int, str]]:
    """Una lletra d'assaig al primer compàs de cada secció, a la pauta superior del guió. Amb una sola secció no
    en posa cap (una «A» sola no serveix de res). Si la peça comença amb anacrusi, la «A» va al primer compàs
    complet (l'anacrusi no es compta, LAY-04)."""
    ms = list(part.getElementsByClass(stream.Measure))
    if anacrusi:
        inicis = [max(i, 1) for i in inicis]
    inicis = sorted({i for i in inicis if 0 <= i < len(ms)})
    if len(inicis) < 2:
        return []
    posades = []
    for n, i in enumerate(inicis):
        txt = lletra_assaig(n)
        marca = expressions.RehearsalMark(txt)
        ms[i].insert(0, marca)
        posades.append((i, txt))
    return posades


def lletres_de(score: stream.Score) -> dict[int, str]:
    """Les lletres que ja té una partitura: {índex de compàs: text}. Mira totes les parts."""
    res: dict[int, str] = {}
    for p in score.parts:
        for i, m in enumerate(p.getElementsByClass(stream.Measure)):
            for r in m.getElementsByClass(expressions.RehearsalMark):
                res.setdefault(i, str(r.content))
    return res


def copia_lletres(lletres: dict[int, str], part_score: stream.Score) -> None:
    """Posa les lletres (mateixa posició que al guió) a la primera pauta d'una particel·la, si encara no les té."""
    if not lletres or not part_score.parts:
        return
    p = part_score.parts[0]
    ms = list(p.getElementsByClass(stream.Measure))
    for i, txt in lletres.items():
        if i < len(ms) and not ms[i].getElementsByClass(expressions.RehearsalMark):
            ms[i].insert(0, expressions.RehearsalMark(txt))


# --------------------------------------------------------------------------- compassos buits i salts de sistema

def es_buit(m: stream.Measure) -> bool:
    return not any(True for _ in m.recurse().notes)


def _te_anotacions(m: stream.Measure) -> bool:
    """Coses que fan que MuseScore no agrupe un compàs en un silenci multicompàs."""
    from music21 import clef, key, meter, tempo
    cls = (expressions.RehearsalMark, expressions.TextExpression, tempo.MetronomeMark, meter.TimeSignature,
           key.KeySignature, clef.Clef)
    return any(m.getElementsByClass(c) for c in cls) or bool(m.getElementsByClass("ChordSymbol"))


def grups_buits(part: stream.Part, minim: int = MIN_BUITS_MULTICOMPAS) -> list[tuple[int, int]]:
    """Trams (índex inicial i final, tots dos inclosos) de compassos buits que MuseScore agruparà en un sol
    silenci multicompàs. Un compàs amb lletra, text, tempo o canvi comença un grup nou (PRT-09)."""
    ms = list(part.getElementsByClass(stream.Measure))
    grups: list[tuple[int, int]] = []
    ini = None
    for i, m in enumerate(ms):
        buit = es_buit(m)
        trenca = _te_anotacions(m) or _te_salt(m) or (i > 0 and _trenca_darrere(ms[i - 1]))
        if buit and ini is not None and not trenca:
            continue
        if ini is not None:
            grups.append((ini, i - 1))
            ini = None
        if buit:
            ini = i
    if ini is not None:
        grups.append((ini, len(ms) - 1))
    return [g for g in grups if g[1] - g[0] + 1 >= minim]


def _trenca_darrere(m: stream.Measure) -> bool:
    """Una barra doble, final o de repetició al final del compàs talla el grup."""
    b = m.rightBarline
    if b is None:
        return False
    return type(b).__name__ == "Repeat" or getattr(b, "type", "regular") not in ("regular", "none")


def _te_salt(m: stream.Measure) -> bool:
    """El compàs comença sistema o pàgina nova (un salt talla el grup de silencis)."""
    return bool(m.getElementsByClass(layout.SystemLayout) or m.getElementsByClass(layout.PageLayout))


def unitats_de_lectura(part: stream.Part, minim: int = MIN_BUITS_MULTICOMPAS) -> list[tuple[int, int]]:
    """Cada «caixa» que veu l'intèrpret: un compàs, o un grup de silenci multicompàs (índex inicial i final)."""
    n = len(list(part.getElementsByClass(stream.Measure)))
    en_grup = {}
    for a, b in grups_buits(part, minim):
        en_grup[a] = b
    res = []
    i = 0
    while i < n:
        if i in en_grup:
            res.append((i, en_grup[i]))
            i = en_grup[i] + 1
        else:
            res.append((i, i))
            i += 1
    return res


def posar_salts_sistema(part: stream.Part, inicis_seccions: list[int],
                        per_sistema: int = COMPASSOS_PER_SISTEMA_ELEMENTAL) -> list[int]:
    """LAY-07: sistema nou a cada secció i, en elemental, cada `per_sistema` caixes de lectura (un silenci
    multicompàs compta com una sola). Retorna els índexs de compàs on ha posat el salt."""
    ms = list(part.getElementsByClass(stream.Measure))
    unitats = unitats_de_lectura(part)
    seccions = sorted(set(i for i in inicis_seccions if 0 <= i < len(ms)) | {0})
    if len(ms) > 1 and (ms[0].number == 0 or ms[0].duration.quarterLength < ms[0].barDuration.quarterLength - 1e-6):
        seccions = [i for i in seccions if i != 1]    # l'anacrusi va al mateix sistema que el primer compàs
    posats = []
    ult = 0
    for a, _ in unitats:
        if a == 0:
            ult = 0
            continue
        nou = a in seccions
        if not nou:
            caixes = sum(1 for x, _y in unitats if ult <= x < a)
            nou = caixes >= per_sistema
        if nou:
            if not ms[a].getElementsByClass(layout.SystemLayout):
                ms[a].insert(0, layout.SystemLayout(isNew=True))
            posats.append(a)
            ult = a
    return posats


# --------------------------------------------------------------------------- claudàtors i ordre (SCO-04, SCO-06)

FAMILIES = {   # clau de l'instrument -> família del claudàtor
    **{c: "fusta" for c in ("flauti", "flauta", "oboe", "corn-angles", "clarinet-sib", "clarinet-la", "clarinet-baix",
                            "clarinet-contrabaix", "saxo-soprano", "saxo-alt", "saxo-tenor", "saxo-bari", "fagot",
                            "contrafagot")},
    **{c: "metall" for c in ("trompa-fa", "trompeta-sib", "trompeta-do", "fliscorn-sib", "trombo", "trombo-baix",
                             "bombardi", "tuba")},
    **{c: "percussio" for c in ("carillo", "xilofon", "xilofon-orff", "metalofon", "vibrafon", "marimba", "bateria",
                                "caixa", "percussio")},
    **{c: "corda" for c in ("violi", "viola", "violoncel", "contrabaix")},
}
MIN_PAUTES_CLAUDATORS_PER_FAMILIA = 6   # SCO-06: guió gran (6 o més pautes) = un claudàtor per família


def grups_claudators(unitats: list[tuple[str, list]]) -> list[tuple[str, list]]:
    """Decideix els claudàtors. `unitats` és la llista (clau d'instrument, [parts]) en l'ordre del guió.
    Retorna [(nom, [parts])]. Guió gran: un claudàtor per família (una pauta sola també en porta). Guió petit:
    un sol claudàtor per a tot (amb barres de compàs contínues), però no si hi ha una clau de dues pautes
    (piano o làmines de dues pautes), que ja uneix el seu propi sistema."""
    pautes = sum(len(pp) for _c, pp in unitats)
    if pautes >= MIN_PAUTES_CLAUDATORS_PER_FAMILIA:
        grups: dict[str, list] = {}
        for clau, pp in unitats:
            fam = FAMILIES.get(clau)
            if fam is None or len(pp) > 1:
                continue
            grups.setdefault(fam, []).extend(pp)
        return list(grups.items())
    if pautes >= 2 and not any(len(pp) > 1 for _c, pp in unitats):
        return [("conjunt", [p for _c, pp in unitats for p in pp])]
    return []


def posar_claudators(res: stream.Score, grups: list[tuple[str, list]]) -> None:
    for _nom, parts in grups:
        res.insert(0, layout.StaffGroup(parts, symbol="bracket", barTogether=True))


# --------------------------------------------------------------------------- informe

def text_lletres(posades: list[tuple[int, str]], compassos) -> str:
    if not posades:
        return ""
    return "Lletres d'assaig: " + ", ".join(f"{t} al compàs {compassos[i].num}" for i, t in posades) + "."
