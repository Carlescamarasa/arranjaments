"""Actualització silenciosa d'Arranjaments.

Només fa servir la biblioteca estàndard (res de music21), perquè s'executa cada vegada que s'obri la icona
i ha de ser ràpid. Tot el que passa queda escrit a «actualitzacio.log», dins de la carpeta de dades.

Què actualitza: les eines (scripts, pyproject.toml, uv.lock, instal·ladors) i la configuració amagada
de la carpeta de treball (.opencode). Mai toca entrada/, eixida/ ni cap fitxer de la persona.

Com ho fa: baixa «versio.json» de la versió «ultima» de GitHub (HTTPS, 5 segons com a màxim); si hi ha una
versió més nova, baixa «actualitzacio.zip», comprova el sha256, ho prepara en una carpeta temporal, guarda
còpia del que hi ha a «anterior/» i canvia les peces d'una en una (si falla, les torna enrere).

Ús intern: python -m partitures.actualitzar --silenci [--obri PROGRAMA]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

URL_BASE = "https://github.com/Carlescamarasa/arranjaments/releases/latest/download"
FITXER_VERSIO = "versio.json"
FITXER_PAQUET = "actualitzacio.zip"
VAR_URL = "ARRANJAMENTS_ACTUALITZACIO_URL"  # només per a proves: una altra carpeta o servidor (http local o file://)

TEMPS_XARXA = 5            # segons per a saber si hi ha versió nova
TEMPS_DESCARREGA = 90      # segons com a màxim per a baixar el paquet
TEMPS_UV = 600
INTERVAL_COMPROVACIO = 3600  # en mode silenciós, com a molt una consulta per hora
MIDA_MAXIMA = 60 * 1024 * 1024
MIDA_MAXIMA_DESCOMPRIMIT = 200 * 1024 * 1024

# Peces de la carpeta de dades que es renoven (rutes dins del paquet i dins de la carpeta de dades)
ELEMENTS_DADES = ("scripts", "instalacio", "pyproject.toml", "uv.lock", ".python-version", "VERSION",
                  "AGENTS.md", "opencode.json", "NOVETATS.md", ".opencode/skills")
# Peces de la configuració amagada de la carpeta de treball: (ruta dins del paquet, ruta dins de .opencode)
ELEMENTS_TREBALL = (("AGENTS.md", "AGENTS.md"), ("opencode.json", "opencode.json"),
                    ("NOVETATS.md", "NOVETATS.md"), (".opencode/skills", "skills"))
OBLIGATORIS = ("scripts/partitures/__init__.py", "scripts/partitures/actualitzar.py", "pyproject.toml", "uv.lock",
               "VERSION", "AGENTS.md", "opencode.json", ".opencode/skills")


class ErrorActualitzacio(Exception):
    pass


@dataclass
class Resultat:
    codi: str       # al_dia, actualitzada, enrere, recent, omesa, sense_xarxa, cal_reinstalar, ocupat, error, res
    missatge: str

    @property
    def be(self) -> bool:
        return self.codi in ("al_dia", "actualitzada", "enrere", "recent", "omesa", "sense_xarxa", "ocupat")


@dataclass
class Instalacio:
    dades: Path
    treball: Path | None
    url: str = URL_BASE
    proves: bool = False   # True si l'adreça ve de la variable d'entorn (permet http local i file://)
    sense_limit: bool = False   # True en proves: no s'aplica el límit d'una consulta per hora


# ---------------------------------------------------------------- versions

def parseja(text: str) -> tuple[int, ...]:
    m = re.fullmatch(r"\s*(\d+(?:\.\d+){0,3})\s*", text or "")
    if not m:
        raise ValueError(f"Versió no vàlida: {text!r}")
    return tuple(int(x) for x in m.group(1).split("."))


def compara(a: str, b: str) -> int:
    """1 si a és més nova que b, -1 si és més vella, 0 si són iguals."""
    x, y = parseja(a), parseja(b)
    n = max(len(x), len(y))
    x, y = x + (0,) * (n - len(x)), y + (0,) * (n - len(y))
    return (x > y) - (x < y)


def versio_de(dades: Path) -> str:
    try:
        return (dades / "VERSION").read_text(encoding="utf-8").strip() or "0"
    except OSError:
        return "0"


# ---------------------------------------------------------------- on és tot

def dades_per_defecte() -> Path:
    if os.environ.get("ARRANJAMENTS_DADES"):
        return Path(os.environ["ARRANJAMENTS_DADES"])
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Arranjaments"
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "Arranjaments"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "Arranjaments"


def _treball(dades: Path) -> Path | None:
    if os.environ.get("ARRANJAMENTS_TREBALL"):
        return Path(os.environ["ARRANJAMENTS_TREBALL"])
    cwd = Path.cwd()
    if (cwd / ".opencode" / "opencode.json").is_file() and (cwd / "entrada").is_dir():
        return cwd
    try:
        t = Path((dades / "treball.txt").read_text(encoding="utf-8-sig").strip())
        if t.is_dir():
            return t
    except (OSError, ValueError):
        pass
    for d in ("Documents", "Documentos", "OneDrive/Documents", "OneDrive/Documentos"):
        t = Path.home() / d / "Arranjaments"
        if (t / ".opencode").is_dir():
            return t
    return None


def instalacio_actual() -> Instalacio | None:
    """La instal·lació on viu este codi. None si s'executa des d'un repositori (mai s'ha de modificar)."""
    dades = dades_per_defecte()
    try:
        dins = Path(__file__).resolve().is_relative_to(dades.resolve())
    except (OSError, ValueError):
        dins = False
    if not dins and not os.environ.get("ARRANJAMENTS_DADES"):
        return None
    url = os.environ.get(VAR_URL) or URL_BASE
    return Instalacio(dades, _treball(dades), url.rstrip("/"), proves=bool(os.environ.get(VAR_URL)),
                      sense_limit=bool(os.environ.get(VAR_URL)))


# ---------------------------------------------------------------- registre i estat

def registra(dades: Path, text: str) -> None:
    try:
        dades.mkdir(parents=True, exist_ok=True)
        ruta = dades / "actualitzacio.log"
        if ruta.exists() and ruta.stat().st_size > 200_000:
            ruta.write_text(ruta.read_text(encoding="utf-8", errors="replace")[-100_000:], encoding="utf-8")
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {text}\n")
    except OSError:
        pass


def _llig_estat(dades: Path) -> dict:
    try:
        d = json.loads((dades / "actualitzacio-estat.json").read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _desa_estat(dades: Path, **canvis) -> None:
    try:
        e = _llig_estat(dades)
        e.update(canvis)
        (dades / "actualitzacio-estat.json").write_text(json.dumps(e), encoding="utf-8")
    except OSError:
        pass


class _Pany:
    """Perquè dues obertures de la icona alhora no actualitzen a la vegada."""

    def __init__(self, dades: Path):
        self.ruta = dades / ".actualitzacio.pany"
        self.te = False

    def __enter__(self):
        try:
            self.ruta.parent.mkdir(parents=True, exist_ok=True)
            if self.ruta.exists() and time.time() - self.ruta.stat().st_mtime > 900:
                self.ruta.unlink()
            os.close(os.open(self.ruta, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            self.te = True
        except OSError:
            pass
        return self

    def __exit__(self, *_):
        if self.te:
            try:
                self.ruta.unlink()
            except OSError:
                pass


# ---------------------------------------------------------------- xarxa

class _RedireccioSegura(urllib.request.HTTPRedirectHandler):
    def __init__(self, proves: bool):
        self.proves = proves

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _comprova_url(newurl, self.proves)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _comprova_url(url: str, proves: bool) -> None:
    esquema = urllib.parse.urlparse(url).scheme
    if esquema == "https" or (proves and esquema in ("http", "file")):
        return
    raise ErrorActualitzacio(f"Adreça no permesa (només HTTPS): {url}")


def _obre(url: str, proves: bool, temps: float):
    _comprova_url(url, proves)
    obridor = urllib.request.build_opener(_RedireccioSegura(proves))
    return obridor.open(urllib.request.Request(url, headers={"User-Agent": "arranjaments-actualitzador"}), timeout=temps)


def _amb_limit(funcio: Callable[[], object], segons: float):
    """Executa la funció amb un límit dur de temps (la resolució de noms de domini no respecta els temps d'espera)."""
    res: dict = {}

    def fil():
        try:
            res["v"] = funcio()
        except BaseException as e:  # noqa: BLE001
            res["e"] = e

    t = threading.Thread(target=fil, daemon=True)
    t.start()
    t.join(segons)
    if t.is_alive():
        raise TimeoutError("Sense resposta a temps")
    if "e" in res:
        raise res["e"]
    return res.get("v")


def llig_versio_remota(inst: Instalacio) -> dict:
    def baixa():
        with _obre(f"{inst.url}/{FITXER_VERSIO}", inst.proves, TEMPS_XARXA) as r:
            return r.read(65536)

    try:
        d = json.loads(_amb_limit(baixa, TEMPS_XARXA + 1))
        parseja(d["versio"])
        if not re.fullmatch(r"[0-9a-f]{64}", d["sha256"]) or not re.fullmatch(r"[A-Za-z0-9._-]+", d["fitxer"]):
            raise ValueError("camps no vàlids")
        d["mida"] = int(d.get("mida", 0))
        return d
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        raise
    except (ValueError, KeyError, TypeError) as e:
        raise ErrorActualitzacio(f"El fitxer de versió no és vàlid ({e})") from None


def _baixa(inst: Instalacio, nom: str, desti: Path, mida: int) -> str:
    h, total, t0 = hashlib.sha256(), 0, time.monotonic()
    with _obre(f"{inst.url}/{nom}", inst.proves, TEMPS_XARXA) as r, open(desti, "wb") as f:
        while True:
            bloc = r.read(65536)
            if not bloc:
                break
            total += len(bloc)
            if total > MIDA_MAXIMA or (mida and total > mida):
                raise ErrorActualitzacio("El paquet és més gran del que s'esperava")
            if time.monotonic() - t0 > TEMPS_DESCARREGA:
                raise TimeoutError("La baixada tarda massa")
            h.update(bloc)
            f.write(bloc)
    if mida and total != mida:
        raise ErrorActualitzacio("El paquet no té la mida esperada")
    return h.hexdigest()


# ---------------------------------------------------------------- paquet

def extrau(zip_ruta: Path, desti: Path) -> Path:
    """Descomprimeix amb proteccions (rutes fora de la carpeta, mida). Retorna l'arrel del paquet."""
    desti.mkdir(parents=True, exist_ok=True)
    base = desti.resolve()
    with zipfile.ZipFile(zip_ruta) as z:
        infos = z.infolist()
        if len(infos) > 5000 or sum(i.file_size for i in infos) > MIDA_MAXIMA_DESCOMPRIMIT:
            raise ErrorActualitzacio("El paquet és massa gran")
        for i in infos:
            nom = i.filename.replace("\\", "/")
            if nom.startswith("/") or re.match(r"^[A-Za-z]:", nom) or ".." in nom.split("/"):
                raise ErrorActualitzacio(f"Ruta no permesa dins del paquet: {i.filename}")
            ruta = (base / nom).resolve()
            if base != ruta and base not in ruta.parents:
                raise ErrorActualitzacio(f"Ruta no permesa dins del paquet: {i.filename}")
            if nom.endswith("/"):
                ruta.mkdir(parents=True, exist_ok=True)
                continue
            ruta.parent.mkdir(parents=True, exist_ok=True)
            with z.open(i) as origen, open(ruta, "wb") as f:
                shutil.copyfileobj(origen, f)
    arrel = base
    if not (arrel / "pyproject.toml").exists():
        fills = [p for p in arrel.iterdir()]
        if len(fills) == 1 and fills[0].is_dir():
            arrel = fills[0]
    return arrel


def valida_paquet(arrel: Path, versio: str) -> None:
    for rel in OBLIGATORIS:
        if not (arrel / rel).exists():
            raise ErrorActualitzacio(f"Al paquet li falta {rel}")
    if versio_de(arrel) != versio:
        raise ErrorActualitzacio("La versió del paquet no coincideix amb la que anuncia")


def crea_paquet(arrel: Path, versio: str, desti: Path) -> Path:
    """Fa actualitzacio.zip i versio.json (per al CI, que els puja a la versió «ultima» de GitHub)."""
    parseja(versio)
    desti.mkdir(parents=True, exist_ok=True)
    fitxers: list[tuple[Path, str]] = []

    def afegeix(rel: str):
        p = arrel / rel
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc":
                    fitxers.append((f, f.relative_to(arrel).as_posix()))
        elif p.is_file():
            fitxers.append((p, rel))

    for rel in ELEMENTS_DADES:
        if rel in ("VERSION", "instalacio"):
            continue
        afegeix(rel)
    for f in sorted((arrel / "instalacio").glob("instalar-*")):
        if f.suffix in (".sh", ".ps1"):
            fitxers.append((f, f"instalacio/{f.name}"))
    ruta_zip = desti / FITXER_PAQUET
    with zipfile.ZipFile(ruta_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f, nom in fitxers:
            z.write(f, nom)
        z.writestr("VERSION", versio + "\n")
    sha = hashlib.sha256(ruta_zip.read_bytes()).hexdigest()
    (desti / FITXER_VERSIO).write_text(
        json.dumps({"versio": versio, "fitxer": FITXER_PAQUET, "sha256": sha, "mida": ruta_zip.stat().st_size},
                   indent=2) + "\n", encoding="utf-8")
    return ruta_zip


# ---------------------------------------------------------------- canvi atòmic de peces

def _esborra(ruta: Path) -> None:
    if ruta.is_symlink() or ruta.is_file():
        ruta.unlink()
    elif ruta.is_dir():
        shutil.rmtree(ruta)


def _mou(origen: Path, desti: Path) -> None:
    for intent in range(4):
        try:
            os.replace(origen, desti)
            return
        except PermissionError:   # a Windows, un fitxer obert ho impedeix un moment
            if intent == 3:
                raise
            time.sleep(0.5)


def _copia(origen: Path, desti: Path) -> None:
    desti.parent.mkdir(parents=True, exist_ok=True)
    if origen.is_dir():
        shutil.copytree(origen, desti)
    else:
        shutil.copy2(origen, desti)


def aplica(parelles: list[tuple[Path | None, Path]]) -> None:
    """Canvia cada destí per l'origen (None = esborrar el destí). Si una cosa falla, ho deixa tot com estava."""
    fet: list[tuple[Path, Path, bool]] = []
    try:
        for origen, desti in parelles:
            desti.parent.mkdir(parents=True, exist_ok=True)
            vell = desti.with_name(desti.name + ".vell")
            _esborra(vell)
            existia = desti.exists() or desti.is_symlink()
            if existia:
                _mou(desti, vell)
            fet.append((desti, vell, existia))
            if origen is not None:
                _mou(origen, desti)
    except BaseException:
        for desti, vell, existia in reversed(fet):
            try:
                _esborra(desti)
                if existia:
                    _mou(vell, desti)
            except OSError:
                pass
        raise
    for _, vell, _ in fet:
        try:
            _esborra(vell)
        except OSError:
            pass


def _parelles_dades(inst: Instalacio, font: Path) -> list[tuple[Path | None, Path]]:
    return [(font / rel, inst.dades / rel) for rel in ELEMENTS_DADES if (font / rel).exists()]


def _parelles_treball(inst: Instalacio, font: Path, preparat: Path) -> list[tuple[Path | None, Path]]:
    """Copia les peces de la configuració amagada a una carpeta temporal dins de .opencode (mateix disc)."""
    res = []
    for rel, nom in ELEMENTS_TREBALL:
        if (font / rel).exists():
            _copia(font / rel, preparat / nom)
            res.append((preparat / nom, inst.treball / ".opencode" / nom))
    return res


def _fes_anterior(inst: Instalacio) -> None:
    """Guarda còpia del que hi ha ara a anterior/ (només una versió enrere)."""
    nou = inst.dades / "anterior.nou"
    _esborra(nou)
    absents = {"dades": [], "treball": []}
    for rel in ELEMENTS_DADES:
        if (inst.dades / rel).exists():
            _copia(inst.dades / rel, nou / "dades" / rel)
        else:
            absents["dades"].append(rel)
    if inst.treball:
        for rel, nom in ELEMENTS_TREBALL:
            if (inst.treball / ".opencode" / nom).exists():
                _copia(inst.treball / ".opencode" / nom, nou / "treball" / nom)
            else:
                absents["treball"].append(nom)
    (nou / "ESTAT.json").write_text(json.dumps({"versio": versio_de(inst.dades), "absents": absents}), encoding="utf-8")
    aplica([(nou, inst.dades / "anterior")])


# ---------------------------------------------------------------- uv

def troba_uv() -> str | None:
    t = shutil.which("uv")
    if t:
        return t
    for c in (Path.home() / ".local" / "bin" / "uv", Path.home() / ".local" / "bin" / "uv.exe",
              Path.home() / ".cargo" / "bin" / "uv", Path("/opt/homebrew/bin/uv"), Path("/usr/local/bin/uv")):
        if c.is_file():
            return str(c)
    return None


def sync_uv(dades: Path) -> bool:
    uv = troba_uv()
    if not uv:
        return False
    kw = {}
    if sys.platform == "win32":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        r = subprocess.run([uv, "sync", "--frozen", "--no-dev"], cwd=dades, capture_output=True, text=True,
                           timeout=TEMPS_UV, **kw)
    except (OSError, subprocess.TimeoutExpired) as e:
        registra(dades, f"uv sync ha fallat: {e}")
        return False
    if r.returncode != 0:
        registra(dades, f"uv sync ha fallat ({r.returncode}): {(r.stderr or '')[-400:]}")
    return r.returncode == 0


def _llig(ruta: Path) -> bytes | None:
    try:
        return ruta.read_bytes()
    except OSError:
        return None


# ---------------------------------------------------------------- l'actualització

def actualitza(inst: Instalacio, *, forca: bool = False, sync: Callable[[Path], bool] = sync_uv,
               ara: Callable[[], float] = time.time) -> Resultat:
    """Comprova si hi ha versió nova i l'aplica. Mai llança excepcions."""
    dades = inst.dades
    try:
        with _Pany(dades) as pany:
            if not pany.te:
                return Resultat("ocupat", "Ja s'està actualitzant.")
            return _actualitza(inst, forca, sync, ara)
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        registra(dades, f"Sense connexió o sense resposta ({type(e).__name__}: {e}). Es continua amb la versió actual.")
        return Resultat("sense_xarxa", "No he pogut comprovar si hi ha novetats (sense internet?). Continues amb la versió actual.")
    except Exception as e:  # noqa: BLE001
        registra(dades, f"Error inesperat: {type(e).__name__}: {e}")
        return Resultat("error", "No he pogut actualitzar. Continues amb la versió actual.")


def _actualitza(inst: Instalacio, forca: bool, sync, ara) -> Resultat:
    dades = inst.dades
    local = versio_de(dades)
    estat = _llig_estat(dades)
    if not forca and not inst.sense_limit:
        ultima = estat.get("ultima_comprovacio", 0)
        if isinstance(ultima, (int, float)) and 0 <= ara() - ultima < INTERVAL_COMPROVACIO:
            return Resultat("recent", "Comprovat fa poc.")
    try:
        remot = llig_versio_remota(inst)
    except ErrorActualitzacio as e:
        registra(dades, str(e))
        return Resultat("error", "No he pogut comprovar les novetats.")
    if not forca:
        _desa_estat(dades, ultima_comprovacio=ara())
    if compara(remot["versio"], local) <= 0:
        return Resultat("al_dia", f"Ja tens l'última versió ({local}).")
    if not forca and estat.get("omet_versio") == remot["versio"]:
        registra(dades, f"La versió {remot['versio']} s'ha omès perquè es va tornar enrere.")
        return Resultat("omesa", "Hi ha una versió nova, però vas tornar enrere. Per a provar-la: partitures actualitzar.")
    registra(dades, f"Hi ha la versió {remot['versio']} (tens la {local}). Baixant.")

    treb = dades / ".actualitzacio"
    _esborra(treb)
    treb.mkdir(parents=True)
    preparat_treball = None
    try:
        zip_ruta = treb / "paquet.zip"
        sha = _baixa(inst, remot["fitxer"], zip_ruta, remot["mida"])
        if sha != remot["sha256"]:
            registra(dades, f"El sha256 del paquet no coincideix (esperat {remot['sha256']}, trobat {sha}). Es rebutja.")
            return Resultat("error", "El paquet baixat no és el que s'esperava, i no l'he instal·lat. Continues amb la versió actual.")
        font = extrau(zip_ruta, treb / "nou")
        valida_paquet(font, remot["versio"])
        pv_nou, pv_vell = _llig(font / ".python-version"), _llig(dades / ".python-version")
        if pv_vell is not None and pv_nou is not None and pv_nou.strip() != pv_vell.strip():
            registra(dades, "La versió nova necessita un Python diferent: cal tornar a obrir «Instal·lar Arranjaments».")
            return Resultat("cal_reinstalar", "Esta novetat necessita tornar a obrir «Instal·lar Arranjaments» una vegada.")
        cal_sync = _llig(font / "uv.lock") != _llig(dades / "uv.lock")
        if cal_sync and not troba_uv():
            registra(dades, "Cal uv per a les dependències noves i no el trobe. Es manté la versió actual.")
            return Resultat("error", "No he pogut actualitzar (falta uv). Continues amb la versió actual.")

        _fes_anterior(inst)
        parelles = _parelles_dades(inst, font)
        if inst.treball and (inst.treball / ".opencode").is_dir():
            preparat_treball = inst.treball / ".opencode" / ".actualitzacio-nou"
            _esborra(preparat_treball)
            parelles += _parelles_treball(inst, font, preparat_treball)
        lock_vell = _llig(dades / "uv.lock")
        aplica(parelles)
        if cal_sync and not sync(dades):
            registra(dades, "Les dependències noves no s'han pogut preparar. Es torna a la versió anterior.")
            _restaura(inst, sync, amb_sync=False)
            if lock_vell is not None:
                sync(dades)
            return Resultat("error", "No he pogut actualitzar (les peces noves no s'han preparat). Continues amb la versió actual.")
    finally:
        _esborra(treb)
        if preparat_treball is not None:
            try:
                _esborra(preparat_treball)
            except OSError:
                pass
    _desa_estat(dades, omet_versio=None)
    registra(dades, f"Actualitzat de la {local} a la {remot['versio']}.")
    return Resultat("actualitzada", f"Arranjaments s'ha actualitzat a la versió {remot['versio']} (abans, la {local}).")


def _restaura(inst: Instalacio, sync, *, amb_sync: bool = True) -> None:
    """Posa el contingut de anterior/ en lloc de l'actual (còpia: anterior/ no es gasta)."""
    ant = inst.dades / "anterior"
    info = json.loads((ant / "ESTAT.json").read_text(encoding="utf-8"))
    treb = inst.dades / ".actualitzacio-enrere"
    _esborra(treb)
    try:
        parelles: list[tuple[Path | None, Path]] = []
        for rel in ELEMENTS_DADES:
            if (ant / "dades" / rel).exists():
                _copia(ant / "dades" / rel, treb / "dades" / rel)
                parelles.append((treb / "dades" / rel, inst.dades / rel))
            elif rel in info["absents"]["dades"]:
                parelles.append((None, inst.dades / rel))
        if inst.treball and (inst.treball / ".opencode").is_dir():
            for rel, nom in ELEMENTS_TREBALL:
                desti = inst.treball / ".opencode" / nom
                if (ant / "treball" / nom).exists():
                    prep = inst.treball / ".opencode" / ".actualitzacio-nou"
                    _copia(ant / "treball" / nom, prep / nom)
                    parelles.append((prep / nom, desti))
                elif nom in info["absents"]["treball"]:
                    parelles.append((None, desti))
        lock_actual = _llig(inst.dades / "uv.lock")
        aplica(parelles)
        if amb_sync and _llig(inst.dades / "uv.lock") != lock_actual:
            if not sync(inst.dades):
                registra(inst.dades, "Avís: no s'han pogut preparar les dependències de la versió anterior.")
    finally:
        _esborra(treb)
        if inst.treball:
            try:
                _esborra(inst.treball / ".opencode" / ".actualitzacio-nou")
            except OSError:
                pass


def torna_enrere(inst: Instalacio, *, sync: Callable[[Path], bool] = sync_uv) -> Resultat:
    dades = inst.dades
    try:
        with _Pany(dades) as pany:
            if not pany.te:
                return Resultat("ocupat", "Ja s'està actualitzant.")
            try:
                info = json.loads((dades / "anterior" / "ESTAT.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return Resultat("error", "No hi ha cap versió anterior guardada.")
            actual = versio_de(dades)
            _restaura(inst, sync)
            _desa_estat(dades, omet_versio=actual)
            registra(dades, f"Tornat enrere de la {actual} a la {info['versio']}.")
            return Resultat("enrere", f"He tornat a la versió {info['versio']}. No s'actualitzarà sola a la {actual}; "
                                      "per a provar-la de nou, escriu «partitures actualitzar».")
    except Exception as e:  # noqa: BLE001
        registra(dades, f"Error en tornar enrere: {type(e).__name__}: {e}")
        return Resultat("error", "No he pogut tornar a la versió anterior.")


def text_versio(inst: Instalacio | None) -> str:
    dades = inst.dades if inst else Path(__file__).resolve().parents[2]
    linies = [f"Arranjaments, versió {versio_de(dades)} (prototip, en proves)"]
    if inst:
        try:
            ant = json.loads((dades / "anterior" / "ESTAT.json").read_text(encoding="utf-8"))["versio"]
            linies.append(f"Versió anterior guardada: {ant} (per a tornar-hi: partitures actualitzar --torna-enrere)")
        except (OSError, ValueError, KeyError):
            pass
    else:
        linies.append("(S'executa des del repositori: no és una instal·lació i no s'actualitza.)")
    return "\n".join(linies)


# ---------------------------------------------------------------- obrir OpenCode i punt d'entrada

def obri_programa(ruta: str, cwd: str | None = None) -> None:
    kw: dict = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=cwd)
    if sys.platform == "win32":
        kw["creationflags"] = 0x00000008 | 0x00000200   # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    subprocess.Popen([ruta], **kw)


def _troba_opencode_windows() -> str | None:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        for p in sorted((Path(base) / "Programs").glob("*/OpenCode.exe")):
            return str(p)
    return None


def main(argv: list[str] | None = None) -> int:
    """python -m partitures.actualitzar --silenci [--obri PROGRAMA]. Mai falla ni mostra res: la icona ha d'obrir sempre."""
    p = argparse.ArgumentParser(prog="partitures.actualitzar")
    p.add_argument("--silenci", action="store_true")
    p.add_argument("--obri", help="Programa que s'obri després (només Windows; Mac i Linux l'obrin des del seu llançador)")
    p.add_argument("--fes-paquet", nargs=3, metavar=("ARREL", "VERSIO", "DESTI"))
    try:
        a = p.parse_args(argv)
    except SystemExit:
        return 0
    if a.fes_paquet:
        crea_paquet(Path(a.fes_paquet[0]), a.fes_paquet[1], Path(a.fes_paquet[2]))
        return 0
    try:
        if a.silenci:
            inst = instalacio_actual()
            if inst:
                r = actualitza(inst)
                if r.codi not in ("recent", "al_dia"):
                    registra(inst.dades, f"[{r.codi}] {r.missatge}")
    except BaseException as e:  # noqa: BLE001
        try:
            registra(dades_per_defecte(), f"Error al llançador: {type(e).__name__}: {e}")
        except BaseException:  # noqa: BLE001
            pass
    finally:
        if a.obri:
            try:
                obri_programa(a.obri if Path(a.obri).exists() else (_troba_opencode_windows() or a.obri), os.getcwd())
            except BaseException:  # noqa: BLE001
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
