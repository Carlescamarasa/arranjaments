"""Harmonia: fitxes de referència i comprovació de corals (regles de veus).

Les fitxes són a `referencies/harmonia/<tema>/fitxa.md` (resums propis amb cites, mai text dels llibres).
Les comprovacions miren, a cada pols, la sonoritat de totes les veus i la comparen amb la següent:
quintes i octaves paral·leles (totes les parelles), quintes i octaves directes, sensible i 7a del V7,
sisena augmentada, i creuament, separació i tessitura. Convenció: solfeig, Do central = Do3.
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


def paraleles(veus, k=None):
    """Quintes i octaves/unísons successius, per a totes les parelles de veus (Zamacois I, §§79-81).
    Excepcions: 5a justa seguida de 5a no justa (si no és entre S i B); 5a disminuïda seguida de 5a justa
    amb el segon acord en 1a inversió (II, §78); quintes de la 6a augmentada alemanya (III, §38)."""
    err = []
    vs = list(veus)
    n = len(veus[vs[0]])
    exterior = (vs[0], vs[-1])
    for i in range(n - 1):
        for a, b in _parelles(vs):
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


def directes(veus, k=None):
    """Quinta i octava directes (Zamacois I, §83): entre S i B només si el Soprano va per grau conjunt;
    amb una veu interior, si una de les dues va per grau conjunt (i, per a la 5a, si una nota ja sonava abans)."""
    err = []
    vs = list(veus)
    n = len(veus[vs[0]])
    for i in range(n - 1):
        anterior = {veus[v][i].name for v in vs}
        for a, b in _parelles(vs):
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


def sensible_duplicada(veus, k):
    g = _graus(k)
    return [(i, "sensible duplicada") for i in range(len(veus[list(veus)[0]]))
            if _dominant(veus, i, k) and sum(veus[v][i].name == g[7] for v in veus) > 1]


def sensible(veus, k):
    """Sensible del V (o V7) cap a una sonoritat amb la tònica (Zamacois I, §§98-102): S i B pugen a la tònica;
    una veu interior, tònica o baixar a la 5a de l'acord de tònica."""
    g = _graus(k)
    err = []
    vs = list(veus)
    for i in range(len(veus[vs[0]]) - 1):
        if not _dominant(veus, i, k):
            continue
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
    g = _graus(k)
    err = []
    vs = list(veus)
    for i in range(len(veus[vs[0]]) - 1):
        noms = {veus[v][i].name for v in vs}
        if not (g[4] in noms and g[7] in noms and _dominant(veus, i, k)):
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
}
GENERALS = ["escriptura", "paraleles", "directes", "sensible", "sensible_duplicada", "setena"]


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


def comprova_veus(veus, k, llocs=None) -> list[dict]:
    """Totes les incidències: [{comprovacio, index, lloc, text, fitxa}] ordenades per posició."""
    res = []
    comps = list(GENERALS)
    tipus, e6 = sisena_augmentada(veus, k)
    if tipus is not None or e6:
        comps.append("sisena_augmentada")
    for c in comps:
        for i, text in COMPROVACIONS[c](veus, k):
            res.append({"comprovacio": c, "index": i, "text": text,
                        "lloc": _lloc(llocs, i) if llocs else f"acord {i + 1}", "fitxa": _tema_cita(c)})
    res.sort(key=lambda r: (r["index"], r["comprovacio"]))
    return res


def comprova(parts_o_score, lletres: str = "SATB", tonalitat: str | None = None) -> str:
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
    inc = comprova_veus(veus, k, llocs)
    t = k.tonic
    ext = f"{_INVERS[t.step]}{t.accidental.modifier.replace('-', 'b') if t.accidental else ''} {'menor' if k.mode == 'minor' else 'major'}"
    out = [f"Comprovació d'harmonia: {n} sonoritats (una per pols), veus {lletres}, tonalitat {ext}"
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
            out.append(f"  - {r['lloc'].split(', ', 1)[1]}: {r['text']}. Fitxa: {r['fitxa']}")
        out.append(f"\n{len(inc)} possible(s) problema(es). Són regles d'escola: algunes tenen excepcions (mira la fitxa) "
                   "i els temps no harmònics (notes de pas) poden donar avisos que no ho són. Decideix amb criteri.")
    out.append("Només comprovo: quintes i octaves paral·leles i directes, sensible, 7a del V7, 6a augmentada, "
               "creuament, separació i tessitura. No és una revisió harmònica completa.")
    return "\n".join(out)
