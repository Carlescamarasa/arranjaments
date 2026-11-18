"""Crides a programes externs: Audiveris (PDF → MusicXML) i MuseScore (→ PDF)."""
from __future__ import annotations

import copy
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from music21 import stream

from . import eines, musica
from .errors import ErrorUsuari


def _entorn_silenciós() -> dict:
    """Entorn perquè els programes no òbrin finestres ni robin el focus."""
    env = dict(os.environ)
    if sys.platform.startswith("linux"):
        env.setdefault("QT_QPA_PLATFORM", "offscreen")  # MuseScore sense finestra (a Mac/Windows no cal)
    env["JAVA_TOOL_OPTIONS"] = (env.get("JAVA_TOOL_OPTIONS", "") + " -Djava.awt.headless=true").strip()
    return env


def netejar_nom(text: str) -> str:
    n = re.sub(r"[^\w\-. ]+", "_", text, flags=re.UNICODE).strip(" ._")
    return n or "partitura"


# --------------------------------------------------------------------------- Audiveris

def importar_pdf(pdf: str | Path, eixida: str | Path, temps_maxim: int = 1800) -> Path:
    pdf = Path(pdf).expanduser().resolve()
    if not pdf.exists():
        raise ErrorUsuari(f"No trobe el fitxer «{pdf}». Comprova el nom i que estiga en la carpeta entrada/.")
    if pdf.suffix.lower() not in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        raise ErrorUsuari("L'ordre «importar» només accepta PDF o imatges (png, jpg, tif).")
    aud = eines.trobar_audiveris()
    eixida = Path(eixida).expanduser().resolve()
    carpeta = eixida / f"{netejar_nom(pdf.stem)}-omr"
    carpeta.mkdir(parents=True, exist_ok=True)
    ordre = [aud, "-batch", "-export", "-output", str(carpeta), str(pdf)]
    try:
        r = subprocess.run(ordre, capture_output=True, text=True, timeout=temps_maxim,
                           env=_entorn_silenciós(), stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired as e:
        raise ErrorUsuari(f"Audiveris ha tardat massa (més de {temps_maxim // 60} minuts) i l'he aturat. "
                          "Prova amb un PDF més curt (unes poques pàgines).") from e
    except OSError as e:
        raise ErrorUsuari(f"No he pogut executar Audiveris ({e}). Comprova la instal·lació.") from e
    resultats = sorted(list(carpeta.rglob("*.mxl")) + list(carpeta.rglob("*.musicxml")) + list(carpeta.rglob("*.xml")))
    resultats = [x for x in resultats if x.is_file()]
    if not resultats:
        cua = "\n".join((r.stdout + "\n" + r.stderr).strip().splitlines()[-8:])
        raise ErrorUsuari(
            "Audiveris no ha pogut reconéixer la partitura (no ha generat cap MusicXML). "
            "Això passa amb escanejats borrosos, fotos o PDF molt retallats. "
            "Prova de buscar la partitura ja en MusicXML (skill buscar-partitura) o amb un PDF més net."
            + (f"\nÚltimes línies del programa:\n{cua}" if cua else "")
        )
    return resultats[0]


# --------------------------------------------------------------------------- MuseScore

def _mscore_a_pdf(mscore: str, origen: Path, desti: Path, temps_maxim: int = 300) -> None:
    desti.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = subprocess.run([mscore, "-o", str(desti), str(origen)], capture_output=True, text=True,
                           timeout=temps_maxim, env=_entorn_silenciós(), stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired as e:
        raise ErrorUsuari("MuseScore ha tardat massa a generar el PDF i l'he aturat.") from e
    if not desti.exists() or desti.stat().st_size == 0:
        cua = "\n".join((r.stdout + "\n" + r.stderr).strip().splitlines()[-6:])
        raise ErrorUsuari(f"MuseScore no ha pogut crear «{desti.name}».\n{cua}".strip())


def exportar(ruta: str | Path, eixida: str | Path, amb_parts: bool = True) -> dict:
    """Genera PDF de la partitura completa i, si es vol, un PDF per cada part."""
    mscore = eines.trobar_musescore()
    ruta = Path(ruta).expanduser().resolve()
    score = musica.carregar(ruta)          # valida el fitxer abans de res més
    base = netejar_nom(ruta.stem)
    carpeta = Path(eixida).expanduser().resolve() / base
    carpeta.mkdir(parents=True, exist_ok=True)
    complet = carpeta / f"{base} - partitura completa.pdf"
    _mscore_a_pdf(mscore, ruta, complet)
    parts_pdf: list[Path] = []
    tot_piano = all(
        (q.getInstrument(returnDefault=False) is not None
         and type(q.getInstrument(returnDefault=False)).__name__ == "Piano") for q in score.parts)
    if amb_parts and len(score.parts) > 1 and not tot_piano:
        with tempfile.TemporaryDirectory(dir=carpeta, prefix=".tmp-") as tmp:
            for i, p in enumerate(score.parts):
                nom = netejar_nom(musica.nom_part(p, i))
                s = stream.Score()
                s.metadata = copy.deepcopy(score.metadata)
                s.insert(0, copy.deepcopy(p))
                x = Path(tmp) / f"part{i + 1}.musicxml"
                s.write("musicxml", fp=str(x))
                pdf = carpeta / f"{base} - {i + 1}. {nom}.pdf"
                _mscore_a_pdf(mscore, x, pdf)
                parts_pdf.append(pdf)
    return {"completa": complet, "parts": parts_pdf}
