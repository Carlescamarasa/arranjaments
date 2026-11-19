"""Harmonia: fitxes de referència i comprovació de corals (regles de veus).

Les fitxes són a `referencies/harmonia/<tema>/fitxa.md` (resums propis amb cites, mai text dels llibres).
Les comprovacions miren, a cada pols, la sonoritat de totes les veus i la comparen amb la següent:
quintes i octaves paral·leles (totes les parelles), quintes i octaves directes, sensible i 7a del V7,
sisena augmentada, i creuament, separació i tessitura. Convenció: solfeig, Do central = Do3.
Les notes estranyes a l'acord (de pas, bordadures, anticipacions...) es reconeixen amb `classifica_notes` i no
compten com a parelles reals. Els dominants secundaris s'avaluen contra el seu objectiu. Cada incidència porta
un pes i un nivell (error, avís, info) que depèn del perfil: `escolar` (estricte) o `arranjament` (permissiu).
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from music21 import chord, interval, key, meter, pitch, scale

from .errors import ErrorUsuari

ORDRE_VEUS = "SATB"
NOMS_VEU = {"S": "Soprano", "A": "Contralt", "T": "Tenor", "B": "Baix"}
_SOLFEIG = {"Do": "C", "Re": "D", "Mi": "E", "Fa": "F", "Sol": "G", "La": "A", "Si": "B"}
_INVERS = {v: k for k, v in _SOLFEIG.items()}
_NOTA = re.compile(r"^(Do|Re|Mi|Fa|Sol|La|Si)(##|#|bb|b)?(-?\d)$")
TESSITURA = {"S": ("Do3", "Sol4"), "A": ("Sol2", "Re4"), "T": ("Do2", "Sol3"), "B": ("Mi1", "Do3")}

# Quin tema (carpeta de referencies/harmonia) explica cada comprovació
TEMA_DE = {
    "paraleles": "quintes-octaves-paraleles",
    "directes": "quintes-octaves-paraleles",
    "sensible": "sensible-i-setena-v7",
    "sensible_duplicada": "sensible-i-setena-v7",
    "setena": "sensible-i-setena-v7",
    "sisena_augmentada": "sisena-augmentada",
    "dominant_secundari": "dominants-secundaris",
    "setena_duplicada": "sensible-i-setena-v7",
    "falsa_relacio": None,
    "registre_greu": None,
    "escriptura": None,
}


# ---------- referències (fitxes) ----------

def carpeta_referencies() -> Path:
    """Dins del repositori és `referencies/`; instal·lat, és a la carpeta de dades, al costat de `scripts/`."""
    env = os.environ.get("PARTITURES_REFERENCIES")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "referencies"


def _harmonia() -> Path:
    return carpeta_referencies() / "harmonia"


def temes() -> list[str]:
    d = _harmonia()
    return sorted(p.name for p in d.iterdir() if (p / "fitxa.md").is_file()) if d.is_dir() else []


def ruta_fitxa(tema: str) -> Path:
    return _harmonia() / tema / "fitxa.md"


def text_fitxa(tema: str) -> str:
    t = temes()
    if not t:
        raise ErrorUsuari("No trobe les fitxes d'harmonia. Potser cal actualitzar Arranjaments (`partitures actualitzar`).")
    n = re.sub(r"[^a-z0-9]+", "-", _sense_accents(tema).lower()).strip("-")
    triats = [x for x in t if x == n] or [x for x in t if n and (n in x or all(p in x for p in n.split("-")))]
    if len(triats) != 1:
        raise ErrorUsuari(f"Temes d'harmonia disponibles: {', '.join(t)}."
                          + (f" «{tema}» no n'identifica cap." if not triats else f" «{tema}» és ambigu: {', '.join(triats)}."))
    return ruta_fitxa(triats[0]).read_text(encoding="utf-8")


def _sense_accents(s: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))


def llista_temes() -> str:
    t = temes()
    if not t:
        return "No hi ha fitxes d'harmonia instal·lades."
    return "Fitxes d'harmonia (`partitures harmonia fitxa <tema>`):\n" + "\n".join(f"  {x}" for x in t)


# ---------- notes i tonalitat ----------

def a_pitch(nom: str) -> pitch.Pitch:
    m = _NOTA.match(nom.strip())
    if not m:
        raise ValueError(f"Nota no vàlida: {nom!r}")
    pas, alt, octava = m.groups()
    return pitch.Pitch(f"{_SOLFEIG[pas]}{(alt or '').replace('b', '-')}{int(octava) + 1}")


def nom_nota(p: pitch.Pitch) -> str:
    alt = p.accidental.modifier.replace("-", "b") if p.accidental else ""
    return f"{_INVERS[p.step]}{alt}{p.octave - 1}"


def a_tonalitat(text: str) -> key.Key:
    """'Do major', 'la menor', 'Sib major', 'fa# menor'."""
    try:
        tonica, modus = text.split()
        tonica = tonica[0].upper() + tonica[1:]
        nom = a_pitch(tonica + "3").name
        if modus.lower() not in ("major", "menor"):
            raise ValueError
    except ValueError:
        raise ErrorUsuari("La tonalitat s'escriu així: «Do major» o «la menor».") from None
    return key.Key(nom, "major" if modus.lower() == "major" else "minor")


def llegir_linia(linia: str) -> dict[str, list[pitch.Pitch]]:
    """'S: Mi4 Re4 | A: Do4 Si3 | T: Sol3 Sol3 | B: Do3 Sol2' (cada columna és un acord)."""
    veus = {}
    for tros in linia.split("|"):
        nom, _, notes = tros.partition(":")
        veus[nom.strip()] = [a_pitch(n) for n in notes.split()]
    if list(veus) != list(ORDRE_VEUS):
        raise ValueError(f"Cal S, A, T, B en este ordre: {linia}")
    if len({len(v) for v in veus.values()}) != 1:
        raise ValueError(f"Les veus no tenen el mateix nombre d'acords: {linia}")
    return veus


def escriure_linia(veus: dict[str, list[pitch.Pitch]]) -> str:
    return " | ".join(f"{v}: " + " ".join(nom_nota(p) for p in veus[v]) for v in ORDRE_VEUS)


# ---------- comprovacions (sobre sonoritats) ----------
# Cada comprovació torna una llista de (índex de la primera sonoritat, text). `veus` és {lletra: [Pitch]}.

def _semi(a: pitch.Pitch, b: pitch.Pitch) -> int:
    return int(b.ps - a.ps)


def _interval(baix, dalt) -> interval.Interval:
    return interval.Interval(baix, dalt)


def _quinta_justa(i) -> bool:
    return i.generic.simpleUndirected == 5 and i.semitones % 12 == 7


def _quinta(i) -> bool:
    return i.generic.simpleUndirected == 5


def _octava(i) -> bool:
    return i.generic.simpleUndirected == 1 and i.semitones % 12 == 0


def _nom_quinta(i) -> str:
    return {"P5": "5a justa", "d5": "5a disminuïda", "A5": "5a augmentada"}.get(i.simpleName, i.simpleName)


def _toca(ignora, a, b, i) -> bool:
    """Alguna de les quatre notes de la parella (veus a i b, sonoritats i i i+1) és una nota estranya."""
    return any((v, j) in ignora for v in (a, b) for j in (i, i + 1))


def _parelles(vs):
    for a in range(len(vs)):
        for b in range(a + 1, len(vs)):
            yield vs[a], vs[b]


def errors_escriptura(veus, k=None):
    err = []
    vs = list(veus)
    n = len(veus[vs[0]])
    for v in vs:
        baix, dalt = (a_pitch(x) for x in TESSITURA[v])
        for i, p in enumerate(veus[v]):
            if p.ps < baix.ps or p.ps > dalt.ps:
                err.append((i, f"{v} fora de tessitura ({nom_nota(p)})"))
    for i in range(n):
        for dalt, baix in zip(vs, vs[1:]):
            if veus[dalt][i].ps < veus[baix][i].ps:
                err.append((i, f"creuament de veus {dalt}-{baix}"))
            if (dalt, baix) in (("S", "A"), ("A", "T")) and veus[dalt][i].ps - veus[baix][i].ps > 12:
                err.append((i, f"més d'una octava entre {dalt} i {baix}"))
    return err


def _graus(k: key.Key):
    sc = scale.HarmonicMinorScale(k.tonic) if k.mode == "minor" else scale.MajorScale(k.tonic)
    return {g: sc.pitchFromDegree(g).name for g in range(1, 8)}


def _alemanya(veus, i, k) -> str | None:
    """Si la sonoritat i és una 6a augmentada alemanya, la veu que fa la 5a justa amb el baix."""
    if k is None or "B" not in veus:
        return None
    tonica = pitch.Pitch(_graus(k)[1])
    vib, ivs, iiib = (tonica.transpose(x).name for x in ("m6", "A4", "m3"))
    noms = {veus[v][i].name for v in veus}
    if veus["B"][i].name == vib and noms == {vib, tonica.name, iiib, ivs}:
        return next(v for v in veus if veus[v][i].name == iiib)
    return None


def paraleles(veus, k=None, ignora=None):
    """Quintes i octaves/unísons successius, per a totes les parelles de veus (Zamacois I, §§79-81).
    Excepcions: 5a justa seguida de 5a no justa (si no és entre S i B); 5a disminuïda seguida de 5a justa
    amb el segon acord en 1a inversió (II, §78); quintes de la 6a augmentada alemanya (III, §38)."""
    err = []
    vs = list(veus)
    n = len(veus[vs[0]])
    exterior = (vs[0], vs[-1])
    for i in range(n - 1):
        for a, b in _parelles(vs):
            if ignora and _toca(ignora, a, b, i):
                continue
            p1, p2, q1, q2 = veus[a][i], veus[a][i + 1], veus[b][i], veus[b][i + 1]
            if p1.ps == p2.ps and q1.ps == q2.ps:
                continue
            i1, i2 = _interval(q1, p1), _interval(q2, p2)
            if _octava(i1) and _octava(i2):
                err.append((i, f"octaves o unísons successius entre {a} i {b}"))
            elif _quinta(i1) and _quinta(i2) and (_quinta_justa(i1) or _quinta_justa(i2)):
                ext = (a, b) == exterior and (a, b) == ("S", "B")
                if b == "B" and not ext and _alemanya(veus, i, k) == a:
                    continue
                if (not _quinta_justa(i1) and _quinta_justa(i2) and b != "B"
                        and chord.Chord([veus[v][i + 1] for v in vs]).inversion() == 1):
                    continue
                if _quinta_justa(i2) or ext:
                    err.append((i, f"quintes successives entre {a} i {b} ({_nom_quinta(i1)} i després {_nom_quinta(i2)})"))
    return err


def directes(veus, k=None, ignora=None):
    """Quinta i octava directes (Zamacois I, §83): entre S i B només si el Soprano va per grau conjunt;
    amb una veu interior, si una de les dues va per grau conjunt (i, per a la 5a, si una nota ja sonava abans)."""
    err = []
    vs = list(veus)
    n = len(veus[vs[0]])
    for i in range(n - 1):
        anterior = {veus[v][i].name for v in vs}
        for a, b in _parelles(vs):
            if ignora and _toca(ignora, a, b, i):
                continue
            p1, p2, q1, q2 = veus[a][i], veus[a][i + 1], veus[b][i], veus[b][i + 1]
            ma, mb = _semi(p1, p2), _semi(q1, q2)
            if ma == 0 or mb == 0 or (ma > 0) != (mb > 0):
                continue
            i1, i2 = _interval(q1, p1), _interval(q2, p2)
            octava, quinta = _octava(i2), _quinta_justa(i2)
            if not (octava or quinta):
                continue
            if (octava and _octava(i1)) or (quinta and _quinta(i1)):
                continue
            nom = "octava directa" if octava else "quinta directa"
            if (a, b) == ("S", "B"):
                if abs(ma) > 2:
                    err.append((i, f"{nom} entre S i B amb el Soprano saltant"))
            elif not (abs(ma) <= 2 or abs(mb) <= 2 or (quinta and (p2.name in anterior or q2.name in anterior))):
                err.append((i, f"{nom} entre {a} i {b} amb les dues veus saltant"))
    return err


def _dominant(veus, i, k) -> bool:
    """Sonoritat de la família de la dominant: conté la sensible i només notes del V7 (graus 5, 7, 2 i 4)."""
    g = _graus(k)
    noms = {veus[v][i].name for v in veus}
    return g[7] in noms and noms <= {g[5], g[7], g[2], g[4]}


def _dominant_secundari(veus, i, k) -> key.Key | None:
    """Si la sonoritat i és un V7 d'un grau diatònic (no la tònica) i la i+1 és eixe grau, la tonalitat
    d'eixe grau (Herrera TEN-03). Cal el baix. La sensible del dominant secundari s'avalua contra el seu objectiu."""
    n = len(veus[next(iter(veus))])
    if "B" not in veus or i + 1 >= n:
        return None
    arrel = veus["B"][i + 1]
    escala = {pitch.Pitch(x).pitchClass for x in _graus(k).values()}
    if arrel.pitchClass not in escala or arrel.pitchClass == pitch.Pitch(_graus(k)[1]).pitchClass:
        return None
    noms = {veus[v][i].name for v in veus}
    seguent = {veus[v][i + 1].name for v in veus}
    for mode, tercera in (("major", "M3"), ("minor", "m3")):
        if arrel.transpose(tercera).name not in seguent:
            continue
        kt = key.Key(arrel.name, mode)
        g = _graus(kt)
        if {g[7], g[4]} <= noms <= {g[5], g[7], g[2], g[4]} and not _dominant(veus, i, k):
            return kt
    return None


def _objectiu(veus, i, k) -> key.Key | None:
    """Tonalitat contra la qual s'avalua el V7 de la sonoritat i: la global, la del dominant secundari o res."""
    if _dominant(veus, i, k):
        return k
    return _dominant_secundari(veus, i, k)


def _nom_tonalitat(kt: key.Key) -> str:
    alt = kt.tonic.accidental.modifier.replace("-", "b") if kt.tonic.accidental else ""
    return f"{_INVERS[kt.tonic.step]}{alt} {'menor' if kt.mode == 'minor' else 'major'}"


def sensible_duplicada(veus, k):
    err = []
    for i in range(len(veus[list(veus)[0]])):
        kt = _objectiu(veus, i, k)
        if kt is not None and sum(veus[v][i].name == _graus(kt)[7] for v in veus) > 1:
            err.append((i, "sensible duplicada"))
    return err


def sensible(veus, k):
    """Sensible del V (o V7, també el dominant d'un altre grau) cap a una sonoritat amb la tònica d'eixe grau
    (Zamacois I, §§98-102): S i B pugen a la tònica; una veu interior, tònica o baixar a la 5a de l'acord."""
    err = []
    vs = list(veus)
    for i in range(len(veus[vs[0]]) - 1):
        kt = _objectiu(veus, i, k)
        if kt is None:
            continue
        g = _graus(kt)
        seguent = {veus[v][i + 1].name for v in vs}
        if g[1] not in seguent:
            continue
        for v in vs:
            p, q = veus[v][i], veus[v][i + 1]
            if p.name != g[7] or (q.name == g[1] and _semi(p, q) == 1):
                continue
            if v in ("A", "T") and q.name == g[5] and _semi(p, q) < 0 and g[5] in seguent:
                continue
            err.append((i, f"la sensible ({nom_nota(p)}) del {v} no puja a la tònica (va a {nom_nota(q)})"))
    return err


def setena(veus, k, excepcio_43=True):
    """7a del V7: baixa per grau conjunt o es manté. Excepció: V 4/3 a I6 (el baix fa 2 a 3), pot pujar."""
    err = []
    vs = list(veus)
    for i in range(len(veus[vs[0]]) - 1):
        kt = _objectiu(veus, i, k)
        if kt is None:
            continue
        g = _graus(kt)
        noms = {veus[v][i].name for v in vs}
        if not (g[4] in noms and g[7] in noms):
            continue
        for v in vs:
            p, q = veus[v][i], veus[v][i + 1]
            if p.name != g[4]:
                continue
            d = _semi(p, q)
            if d in (-1, -2, 0):
                continue
            if "B" in veus and excepcio_43 and d in (1, 2):
                b1, b2 = veus["B"][i], veus["B"][i + 1]
                if b1.name == g[2] and b2.name == g[3] and _semi(b1, b2) > 0:
                    continue
            err.append((i, f"la 7a del V7 ({nom_nota(p)}) del {v} no baixa per grau conjunt (va a {nom_nota(q)})"))
    return err


def setena_duplicada(veus, k):
    """La 7a de la dominant no es duplica (Zamacois II, B04 a B06)."""
    err = []
    for i in range(len(veus[list(veus)[0]])):
        kt = _objectiu(veus, i, k)
        if kt is not None and sum(veus[v][i].name == _graus(kt)[4] for v in veus) > 1:
            err.append((i, "7a de la dominant duplicada"))
    return err


def dominant_secundari(veus, k):
    """Avís de perfil escolar: un acord fora de la tonalitat (V7 d'un altre grau) és vàlid, però cal que siga intencionat."""
    return [(i, f"acord fora de la tonalitat: dominant de {_nom_tonalitat(kt)}; comprova que és intencionat")
            for i in range(len(veus[list(veus)[0]]) - 1) if (kt := _dominant_secundari(veus, i, k)) is not None]


def falsa_relacio(veus, k):
    """Una nota i, a la sonoritat següent, la mateixa nota alterada en una altra veu (Zamacois II, R04)."""
    err = []
    vs = list(veus)
    for i in range(len(veus[vs[0]]) - 1):
        for a in vs:
            for b in vs:
                p, q = veus[a][i], veus[b][i + 1]
                if a != b and p.step == q.step and abs(p.ps - q.ps) == 1:
                    err.append((i, f"falsa relació entre {nom_nota(p)} ({a}) i {nom_nota(q)} ({b})"))
    return err


LIMIT_GREU_PAR = "Do2"    # sota d'ací, dues notes a 2a o 7a s'embruten (Zamacois III, Z5-14)
LIMIT_GREU_NOTA = "Fa1"   # sota d'ací, qualsevol 2a o 7a


def registre_greu(veus, k):
    err = []
    vs = list(veus)
    par, sol = a_pitch(LIMIT_GREU_PAR).ps, a_pitch(LIMIT_GREU_NOTA).ps
    for i in range(len(veus[vs[0]])):
        for a, b in _parelles(vs):
            p, q = veus[a][i], veus[b][i]
            if interval.Interval(q, p).generic.simpleUndirected not in (2, 7) or p.ps == q.ps:
                continue
            if max(p.ps, q.ps) < par or min(p.ps, q.ps) < sol:
                err.append((i, f"{nom_nota(q)} ({b}) i {nom_nota(p)} ({a}) a 2a o 7a, massa greu"))
    return err


def sisena_augmentada(veus, k) -> tuple[str | None, list[tuple[int, str]]]:
    """Troba la 6a augmentada (VIb al baix, IV# en una veu), diu el tipus i comprova que s'òbriga a la dominant."""
    if "B" not in veus:
        return None, []
    g = _graus(k)
    tonica = pitch.Pitch(g[1])
    vib, ivs = tonica.transpose("m6").name, tonica.transpose("A4").name
    iiib, ii, dom = tonica.transpose("m3").name, tonica.transpose("M2").name, g[5]
    err, tipus = [], None
    vs = list(veus)
    n = len(veus[vs[0]])
    for i in range(n):
        noms = {veus[v][i].name for v in vs}
        if veus["B"][i].name != vib or ivs not in noms:
            continue
        resta = noms - {vib, ivs, g[1]}
        if g[1] not in noms:
            err.append((i, "a la 6a augmentada li falta la tònica"))
        if not resta:
            tipus = "italiana"
        elif resta == {ii}:
            tipus = "francesa"
        elif resta == {iiib}:
            tipus = "alemanya"
        else:
            err.append((i, f"notes que no són d'una 6a augmentada: {sorted(resta)}"))
        dalt = next(v for v in vs if veus[v][i].name == ivs)
        if _interval(veus["B"][i], veus[dalt][i]).simpleName != "A6":
            err.append((i, f"entre B i {dalt} no hi ha una 6a augmentada"))
        if i + 1 >= n:
            err.append((i, "la 6a augmentada no resol"))
            continue
        b1, b2, d1, d2 = veus["B"][i], veus["B"][i + 1], veus[dalt][i], veus[dalt][i + 1]
        if not (b2.name == dom and _semi(b1, b2) == -1):
            err.append((i, f"el baix ({nom_nota(b1)}) no baixa un semitò a la dominant"))
        if not (d2.name == dom and _semi(d1, d2) == 1):
            err.append((i, f"el IV# ({nom_nota(d1)}) del {dalt} no puja un semitò a la dominant"))
    return tipus, err


COMPROVACIONS = {
    "escriptura": errors_escriptura,
    "paraleles": paraleles,
    "sensible_duplicada": sensible_duplicada,
    "directes": directes,
    "sensible": sensible,
    "setena": setena,
    "sisena_augmentada": lambda veus, k: sisena_augmentada(veus, k)[1],
    "setena_duplicada": setena_duplicada,
    "dominant_secundari": dominant_secundari,
    "falsa_relacio": falsa_relacio,
    "registre_greu": registre_greu,
}
GENERALS = ["escriptura", "paraleles", "directes", "sensible", "sensible_duplicada", "setena"]
# comprovacions afegides al paquet 4 (Zamacois II i III); no entren a GENERALS perquè les proves antigues
# fixen exactament quines regles falla cada exemple
NOVES = ["setena_duplicada", "falsa_relacio", "registre_greu"]


# ---------- notes reals i notes estranyes a l'acord ----------

PLANTILLES_ACORD = ((0, 4, 7), (0, 3, 7), (0, 3, 6), (0, 4, 7, 10), (0, 4, 8))
ESTRANYES = ("pas", "bordadura", "anticipació", "escapada", "apoiatura")   # les que no són errors per se
ESTRANYES_ESCOLAR = ("pas", "bordadura")   # a l'escola només s'accepten les dues més clares


def acord_de_sonoritat(veus, i) -> frozenset:
    """Classes d'altura de l'acord que millor explica la sonoritat i (el baix pesa una mica més com a arrel).
    Les notes de la sonoritat que no hi caben són candidates a notes estranyes."""
    notes = [veus[v][i] for v in veus]
    baix = veus["B"][i].pitchClass if "B" in veus else min(notes, key=lambda p: p.ps).pitchClass
    millor = None
    for arrel in range(12):
        for pla in PLANTILLES_ACORD:
            pcs = frozenset((arrel + x) % 12 for x in pla)
            v = sum(p.pitchClass in pcs for p in notes) + (0.4 if arrel == baix else 0) - (0.3 if len(pla) == 4 else 0)
            if millor is None or v > millor[0] + 1e-9:
                millor = (v, pcs)
    return millor[1]


def _pas(d: float) -> bool:
    return 1 <= abs(d) <= 2


def classifica_notes(veus, acords=None, llocs=None) -> dict[str, list[str]]:
    """Etiqueta cada nota de cada veu: real, pas, bordadura, anticipació, escapada, apoiatura o estranya.
    Una nota és de pas o bordadura només si les tres coses van juntes (Z3-A, INF-01): no és de l'acord,
    s'arriba i se surt per grau conjunt i va en part feble; a més ha de resoldre a una nota de l'acord següent.
    `acords` és una llista de conjunts de classes d'altura (un per sonoritat); si falta, es dedueix.
    `llocs[i] = (compàs, temps)`; sense això no es pot saber la part feble i se suposa que ho és."""
    n = len(veus[next(iter(veus))])
    acords = acords or [acord_de_sonoritat(veus, i) for i in range(n)]
    res = {}
    for v, notes in veus.items():
        etiq = []
        for i, p in enumerate(notes):
            if p.pitchClass in acords[i]:
                etiq.append("real")
                continue
            feble = True if llocs is None else llocs[i][1] != 1
            ant = notes[i - 1] if i > 0 else None
            seg = notes[i + 1] if i + 1 < n else None
            d0 = p.ps - ant.ps if ant is not None else None
            d1 = seg.ps - p.ps if seg is not None else None
            resol = seg is not None and seg.pitchClass in acords[i + 1]
            tipus = "estranya"
            if seg is not None and d1 == 0 and resol and feble:
                tipus = "anticipació"
            elif ant is not None and seg is not None and _pas(d0) and _pas(d1) and resol and feble:
                tipus = "pas" if d0 * d1 > 0 else "bordadura" if ant.ps == seg.ps else "estranya"
            elif ant is not None and seg is not None and _pas(d0) and abs(d1) >= 3 and d0 * d1 < 0 and feble:
                tipus = "escapada"
            elif seg is not None and _pas(d1) and resol and llocs is not None and not feble:
                tipus = "apoiatura"
            etiq.append(tipus)
        res[v] = etiq
    return res


def solidifica(veu: list, finestra: int) -> list[tuple]:
    """Acord solidificat (Z4-02): les notes d'un arpegi, agrupades de `finestra` en `finestra`, com un sol acord."""
    if finestra < 1:
        raise ValueError("La finestra ha de ser d'1 nota com a mínim.")
    return [tuple(sorted({p.nameWithOctave: p for p in veu[x:x + finestra]}.values(), key=lambda p: p.ps))
            for x in range(0, len(veu), finestra)]


# ---------- perfils i pesos ----------

PERFILS = ("escolar", "arranjament")
# pes base de cada comprovació: >= 2 error, >= 1 avís, la resta info (Zamacois III, Z5-07)
PES_BASE = {"escriptura": 2.0, "paraleles": 3.0, "directes": 2.0, "sensible": 2.0, "sensible_duplicada": 2.0,
            "setena": 2.0, "sisena_augmentada": 2.0, "setena_duplicada": 1.5, "falsa_relacio": 1.0,
            "registre_greu": 1.0, "dominant_secundari": 1.0}
AJUST_PERFIL = {"escolar": 0.0, "arranjament": -1.0}   # l'arranjament és més permissiu (Z5-18, Z5-19)
LLINDAR_ERROR, LLINDAR_AVIS = 2.0, 1.0
_VEUS_EN_TEXT = re.compile(r"\b(?:entre|del|de la|al|de)\s+([SATB])(?: i ([SATB]))?\b")


def nivell_de_pes(pes: float) -> str:
    return "error" if pes >= LLINDAR_ERROR else "avís" if pes >= LLINDAR_AVIS else "info"


def _veus_de_text(text: str) -> set[str]:
    return {x for m in _VEUS_EN_TEXT.finditer(text) for x in m.groups() if x}


def pes_incidencia(comp: str, i: int, text: str, veus, k, perfil: str) -> float:
    """Pes base del perfil i modificadors de Z5-07 (-1 cadascun): acord següent dissonant, veu interior,
    i, en arranjament, la melodia (S) com a protagonista. Retrocés i línies semitonals queden per a més endavant."""
    pes = PES_BASE[comp] + AJUST_PERFIL[perfil]
    n = len(veus[next(iter(veus))])
    if comp in ("paraleles", "directes", "sensible", "setena") and i + 1 < n and _objectiu(veus, i + 1, k) is not None:
        pes -= 1.0
    implicades = _veus_de_text(text)
    if implicades and not (implicades & {"S", "B"}):
        pes -= 1.0
    elif perfil == "arranjament" and implicades == {"S"}:
        pes -= 1.0
    return pes


# ---------- lectura d'una partitura ----------

def _tonalitat_de(parts) -> key.Key:
    ks = parts[0].recurse().getElementsByClass(key.KeySignature).first()
    if ks is None:
        return key.Key("C", "major")
    return ks if isinstance(ks, key.Key) else ks.asKey("major")


def sonoritats(parts, lletres: str):
    """Sonoritat a cada pols (i només quan canvia alguna veu). Torna (veus, llocs); llocs[i] = (compàs, temps)."""
    llistes = []
    for p in parts:
        fl = []
        for n in p.flatten().notesAndRests:
            if n.duration.quarterLength == 0:
                continue
            if isinstance(n, chord.Chord) and len(n.pitches) > 1:
                raise ErrorUsuari("Hi ha acords dins d'una sola veu. Per a esta comprovació cal una part per veu "
                                  "(soprano, contralt, tenor i baix en pentagrames separats).")
            ini = float(n.getOffsetInHierarchy(p))
            fl.append((ini, ini + float(n.duration.quarterLength), None if n.isRest else n.pitches[0]))
        llistes.append(fl)

    def sona(fl, t):
        for ini, fi, pt in fl:
            if ini <= t + 1e-6 < fi:
                return pt
        return None

    veus = {v: [] for v in lletres}
    llocs = []
    anterior = None
    for m in parts[0].getElementsByClass("Measure"):
        ts = m.getContextByClass(meter.TimeSignature)
        pols = float(ts.beatDuration.quarterLength) if ts else 1.0
        base = float(m.offset)
        durada = float(m.highestTime) or pols
        k = 0
        while k * pols < durada - 1e-6:
            t = base + k * pols
            cols = [sona(fl, t) for fl in llistes]
            k += 1
            if any(c is None for c in cols):
                continue
            clau = tuple(c.ps for c in cols)
            if clau == anterior:
                continue
            anterior = clau
            for v, c in zip(lletres, cols):
                veus[v].append(c)
            llocs.append((m.number, k))
    return veus, llocs


def _lloc(llocs, i: int) -> str:
    c, t = llocs[i]
    return f"compàs {c}, temps {t}"


def _tema_cita(c: str) -> str:
    tema = TEMA_DE.get(c)
    return f"referencies/harmonia/{tema}/fitxa.md (partitures harmonia fitxa {tema})" if tema else "sense fitxa (tessitures orientatives del cor)"


def comprova_veus(veus, k, llocs=None, perfil: str = "escolar") -> list[dict]:
    """Totes les incidències: [{comprovacio, index, lloc, text, fitxa, pes, nivell}] ordenades per posició.
    Les parelles amb una nota estranya a l'acord (de pas, bordadura...) no compten com a paral·leles ni directes."""
    if perfil not in PERFILS:
        raise ErrorUsuari(f"El perfil ha de ser {' o '.join(PERFILS)}.")
    etiquetes = classifica_notes(veus, llocs=llocs)
    admeses = ESTRANYES if perfil == "arranjament" else ESTRANYES_ESCOLAR
    ignora = {(v, i) for v, e in etiquetes.items() for i, t in enumerate(e) if t in admeses}
    res = []
    comps = list(GENERALS) + NOVES
    if perfil == "escolar":
        comps.append("dominant_secundari")
    tipus, e6 = sisena_augmentada(veus, k)
    if tipus is not None or e6:
        comps.append("sisena_augmentada")
    for c in comps:
        trobats = COMPROVACIONS[c](veus, k) if c not in ("paraleles", "directes") else \
            COMPROVACIONS[c](veus, k, ignora=ignora)
        for i, text in trobats:
            pes = pes_incidencia(c, i, text, veus, k, perfil)
            res.append({"comprovacio": c, "index": i, "text": text, "pes": pes, "nivell": nivell_de_pes(pes),
                        "lloc": _lloc(llocs, i) if llocs else f"acord {i + 1}", "fitxa": _tema_cita(c)})
    res.sort(key=lambda r: (r["index"], r["comprovacio"]))
    return res


def comprova(parts_o_score, lletres: str = "SATB", tonalitat: str | None = None, perfil: str = "escolar") -> str:
    score = parts_o_score
    parts = list(score.parts)
    lletres = (lletres or "SATB").upper()
    if (not lletres or any(c not in ORDRE_VEUS for c in lletres) or len(set(lletres)) != len(lletres)
            or [ORDRE_VEUS.index(c) for c in lletres] != sorted(ORDRE_VEUS.index(c) for c in lletres)):
        raise ErrorUsuari("--veus ha de ser una llista de S, A, T i B de dalt a baix (per exemple SATB o SAB).")
    if len(parts) != len(lletres):
        raise ErrorUsuari(f"La partitura té {len(parts)} parts i has indicat {len(lletres)} veus ({lletres}). "
                          "Cal una part per veu (si són dues veus en un pentagrama, separa-les amb MuseScore) "
                          "o indica el repartiment amb --veus.")
    if len(parts) < 2:
        raise ErrorUsuari("Calen almenys dues veus per a comprovar l'harmonia.")
    k = a_tonalitat(tonalitat) if tonalitat else _tonalitat_de(parts)
    veus, llocs = sonoritats(parts, lletres)
    n = len(llocs)
    if n < 2:
        raise ErrorUsuari("No he trobat dues sonoritats seguides amb totes les veus sonant: no hi ha res a comprovar.")
    inc = comprova_veus(veus, k, llocs, perfil)
    t = k.tonic
    ext = f"{_INVERS[t.step]}{t.accidental.modifier.replace('-', 'b') if t.accidental else ''} {'menor' if k.mode == 'minor' else 'major'}"
    out = [f"Comprovació d'harmonia (perfil {perfil}): {n} sonoritats (una per pols), veus {lletres}, tonalitat {ext}"
           + (" (llegida de l'armadura; si és menor, indica-ho amb --tonalitat \"la menor\")" if not tonalitat and k.mode == "major" else "") + "."]
    if not inc:
        out.append("No he trobat cap problema de les regles que comprovo.")
    else:
        compas = None
        for r in inc:
            c = llocs[r["index"]][0]
            if c != compas:
                out.append(f"\nCompàs {c}:")
                compas = c
            out.append(f"  - {r['lloc'].split(', ', 1)[1]}: {r['text']} ({r['nivell']}). Fitxa: {r['fitxa']}")
        resum = ", ".join(f"{sum(r['nivell'] == x for r in inc)} {x}" for x in ("error", "avís", "info")
                          if any(r["nivell"] == x for r in inc))
        out.append(f"\n{len(inc)} possible(s) problema(es) ({resum}). Són regles d'escola: algunes tenen excepcions "
                   "(mira la fitxa). Les notes de pas i les bordadures no compten com a parelles; el perfil "
                   "«escolar» és estricte i «arranjament» més permissiu. Decideix amb criteri.")
    out.append("Només comprovo: quintes i octaves paral·leles i directes, sensible, 7a del V7, 6a augmentada, "
               "creuament, separació i tessitura, 7a i sensible duplicades, falsa relació i registre greu. "
               "No és una revisió harmònica completa.")
    return "\n".join(out)
