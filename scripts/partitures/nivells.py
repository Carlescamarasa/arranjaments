"""Perfils de nivell que l'ajudant va aprenent, i preferències de cada docent.

Res no ve ple de sèrie: quan l'ajudant necessita saber un nivell (per exemple «fins on arriba la flauta a 4t elemental»),
ho pregunta i ho desa ací amb `partitures nivell desa`. Es guarda a la carpeta de dades de la persona (fora de la carpeta
de treball), en fitxers que es poden llegir:

  perfil/nivells.json       un perfil per instrument i curs, amb l'historial de canvis
  perfil/preferencies.md    preferències lliures («a 4t elemental la flauta no passa de Re5»)

Es poden compartir: `partitures nivell exporta` crea un fitxer a eixida/, i les eines llegeixen (només lectura) els fitxers
`nivells/*.json` de la biblioteca compartida si n'hi ha.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import shutil
import sys
from pathlib import Path

from . import instruments as inst
from . import rutes
from .errors import ErrorUsuari

VERSIO = 1
MAX_NOTES = 300          # lletres màximes del camp «notes» (és text lliure que acaba davant del model)
CAMPS_LLISTA = ("tonalitats", "figures", "compassos", "articulacions")
CAMPS = ("tessitura",) + CAMPS_LLISTA + ("notes",)
NOM_CAMP = {"tessitura": "tessitura", "tonalitats": "tonalitats", "figures": "figures rítmiques",
            "compassos": "compassos (3/4, 4/4...)", "articulacions": "articulacions", "notes": "notes"}
PREGUNTA_CAMP = {
    "tessitura": "fins on arriba (nota més greu i més aguda, per exemple Do3-Sol4)",
    "tonalitats": "quines tonalitats (o fins a quantes alteracions)",
    "figures": "quines figures rítmiques (negra, corxera, puntet, tresillo...)",
    "compassos": "quins compassos (2/4, 3/4, 4/4, 6/8...)",
    "articulacions": "quines articulacions (picat, lligat, accent...)",
}


# --------------------------------------------------------------------------- carpeta de dades

def _dades() -> Path:
    from .actualitzar import dades_per_defecte
    return dades_per_defecte() / "perfil"


def fitxer_nivells() -> Path:
    return _dades() / "nivells.json"


def fitxer_preferencies() -> Path:
    return _dades() / "preferencies.md"


def _avui() -> str:
    return datetime.date.today().isoformat()


# --------------------------------------------------------------------------- noms i validació

def norm(text: str) -> str:
    return re.sub(r"\s+", " ", inst._norm(str(text))).strip()


_SOLFEIG = {"do": "C", "re": "D", "mi": "E", "fa": "F", "sol": "G", "la": "A", "si": "B"}
_NOTA = r"(?<![a-z])(do|re|mi|fa|sol|la|si)\s*(#{1,2}|b{1,2})?\s*(-?\d)(?!\d)"
_RE_NOTA = re.compile(rf"^{_NOTA}$")
_RE_NOTES = re.compile(_NOTA)


def _net_nota(text) -> str:
    """Minúscules, sense accents, amb # i b normals (també accepta els símbols de sostingut i bemoll)."""
    return inst._norm(str(text).replace("\u266f", "#").replace("\u266d", "b")).replace(" ", "")


def nota_a_midi(text: str) -> int:
    """«Do3» (Do central = Do3) a número MIDI. Només solfeig."""
    m = _RE_NOTA.match(_net_nota(text))
    if not m:
        raise ErrorUsuari(f"No entenc la nota «{text}». Escriu-la en solfeig amb l'octava, com Do3, Fa#2 o Sib3 "
                          "(el Do central és Do3).")
    lletra, alt, octava = _SOLFEIG[m.group(1)], (m.group(2) or "").replace("b", "-"), int(m.group(3)) + 1
    from music21 import pitch
    return pitch.Pitch(f"{lletra}{alt}{octava}").midi


def nom_midi(midi: int) -> str:
    from .musica import nom_nota
    return nom_nota(midi)


def nom_escrit(text: str) -> str:
    """«lab3» a «Lab3»: el nom en solfeig tal com l'ha escrit la persona (els bemolls es queden bemolls)."""
    m = _RE_NOTA.match(_net_nota(text))
    return m.group(1).capitalize() + (m.group(2) or "") + m.group(3)


def _extrems(text: str) -> tuple[str, str]:
    """Les dues notes d'una tessitura escrita de qualsevol manera: «Do3-Sol4», «Lab3-Mib5», «Do3 fins a Sol4»,
    «de Do3 a Sol4», «do3 a sol4». Retorna els noms, la més greu primer."""
    notes = [m.group(0) for m in _RE_NOTES.finditer(_net_nota_cerca(text))]
    if len(notes) != 2:
        raise ErrorUsuari(f"No entenc la tessitura «{text}». Escriu la nota més greu i la més aguda en solfeig, per exemple Do3-Sol4 (el Do central és Do3).")
    a, b = notes
    return (nom_escrit(a), nom_escrit(b)) if nota_a_midi(a) <= nota_a_midi(b) else (nom_escrit(b), nom_escrit(a))


def _net_nota_cerca(text) -> str:
    """Com _net_nota però deixa els espais entre paraules (per a trobar les notes dins d'una frase)."""
    return inst._norm(str(text).replace("\u266f", "#").replace("\u266d", "b"))


def normalitza_tessitura(text: str) -> str:
    """«do3 a SOL4» → «Do3-Sol4» (la més greu primer). Els bemolls es queden bemolls: «Lab3-Mib5»."""
    lo, hi = _extrems(text)
    return f"{lo}-{hi}"


def rang_midi(text: str) -> tuple[int, int]:
    lo, hi = _extrems(text)
    return nota_a_midi(lo), nota_a_midi(hi)


_NUMS = {"un": 1, "una": 1, "dos": 2, "dues": 2, "tres": 3, "quatre": 4, "cinc": 5, "sis": 6, "set": 7,
         "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7}
_RE_FINS = re.compile(r"^(?:fins a|com a maxim|maxim|fins)\s+(\d|un|una|dos|dues|tres|quatre|cinc|sis|set)\s*"
                      r"(alteracions|alteracio|sostenits|sostinguts|sostenit|sostingut|bemolls|bemoll)?$")
_MODES = {"major": "major", "mayor": "major", "menor": "minor"}
_RE_TON_CURTA = re.compile(r"^\s*((?i:do|re|mi|fa|sol|la|si))\s*(#|b)?\s*(M|m)\s*$")   # «Do M», «La m» (la M gran és major)


def _tonalitat_key(lletra: str, alt: str | None, mode: str) -> int:
    from music21 import key
    return key.Key(_SOLFEIG[lletra] + {"#": "#", "b": "-", None: ""}[alt], mode).sharps


def alteracions_de_tonalitat(text: str) -> set[int]:
    """Tonalitat d'un perfil → conjunt de nombres d'alteracions (sostinguts positiu, bemolls negatiu)."""
    m = _RE_TON_CURTA.match(str(text))
    if m:
        return {_tonalitat_key(m.group(1).lower(), m.group(2), "major" if m.group(3) == "M" else "minor")}
    n = norm(text)
    if n in ("sense alteracions", "sense armadura", "cap alteracio", "sense alteracio"):
        return {0}
    m = _RE_FINS.match(n)
    if m:
        k = _NUMS[m.group(1)]
        if (m.group(2) or "").startswith("sosten") or (m.group(2) or "").startswith("sosting"):
            return set(range(0, k + 1))
        if (m.group(2) or "").startswith("bemoll"):
            return set(range(-k, 1))
        return set(range(-k, k + 1))
    m = re.match(r"^(do|re|mi|fa|sol|la|si)\s*(#|b)?\s+(major|mayor|menor)$", n)
    if m:
        return {_tonalitat_key(m.group(1), m.group(2), _MODES[m.group(3)])}
    raise ErrorUsuari(f"No entenc la tonalitat «{text}». Exemples: «Do major», «Do M», «La menor», «Sib major», "
                      "«fins a 2 alteracions», «fins a dues alteracions», «sense alteracions».")


def normalitza_compas(text: str) -> str:
    m = re.match(r"^\s*(?:compas\s+(?:de\s+)?)?(\d{1,2})\s*/\s*(\d{1,2})\s*$", norm(text))
    if not m:
        raise ErrorUsuari(f"No entenc el compàs «{text}». Escriu-lo com 2/4, 3/4, 4/4 o 6/8.")
    return f"{int(m.group(1))}/{int(m.group(2))}"


_FIGURES = {"rodona": "whole", "blanca": "half", "negra": "quarter", "corxera": "eighth", "semicorxera": "16th",
            "fusa": "32nd"}
_SINONIMS = {"redona": "rodona", "croma": "corxera", "semicroma": "semicorxera", "tresillos": "tresillo",
             "tresillo": "tresillo", "tercet": "tresillo", "tercets": "tresillo", "puntets": "puntet", "puntillo": "puntet",
             # plurals: «negres i blanques»
             "rodones": "rodona", "redones": "rodona", "blanques": "blanca", "negres": "negra", "corxeres": "corxera",
             "semicorxeres": "semicorxera", "fuses": "fusa", "cromas": "corxera", "semicromas": "semicorxera"}


def normalitza_figura(text: str) -> str:
    n = norm(text)
    base = re.sub(r"\s+(amb|con)\s+(puntet|puntillo|puntets)$", "", n)
    puntet = base != n
    base = _SINONIMS.get(base, base)
    if base in ("puntet", "tresillo"):
        return base
    if base not in _FIGURES:
        raise ErrorUsuari(f"No conec la figura «{text}». Pots dir: rodona, blanca, negra, corxera, semicorxera, fusa "
                          "(també en plural: negres, blanques...), «negra amb puntet» (o «corxera amb puntet»...), puntet, tresillo.")
    return base + (" amb puntet" if puntet else "")


def _llista(valor: str | None) -> list[str]:
    """«negres, blanques i corxeres» → tres elements (coma, punt i coma, « i » o « y »)."""
    return [t.strip() for t in re.split(r"\s*[,;]\s*|\s+(?:i|y)\s+", valor or "") if t.strip()]


def valida_camp(camp: str, valor: str):
    """Valida i normalitza un camp del perfil. Retorna text (tessitura, notes) o llista."""
    if camp == "tessitura":
        return normalitza_tessitura(valor)
    if camp == "notes":
        return re.sub(r"\s+", " ", str(valor)).strip()[:MAX_NOTES]
    elements = _llista(valor)
    if not elements:
        raise ErrorUsuari(f"El camp «{NOM_CAMP[camp]}» està buit.")
    if camp == "tonalitats":
        for e in elements:
            alteracions_de_tonalitat(e)
        return [re.sub(r"\s+", " ", e) for e in elements]
    if camp == "compassos":
        return [normalitza_compas(e) for e in elements]
    if camp == "figures":
        return [normalitza_figura(e) for e in elements]
    return [re.sub(r"\s+", " ", e) for e in elements]


# --------------------------------------------------------------------------- instruments i cursos

_ORDINALS_CURS = {"primer": "1", "primera": "1", "primero": "1", "segon": "2", "segona": "2", "segundo": "2",
                  "tercer": "3", "tercera": "3", "quart": "4", "quarta": "4", "cuarto": "4", "cinque": "5", "quint": "5",
                  "quinta": "5", "quinto": "5", "sise": "6", "sext": "6", "sexta": "6", "sexto": "6"}
_ETAPES_CURS = {"ee": "elemental", "elementals": "elemental", "ep": "professional", "professionals": "professional"}


def normalitza_curs(text: str) -> str:
    """«4t elemental», «4t d'elemental», «quart elemental», «4t EE» i «4º Elemental» donen tots «4 elemental»."""
    n = norm(str(text).replace("\u2019", "'"))
    n = re.sub(r"\b(\d{1,2})\s?(?:r|n|t|e|er|o|a|\u00ba|\u00aa)\b", r"\1", n)
    n = re.sub(r"\b(\d{1,2})(?:\u00ba|\u00aa)", r"\1", n)
    paraules = []
    for w in re.split(r"[\s']+", n):
        w = _ORDINALS_CURS.get(w, w)
        w = _ETAPES_CURS.get(w, w)
        if w in ("d", "de", "del", "curs", "grau", "ensenyances", "ensenyanzas", "nivell", "nivel"):
            continue
        if w:
            paraules.append(w)
    return " ".join(paraules)


def _instrument(text: str) -> tuple[str, str]:
    """(clau, nom) d'un instrument: del catàleg si el coneixem; si no (làmines, xilòfon, veu...), tal com l'ha dit la persona."""
    try:
        if inst.grup(text):          # un grup («làmines») és un perfil propi, no el del primer instrument del grup
            raise ErrorUsuari("grup")
        i = inst.obtenir(text)
        return i.clau, i.nom
    except ErrorUsuari:
        lliure = re.sub(r"\s+", " ", str(text)).strip()
        clau = re.sub(r"[^a-z0-9]+", "-", norm(lliure)).strip("-")
        if not clau or len(lliure) > 40:
            raise ErrorUsuari("Digues el nom de l'instrument (per exemple flauta, trompeta o làmines).") from None
        return clau[:40], lliure


def _nom_instrument(clau: str, p: dict | None = None) -> str:
    if p and p.get("instrument_nom"):
        return p["instrument_nom"]
    try:
        return inst.obtenir(clau).nom
    except ErrorUsuari:
        return clau


def _clau_perfil(instrument: str, curs: str) -> tuple[str, str]:
    clau, _ = _instrument(instrument)
    c = normalitza_curs(curs)
    if not c:
        raise ErrorUsuari("Falta el curs (per exemple --curs \"4t elemental\").")
    return clau, c


# --------------------------------------------------------------------------- emmagatzematge

def _data_segura() -> str:
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def aparta_malmes(ruta: Path, que: str) -> Path | None:
    """Un fitxer de dades que no es pot llegir no se sobreescriu mai: es guarda a part (`.malmes-<data>`) i es diu."""
    desti = ruta.with_name(f"{ruta.name}.malmes-{_avui()}")
    k = 2
    while desti.exists():
        desti = ruta.with_name(f"{ruta.name}.malmes-{_avui()}-{k}")
        k += 1
    try:
        os.replace(ruta, desti)
    except OSError:
        raise ErrorUsuari(f"El fitxer de {que} ({ruta}) està malmés i no el puc apartar. No he canviat res: "
                          "demana ajuda a qui t'ajuda amb el programa.") from None
    print(f"Avís: el fitxer de {que} estava malmés. L'he guardat a part com «{desti.name}» (a la mateixa carpeta) "
          "i començo de nou; el contingut antic no s'ha perdut.", file=sys.stderr)
    return desti


def _llig(ruta: Path) -> dict:
    """Lectura tolerant, per als fitxers de la biblioteca (només lectura): si no val, res."""
    try:
        d = json.loads(ruta.read_text(encoding="utf-8-sig"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _re_clau(perfils: dict) -> dict:
    """Perfils desats amb una clau d'abans (curs escrit d'una altra manera): els passa a la clau normalitzada."""
    res: dict = {}
    for k, p in perfils.items():
        if not isinstance(p, dict) or "|" not in str(k):
            continue
        ci, cc = str(k).split("|", 1)
        nova = f"{ci}|{normalitza_curs(p.get('curs') or cc)}"
        res.setdefault(nova, p)
    return res


def carrega() -> dict:
    ruta = fitxer_nivells()
    try:
        text = ruta.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        text = None
    except OSError as e:
        raise ErrorUsuari(f"No puc llegir el fitxer de nivells ({ruta}): {type(e).__name__}. No he canviat res.") from None
    except UnicodeDecodeError:
        aparta_malmes(ruta, "nivells")
        text = None
    d: dict = {}
    if text is not None:
        try:
            d = json.loads(text)
            if not isinstance(d, dict) or not isinstance(d.get("perfils", {}), dict):
                raise ValueError("forma inesperada")
        except ValueError:
            aparta_malmes(ruta, "nivells")
            d = {}
    d.setdefault("versio", VERSIO)
    d["perfils"] = _re_clau(d.get("perfils", {}))
    return d


def _desa(d: dict) -> None:
    ruta = fitxer_nivells()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(ruta.name + ".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, ruta)


# --------------------------------------------------------------------------- perfils compartits (biblioteca)

_MEMO_COMPARTITS: dict = {}
MAX_PERFILS_COMPARTITS = 300
MAX_ELEMENTS = 30


def esborra_cache() -> None:
    _MEMO_COMPARTITS.clear()


def neteja_compartit(p) -> dict | None:
    """Valida un perfil d'un fitxer compartit amb els mateixos validadors que els perfils propis (o llança ErrorUsuari).
    Queda net: només els camps coneguts, llistes curtes i notes de com a molt MAX_NOTES lletres."""
    if not isinstance(p, dict):
        raise ErrorUsuari("no és un perfil")
    if not isinstance(p.get("instrument"), str) or not isinstance(p.get("curs"), str):
        raise ErrorUsuari("falta l'instrument o el curs")
    clau, nom = _instrument(p["instrument"])
    curs = re.sub(r"\s+", " ", p["curs"]).strip()
    if not normalitza_curs(curs) or len(curs) > 40:
        raise ErrorUsuari("el curs no és vàlid")
    net: dict = {"instrument": clau, "curs": curs}
    if nom != _nom_instrument(clau):
        net["instrument_nom"] = nom
    for camp in CAMPS:
        v = p.get(camp)
        if v in (None, "", []):
            continue
        if camp in CAMPS_LLISTA:
            if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                raise ErrorUsuari(f"«{NOM_CAMP[camp]}» no és una llista")
            v = ", ".join(v[:MAX_ELEMENTS])
        elif not isinstance(v, str):
            raise ErrorUsuari(f"«{NOM_CAMP[camp]}» no és text")
        net[camp] = valida_camp(camp, v)
    return net


def compartits() -> dict[str, dict]:
    """Perfils compartits de la carpeta `nivells/` de la biblioteca (només lectura), si n'hi ha.

    Cada perfil es valida; els que no valen s'ignoren amb un avís d'una línia. El resultat es recorda en memòria."""
    try:
        from . import biblioteca as bib
        arrel = bib.localitzar()["ruta"]
        if arrel is None or not (arrel / "nivells").is_dir():
            return {}
        if _MEMO_COMPARTITS.get("arrel") == str(arrel):
            return _MEMO_COMPARTITS["res"]
        res: dict[str, dict] = {}
        for f in sorted((arrel / "nivells").glob("*.json")):
            if f.stat().st_size > 2_000_000:
                continue
            perfils = _llig(f).get("perfils", {})
            if not isinstance(perfils, dict):
                continue
            for k, p in list(perfils.items())[:MAX_PERFILS_COMPARTITS]:
                try:
                    net = neteja_compartit(p)
                except ErrorUsuari as e:
                    print(f"Avís: ignore el perfil «{str(k)[:40]}» de nivells/{f.name[:40]} ({str(e)[:90]}).", file=sys.stderr)
                    continue
                clau = f"{net['instrument']}|{normalitza_curs(net['curs'])}"
                res.setdefault(clau, dict(net, _origen=f"nivells/{f.name}"))
        _MEMO_COMPARTITS.update({"arrel": str(arrel), "res": res})
        return res
    except Exception:  # la biblioteca compartida mai ha de trencar res
        return {}


def perfil(instrument: str, curs: str) -> dict | None:
    """Perfil efectiu: el personal i, pels camps buits, el compartit de la biblioteca."""
    clau_i, c = _clau_perfil(instrument, curs)
    k = f"{clau_i}|{c}"
    propi = carrega()["perfils"].get(k)
    comu = compartits().get(k)
    if not propi and not comu:
        return None
    res = {"instrument": clau_i, "curs": (propi or comu).get("curs", curs), "origens": {}}
    nom = (propi or {}).get("instrument_nom") or (comu or {}).get("instrument_nom")
    if nom:
        res["instrument_nom"] = nom
    for camp in CAMPS:
        for font, nom in ((propi, "teu"), (comu, comu and comu.get("_origen"))):
            if font and font.get(camp):
                res[camp] = font[camp]
                res["origens"][camp] = nom
                break
    return res


def cursos_coneguts(clau_instrument: str | None = None) -> list[str]:
    """Cursos dels quals ja hi ha perfil (del teu o de la biblioteca), per a ensenyar-los quan un curs no es troba."""
    claus = set(carrega()["perfils"]) | set(compartits())
    res: dict[str, str] = {}
    for k in sorted(claus):
        ci, cc = k.split("|", 1)
        if clau_instrument and ci != clau_instrument:
            continue
        p = carrega()["perfils"].get(k) or compartits().get(k) or {}
        res.setdefault(cc, p.get("curs") or cc)
    return list(res.values())


def camps_que_falten(p: dict | None) -> list[str]:
    return [c for c in ("tessitura",) + CAMPS_LLISTA if not (p or {}).get(c)]


def text_que_falta(instrument: str, curs: str, p: dict | None) -> str:
    clau, nom = _instrument(instrument)
    nom = _nom_instrument(clau, p) if p else nom
    falten = camps_que_falten(p)
    if not falten:
        return ""
    ll = [f"No tinc el perfil complet de {nom} per a «{curs}». Falta: " + "; ".join(PREGUNTA_CAMP[c] for c in falten) + ".",
          "Pregunta-ho a la persona, d'una cosa cada vegada, i desa cada resposta amb: "
          f"partitures nivell desa --instrument {clau} --curs \"{curs}\" --{falten[0]} \"...\""]
    if p is None:
        propis = cursos_coneguts(clau)
        altres = cursos_coneguts()
        if propis:
            ll.append("Cursos que ja conec per a este instrument: " + ", ".join(propis[:12]) + ". Si és un d'ells escrit d'una altra manera, usa'l tal com està.")
        elif altres:
            ll.append("Cursos que ja conec (d'altres instruments): " + ", ".join(altres[:12]) + ".")
        else:
            ll.append("Encara no conec cap curs.")
    return "\n".join(ll)


def desa(instrument: str, curs: str, camps: dict[str, str | None], substitueix: bool = False) -> list[str]:
    """Desa (fusiona) camps al perfil. Retorna les línies «abans → ara» que cal ensenyar."""
    clau_i, c = _clau_perfil(instrument, curs)
    nom_i = _instrument(instrument)[1]
    nous = {k: v for k, v in camps.items() if v is not None and str(v).strip()}
    if not nous:
        raise ErrorUsuari("No m'has dit cap dada per a desar. Pots usar --tessitura, --tonalitats, --figures, "
                          "--compassos, --articulacions o --notes.")
    validats = {k: valida_camp(k, v) for k, v in nous.items()}   # primer valida tot: si falla, no es desa res
    d = carrega()
    k = f"{clau_i}|{c}"
    p = d["perfils"].setdefault(k, {"instrument": clau_i, "curs": re.sub(r"\s+", " ", curs).strip(), "historial": []})
    if nom_i != _nom_instrument(clau_i):
        p["instrument_nom"] = nom_i      # instrument que no és del catàleg (làmines, veu...): es guarda tal com s'ha dit
    ll = []
    for camp, nou in validats.items():
        abans = p.get(camp)
        if camp in CAMPS_LLISTA and abans and not substitueix:
            ja = {norm(x) for x in abans}
            despres = abans + [x for x in nou if norm(x) not in ja]
        elif camp == "notes" and abans and not substitueix and norm(nou) not in norm(abans):
            despres = f"{abans}; {nou}"
        else:
            despres = nou
        if despres == abans:
            ll.append(f"{NOM_CAMP[camp]}: ja era així ({_text(despres)}).")
            continue
        p[camp] = despres
        p.setdefault("historial", []).append({"data": _avui(), "camp": camp, "abans": abans, "despres": despres})
        ll.append(f"{NOM_CAMP[camp]}: " + (f"abans {_text(abans)}, ara {_text(despres)}." if abans else f"desat {_text(despres)}."))
    p["actualitzat"] = _avui()
    _desa(d)
    cap = f"Perfil de {_nom_instrument(clau_i, p)} per a «{p['curs']}» (guardat a la carpeta de dades, no a la biblioteca):"
    falten = camps_que_falten(p)
    return [cap] + ll + ([f"Encara falta saber: {', '.join(NOM_CAMP[c] for c in falten)}."] if falten else [])


def _text(v) -> str:
    return ", ".join(v) if isinstance(v, list) else str(v)


def text_mostra(instrument: str | None = None, curs: str | None = None) -> str:
    propis = carrega()["perfils"]
    comuns = compartits()
    claus = sorted(set(propis) | set(comuns))
    filtre_i = _instrument(instrument)[0] if instrument else None
    filtre_c = normalitza_curs(curs) if curs else None
    ll = []
    for k in claus:
        ci, cc = k.split("|", 1)
        if (filtre_i and ci != filtre_i) or (filtre_c and filtre_c not in cc):
            continue
        p = perfil(ci, cc)
        if p is None:
            continue
        ll.append(f"{_nom_instrument(ci, p)}, {p['curs']}:")
        for camp in CAMPS:
            if p.get(camp):
                orig = p["origens"].get(camp)
                ll.append(f"  {NOM_CAMP[camp]}: {_text(p[camp])}" + (f"   (de la biblioteca: {orig})" if orig != "teu" else ""))
        falten = camps_que_falten(p)
        if falten:
            ll.append("  Falta saber: " + ", ".join(NOM_CAMP[c] for c in falten))
    if not ll:
        return ("Encara no sé res d'este nivell." if (filtre_i or filtre_c) else
                "Encara no he après cap nivell. Quan en necessite un, et preguntaré i ho desaré.")
    return "\n".join(ll)


def exporta(sol_licitada: str | None = None) -> Path:
    d = carrega()
    nets = {}
    for k, p in d["perfils"].items():
        nets[k] = {c: v for c, v in p.items() if c not in ("historial", "actualitzat")}
    ruta = rutes.eixida_per_defecte("nivells", "", extensio=".json", sol_licitada=sol_licitada)
    if not nets:
        raise ErrorUsuari("Encara no hi ha cap perfil per a exportar.")
    ruta.write_text(json.dumps({"versio": VERSIO, "perfils": nets}, ensure_ascii=False, indent=1), encoding="utf-8")
    return ruta


def esborra(instrument: str, curs: str, camp: str | None = None) -> str:
    """Esborra un camp d'un perfil o el perfil sencer (només del teu; el de la biblioteca no es toca).
    Abans, deixa còpia del fitxer com `nivells.json.anterior`."""
    clau_i, c = _clau_perfil(instrument, curs)
    d = carrega()
    k = f"{clau_i}|{c}"
    p = d["perfils"].get(k)
    if p is None:
        if k in compartits():
            raise ErrorUsuari("Este perfil és de la biblioteca compartida i no el puc esborrar des d'ací (la biblioteca és només de lectura).")
        raise ErrorUsuari("No tinc cap perfil d'este instrument i curs." + (
            " Cursos que conec: " + ", ".join(cursos_coneguts(clau_i)[:12]) + "." if cursos_coneguts(clau_i) else ""))
    try:
        shutil.copyfile(fitxer_nivells(), fitxer_nivells().with_name("nivells.json.anterior"))
    except OSError:
        pass
    nom = _nom_instrument(clau_i, p)
    if camp:
        if camp not in CAMPS:
            raise ErrorUsuari("El camp ha de ser un d'estos: " + ", ".join(CAMPS) + ".")
        if not p.get(camp):
            raise ErrorUsuari(f"El perfil no té «{NOM_CAMP[camp]}» desat.")
        abans = p.pop(camp)
        p.setdefault("historial", []).append({"data": _avui(), "camp": camp, "abans": abans, "despres": None})
        p["actualitzat"] = _avui()
        _desa(d)
        return f"He esborrat «{NOM_CAMP[camp]}» ({_text(abans)}) del perfil de {nom} per a «{p['curs']}»."
    del d["perfils"][k]
    _desa(d)
    return f"He esborrat el perfil de {nom} per a «{p['curs']}». (Còpia d'abans: nivells.json.anterior, a la carpeta de dades.)"


# --------------------------------------------------------------------------- preferències

def desa_preferencia(text: str) -> str:
    linia = re.sub(r"\s+", " ", str(text)).strip()
    if not linia:
        raise ErrorUsuari("Digues quina preferència vols desar, entre cometes.")
    if len(linia) > 400:
        raise ErrorUsuari("La preferència és massa llarga (màxim 400 lletres): divideix-la en dues.")
    ruta = fitxer_preferencies()
    ja = mostra_preferencies()
    if norm(linia) in norm(ja):
        return "Ja ho tenia desat."
    ruta.parent.mkdir(parents=True, exist_ok=True)
    nou = (ja if ja.strip() else "# Preferències\n").rstrip("\n") + f"\n- {_avui()}: {linia}\n"
    tmp = ruta.with_name(ruta.name + ".tmp")
    tmp.write_text(nou, encoding="utf-8")
    os.replace(tmp, ruta)
    return f"Desat: {linia}"


def mostra_preferencies() -> str:
    ruta = fitxer_preferencies()
    try:
        return ruta.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return ""
    except UnicodeDecodeError:
        aparta_malmes(ruta, "preferències")
        return ""
    except OSError as e:
        raise ErrorUsuari(f"No puc llegir el fitxer de preferències ({ruta}): {type(e).__name__}. No he canviat res.") from None


def text_preferencies() -> str:
    t = mostra_preferencies().strip()
    return t if t else "Encara no he après cap preferència."


def esborra_preferencia(text: str) -> str:
    """Esborra LA preferència que conté el text (si en conté més d'una, no esborra res i les mostra)."""
    q = norm(text)
    if len(q) < 3:
        raise ErrorUsuari("Digues unes quantes paraules de la preferència que vols esborrar.")
    linies = mostra_preferencies().splitlines()
    coincidents = [k for k, l in enumerate(linies) if l.startswith("- ") and q in norm(l)]
    if not coincidents:
        raise ErrorUsuari("No he trobat cap preferència amb eixes paraules. Les que tinc:\n" + text_preferencies())
    if len(coincidents) > 1:
        raise ErrorUsuari("Eixes paraules coincideixen amb més d'una preferència; sigues més concreta:\n"
                          + "\n".join(linies[k] for k in coincidents))
    ruta = fitxer_preferencies()
    try:
        shutil.copyfile(ruta, ruta.with_name("preferencies.md.anterior"))
    except OSError:
        pass
    esborrada = linies.pop(coincidents[0])
    tmp = ruta.with_name(ruta.name + ".tmp")
    tmp.write_text("\n".join(linies).rstrip("\n") + "\n", encoding="utf-8")
    os.replace(tmp, ruta)
    return f"He esborrat: {esborrada[2:]}"


# --------------------------------------------------------------------------- comprovació d'una partitura

_NOM_FIGURA = {v: k for k, v in _FIGURES.items()}


def _figura_de(n) -> str | None:
    t = n.duration.type
    nom = _NOM_FIGURA.get(t)
    if nom is None:
        return None
    if n.duration.tuplets:
        return "tresillo"
    return nom + (" amb puntet" if n.duration.dots else "")


def _figura_permesa(fig: str, permeses: set[str]) -> bool:
    if fig in permeses:
        return True
    if fig == "tresillo":
        return "tresillo" in permeses
    base = fig.replace(" amb puntet", "")
    return fig.endswith("amb puntet") and "puntet" in permeses and base in permeses


def comprova(instrument, curs: str, parts: list) -> dict:
    """Mira les parts d'un instrument contra el perfil del curs. `parts`: pentagrames (de music21) d'un mateix instrument."""
    from music21 import interval, key, meter, stream
    from . import musica
    p = perfil(instrument.clau, curs)
    res = {"curs": curs, "instrument": instrument.clau, "perfil": p is not None, "mancant": camps_que_falten(p), "problemes": [], "avis": []}
    if p is None:
        return res
    trans = instrument.semitons()
    inversa = interval.Interval(instrument.transposicio).reverse() if instrument.transposicio != "P1" else None

    def num(x):
        c = x.getContextByClass(stream.Measure)
        return c.number if c is not None else 0

    lo = hi = None
    if p.get("tessitura"):
        lo, hi = rang_midi(p["tessitura"])
    claus_ok = None
    if p.get("tonalitats"):
        claus_ok = set()
        for t in p["tonalitats"]:
            claus_ok |= alteracions_de_tonalitat(t)
    compassos_ok = {normalitza_compas(c) for c in p.get("compassos", [])} or None
    figures_ok = {normalitza_figura(f) for f in p.get("figures", [])} or None
    for part in parts:
        sons = musica.part_sonora(part)
        if lo is not None:
            for n in musica.notes_reals(sons):
                for pp in n.pitches:
                    w = pp.midi - trans
                    if w < lo:
                        res["problemes"].append({"compas": num(n), "tipus": "tessitura", "text": f"{nom_midi(w)} és més greu que {nom_midi(lo)}"})
                    elif w > hi:
                        res["problemes"].append({"compas": num(n), "tipus": "tessitura", "text": f"{nom_midi(w)} és més agut que {nom_midi(hi)}"})
        if claus_ok is not None:
            for ks in sons.recurse().getElementsByClass(key.KeySignature):
                escrita = ks.transpose(inversa) if inversa is not None else ks
                if escrita.sharps not in claus_ok:
                    res["problemes"].append({"compas": num(ks), "tipus": "tonalitat",
                                             "text": f"armadura de {abs(escrita.sharps)} {'sostinguts' if escrita.sharps > 0 else 'bemolls'} (escrita)"})
        if compassos_ok is not None:
            for ts in sons.recurse().getElementsByClass(meter.TimeSignature):
                if ts.ratioString not in compassos_ok:
                    res["problemes"].append({"compas": num(ts), "tipus": "compàs", "text": f"compàs {ts.ratioString}"})
        if figures_ok is not None:
            for n in sons.recurse().notes:
                f = _figura_de(n)
                if f and not _figura_permesa(f, figures_ok):
                    res["problemes"].append({"compas": num(n), "tipus": "figura", "text": f})
    if p.get("articulacions"):
        res["avis"].append("Articulacions del nivell: " + _text(p["articulacions"]) + " (això no ho comprove sola: mira-ho tu).")
    return res


def text_comprovacio(c: dict, maxim: int = 12) -> list[str]:
    ll = []
    if not c["perfil"]:
        return ["   " + x for x in text_que_falta(c["instrument"], c["curs"], None).splitlines()]
    if c["mancant"]:
        ll += ["   " + x for x in text_que_falta(c["instrument"], c["curs"], {k: 1 for k in CAMPS if k not in c["mancant"]}).splitlines()]
    # agrupa duplicats (mateix compàs i text)
    vists, uniques = set(), []
    for pr in sorted(c["problemes"], key=lambda x: (str(x["compas"]).zfill(5), x["tipus"])):
        clau = (pr["compas"], pr["tipus"], pr["text"])
        if clau not in vists:
            vists.add(clau)
            uniques.append(pr)
    if not uniques:
        ll.append(f"   Nivell «{c['curs']}»: tot dins del que sé d'este curs." if not c["mancant"] else
                  f"   Nivell «{c['curs']}»: res fora del que sé (però no ho he pogut comprovar tot).")
    else:
        ll.append(f"   Nivell «{c['curs']}»: {len(uniques)} coses per damunt del nivell:")
        for pr in uniques[:maxim]:
            ll.append(f"   - compàs {pr['compas']}: {pr['text']} ({pr['tipus']})")
        if len(uniques) > maxim:
            ll.append(f"   ... i {len(uniques) - maxim} més.")
    ll += [f"   {a}" for a in c["avis"]]
    return ll


def avisos_cerca(reg: dict, curs: str) -> list[str]:
    """Per a `biblioteca cerca --nivell`: parts de l'índex que passen de la tessitura desada per a eixe curs."""
    res = []
    for part in reg.get("parts", []):
        if not part.get("instrument") or not part.get("mes_greu"):
            continue
        try:
            i = inst.obtenir(part["instrument"])
            p = perfil(i.clau, curs)
            if not p or not p.get("tessitura"):
                continue
            lo, hi = rang_midi(p["tessitura"])
            t = i.semitons()
            g, a = nota_a_midi(part["mes_greu"]) - t, nota_a_midi(part["mes_agut"]) - t
        except ErrorUsuari:
            continue
        if g < lo or a > hi:
            res.append(f"Ull: {part['nom']} va de {nom_midi(g)} a {nom_midi(a)} (escrit) i el perfil de {curs} és {p['tessitura']}")
    return res
