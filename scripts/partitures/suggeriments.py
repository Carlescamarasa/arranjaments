"""Suggeriments de peces: tradueix una petició lliure («un trio de canyes clàssic») en candidates reals.

Tot és determinista i ve de dades reals: la biblioteca compartida (si n'hi ha), el corpus de music21 (el títol i
l'obra es treuen del nom de la carpeta del corpus, mai s'inventen) i, només si encaixen, les partitures d'entrada/.
Les peces que es troben al web les busca l'ajudant (skill buscar-partitura): ací només es diuen les fonts.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from . import instruments as inst
from . import rutes
from .errors import ErrorUsuari

# directori del corpus -> (nom per a mostrar, paraules que el reconeixen)
COMPOSITORS: dict[str, tuple[str, tuple[str, ...]]] = {
    "haydn": ("Haydn", ("haydn",)),
    "mozart": ("Mozart", ("mozart",)),
    "beethoven": ("Beethoven", ("beethoven",)),
    "cpebach": ("C.P.E. Bach", ("cpebach", "emanuel", "cpe")),
    "bach": ("J.S. Bach", ("bach",)),
    "handel": ("Händel", ("handel", "haendel", "hendel", "haendl")),
    "corelli": ("Corelli", ("corelli",)),
    "weber": ("Weber", ("weber",)),
    "schubert": ("Schubert", ("schubert",)),
    "schumann_robert": ("Robert Schumann", ("schumann",)),
    "schumann_clara": ("Clara Schumann", ("clara",)),
    "chopin": ("Chopin", ("chopin",)),
    "verdi": ("Verdi", ("verdi",)),
    "beach": ("Amy Beach", ("beach",)),
    "palestrina": ("Palestrina", ("palestrina",)),
    "josquin": ("Josquin", ("josquin",)),
    "monteverdi": ("Monteverdi", ("monteverdi",)),
    "ciconia": ("Ciconia", ("ciconia",)),
    "trecento": ("Trecento (segle XIV)", ("trecento",)),
    "joplin": ("Scott Joplin", ("joplin",)),
    "leadSheet": ("Cançons amb acords", ("foster", "berlin")),
    "johnson_j_r": ("J. Rosamond Johnson", ("johnson",)),
    "schoenberg": ("Schoenberg", ("schoenberg", "schonberg")),
    "webern": ("Webern", ("webern",)),
    "essenFolksong": ("Cançó popular (Essen)", ()),
    "airdsAirs": ("Cançó popular (Aird)", ()),
    "oneills1850": ("Cançó popular (O'Neill)", ()),
    "ryansMammoth": ("Cançó popular (Ryan)", ()),
    "miscFolk": ("Cançó popular", ()),
}

# període o estil -> (nom, paraules que el reconeixen, directoris del corpus en ordre, paraules per a l'entrada)
PERIODES: dict[str, tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {
    "classicisme": ("classicisme", ("classicisme", "classic", "classica", "classico", "classical", "clasicismo", "clasico",
                                    "clasica", "vienes", "viena"),
                    ("haydn", "mozart", "beethoven", "cpebach"), ("haydn", "mozart", "beethoven", "clementi", "sonatina")),
    "barroc": ("barroc", ("barroc", "barroca", "barroco", "baroque", "barroque"),
               ("bach", "handel", "corelli", "cpebach"), ("bach", "handel", "corelli", "vivaldi", "telemann", "bwv")),
    "romanticisme": ("romanticisme", ("romanticisme", "romantic", "romantica", "romantico", "romanticismo", "romantique"),
                     ("schumann_robert", "schumann_clara", "schubert", "chopin", "weber", "verdi", "beach"),
                     ("schumann", "schubert", "chopin", "weber", "verdi")),
    "renaixement": ("renaixement", ("renaixement", "renacimiento", "renaissance", "medieval", "antiga", "antigua", "ancient"),
                    ("palestrina", "josquin", "monteverdi", "ciconia", "trecento"),
                    ("palestrina", "josquin", "monteverdi", "trecento")),
    "jazz": ("jazz i ragtime", ("jazz", "ragtime", "rag", "swing", "blues", "dixieland"),
             ("joplin", "leadSheet", "johnson_j_r"), ("joplin", "rag", "ragtime", "swing", "blues", "jazz")),
    "popular": ("cançó popular", ("popular", "populars", "folk", "folklore", "folklorica", "tradicional", "traditional",
                                  "canço", "cancion", "cancons", "cancion"),
                ("essenFolksong", "miscFolk", "airdsAirs", "oneills1850", "ryansMammoth"), ()),
    "modern": ("segle XX", ("modern", "moderna", "contemporani", "contemporanea", "atonal", "dodecafonic"),
               ("schoenberg", "webern"), ("schoenberg", "webern")),
    "coral": ("coral", ("coral", "corals", "chorale", "chorales"), ("bach",), ("bach", "coral", "bwv")),
}

# les paraules d'una petició que NO són una peça ni un compositor
_ESTRANYES = {
    "vull", "voldria", "busque", "busca", "quiero", "queria", "necessite", "necesito", "una", "uns", "unes", "peca", "peces",
    "pieza", "obra", "obres", "per", "para", "amb", "con", "del", "dels", "les", "los", "las", "uno", "que", "algo",
    "alguna", "algun", "classe", "classes", "curs", "nivell", "nivel", "elemental", "elementals", "professional", "professionals",
    "mitja", "grau", "primer", "segon", "tercer", "quart", "cinque", "sisque", "ensenyances", "arranjament", "arreglo",
    "arranjar", "trio", "quartet", "quintet", "duo", "duet", "cuarteto", "quinteto", "conjunt", "grup", "ensemble",
    "cambra", "orquestra", "banda", "musica", "partitura", "partitures", "nova", "nou", "facil", "senzilla", "senzill",
    "curta", "curt", "llarga", "bonica", "bonic", "estil", "epoca", "periode", "periodo", "epoch", "style", "period",
    "canyes", "canas", "cana", "vent", "metall", "corda", "cordes", "percussio", "tecla", "teclat",
}


def _norm(text: str) -> str:
    return inst._norm(text)


def _tokens(text: str) -> list[str]:
    return [w for w in re.split(r"[^0-9a-z#]+", _norm(text)) if w]


def _paraules_instrument() -> set[str]:
    sortida: set[str] = set()
    for i in inst.CATALEG:
        sortida.update(_tokens(f"{i.clau} {i.nom}"))
    for g in inst.GRUPS:
        sortida.add(_norm(g))
    return sortida


def comprendre(text: str) -> dict:
    """Què demana el text: períodes reconeguts, compositors (directoris del corpus) i paraules soltes."""
    tokens = _tokens(re.sub(r"\bc\.?\s?p\.?\s?e\.?", "cpe", text, flags=re.I))
    periodes: list[str] = []
    dirs: list[str] = []
    estranyes = _ESTRANYES | _paraules_instrument()
    soltes: list[str] = []
    for w in tokens:
        trobat = False
        for clau, (_, paraules, _, _) in PERIODES.items():
            if w in paraules:
                if clau not in periodes:
                    periodes.append(clau)
                trobat = True
        for d, (_, paraules) in COMPOSITORS.items():
            if w in paraules:
                if d not in dirs:
                    dirs.append(d)
                trobat = True
        if not trobat and len(w) >= 4 and w not in estranyes and not w.isdigit():
            soltes.append(w)
    # «c.p.e. bach» o «emanuel bach» no han de dur també J.S. Bach
    if "cpebach" in dirs and "bach" in dirs and any(w in tokens for w in ("emanuel", "cpebach", "cpe")):
        dirs.remove("bach")
    return {"periodes": periodes, "compositors": dirs, "soltes": soltes}


# ---------------------------------------------------------------- noms llegibles a partir del corpus

def _segment(seg: str) -> str:
    s = re.sub(r"\.(mxl|xml|musicxml|krn|mid|abc)$", "", seg, flags=re.I)
    m = re.fullmatch(r"opus(\d+)(?:no(\d+))?", s, flags=re.I)
    if m:
        return f"op. {m.group(1)}" + (f" núm. {m.group(2)}" if m.group(2) else "")
    m = re.fullmatch(r"k(\d+)", s, flags=re.I)
    if m:
        return f"K. {m.group(1)}"
    m = re.fullmatch(r"bwv(\d+(?:\.\d+)?)", s, flags=re.I)
    if m:
        return f"BWV {m.group(1)}"
    m = re.fullmatch(r"h(\d+)", s, flags=re.I)
    if m:
        return f"H. {m.group(1)}"
    m = re.fullmatch(r"movement(\d+)(?:_(\w+))?", s, flags=re.I)
    if m:
        return f"moviment {m.group(1)}" + (f" ({m.group(2)})" if m.group(2) else "")
    return re.sub(r"[_]+", " ", re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)).strip()


def titol_de_ruta(ruta: str) -> str:
    """«haydn/opus74no1/movement2.mxl» -> «Haydn: op. 74 núm. 1, moviment 2». Només el que diu la ruta."""
    segs = ruta.replace("\\", "/").split("/")
    nom = COMPOSITORS.get(segs[0], (segs[0].capitalize(), ()))[0]
    resta = ", ".join(_segment(s) for s in segs[1:])
    return f"{nom}: {resta}" if resta else nom


def _obra(ruta: str) -> str:
    """Identifica l'obra (sense el moviment): per a «haydn/opus74no1/movement2.mxl», «haydn/opus74no1»."""
    segs = ruta.replace("\\", "/").split("/")
    if len(segs) > 2:
        return "/".join(segs[:-1])
    return "/".join(segs)[: -len(Path(segs[-1]).suffix)] if Path(segs[-1]).suffix else "/".join(segs)


def _moviment(ruta: str) -> int | None:
    m = re.search(r"movement(\d+)", ruta)
    return int(m.group(1)) if m else None


def _facil(nivell: str | None) -> bool:
    if not nivell:
        return False
    try:
        from .nivells import normalitza_curs
        n = normalitza_curs(nivell)
    except Exception:  # noqa: BLE001
        n = _norm(nivell)
    return "elemental" in n or "iniciacio" in n or "preparatori" in n or "bàsic" in n or "basic" in n


def _entrades_corpus() -> list[str]:
    from music21 import corpus
    rutes_ = []
    for e in corpus.corpora.CoreCorpus().metadataBundle:
        rutes_.append(Path(str(e.sourcePath)).as_posix().split("/corpus/")[-1])
    return sorted(set(rutes_))


def candidates_corpus(dirs: list[str], facil: bool, maxim: int, tots: list[str] | None = None) -> list[dict]:
    """Una peça per obra, repartida per compositors a tombs (Haydn, Mozart, Beethoven, Haydn...)."""
    tots = tots if tots is not None else _entrades_corpus()
    per_comp: dict[str, list[str]] = {}
    for d in dirs:
        obres: dict[str, list[str]] = {}
        for r in tots:
            if r.split("/")[0] != d:
                continue
            obres.setdefault(_obra(r), []).append(r)
        triades = []
        for obra in sorted(obres):
            movs = sorted(obres[obra], key=lambda r: (r.endswith(".krn"), _moviment(r) or 0, r))
            sense_krn = [r for r in movs if not r.endswith(".krn")] or movs
            if facil:   # un moviment lent o un minuet sol ser més assequible que un primer moviment
                preferit = [r for r in sense_krn if _moviment(r) in (2, 3)]
                triades.append((preferit or sense_krn)[0])
            else:
                triades.append(sense_krn[0])
        # obres molt abundants (milers de cançons o misses): se'n mostren poques i repartides
        if len(triades) > 40:
            pas = len(triades) // 4
            triades = triades[::pas][:4]
        per_comp[d] = triades
    sortida: list[dict] = []
    k = 0
    while len(sortida) < maxim and any(k < len(v) for v in per_comp.values()):
        for d in dirs:
            if k < len(per_comp.get(d, [])) and len(sortida) < maxim:
                r = per_comp[d][k]
                sortida.append({"font": "corpus", "ref": r, "titol": titol_de_ruta(r), "motiu": ""})
        k += 1
    return sortida


# ---------------------------------------------------------------- detalls de les candidates

def _detall_corpus(ref: str) -> str:
    try:
        import warnings
        from music21 import corpus
        from . import musica
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            s = corpus.parse(ref)
            s = s.scores[0] if hasattr(s, "scores") else s
            d = musica.info(s)
    except Exception:  # noqa: BLE001
        return ""
    parts = d["parts"]
    noms = ", ".join(musica._curt(p["nom"], 18) for p in parts[:4]) + (", ..." if len(parts) > 4 else "")
    ll = [f"{len(parts)} {'part' if len(parts) == 1 else 'parts'} ({noms})"]
    if parts and parts[0]["compassos"]:
        ll.append(f"{parts[0]['compassos']} compassos")
    if d["tonalitat"]:
        ll.append(d["tonalitat"])
    if d["compas"]:
        ll.append(f"compàs {d['compas']}")
    return "; ".join(ll)


MAX_COMPASSOS_FACIL = 250


def _compassos(detall: str) -> int:
    m = re.search(r"(\d+) compassos", detall)
    return int(m.group(1)) if m else 0


def _quants(instruments: str | None) -> int:
    if not instruments:
        return 0
    return len([x for x in re.split(r",|;|\+|\by\b|\bi\b|\be\b", instruments) if x.strip()])


def _consell_parts(detall: str, n: int) -> str:
    m = re.match(r"(\d+) part", detall)
    if not n or not m:
        return ""
    p = int(m.group(1))
    if p == n:
        return "Les parts ja coincideixen amb el nombre d'instruments."
    if p > n:
        return f"Té {p} parts i en vols {n}: es poden repartir o reduir."
    if p == 1:
        return f"Té una sola part (la melodia): les altres {n - 1} les pot crear l'arranjament."
    return f"Té {p} parts i en vols {n}: l'arranjament pot crear les que falten."


# ---------------------------------------------------------------- biblioteca i entrada

def _biblioteca(cerques: list[tuple[str, str | None]], nivell: str | None, maxim: int) -> list[dict]:
    """Resultats de la biblioteca compartida (si n'hi ha) per a cada (paraules, estil)."""
    from . import biblioteca as bib
    try:
        if not bib.hi_ha_biblioteca():
            return []
        arrel = bib.biblioteca()
        if not bib.llig_index(arrel)["fitxers"]:
            return []
    except Exception:  # noqa: BLE001
        return []
    vistos: set[str] = set()
    sortida: list[dict] = []
    for text, estil in cerques:
        trobats = []
        for ambit in ((nivell, None) if nivell else (None,)):
            trobats = bib.cerca(text, ambit, estil, None, arrel)
            if trobats:
                break
        for _, rel, reg in trobats[:2]:
            if rel in vistos or len(sortida) >= maxim:
                continue
            vistos.add(rel)
            tit = reg.get("titol_f") or reg.get("titol") or bib._titol_del_nom(rel)
            comp = reg.get("compositor_f") or reg.get("compositor")
            sortida.append({"font": "biblioteca", "ref": rel, "titol": tit + (f", {comp}" if comp else ""),
                            "motiu": "És a la biblioteca de l'escola"
                            + (f" (nivell {', '.join(reg['nivell'])})" if reg.get("nivell") else "") + "."})
    return sortida


def _entrada(paraules: list[str]) -> list[dict]:
    base = rutes.carpeta("entrada")
    if not base.is_dir() or not paraules:
        return []
    sortida = []
    for f in sorted(base.iterdir(), key=lambda f: f.name.lower()):
        if not f.is_file() or f.suffix.lower() not in (".musicxml", ".xml", ".mxl", ".mscz", ".mscx"):
            continue
        n = _norm(f.stem)
        hits = [w for w in paraules if w in n]
        if hits:
            sortida.append({"font": "entrada", "ref": f.name, "titol": f.name,
                            "motiu": f"Ja és a entrada/ i encaixa amb «{hits[0]}»."})
    return sortida


# ---------------------------------------------------------------- l'ordre

FONTS_WEB = [
    "OpenScore (https://github.com/OpenScore i https://musescore.com/openscore): transcripcions lliures (CC0); "
    "fitxers de MuseScore (.mscx) que es converteixen a MusicXML.",
    "CPDL (https://www.cpdl.org): música coral i antiga; molts arxius tenen MusicXML, però cal mirar cada edició.",
    "Mutopia (https://www.mutopiaproject.org): domini públic; sobretot PDF i LilyPond, el MusicXML és rar.",
    "IMSLP (https://imslp.org): quasi tot PDF (via PDF, no recomanada).",
]


def fitxer_ultim() -> Path:
    from . import biblioteca as bib
    return bib._dades() / "suggeriments-ultims.json"


def suggereix(text: str, nivell: str | None = None, instruments: str | None = None, maxim: int = 6) -> tuple[list[dict], list[str]]:
    """(llista de candidates, línies de text per a mostrar)."""
    maxim = max(1, min(maxim, 8))
    q = comprendre(text)
    dirs: list[str] = list(q["compositors"])
    pals: list[str] = []
    for p in q["periodes"]:
        for d in PERIODES[p][2]:
            if d not in dirs:
                dirs.append(d)
        pals.extend(PERIODES[p][3])
    for d in q["compositors"]:
        pals.extend(COMPOSITORS[d][1])
    paraules_entrada = list(dict.fromkeys(pals + q["soltes"]))

    candidates: list[dict] = []
    candidates += _entrada(paraules_entrada)[:2]
    cerques: list[tuple[str, str | None]] = [(COMPOSITORS[d][0], None) for d in dirs[:5] if COMPOSITORS[d][1]]
    cerques += [(w, None) for w in q["soltes"][:2]]
    if "jazz" in q["periodes"]:
        cerques.append(("", "jazz"))
    candidates += _biblioteca(cerques, nivell, 3)
    lliures = max(1, maxim - len(candidates))
    corpus_dirs = list(dirs)
    facil = _facil(nivell)
    candidates += candidates_corpus(corpus_dirs, facil, lliures + (3 if facil else 0))
    # paraules soltes: potser són una obra o un compositor del corpus («fosters», «chopin mazurka»)
    if q["soltes"] and len(candidates) < maxim:
        from . import musica
        for w in q["soltes"][:2]:
            for t in musica.cercar_corpus(w)[:2]:
                if len(candidates) >= maxim:
                    break
                if all(c["ref"] != t["ruta"] for c in candidates):
                    candidates.append({"font": "corpus", "ref": t["ruta"], "titol": titol_de_ruta(t["ruta"]),
                                       "motiu": f"Coincideix amb «{w}»."})
    n = _quants(instruments)
    nom_per = " i ".join(PERIODES[p][0] for p in q["periodes"])
    ll: list[str] = []
    if not candidates:
        ll.append(f"No tinc cap peça del corpus ni de la biblioteca per a «{text.strip()}».")
    # un curs elemental no vol una obra de mil compassos: es descarten les molt llargues (i se'n queden les primeres)
    for c in candidates:
        if c["font"] == "corpus":
            c["detall"] = _detall_corpus(c["ref"])
    if facil:
        curtes = [c for c in candidates if c["font"] != "corpus" or _compassos(c.get("detall", "")) <= MAX_COMPASSOS_FACIL]
        candidates = curtes if len(curtes) >= min(3, len(candidates)) else candidates
    candidates = candidates[:maxim]
    for k, c in enumerate(candidates, 1):
        if c["font"] == "corpus":
            detall = c.get("detall", "")
            comp = _comp_de_ruta(c["ref"])
            extra = []
            if c["motiu"]:
                extra.append(c["motiu"])
            elif nom_per and comp in _dirs_periodes(q):
                extra.append(f"Encaixa amb {nom_per}.")
            if _facil(nivell) and _moviment(c["ref"]) in (2, 3):
                extra.append("Moviment lent o minuet: sol ser més assequible.")
            consell = _consell_parts(detall, n)
            if consell:
                extra.append(consell)
            c["motiu"] = " ".join(extra)
            ll.append(f"{k}. {c['titol']}   [corpus lliure]")
            if detall:
                ll.append(f"   {detall}")
        else:
            ll.append(f"{k}. {c['titol']}   [{'biblioteca' if c['font'] == 'biblioteca' else 'entrada/'}]")
        if c["motiu"]:
            ll.append(f"   Per què: {c['motiu']}")
    if candidates:
        ll.append("Per a deixar-ne una a entrada/: partitures suggereix --copia <número>")
    ll.append("Si no n'hi ha cap que et convinga, busca al web (confirma que hi ha un fitxer MusicXML o MuseScore abans "
              "d'oferir-ho; no t'inventes títols ni enllaços):")
    ll += [f"  - {f}" for f in FONTS_WEB]
    ll.append("També pot dir una peça concreta, o deixar el seu fitxer a entrada/.")
    return candidates, ll


def _comp_de_ruta(ref: str) -> str:
    return ref.replace("\\", "/").split("/")[0]


def _dirs_periodes(q: dict) -> set[str]:
    out: set[str] = set(q["compositors"])
    for p in q["periodes"]:
        out.update(PERIODES[p][2])
    return out


def desa_ultims(candidates: list[dict]) -> None:
    f = fitxer_ultim()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps([{k: c[k] for k in ("font", "ref", "titol")} for c in candidates], ensure_ascii=False), encoding="utf-8")


def copia(n: int) -> Path:
    """Deixa a entrada/ la candidata n de l'últim suggeriment."""
    try:
        llista = json.loads(fitxer_ultim().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        llista = []
    if not llista:
        raise ErrorUsuari("Primer cal demanar suggeriments: partitures suggereix \"el que busques\".")
    if not 1 <= n <= len(llista):
        raise ErrorUsuari(f"El número {n} no coincideix amb cap suggeriment (de l'1 al {len(llista)}).")
    c = llista[n - 1]
    if c["font"] == "entrada":
        return rutes.dins(rutes.carpeta("entrada") / Path(c["ref"]).name, "entrada")
    if c["font"] == "biblioteca":
        from . import biblioteca as bib
        return bib.copia_fitxer(bib.biblioteca(), c["ref"])
    from music21 import corpus
    from . import musica
    s = corpus.parse(c["ref"])
    s = s.scores[0] if hasattr(s, "scores") else s
    segs = [re.sub(r"\.(mxl|xml|musicxml|krn|mid|abc)$", "", s, flags=re.I) for s in c["ref"].replace("\\", "/").split("/")]
    nom = rutes.netejar_nom("-".join(re.sub(r"^movement", "mov", s) for s in segs)).replace(" ", "-").lower()
    desti = rutes.eixida_per_defecte(nom, "", nom_carpeta="entrada")
    return musica.desar(s, desti)
