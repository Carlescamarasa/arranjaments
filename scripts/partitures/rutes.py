"""Rutes segures: tot el que s'escriu va dins de la carpeta de treball (eixida/ o entrada/).

La carpeta de treball és aquella des d'on s'executa l'ordre (Documents/Arranjaments, en una instal·lació normal).

- Mai s'escriu fora de la carpeta de treball.
- Cada peça té UNA carpeta dins d'eixida/ (eixida/<peça>/) amb el MusicXML, el fitxer de MuseScore, el PDF del guió
  i la subcarpeta Particel·les/. Un resultat nou REEMPLAÇA l'anterior (escriptura atòmica: mai queda mig escrit).
- Per conservar la versió anterior, l'opció --nova-versio usa una carpeta nova (eixida/<peça>-2/, -3...).
- Les còpies d'entrada/ i les rutes demanades amb --eixida no sobreescriuen mai: s'afegeix -2, -3...
- Per a provar-ho des d'un altre lloc, la variable d'entorn PARTITURES_ARREL fixa la carpeta de treball.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from .errors import ErrorUsuari

SUFIXOS_ORDRES = ("instruments", "transportat", "reduccio", "arranjament")


def arrel() -> Path:
    return Path(os.environ.get("PARTITURES_ARREL") or Path.cwd()).resolve()


def carpeta(nom: str) -> Path:
    return arrel() / nom


def dins(ruta: str | Path, nom_carpeta: str) -> Path:
    """Resol la ruta (relativa a la carpeta de treball) i comprova que és dins de `nom_carpeta/`."""
    p = Path(ruta).expanduser()
    if not p.is_absolute():
        p = arrel() / p
    p = p.resolve()
    base = carpeta(nom_carpeta).resolve()
    try:
        p.relative_to(base)
    except ValueError:
        raise ErrorUsuari(
            f"Només puc guardar fitxers dins de la carpeta «{nom_carpeta}/» de la carpeta de treball, no en «{ruta}». "
            f"Deixa que decidisca jo el nom, o tria una ruta que comence per {nom_carpeta}/."
        ) from None
    return p


def lliure(ruta: Path) -> Path:
    """Si la ruta ja existeix, afegeix -2, -3... al nom (mai sobreescriu)."""
    if not ruta.exists():
        return ruta
    k = 2
    while True:
        cand = ruta.with_name(f"{ruta.stem}-{k}{ruta.suffix}")
        if not cand.exists():
            return cand
        k += 1


def nom_base(stem: str) -> str:
    """Treu el sufix d'ordre i el número del final perquè els noms no vagen creixent."""
    patro = r"(-(?:%s))?(-\d+)?$" % "|".join(SUFIXOS_ORDRES)
    net = re.sub(patro, "", stem)
    return net or stem


def eixida_per_defecte(origen: str | Path, sufix: str, extensio: str = ".musicxml",
                       sol_licitada: str | None = None, nom_carpeta: str = "eixida") -> Path:
    """Ruta final (segura i que no existeix) per a un resultat."""
    if sol_licitada:
        p = dins(sol_licitada, nom_carpeta)
        if p.suffix.lower() != extensio:
            p = p.with_suffix(extensio)
    else:
        nom = nom_base(Path(origen).stem)
        p = carpeta(nom_carpeta) / (f"{nom}-{sufix}{extensio}" if sufix else f"{nom}{extensio}")
    p.parent.mkdir(parents=True, exist_ok=True)
    return lliure(p)


def netejar_nom(text: str) -> str:
    n = re.sub(r"[^\w\-. ]+", "_", text, flags=re.UNICODE).strip(" ._")
    return n or "partitura"


def carpeta_lliure(carpeta_: Path) -> Path:
    """Carpeta que no existeix: afegeix -2, -3... al nom sencer (els punts del nom no són extensió)."""
    if not carpeta_.exists():
        return carpeta_
    k = 2
    while (carpeta_.parent / f"{carpeta_.name}-{k}").exists():
        k += 1
    return carpeta_.parent / f"{carpeta_.name}-{k}"


def peca_de(origen: str | Path) -> tuple[str, bool]:
    """(nom de la peça, ja_es_carpeta_de_peça). Si l'origen és eixida/<peça>/<peça>.musicxml, el nom es manté tal qual."""
    o = Path(origen).expanduser()
    if not o.is_absolute():
        o = arrel() / o
    o = o.resolve()
    if o.parent.parent == carpeta("eixida").resolve() and o.stem == o.parent.name:
        return o.parent.name, True
    return netejar_nom(nom_base(o.stem)), False


def carpeta_peca(origen: str | Path, nova_versio: bool = False) -> Path:
    """Carpeta eixida/<peça>/ (nova, amb -2... si es demana una versió nova)."""
    nom, _ = peca_de(origen)
    if nova_versio:
        nom = netejar_nom(nom_base(nom))
        c = carpeta_lliure(carpeta("eixida") / nom)
    else:
        c = carpeta("eixida") / nom
    c.mkdir(parents=True, exist_ok=True)
    return c


def eixida_peca(origen: str | Path, sol_licitada: str | None = None, nova_versio: bool = False) -> Path:
    """Ruta del MusicXML d'una peça: eixida/<peça>/<peça>.musicxml (es reemplaça), o la demanada amb --eixida."""
    if sol_licitada:
        return eixida_per_defecte(origen, "", sol_licitada=sol_licitada)
    c = carpeta_peca(origen, nova_versio)
    return c / f"{c.name}.musicxml"


def relativa(ruta: str | Path) -> str:
    p = Path(ruta).resolve()
    try:
        return p.relative_to(arrel()).as_posix()
    except ValueError:
        return p.as_posix()


def linia_actual(ruta: str | Path) -> str:
    return f"Fitxer actual: {relativa(ruta)}"
