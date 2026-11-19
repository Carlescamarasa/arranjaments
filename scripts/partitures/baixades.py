"""Baixar una partitura lliure del web a entrada/, amb moltes garanties.

- Només https i només dominis de partitures lliures coneguts (també en les redireccions).
- Només fitxers MusicXML (.musicxml, .xml, .mxl) o de MuseScore (.mscx, .mscz; es converteixen a MusicXML).
- Només es guarda dins d'entrada/, amb mida màxima, i mai se sobreescriu res.
- Si la pàgina respon amb HTML (comprovació de robot, inici de sessió...), no s'intenta saltar: s'avisa.
"""
from __future__ import annotations

import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import rutes
from .errors import ErrorUsuari

DOMINIS = {
    "cpdl.org", "www.cpdl.org",
    "mutopiaproject.org", "www.mutopiaproject.org",
    "github.com", "raw.githubusercontent.com", "objects.githubusercontent.com",
}
EXTENSIONS = {".musicxml", ".xml", ".mxl", ".mscx", ".mscz"}
MIDA_MAXIMA = 20 * 1024 * 1024
TEMPS_MAXIM = 30
MAX_REDIRECCIONS = 4
AGENT = "Arranjaments (baixada de partitures lliures)"


def _comprova_url(url: str) -> urllib.parse.ParseResult:
    p = urllib.parse.urlparse(url.strip())
    if p.scheme != "https":
        raise ErrorUsuari("Només baixe adreces que comencen per https://.")
    if p.username or p.password or p.port not in (None, 443):
        raise ErrorUsuari("Esta adreça no és una baixada normal; no la use.")
    if (p.hostname or "").lower() not in DOMINIS:
        raise ErrorUsuari(f"Només baixe de webs de partitures lliures conegudes ({', '.join(sorted(DOMINIS))}). "
                          "Baixa el fitxer des del navegador i deixa'l a la carpeta entrada/.")
    return p


class _Redireccio(urllib.request.HTTPRedirectHandler):
    """Cada salt de redirecció ha de continuar dins dels dominis permesos."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _comprova_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _obri(url: str):
    obridor = urllib.request.build_opener(_Redireccio())
    peticio = urllib.request.Request(url, headers={"User-Agent": AGENT})
    return obridor.open(peticio, timeout=TEMPS_MAXIM)


def _extensio(url: str, nom_resposta: str | None = None) -> str:
    for text in (nom_resposta, urllib.parse.unquote(urllib.parse.urlparse(url).path)):
        if text:
            ext = Path(text).suffix.lower()
            if ext in EXTENSIONS:
                return ext
    raise ErrorUsuari("Només baixe fitxers MusicXML (.musicxml, .xml, .mxl) o de MuseScore (.mscx, .mscz). "
                      "Esta adreça no acaba així; si és un PDF, no el baixe: no és editable.")


def _nom_fitxer(url: str, ext: str) -> str:
    base = Path(urllib.parse.unquote(urllib.parse.urlparse(url).path)).stem
    return (rutes.netejar_nom(base) or "partitura") + ext


def _valida(dades: bytes, ext: str) -> None:
    cap = dades[:2048].lstrip().lower()
    if cap.startswith(b"<!doctype html") or cap.startswith(b"<html") or b"<html" in cap[:600]:
        raise ErrorUsuari("La pàgina no ha donat el fitxer sinó una pàgina web (potser demana una comprovació de robot "
                          "o iniciar sessió). No intente saltar-m'ho: baixa'l tu des del navegador i deixa'l a entrada/.")
    if ext in (".mxl", ".mscz"):
        if not dades.startswith(b"PK"):
            raise ErrorUsuari("El fitxer baixat no té el format esperat (hauria de ser un arxiu comprimit).")
    else:
        text = dades[:8192].decode("utf-8", errors="ignore")
        if ext in (".musicxml", ".xml") and "score-partwise" not in text and "score-timewise" not in text:
            raise ErrorUsuari("El fitxer baixat no sembla una partitura MusicXML.")
        if ext == ".mscx" and "<museScore" not in text:
            raise ErrorUsuari("El fitxer baixat no sembla un fitxer de MuseScore.")


def descarrega(url: str) -> Path:
    """Baixa `url` a entrada/ i retorna la ruta del fitxer (MusicXML si venia de MuseScore)."""
    _comprova_url(url)
    try:
        with _obri(url) as r:
            nom_resp = None
            cd = r.headers.get("Content-Disposition") or ""
            m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', cd)
            if m:
                nom_resp = urllib.parse.unquote(m.group(1))
            ext = _extensio(r.geturl() or url, nom_resp)
            llargada = r.headers.get("Content-Length")
            if llargada and llargada.isdigit() and int(llargada) > MIDA_MAXIMA:
                raise ErrorUsuari("El fitxer és massa gran (més de 20 MB).")
            dades = r.read(MIDA_MAXIMA + 1)
    except ErrorUsuari:
        raise
    except urllib.error.HTTPError as e:
        raise ErrorUsuari(f"El web ha respost amb un error ({e.code}). Si cal, baixa'l des del navegador i deixa'l a entrada/.") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ErrorUsuari("No he pogut baixar el fitxer (sense connexió o el web no respon). "
                          "Baixa'l des del navegador i deixa'l a entrada/.") from e
    if len(dades) > MIDA_MAXIMA:
        raise ErrorUsuari("El fitxer és massa gran (més de 20 MB).")
    _valida(dades, ext)
    entrada = rutes.carpeta("entrada")
    entrada.mkdir(parents=True, exist_ok=True)
    nom = _nom_fitxer(url, ext)
    if ext in (".mscx", ".mscz"):
        from . import eines, externs
        mscore = eines.trobar_musescore()
        desti = rutes.lliure(entrada / (Path(nom).stem + ".musicxml"))
        with tempfile.TemporaryDirectory() as tmp:
            origen = Path(tmp) / nom
            origen.write_bytes(dades)
            externs._mscore_a_pdf(mscore, origen, desti)   # «mscore -o sortida entrada»: serveix per a qualsevol format
        return desti
    desti = rutes.lliure(entrada / nom)
    desti.write_bytes(dades)
    return desti

