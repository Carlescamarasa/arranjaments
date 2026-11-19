"""Localitza MuseScore i Audiveris a Mac, Windows i Linux.

Es pot forçar la ruta amb les variables d'entorn MUSESCORE_PATH i AUDIVERIS_PATH.
"""
import glob
import os
import shutil
import sys
from pathlib import Path

from .errors import ErrorUsuari

URL_MUSESCORE = "https://musescore.org/ca/download"  # tria l'opció «sense MuseHub»
URL_AUDIVERIS = "https://github.com/Audiveris/audiveris/releases"


def _es_windows() -> bool:
    return sys.platform.startswith("win")


def _es_mac() -> bool:
    return sys.platform == "darwin"


def _dades_linux() -> Path:
    """Carpeta de dades de l'aplicació a Linux (la mateixa que fa servir l'instal·lador)."""
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "Arranjaments"


def _candidats_musescore() -> list[str]:
    """Qualsevol MuseScore (4 i versions futures), la més nova primer."""
    if _es_mac():
        trobats = []
        for base in ("/Applications", str(Path.home() / "Applications")):
            trobats += glob.glob(str(Path(base) / "MuseScore*.app" / "Contents" / "MacOS" / "mscore"))
        return sorted(trobats, reverse=True)
    if _es_windows():
        bases = [os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")]
        if os.environ.get("LOCALAPPDATA"):
            bases.append(str(Path(os.environ["LOCALAPPDATA"]) / "Programs"))
        trobats = []
        for base in bases:
            trobats += glob.glob(str(Path(base) / "MuseScore*" / "bin" / "MuseScore*.exe"))
        return sorted(trobats, reverse=True)
    # Linux: la que deixa l'instal·lador (AppImage descomprimida), altres AppImage conegudes i Flatpak
    trobats = [str(_dades_linux() / "MuseScore" / "AppRun")]
    for base in (Path.home() / "Applications", Path.home() / ".local" / "bin", Path("/opt")):
        trobats += sorted(glob.glob(str(base / "MuseScore*.AppImage")), reverse=True)
    trobats += [str(Path.home() / ".local/share/flatpak/exports/bin/org.musescore.MuseScore"),
                "/var/lib/flatpak/exports/bin/org.musescore.MuseScore"]
    return trobats


def _candidats_audiveris() -> list[str]:
    if _es_mac():
        trobats = []
        for base in ("/Applications", str(Path.home() / "Applications")):
            trobats += glob.glob(str(Path(base) / "Audiveris*.app" / "Contents" / "MacOS" / "Audiveris"))
        return sorted(trobats, reverse=True)
    if _es_windows():
        bases = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
                 os.environ.get("LOCALAPPDATA") and str(Path(os.environ["LOCALAPPDATA"]) / "Programs"),
                 os.environ.get("LOCALAPPDATA")]
        llista = []
        for base in bases:
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
            f"La variable {var_entorn} apunta a «{forçada}», però este fitxer no existeix."
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
            f"{URL_MUSESCORE} (tria l'opció «sense MuseHub») i torna-ho a provar. "
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


def coses_instalables(plataforma: str | None = None) -> tuple:
    plataforma = plataforma or sys.platform
    # a Linux no hi ha OneDrive: no s'ofereix
    return ("musescore", "audiveris", "opencode", "icona", "eines", "carpeta", "uv") + (
        () if plataforma.startswith("linux") else ("onedrive",))


COSES_INSTALABLES = coses_instalables()


def es_opcional(nom: str) -> bool:
    """Coses que, si falten, només són un avís (no impedeixen obrir Arranjaments)."""
    return "opcional" in nom or nom.startswith("MuseScore")


def instalar(cosa: str | None, prova: bool = False) -> int:
    """Executa l'instal·lador del sistema (el mateix que fa servir «Instal·lar Arranjaments») per a una sola cosa.

    L'instal·lador viu al costat d'estes eines (carpeta instalacio/). Retorna el seu codi d'eixida.
    """
    import subprocess
    carpeta = Path(__file__).resolve().parents[2] / "instalacio"
    if _es_windows():
        guio = carpeta / "instalar-windows.ps1"
        arrel_sistema = os.environ.get("SystemRoot", r"C:\Windows")
        ordre = [str(Path(arrel_sistema) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"),
                 "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(guio), "-SensePreguntes"]
        ordre += ["-Prova"] if prova else ["-Nomes", cosa]
    elif _es_mac() or sys.platform.startswith("linux"):
        guio = carpeta / ("instalar-mac.sh" if _es_mac() else "instalar-linux.sh")
        ordre = ["/bin/bash", str(guio), "--sense-preguntes"] + (["--prova"] if prova else ["--nomes", cosa])
    else:
        raise ErrorUsuari("L'instal·lador automàtic només existeix per a Mac, Windows i Linux.")
    if not guio.exists():
        raise ErrorUsuari("No trobe l'instal·lador. Torna a obrir «Instal·lar Arranjaments» (el programa amb què vas "
                          "instal·lar-ho tot) i prova-ho de nou.")
    entorn = {k: v for k, v in os.environ.items() if k not in ("ARRANJAMENTS_PROGRES", "PSModulePath")}
    sys.stdout.flush()
    return subprocess.run(ordre, env=entorn, stdin=subprocess.DEVNULL).returncode


def comprovar() -> list[tuple[str, bool, str]]:
    """Retorna [(nom, està_bé, missatge)] per a tot el que cal tindre instal·lat."""
    res: list[tuple[str, bool, str]] = []
    try:
        import music21  # noqa: F401
        res.append(("Eines musicals (music21)", True, "preparades"))
    except ImportError:
        res.append(("Eines musicals (music21)", False, "falten; torna a obrir «Instal·lar Arranjaments»"))
    for nom, fn, ajuda in (("MuseScore (per a fer PDF)", trobar_musescore, "Revisar partitures i fer PDF"),
                           ("Audiveris (opcional, només per a PDF)", trobar_audiveris, "Convertir PDF en partitura editable")):
        try:
            res.append((nom, True, fn()))
        except ErrorUsuari as e:
            res.append((nom, False, str(e)))
    return res
