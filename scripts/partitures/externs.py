"""Crides a programes externs: Audiveris (PDF → MusicXML), MuseScore (→ PDF) i obrir una partitura."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from . import eines, musica, rutes
from .errors import ErrorUsuari

# Totes les crides porten encoding UTF-8 amb errors="replace": a Windows la consola pot ser cp1252/cp850.
_TEXT = {"capture_output": True, "text": True, "encoding": "utf-8", "errors": "replace",
         "stdin": subprocess.DEVNULL}


def _entorn_silenciós() -> dict:
    """Entorn perquè els programes no òbrin finestres ni robin el focus."""
    env = dict(os.environ)
    if sys.platform.startswith("linux"):
        env.setdefault("QT_QPA_PLATFORM", "offscreen")  # MuseScore sense finestra (a Mac/Windows no cal)
    env["JAVA_TOOL_OPTIONS"] = (env.get("JAVA_TOOL_OPTIONS", "") + " -Djava.awt.headless=true").strip()
    return env


netejar_nom = rutes.netejar_nom


def _cua(r) -> str:
    return "\n".join(((r.stdout or "") + "\n" + (r.stderr or "")).strip().splitlines()[-8:])


# --------------------------------------------------------------------------- Audiveris

def importar_pdf(pdf: str | Path, temps_maxim: int = 1800) -> list[Path]:
    """Converteix un PDF o imatge en MusicXML. Cada execució usa una carpeta nova dins d'eixida/ (neta)."""
    pdf = Path(pdf).expanduser().resolve()
    if not pdf.exists():
        raise ErrorUsuari(f"No trobe el fitxer «{pdf.name}». Comprova el nom i que estiga en la carpeta entrada/.")
    if pdf.suffix.lower() not in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        raise ErrorUsuari("L'ordre «importar» només accepta PDF o imatges (png, jpg, tif).")
    aud = eines.trobar_audiveris()
    carpeta = rutes.lliure(rutes.carpeta("eixida") / f"{netejar_nom(pdf.stem)}-omr")
    carpeta.mkdir(parents=True, exist_ok=False)   # carpeta nova: només hi haurà el resultat d'esta execució
    ordre = [aud, "-batch", "-export", "-output", str(carpeta), str(pdf)]
    try:
        r = subprocess.run(ordre, timeout=temps_maxim, env=_entorn_silenciós(), **_TEXT)
    except subprocess.TimeoutExpired as e:
        raise ErrorUsuari(f"Audiveris ha tardat massa (més de {temps_maxim // 60} minuts) i l'he aturat. "
                          "Prova amb un PDF més curt (unes poques pàgines).") from e
    except OSError as e:
        raise ErrorUsuari(f"No he pogut executar Audiveris ({type(e).__name__}). Comprova la instal·lació.") from e
    resultats = sorted(x for x in list(carpeta.rglob("*.mxl")) + list(carpeta.rglob("*.musicxml"))
                       if x.is_file())
    if not resultats:
        cua = _cua(r)
        raise ErrorUsuari(
            "Audiveris no ha pogut reconéixer la partitura (no ha generat cap MusicXML). "
            "Això passa amb escanejats borrosos, fotos o PDF molt retallats. "
            "Prova de buscar la partitura ja en MusicXML (skill buscar-partitura) o amb un PDF més net."
            + (f"\nÚltimes línies del programa:\n{cua}" if cua else "")
        )
    return resultats


# --------------------------------------------------------------------------- MuseScore

def _mscore_a_pdf(mscore: str, origen: Path, desti: Path, temps_maxim: int = 300) -> None:
    desti.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = subprocess.run([mscore, "-o", str(desti), str(origen)], timeout=temps_maxim,
                           env=_entorn_silenciós(), **_TEXT)
    except subprocess.TimeoutExpired as e:
        raise ErrorUsuari("MuseScore ha tardat massa a generar el PDF i l'he aturat.") from e
    except OSError as e:
        raise ErrorUsuari(f"No he pogut executar MuseScore ({type(e).__name__}). Comprova la instal·lació.") from e
    if not desti.exists() or desti.stat().st_size == 0:
        raise ErrorUsuari(f"MuseScore no ha pogut crear «{desti.name}».\n{_cua(r)}".strip())


def _registre() -> Path:
    from .actualitzar import dades_per_defecte
    return dades_per_defecte() / "registre-mscz.json"


def _empremta(ruta: Path) -> dict:
    st = ruta.stat()
    return {"mida": st.st_size, "mtime_ns": st.st_mtime_ns}


def _llig_registre() -> dict:
    try:
        d = json.loads(_registre().read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _anota_mscz(ruta: Path) -> None:
    """Recorda com és el .mscz que acabem d'escriure, per saber si algú el retoca després a MuseScore."""
    d = _llig_registre()
    d[str(ruta.resolve())] = _empremta(ruta)
    try:
        _registre().parent.mkdir(parents=True, exist_ok=True)
        _registre().write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass   # sense registre, el pitjor cas és guardar una còpia de més


def _es_retocat(mscz: Path) -> bool:
    anotat = _llig_registre().get(str(mscz.resolve()))
    return anotat != _empremta(mscz)


def exportar(ruta: str | Path, amb_parts: bool = True) -> dict:
    """Deixa la peça completa en la seua carpeta d'eixida: MuseScore, guió en PDF i particel·les en PDF."""
    mscore = eines.trobar_musescore()
    ruta = Path(ruta).expanduser().resolve()
    score = musica.carregar(ruta)          # valida el fitxer abans de res més
    nom, es_carpeta = rutes.peca_de(ruta)
    if es_carpeta:
        carpeta = ruta.parent
    else:
        carpeta = rutes.carpeta("eixida") / nom
    carpeta.mkdir(parents=True, exist_ok=True)
    base = carpeta.name
    avis = ""
    mscz = carpeta / f"{base}.mscz"
    if ruta.resolve() != mscz.resolve():
        if mscz.exists() and _es_retocat(mscz):
            apart = mscz.with_name(f"{base} (retocat a MuseScore).mscz")
            k = 2
            while apart.exists():
                apart = mscz.with_name(f"{base} (retocat a MuseScore {k}).mscz")
                k += 1
            os.replace(mscz, apart)
            avis = (f"Atenció: el fitxer de MuseScore d'esta peça tenia canvis fets a mà. L'he guardat amb el nom "
                    f"«{apart.name}» perquè no es perda; el fitxer nou «{mscz.name}» ve del MusicXML.")
        with tempfile.TemporaryDirectory(dir=carpeta, prefix=".tmp-") as tmp:
            nou = Path(tmp) / mscz.name
            _mscore_a_pdf(mscore, ruta, nou)
            os.replace(nou, mscz)
        _anota_mscz(mscz)
    guio = carpeta / f"{base} - Guió.pdf"
    _mscore_a_pdf(mscore, ruta, guio)
    parts_pdf: list[Path] = []
    separades = musica.parts_separades(score)
    if amb_parts and len(separades) > 1:
        dest = carpeta / "Particel·les"
        dest.mkdir(exist_ok=True)
        for vell in dest.glob("*.pdf"):    # instruments de versions anteriors
            vell.unlink()
        with tempfile.TemporaryDirectory(dir=carpeta, prefix=".tmp-") as tmp:
            for i, (nom_part, s) in enumerate(separades):
                x = Path(tmp) / f"part{i + 1}.musicxml"
                s.write("musicxml", fp=str(x))
                pdf = dest / f"{base} - {i + 1}. {netejar_nom(nom_part)}.pdf"
                _mscore_a_pdf(mscore, x, pdf)
                parts_pdf.append(pdf)
    return {"guio": guio, "parts": parts_pdf, "mscz": mscz if mscz.exists() else None, "avis": avis}


def obrir(fitxer: str | Path) -> Path:
    """Obri una partitura amb MuseScore (Mac i Windows), sense esperar que es tanque."""
    ruta = Path(fitxer).expanduser().resolve()
    if not ruta.exists():
        raise ErrorUsuari(f"No trobe el fitxer «{ruta.name}».")
    if ruta.suffix.lower() not in musica.EXT_ACCEPTADES:
        raise ErrorUsuari("Només sé obrir partitures (MusicXML, MuseScore, MIDI...) amb MuseScore.")
    mscz = ruta.with_suffix(".mscz")
    if ruta.suffix.lower() in (".musicxml", ".xml", ".mxl") and mscz.exists():
        ruta = mscz
        print(f"Hi ha una versió de MuseScore («{mscz.name}»); obric esa, que pot tenir retocs.")
    mscore = eines.trobar_musescore()
    try:
        if sys.platform == "darwin" and ".app/" in mscore:
            app = mscore.split(".app/")[0] + ".app"
            subprocess.Popen(["open", "-a", app, str(ruta)])
        else:
            subprocess.Popen([mscore, str(ruta)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
    except OSError as e:
        raise ErrorUsuari(f"No he pogut obrir MuseScore ({type(e).__name__}).") from e
    return ruta
