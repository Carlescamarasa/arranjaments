"""Localitza MuseScore i Audiveris a Mac i Windows (i, per si de cas, Linux).

Es pot forçar la ruta amb les variables d'entorn MUSESCORE_PATH i AUDIVERIS_PATH.
"""
import glob
import os
import shutil
import sys
from pathlib import Path

from .errors import ErrorUsuari

URL_MUSESCORE = "https://musescore.org/ca/download"
URL_AUDIVERIS = "https://github.com/Audiveris/audiveris/releases"


def _es_windows() -> bool:
    return sys.platform.startswith("win")


def _es_mac() -> bool:
    return sys.platform == "darwin"


def _candidats_musescore() -> list[str]:
    if _es_mac():
        return [
            "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
            str(Path.home() / "Applications/MuseScore 4.app/Contents/MacOS/mscore"),
        ]
    if _es_windows():
        pf = [os.environ.get("ProgramFiles", r"C:\Program Files"),
              os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")]
        llista = []
        for base in pf:
            llista.append(str(Path(base) / "MuseScore 4" / "bin" / "MuseScore4.exe"))
        return llista
    return []


def _candidats_audiveris() -> list[str]:
    if _es_mac():
        return [
            "/Applications/Audiveris.app/Contents/MacOS/Audiveris",
            str(Path.home() / "Applications/Audiveris.app/Contents/MacOS/Audiveris"),
        ]
    if _es_windows():
        pf = [os.environ.get("ProgramFiles", r"C:\Program Files"),
              os.environ.get("LOCALAPPDATA", "") and str(Path(os.environ["LOCALAPPDATA"]) / "Programs")]
        llista = []
        for base in pf:
            if not base:
                continue
            llista += sorted(glob.glob(str(Path(base) / "Audiveris*" / "Audiveris*.exe")))
            llista.append(str(Path(base) / "Audiveris" / "Audiveris.exe"))
        return llista
    return ["/opt/audiveris/bin/Audiveris"]


def _trobar(var_entorn: str, candidats: list[str], noms_path: list[str]) -> str | None:
    forçada = os.environ.get(var_entorn)
    if forçada:
        if Path(forçada).exists():
            return forçada
        raise ErrorUsuari(
            f"La variable {var_entorn} apunta a «{forçada}», però aquest fitxer no existeix."
        )
    for c in candidats:
        if c and Path(c).exists():
            return c
    for nom in noms_path:
        trobat = shutil.which(nom)
        if trobat:
            return trobat
    return None


def trobar_musescore() -> str:
    ruta = _trobar("MUSESCORE_PATH", _candidats_musescore(), ["mscore", "musescore", "MuseScore4"])
    if not ruta:
        raise ErrorUsuari(
            "No trobe MuseScore. Instal·la'l des de "
            f"{URL_MUSESCORE} i torna-ho a provar. "
            "Si ja el tens instal·lat en un lloc estrany, indica'm la ruta amb la variable "
            "d'entorn MUSESCORE_PATH."
        )
    return ruta


def trobar_audiveris() -> str:
    ruta = _trobar("AUDIVERIS_PATH", _candidats_audiveris(), ["audiveris", "Audiveris"])
    if not ruta:
        raise ErrorUsuari(
            "No trobe Audiveris. Instal·la'l des de "
            f"{URL_AUDIVERIS} (baixa l'instal·lador del teu sistema) i torna-ho a provar. "
            "Si el tens en un altre lloc, indica la ruta amb la variable d'entorn AUDIVERIS_PATH."
        )
    return ruta


def trobar_opencode() -> str | None:
    home = Path.home()
    candidats = [home / ".opencode" / "bin" / "opencode", home / ".opencode" / "bin" / "opencode.exe",
                 home / ".opencode" / "bin" / "opencode.cmd"]
    for c in candidats:
        if c.exists():
            return str(c)
    return shutil.which("opencode")


def comprovar() -> list[tuple[str, bool, str]]:
    """Retorna [(nom, està_bé, missatge)] per a tot el que cal tindre instal·lat."""
    res: list[tuple[str, bool, str]] = []
    try:
        import music21  # noqa: F401
        res.append(("Eines musicals (music21)", True, "preparades"))
    except ImportError:
        res.append(("Eines musicals (music21)", False, "falten; executa l'instal·lador d'este projecte"))
    for nom, fn, ajuda in (("MuseScore 4", trobar_musescore, "Revisar partitures i fer PDF"),
                           ("Audiveris", trobar_audiveris, "Convertir PDF en partitura editable")):
        try:
            res.append((nom, True, fn()))
        except ErrorUsuari as e:
            res.append((nom, False, str(e)))
    oc = trobar_opencode()
    res.append(("OpenCode", bool(oc), oc or "no trobat"))
    return res
