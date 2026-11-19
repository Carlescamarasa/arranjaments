"""Biblioteca compartida del professorat: una carpeta de Teams/OneDrive que apareix al disc de l'ordinador.

Les eines NOMÉS LLIGEN d'esta carpeta: mai hi escriuen, mai hi esborren ni hi canvien res.
L'índex (per a cercar de pressa) es guarda a la carpeta de dades d'Arranjaments, fora de la biblioteca.

Com la troba (en este ordre):
  1. la variable d'entorn ARRANJAMENTS_BIBLIOTECA;
  2. el fitxer biblioteca.txt de la carpeta de dades (una línia amb la ruta);
  3. cerca automàtica d'una carpeta «Biblioteca d'arranjaments» dins de les carpetes de OneDrive
     (Mac: ~/Library/CloudStorage/OneDrive-*; Windows: OneDriveCommercial, OneDrive i carpetes
     del perfil que comencen per «OneDrive» o tenen la forma «Organització - Lloc»).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
import unicodedata
from pathlib import Path

from . import rutes
from .errors import ErrorUsuari

NOM_CARPETA = "Biblioteca d'arranjaments"
CLAU_NOM = "bibliotecadarranjaments"
PROFUNDITAT_CERCA = 5          # nivells de carpetes a mirar dins de cada carpeta de OneDrive
MAX_CARPETES_CERCA = 20000     # límit de seguretat
PROFUNDITAT_MAXIMA = 12
EXT_PARTITURA = {".musicxml", ".xml", ".mxl"}
EXT_MUSESCORE = {".mscz", ".mscx"}
EXT_PDF = {".pdf"}
EXT_INDEXADES = EXT_PARTITURA | EXT_MUSESCORE | EXT_PDF
MIDA_MAXIMA_ANALISI = 30 * 1024 * 1024
MAX_NOVES = 200
MAX_SEGONS = 120
VERSIO_INDEX = 1

URL_ONEDRIVE = "https://www.microsoft.com/microsoft-365/onedrive/download"
URL_ONEDRIVE_MAC_PKG = "https://go.microsoft.com/fwlink/?linkid=823060"       # OneDrive.pkg (enllaç oficial de Microsoft)
URL_ONEDRIVE_WIN_EXE = "https://go.microsoft.com/fwlink/?linkid=844652"       # OneDriveSetup.exe (enllaç oficial de Microsoft)
URL_ONEDRIVE_APPSTORE = "https://apps.apple.com/app/onedrive/id823766827"

PASSOS_TEAMS = (
    "Només cal fer-ho una vegada, des del navegador, amb el teu compte de l'escola:\n"
    "  0. Qui crea la biblioteca ha de posar a la carpeta compartida EXACTAMENT el nom «Biblioteca d'arranjaments».\n"
    "  1. Obri l'enllaç de la biblioteca que t'ha passat una companya (o Teams: el canal i la pestanya «Fitxers»).\n"
    "  2. Selecciona la carpeta (el cercle de la seua targeta) i prem «Afegeix una drecera a Els meus fitxers».\n"
    "     (En castellà: «Agregar acceso directo a Mis archivos»; en anglés: «Add shortcut to My files».\n"
    "     En versions noves pot dir «Afegeix una drecera a OneDrive»: tria «Els meus fitxers».)\n"
    "  3. Tingues l'aplicació OneDrive instal·lada i amb el compte de l'escola. Espera uns minuts i la carpeta\n"
    "     apareixerà dins de la teua carpeta OneDrive de l'ordinador.\n"
    "  4. Torna a provar amb: partitures biblioteca on-es\n"
    "Si ja la veus al Finder o a l'Explorador de fitxers però ací no la troba, digues-me la ruta i la guarde."
)


# --------------------------------------------------------------------------- text

def norm(text: str) -> str:
    """Minúscules, sense accents i amb espais simples."""
    t = unicodedata.normalize("NFD", str(text).lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t).strip()


def _clau(text: str) -> str:
    """Només lletres i xifres: «Biblioteca d'arranjaments», «biblioteca d’arranjaments» i «Biblioteca d arranjaments» coincideixen."""
    return re.sub(r"[^0-9a-z]", "", norm(text))


def es_la_biblioteca(nom: str) -> bool:
    return CLAU_NOM in _clau(nom)


# --------------------------------------------------------------------------- on és

def _plataforma() -> str:
    if sys.platform == "darwin":
        return "mac"
    if sys.platform.startswith("win"):
        return "windows"
    return "altre"


def _dades() -> Path:
    from .actualitzar import dades_per_defecte
    return dades_per_defecte()


def arrels_onedrive(home: Path | None = None, entorn: dict | None = None, plataforma: str | None = None) -> list[Path]:
    """Carpetes de OneDrive (locals) on pot aparéixer la biblioteca, ordenades de més a menys probable."""
    home = Path(home) if home else Path.home()
    entorn = os.environ if entorn is None else entorn
    plataforma = plataforma or _plataforma()
    res: list[Path] = []

    def afig(p):
        if p and Path(p).is_dir() and Path(p) not in res:
            res.append(Path(p))

    def fills(base: Path):
        try:
            return sorted(c for c in base.iterdir() if c.is_dir() and not c.name.startswith("."))
        except OSError:
            return []

    if plataforma == "mac":
        altres = ("googledrive", "dropbox", "box", "icloud", "proton", "pcloud", "nextcloud")
        base = home / "Library" / "CloudStorage"
        carpetes = fills(base)
        for c in carpetes:                                   # primer les de OneDrive...
            if norm(c.name).startswith("onedrive"):
                afig(c)
        for c in carpetes:                                   # ...després altres (dreceres de SharePoint amb el nom de l'organització)
            if not norm(c.name).startswith(altres):
                afig(c)
        for c in fills(home):                                # forma antiga: ~/OneDrive - Escola
            if norm(c.name).startswith("onedrive"):
                afig(c)
    elif plataforma == "windows":
        for v in ("OneDriveCommercial", "OneDrive", "OneDriveConsumer"):
            afig(entorn.get(v))
        perfil = Path(entorn.get("USERPROFILE") or home)
        carpetes = fills(perfil)
        for c in carpetes:
            if norm(c.name).startswith("onedrive"):          # «OneDrive - Escola»
                afig(c)
        for c in carpetes:
            if " - " in c.name:                              # «Escola - Lloc» (biblioteca de SharePoint sincronitzada)
                afig(c)
    return res


def _buscar_dins(arrel: Path) -> list[Path]:
    """Cerca per amplada (el més superficial primer) carpetes amb el nom de la biblioteca, amb límits."""
    trobades: list[Path] = []
    nivell = [arrel]
    visitades = 0
    for profunditat in range(PROFUNDITAT_CERCA + 1):
        seguent = []
        for d in nivell:
            try:
                entrades = sorted(os.scandir(d), key=lambda e: e.name)
            except OSError:
                continue
            for e in entrades:
                try:
                    if not e.is_dir() or e.name.startswith("."):
                        continue
                except OSError:
                    continue
                visitades += 1
                if es_la_biblioteca(e.name):
                    trobades.append(Path(e.path))
                else:
                    seguent.append(Path(e.path))
        if visitades > MAX_CARPETES_CERCA:
            break
        nivell = seguent
        if trobades:
            break
    if not trobades and es_la_biblioteca(arrel.name):
        trobades.append(arrel)
    return trobades


def fitxer_config() -> Path:
    return _dades() / "biblioteca.txt"


def guarda_ruta(ruta: str) -> Path:
    """Guarda la carpeta de la biblioteca (si té un altre nom o és en un altre lloc) a biblioteca.txt, a la carpeta de dades."""
    p = Path(ruta).expanduser()
    if not p.is_dir():
        raise ErrorUsuari(f"«{ruta}» no és una carpeta que existisca. Comprova la ruta (la carpeta ha d'estar ja al Finder o a l'Explorador).")
    f = fitxer_config()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(str(p.resolve()) + "\n", encoding="utf-8")
    return p


def localitzar(home: Path | None = None, entorn: dict | None = None, plataforma: str | None = None) -> dict:
    """Retorna {"ruta": Path|None, "origen": str, "altres": [Path], "mirat": [Path], "avis": str|None}."""
    entorn = os.environ if entorn is None else entorn
    plataforma = plataforma or _plataforma()
    forcada = entorn.get("ARRANJAMENTS_BIBLIOTECA")
    if forcada:
        p = Path(forcada).expanduser()
        if p.is_dir():
            return {"ruta": p, "origen": "variable ARRANJAMENTS_BIBLIOTECA", "altres": [], "mirat": [], "avis": None}
        return {"ruta": None, "origen": "variable ARRANJAMENTS_BIBLIOTECA", "altres": [], "mirat": [],
                "avis": f"La variable ARRANJAMENTS_BIBLIOTECA apunta a «{forcada}», però esta carpeta no existeix."}
    try:
        text = fitxer_config().read_text(encoding="utf-8-sig").strip().splitlines()
    except OSError:
        text = []
    if text and text[0].strip():
        p = Path(text[0].strip()).expanduser()
        if p.is_dir():
            return {"ruta": p, "origen": f"fitxer {fitxer_config()}", "altres": [], "mirat": [], "avis": None}
        avis = f"El fitxer biblioteca.txt apunta a «{p}», però esta carpeta no existeix (o OneDrive encara no l'ha creada)."
    else:
        avis = None
    arrels = arrels_onedrive(home, entorn, plataforma)
    trobades: list[Path] = []
    for a in arrels:
        for t in _buscar_dins(a):
            if t not in trobades:
                trobades.append(t)
    if trobades:
        return {"ruta": trobades[0], "origen": "cerca automàtica a OneDrive", "altres": trobades[1:],
                "mirat": arrels, "avis": avis}
    return {"ruta": None, "origen": "cerca automàtica a OneDrive", "altres": [], "mirat": arrels, "avis": avis}


def biblioteca() -> Path:
    """Ruta de la biblioteca o error amb les instruccions d'una sola vegada."""
    r = localitzar()
    if r["ruta"] is None:
        raise ErrorUsuari("No trobe la biblioteca compartida («Biblioteca d'arranjaments»). Executa «partitures biblioteca on-es» "
                          "per a veure què cal fer.")
    return r["ruta"]


def onedrive_instalat(home: Path | None = None, entorn: dict | None = None, plataforma: str | None = None) -> bool:
    """Hi ha l'aplicació OneDrive a l'ordinador? (No diu si s'ha entrat amb un compte.)"""
    home = Path(home) if home else Path.home()
    entorn = os.environ if entorn is None else entorn
    plataforma = plataforma or _plataforma()
    if plataforma == "mac":
        return any((b / "OneDrive.app").exists() for b in (Path("/Applications"), home / "Applications"))
    if plataforma == "windows":
        bases = [entorn.get("LOCALAPPDATA") and Path(entorn["LOCALAPPDATA"]) / "Microsoft" / "OneDrive",
                 entorn.get("ProgramFiles") and Path(entorn["ProgramFiles"]) / "Microsoft OneDrive",
                 entorn.get("ProgramFiles(x86)") and Path(entorn["ProgramFiles(x86)"]) / "Microsoft OneDrive"]
        return any(b and (b / "OneDrive.exe").exists() for b in bases)
    return False


def _guia_onedrive(plataforma: str, instalat: bool, arrels: list) -> list[str]:
    """Quin pas falta: instal·lar OneDrive, entrar-hi amb el compte, o afegir la drecera."""
    if not instalat and not arrels:
        if plataforma == "mac":
            return ["Pas que falta: instal·lar OneDrive (no el trobe a este Mac).",
                    f"  Baixa l'instal·lador oficial de Microsoft (OneDrive.pkg, demana la contrasenya del Mac): {URL_ONEDRIVE_MAC_PKG}",
                    f"  O, sense contrasenya d'administrador, des de l'App Store: {URL_ONEDRIVE_APPSTORE}",
                    f"  Més informació: {URL_ONEDRIVE}"]
        if plataforma == "windows":
            return ["Pas que falta: OneDrive hauria de venir amb Windows, però no el trobe.",
                    f"  Baixa l'instal·lador oficial de Microsoft (OneDriveSetup.exe): {URL_ONEDRIVE_WIN_EXE}",
                    f"  Més informació: {URL_ONEDRIVE}"]
        return []
    if not arrels:
        return ["Pas que falta: obrir OneDrive i entrar amb el compte de l'escola (@edu.gva.es). "
                "Encara no hi ha cap carpeta de OneDrive en este ordinador."]
    return ["OneDrive ja està en marxa, però la carpeta de la biblioteca no hi apareix. Pas que falta: obrir l'enllaç de la "
            "biblioteca i prémer «Afegeix una drecera a Els meus fitxers» (o esperar uns minuts si ja ho has fet)."]


def text_on_es() -> str:
    r = localitzar()
    ll = []
    if r["ruta"] is not None:
        ll.append(f"He trobat la biblioteca: {r['ruta']}")
        ll.append(f"(Com l'he trobada: {r['origen']}.)")
        for o in r["altres"]:
            ll.append(f"També hi ha una altra carpeta amb nom paregut: {o} (no l'he usada).")
        n = estadistica(r["ruta"])
        ll.append(f"Dins hi ha {n['partitures']} partitures editables, {n['musescore']} de MuseScore i {n['pdf']} PDF"
                  + (f" ({n['al_nuvol']} encara només al núvol, no descarregades)." if n["al_nuvol"] else "."))
        ll.append("La biblioteca només es llig: les eines mai hi escriuen ni hi esborren res.")
        return "\n".join(ll)
    if r["avis"]:
        ll.append(r["avis"])
    if _plataforma() == "altre" and not r["mirat"]:
        ll.append("Este ordinador no té OneDrive (per exemple LliureX o Linux): la biblioteca compartida no hi funciona, "
                  "perquè no hi ha cap programa de OneDrive que la baixe. Pots usar-la des d'un Mac o Windows.")
        ll.append("Si algú t'ha passat una còpia de la carpeta, indica'm on és amb la variable ARRANJAMENTS_BIBLIOTECA "
                  f"o desant-la amb: partitures biblioteca on-es --ruta \"/ruta/de/la/carpeta\".")
        return "\n".join(ll)
    ll.append("No trobe la carpeta «Biblioteca d'arranjaments» a l'ordinador.")
    if r["mirat"]:
        ll.append("He mirat dins de: " + "; ".join(str(m) for m in r["mirat"]))
    ll += _guia_onedrive(_plataforma(), onedrive_instalat(), r["mirat"])
    ll.append(PASSOS_TEAMS)
    ll.append("Si la carpeta té un altre nom o és en un altre lloc, desa'n la ruta amb: "
              "partitures biblioteca on-es --ruta \"/ruta/de/la/carpeta\"")
    return "\n".join(ll)


# --------------------------------------------------------------------------- recorregut (només lectura)

def al_nuvol(st: os.stat_result) -> bool:
    """El fitxer és un marcador: encara no s'ha descarregat (Files On-Demand de Windows o de Mac)."""
    attrs = getattr(st, "st_file_attributes", 0) or 0
    if attrs & (0x00400000 | 0x00040000 | 0x00001000):    # RECALL_ON_DATA_ACCESS | RECALL_ON_OPEN | OFFLINE
        return True
    flags = getattr(st, "st_flags", 0) or 0
    return bool(flags & 0x40000000)                       # SF_DATALESS (macOS File Provider)


def recorre(arrel: Path):
    """Dona (ruta_relativa_posix, DirEntry-stat) de cada fitxer indexable. No obri res ni segueix enllaços a fora."""
    pila = [(Path(arrel), 0)]
    while pila:
        d, prof = pila.pop()
        if prof > PROFUNDITAT_MAXIMA:
            continue
        try:
            entrades = sorted(os.scandir(d), key=lambda e: e.name)
        except OSError:
            continue
        for e in entrades:
            if e.name.startswith((".", "~$")):
                continue
            try:
                if e.is_dir(follow_symlinks=False):
                    pila.append((Path(e.path), prof + 1))
                    continue
                if Path(e.name).suffix.lower() not in EXT_INDEXADES or not e.is_file(follow_symlinks=False):
                    continue
                st = e.stat(follow_symlinks=False)
            except OSError:
                continue
            yield Path(e.path).relative_to(arrel).as_posix(), st


def estadistica(arrel: Path) -> dict:
    n = {"partitures": 0, "musescore": 0, "pdf": 0, "al_nuvol": 0}
    for rel, st in recorre(arrel):
        ext = Path(rel).suffix.lower()
        n["partitures" if ext in EXT_PARTITURA else "musescore" if ext in EXT_MUSESCORE else "pdf"] += 1
        n["al_nuvol"] += al_nuvol(st)
    return n


# --------------------------------------------------------------------------- etiquetes (nivell i estil)

_PARAULES_NIVELL = ("elemental", "professional", "mitja", "mitjana", "mitjano", "basic", "basico", "iniciacio",
                    "superior", "avancat", "avanzado", "principiant", "intermedi", "intermedio", "grau", "grado")
_RE_CURS = re.compile(r"^\d{1,2}\s?(r|n|t|e|er|o|a)?(\s|$)")


def es_nivell(etiqueta: str) -> bool:
    n = norm(etiqueta)
    return bool(_RE_CURS.match(n)) or any(p in n.split() or p in n for p in _PARAULES_NIVELL)


def _llista(text: str) -> list[str]:
    return [t.strip() for t in re.split(r"[,;]", text) if t.strip()]


def etiquetes_de(rel: str, arrel: Path) -> dict:
    """Nivell i estil a partir de: carpetes, [etiquetes] del nom i fitxer de text al costat (opcional)."""
    nivell: list[str] = []
    estil: list[str] = []
    nota = ""
    titol_f = compositor_f = None

    def posa(et: str):
        et = et.strip()
        if et and et not in nivell and et not in estil:
            (nivell if es_nivell(et) else estil).append(et)

    p = Path(rel)
    for carpeta in p.parts[:-1]:
        posa(carpeta)
    for et in re.findall(r"\[([^\]]+)\]", p.name):
        posa(et)
    for cand in (arrel / (rel + ".txt"), arrel / p.with_suffix(".txt")):
        try:
            if not cand.is_file() or cand.stat().st_size > 20000:
                continue
            text = cand.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        lliures = []
        for linia in text.splitlines():
            m = re.match(r"\s*(nivell|nivel|level|estil|estilo|style|etiquetes|etiquetas|tags|titol|titulo|title|"
                         r"compositor|autor|composer)\s*[:=]\s*(.+)$", linia, re.I)
            if not m:
                lliures.append(linia)
                continue
            clau, valor = norm(m.group(1)), m.group(2)
            if clau in ("nivell", "nivel", "level"):
                nivell += [v for v in _llista(valor) if v not in nivell]
            elif clau in ("estil", "estilo", "style"):
                estil += [v for v in _llista(valor) if v not in estil]
            elif clau in ("etiquetes", "etiquetas", "tags"):
                for v in _llista(valor):
                    posa(v)
            elif clau in ("titol", "titulo", "title"):
                titol_f = valor.strip()
            else:
                compositor_f = valor.strip()
        resta = "\n".join(lliures)
        for et in re.findall(r"\[([^\]]+)\]", resta):
            posa(et)
        nota = re.sub(r"\s+", " ", resta).strip()[:500]
        break
    return {"nivell": nivell, "estil": estil, "nota": nota, "titol_f": titol_f, "compositor_f": compositor_f}


def _titol_del_nom(rel: str) -> str:
    stem = Path(rel).stem
    stem = re.sub(r"\s*\[[^\]]*\]", "", stem)
    return re.sub(r"[-_]+", " ", stem).strip() or Path(rel).stem


# --------------------------------------------------------------------------- índex

def fitxer_index() -> Path:
    return _dades() / "biblioteca-index.json"


def fitxer_ultima() -> Path:
    return _dades() / "biblioteca-ultima-cerca.json"


def _llig_json(ruta: Path) -> dict:
    try:
        d = json.loads(ruta.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _desa_json(ruta: Path, dades: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(ruta.name + ".tmp")
    tmp.write_text(json.dumps(dades, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, ruta)


def llig_index(arrel: Path) -> dict:
    d = _llig_json(fitxer_index())
    if d.get("versio") != VERSIO_INDEX or d.get("arrel") != str(arrel):
        return {"versio": VERSIO_INDEX, "arrel": str(arrel), "fitxers": {}}
    d.setdefault("fitxers", {})
    return d


def _analitza(ruta: Path) -> dict:
    """Metadades musicals d'un MusicXML (es descarrega si només és al núvol). Mai modifica res."""
    from . import musica
    d = musica.info(musica.carregar(ruta))
    parts = [{"nom": p["nom"], "instrument": p["instrument_detectat"],
              "mes_greu": p["mes_greu"], "mes_agut": p["mes_agut"]} for p in d["parts"]]
    return {"estat": "ok", "titol": d["titol"], "compositor": d["compositor"], "tonalitat": d["tonalitat"],
            "compas": d["compas"], "compassos": d["parts"][0]["compassos"] if d["parts"] else None, "parts": parts}


def _registre_base(rel: str, st: os.stat_result) -> dict:
    ext = Path(rel).suffix.lower()
    tipus = "pdf" if ext in EXT_PDF else "musescore" if ext in EXT_MUSESCORE else "musicxml"
    return {"mida": st.st_size, "mtime": int(st.st_mtime), "tipus": tipus, "al_nuvol": al_nuvol(st),
            "estat": "pendent" if tipus == "musicxml" else "nomes-nom"}


def actualitza(arrel: Path | None = None, maxim_noves: int = MAX_NOVES, segons: float = MAX_SEGONS,
               sortida=print) -> dict:
    """Posa l'índex al dia. Només analitza fitxers nous o canviats, amb un límit per vegada."""
    import warnings
    arrel = Path(arrel) if arrel else biblioteca()
    antic = llig_index(arrel)["fitxers"]
    nou: dict[str, dict] = {}
    pendents: list[str] = []
    for rel, st in recorre(arrel):
        reg = antic.get(rel)
        if reg and reg.get("mida") == st.st_size and reg.get("mtime") == int(st.st_mtime) and reg.get("estat") != "pendent":
            reg["al_nuvol"] = al_nuvol(st) if reg.get("al_nuvol") else False
            nou[rel] = reg
            continue
        nou[rel] = _registre_base(rel, st)
        if nou[rel]["estat"] == "pendent":
            if st.st_size > MIDA_MAXIMA_ANALISI:
                nou[rel]["estat"] = "nomes-nom"
            else:
                pendents.append(rel)
    inici = time.monotonic()
    fets = errors = 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for rel in pendents:
            if fets + errors >= maxim_noves or time.monotonic() - inici > segons:
                break
            try:
                nou[rel].update(_analitza(arrel / rel))
                fets += 1
            except Exception as e:  # un fitxer dolent no atura la resta
                nou[rel].update({"estat": "error", "error": type(e).__name__})
                errors += 1
            if (fets + errors) % 20 == 0:
                sortida(f"  ... {fets + errors} de {len(pendents)} analitzades")
    queden = sum(1 for r in nou.values() if r["estat"] == "pendent")
    # les etiquetes es calculen sempre (una carpeta o un fitxer de text pot canviar sense tocar la partitura)
    for rel, reg in nou.items():
        reg.update(etiquetes_de(rel, arrel))
    _desa_json(fitxer_index(), {"versio": VERSIO_INDEX, "arrel": str(arrel), "fitxers": nou})
    return {"total": len(nou), "analitzades": fets, "errors": errors, "queden": queden,
            "pdf": sum(1 for r in nou.values() if r["tipus"] == "pdf"),
            "musescore": sum(1 for r in nou.values() if r["tipus"] == "musescore"),
            "al_nuvol": sum(1 for r in nou.values() if r.get("al_nuvol"))}


def text_actualitza(r: dict) -> str:
    ll = [f"Biblioteca: {r['total']} fitxers a l'índex ({r['analitzades']} analitzats ara"
          + (f", {r['errors']} que no he pogut llegir" if r["errors"] else "") + ")."]
    if r["queden"]:
        ll.append(f"Encara en queden {r['queden']} per analitzar: torna a executar «partitures biblioteca actualitza» "
                  "i continuaré on ho havia deixat. Mentrestant ja pots cercar (pels noms i carpetes).")
    else:
        ll.append("Tot al dia.")
    if r["pdf"]:
        ll.append(f"{r['pdf']} són PDF: només els indexe pel nom; per a editar-los cal importar-los («PDF: cal importar»).")
    if r["musescore"]:
        ll.append(f"{r['musescore']} són fitxers de MuseScore: només els indexe pel nom (cal obrir-los amb MuseScore).")
    return "\n".join(ll)


# --------------------------------------------------------------------------- cerca

def _paraules(text: str) -> list[str]:
    return [w for w in re.split(r"[^0-9a-z#]+", norm(text)) if w]


def _pall(rel: str, reg: dict) -> tuple[str, str, str]:
    """(text fort, text de carpetes, text d'etiquetes i parts) normalitzats."""
    fort = norm(" ".join(filter(None, [reg.get("titol_f") or reg.get("titol"), reg.get("compositor_f") or reg.get("compositor"),
                                      _titol_del_nom(rel)])))
    carpetes = norm(" ".join(Path(rel).parts[:-1]))
    extra = norm(" ".join(reg.get("nivell", []) + reg.get("estil", []) + [reg.get("nota", "")]
                          + [f"{p['nom']} {p.get('instrument') or ''}" for p in reg.get("parts", [])]))
    return fort, carpetes, extra


def _coincideix(consulta: str, text: str) -> bool:
    c = norm(consulta)
    return all(w in text for w in _paraules(c)) if c else True


def cerca(paraules: str, nivell: str | None = None, estil: str | None = None, instrument: str | None = None,
          arrel: Path | None = None) -> list[tuple[int, str, dict]]:
    arrel = Path(arrel) if arrel else biblioteca()
    fitxers = llig_index(arrel)["fitxers"]
    ws = _paraules(paraules)
    res = []
    for rel, reg in fitxers.items():
        fort, carpetes, extra = _pall(rel, reg)
        tot = f"{fort} {carpetes} {extra}"
        if not all(w in tot for w in ws):
            continue
        if nivell and not _coincideix(nivell, norm(" ".join(reg.get("nivell", [])))):
            continue
        if estil and not _coincideix(estil, norm(" ".join(reg.get("estil", [])))):
            continue
        if instrument and not _coincideix(instrument, norm(" ".join(
                f"{p['nom']} {p.get('instrument') or ''}" for p in reg.get("parts", [])) + " " + carpetes + " " + norm(rel))):
            continue
        punts = 0
        for w in ws:
            punts += 6 if w in _paraules(fort) else 3 if w in fort else 0
            punts += 2 if w in extra else 0
            punts += 1 if w in carpetes else 0
        if reg.get("estat") == "ok":
            punts += 1
        res.append((punts, rel, reg))
    res.sort(key=lambda x: (-x[0], x[1]))
    return res


def _rang(p: dict) -> str:
    return f"{p['mes_greu']}-{p['mes_agut']}" if p.get("mes_greu") else ""


def format_resultat(k: int, rel: str, reg: dict) -> str:
    from .musica import _curt
    titol = _curt(reg.get("titol_f") or reg.get("titol") or _titol_del_nom(rel), 70)
    comp = reg.get("compositor_f") or reg.get("compositor")
    cap = f"{k}. {titol}" + (f", {_curt(comp, 40)}" if comp else "")
    et = reg.get("nivell", []) + reg.get("estil", [])
    if et:
        cap += "   [" + " | ".join(_curt(e, 30) for e in et[:5]) + "]"
    ll = [cap]
    if reg.get("estat") == "ok":
        dades = [x for x in (reg.get("tonalitat"), reg.get("compas"),
                             f"{reg['compassos']} compassos" if reg.get("compassos") else None) if x]
        ll.append("   " + "; ".join(dades))
        parts = [f"{_curt(p['nom'], 22)}" + (f" ({_rang(p)})" if _rang(p) else "") for p in reg.get("parts", [])[:6]]
        if len(reg.get("parts", [])) > 6:
            parts.append(f"... i {len(reg['parts']) - 6} més")
        if parts:
            ll.append("   Parts: " + ", ".join(parts))
    elif reg.get("tipus") == "pdf":
        ll.append("   PDF: cal importar (amb l'ordre «importar» i després revisar-lo amb MuseScore)")
    elif reg.get("tipus") == "musescore":
        ll.append("   Fitxer de MuseScore: cal obrir-lo amb MuseScore i exportar-lo a MusicXML")
    elif reg.get("estat") == "pendent":
        ll.append("   (encara no analitzada: executa «partitures biblioteca actualitza»)")
    else:
        ll.append("   (no he pogut llegir el contingut; potser cal obrir-la amb MuseScore)")
    ll.append("   " + rel)
    return "\n".join(ll)


def _avisos_nivell(reg: dict, nivell: str) -> list[str]:
    try:
        from . import nivells
        return ["   " + a for a in nivells.avisos_cerca(reg, nivell)]
    except Exception:
        return []


def ordre_cerca(paraules: str, nivell=None, estil=None, instrument=None, maxim: int = 10, sortida=print) -> None:
    arrel = biblioteca()
    if not llig_index(arrel)["fitxers"]:
        raise ErrorUsuari("L'índex de la biblioteca està buit. Executa primer «partitures biblioteca actualitza».")
    trobats = cerca(paraules, nivell, estil, instrument, arrel)
    _desa_json(fitxer_ultima(), {"arrel": str(arrel), "ruta": [r for _, r, _ in trobats[:maxim]]})
    if not trobats:
        sortida("Cap resultat a la biblioteca. Prova amb menys paraules, o cerca al corpus lliure («partitures corpus ...»).")
        return
    for k, (_, rel, reg) in enumerate(trobats[:maxim], 1):
        sortida("\n".join([format_resultat(k, rel, reg)] + (_avisos_nivell(reg, nivell) if nivell else [])))
    if len(trobats) > maxim:
        sortida(f"... i {len(trobats) - maxim} més. Afina la cerca.")
    sortida("Per a copiar-ne una a entrada/: partitures biblioteca copia <número>")


def copia(n: int) -> Path:
    """Copia el resultat n de l'última cerca a entrada/ (la biblioteca no es toca)."""
    arrel = biblioteca()
    ultima = _llig_json(fitxer_ultima())
    llista = ultima.get("ruta") or []
    if ultima.get("arrel") != str(arrel) or not llista:
        raise ErrorUsuari("Primer cal fer una cerca: partitures biblioteca cerca <paraules>.")
    if not 1 <= n <= len(llista):
        raise ErrorUsuari(f"El número {n} no coincideix amb cap resultat de l'última cerca (de l'1 al {len(llista)}).")
    origen = (arrel / llista[n - 1]).resolve()
    try:
        origen.relative_to(arrel.resolve())
    except ValueError:
        raise ErrorUsuari("Este fitxer és fora de la biblioteca; no el copie.") from None
    if not origen.is_file():
        raise ErrorUsuari("Este fitxer ja no és a la biblioteca. Executa «partitures biblioteca actualitza».")
    nom = re.sub(r"\s*\[[^\]]*\]", "", origen.stem).strip() or origen.stem
    desti = rutes.lliure(rutes.carpeta("entrada") / (nom + origen.suffix.lower()))
    desti.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(origen, desti)
    return desti
