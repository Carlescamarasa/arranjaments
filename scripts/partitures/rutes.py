"""Rutes segures: tot el que s'escriu va dins de la carpeta del projecte (eixida/ o entrada/).

- Mai s'escriu fora del projecte.
- Mai se sobreescriu res: si el nom ja existeix, s'afegeix -2, -3...
- Per a provar-ho des d'un altre lloc, la variable d'entorn PARTITURES_ARREL fixa la carpeta del projecte.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from .errors import ErrorUsuari

SUFIXOS_ORDRES = ("instruments", "transportat", "reduccio")


def arrel() -> Path:
    return Path(os.environ.get("PARTITURES_ARREL") or Path.cwd()).resolve()


def carpeta(nom: str) -> Path:
    return arrel() / nom


def dins(ruta: str | Path, nom_carpeta: str) -> Path:
    """Resol la ruta (relativa a la carpeta del projecte) i comprova que és dins de `nom_carpeta/`."""
    p = Path(ruta).expanduser()
    if not p.is_absolute():
        p = arrel() / p
    p = p.resolve()
    base = carpeta(nom_carpeta).resolve()
    try:
        p.relative_to(base)
    except ValueError:
        raise ErrorUsuari(
            f"Només puc guardar fitxers dins de la carpeta «{nom_carpeta}/» del projecte, no en «{ruta}». "
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


def relativa(ruta: str | Path) -> str:
    p = Path(ruta).resolve()
    try:
        return p.relative_to(arrel()).as_posix()
    except ValueError:
        return p.as_posix()


def linia_actual(ruta: str | Path) -> str:
    return f"Fitxer actual: {relativa(ruta)}"
