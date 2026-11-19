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
from pathlib import Path

from . import instruments as inst
from . import rutes
from .errors import ErrorUsuari

VERSIO = 1
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
_RE_NOTA = re.compile(r"^(do|re|mi|fa|sol|la|si)\s*(#{1,2}|b{1,2})?\s*(-?\d)$")


def nota_a_midi(text: str) -> int:
    """«Do3» (Do central = Do3) a número MIDI. Només solfeig."""
    m = _RE_NOTA.match(inst._norm(str(text)).replace(" ", ""))
    if not m:
        raise ErrorUsuari(f"No entenc la nota «{text}». Escriu-la en solfeig amb l'octava, com Do3, Fa#2 o Sib3 "
                          "(el Do central és Do3).")
    lletra, alt, octava = _SOLFEIG[m.group(1)], (m.group(2) or "").replace("b", "-"), int(m.group(3)) + 1
    from music21 import pitch
    return pitch.Pitch(f"{lletra}{alt}{octava}").midi


def nom_midi(midi: int) -> str:
    from .musica import nom_nota
    return nom_nota(midi)


def normalitza_tessitura(text: str) -> str:
    """«do3 a SOL4» → «Do3-Sol4» (la més greu primer)."""
    parts = re.split(r"\s*(?:-|–|a|fins|\ba\b)\s*(?=[a-zA-Z])", str(text).strip(), maxsplit=1)
    if len(parts) != 2:
        trossos = re.findall(r"[A-Za-z]+\s*[#b]{0,2}\s*-?\d", str(text))
        parts = trossos if len(trossos) == 2 else parts
    if len(parts) != 2:
        raise ErrorUsuari(f"No entenc la tessitura «{text}». Escriu la nota més greu i la més aguda, per exemple Do3-Sol4.")
    lo, hi = sorted((nota_a_midi(parts[0]), nota_a_midi(parts[1])))
    return f"{nom_midi(lo)}-{nom_midi(hi)}"


def rang_midi(text: str) -> tuple[int, int]:
    lo, hi = normalitza_tessitura(text).split("-")
    return nota_a_midi(lo), nota_a_midi(hi)


_RE_FINS = re.compile(r"^fins a (\d)\s*(alteracions|alteracio|sostenits|sostinguts|bemolls)?$")
_MODES = {"major": "major", "mayor": "major", "menor": "minor"}


def alteracions_de_tonalitat(text: str) -> set[int]:
    """Tonalitat d'un perfil → conjunt de nombres d'alteracions (sostinguts positiu, bemolls negatiu)."""
    n = norm(text)
    if n in ("sense alteracions", "sense armadura", "cap alteracio"):
        return {0}
    m = _RE_FINS.match(n)
    if m:
        k = int(m.group(1))
        if m.group(2) in ("sostenits", "sostinguts"):
            return set(range(0, k + 1))
        if m.group(2) == "bemolls":
            return set(range(-k, 1))
        return set(range(-k, k + 1))
    m = re.match(r"^(do|re|mi|fa|sol|la|si)\s*(#|b)?\s+(major|mayor|menor)$", n)
    if m:
        from music21 import key
        alt = {"#": "#", "b": "-", None: ""}[m.group(2)]
        return {key.Key(_SOLFEIG[m.group(1)] + alt, _MODES[m.group(3)]).sharps}
    raise ErrorUsuari(f"No entenc la tonalitat «{text}». Exemples: «Do major», «La menor», «Sib major», «fins a 2 alteracions», "
                      "«sense alteracions».")


def normalitza_compas(text: str) -> str:
    m = re.match(r"^\s*(\d{1,2})\s*/\s*(\d{1,2})\s*$", str(text))
    if not m:
        raise ErrorUsuari(f"No entenc el compàs «{text}». Escriu-lo com 2/4, 3/4, 4/4 o 6/8.")
    return f"{int(m.group(1))}/{int(m.group(2))}"


_FIGURES = {"rodona": "whole", "blanca": "half", "negra": "quarter", "corxera": "eighth", "semicorxera": "16th",
            "fusa": "32nd"}
_SINONIMS = {"redona": "rodona", "croma": "corxera", "semicroma": "semicorxera", "tresillos": "tresillo",
             "tresillo": "tresillo", "tercet": "tresillo", "tercets": "tresillo", "puntets": "puntet", "puntillo": "puntet"}


def normalitza_figura(text: str) -> str:
    n = norm(text)
    base = re.sub(r"\s+(amb|con)\s+(puntet|puntillo)$", "", n)
    puntet = base != n
    base = _SINONIMS.get(base, base)
    if base in ("puntet", "tresillo"):
        return base
    if base not in _FIGURES:
        raise ErrorUsuari(f"No conec la figura «{text}». Pots dir: rodona, blanca, negra, corxera, semicorxera, fusa, "
                          "«negra amb puntet» (o «corxera amb puntet»...), puntet, tresillo.")
    return base + (" amb puntet" if puntet else "")


def _llista(valor: str | None) -> list[str]:
    return [t.strip() for t in re.split(r"[,;]", valor or "") if t.strip()]


def valida_camp(camp: str, valor: str):
    """Valida i normalitza un camp del perfil. Retorna text (tessitura, notes) o llista."""
    if camp == "tessitura":
        return normalitza_tessitura(valor)
    if camp == "notes":
        return re.sub(r"\s+", " ", str(valor)).strip()[:500]
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


# --------------------------------------------------------------------------- emmagatzematge

def _llig(ruta: Path) -> dict:
    try:
        d = json.loads(ruta.read_text(encoding="utf-8-sig"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def carrega() -> dict:
    d = _llig(fitxer_nivells())
    d.setdefault("versio", VERSIO)
    d.setdefault("perfils", {})
    return d


def _desa(d: dict) -> None:
    ruta = fitxer_nivells()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(ruta.name + ".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, ruta)


def _clau_perfil(instrument: str, curs: str) -> tuple[str, str]:
    i = inst.obtenir(instrument)
    c = norm(curs)
    if not c:
        raise ErrorUsuari("Falta el curs (per exemple --curs \"4t elemental\").")
    return i.clau, c


def compartits() -> dict[str, dict]:
    """Perfils compartits de la carpeta `nivells/` de la biblioteca (només lectura), si n'hi ha."""
    try:
        from . import biblioteca as bib
        arrel = bib.localitzar()["ruta"]
        if arrel is None or not (arrel / "nivells").is_dir():
            return {}
        res: dict[str, dict] = {}
        for f in sorted((arrel / "nivells").glob("*.json")):
            if f.stat().st_size > 2_000_000:
                continue
            for k, p in _llig(f).get("perfils", {}).items():
                if isinstance(p, dict):
                    res.setdefault(k, dict(p, _origen=f"nivells/{f.name}"))
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
    for camp in CAMPS:
        for font, nom in ((propi, "teu"), (comu, comu and comu.get("_origen"))):
            if font and font.get(camp):
                res[camp] = font[camp]
                res["origens"][camp] = nom
                break
    return res


def camps_que_falten(p: dict | None) -> list[str]:
    return [c for c in ("tessitura",) + CAMPS_LLISTA if not (p or {}).get(c)]


def text_que_falta(instrument: str, curs: str, p: dict | None) -> str:
    i = inst.obtenir(instrument)
    falten = camps_que_falten(p)
    if not falten:
        return ""
    ll = [f"No tinc el perfil complet de {i.nom} per a «{curs}». Falta: " + "; ".join(PREGUNTA_CAMP[c] for c in falten) + ".",
          "Pregunta-ho a la persona, d'una cosa cada vegada, i desa cada resposta amb: "
          f"partitures nivell desa --instrument {i.clau} --curs \"{curs}\" --{falten[0]} \"...\""]
    return "\n".join(ll)


def desa(instrument: str, curs: str, camps: dict[str, str | None], substitueix: bool = False) -> list[str]:
    """Desa (fusiona) camps al perfil. Retorna les línies «abans → ara» que cal ensenyar."""
    clau_i, c = _clau_perfil(instrument, curs)
    nous = {k: v for k, v in camps.items() if v is not None and str(v).strip()}
    if not nous:
        raise ErrorUsuari("No m'has dit cap dada per a desar. Pots usar --tessitura, --tonalitats, --figures, "
                          "--compassos, --articulacions o --notes.")
    validats = {k: valida_camp(k, v) for k, v in nous.items()}   # primer valida tot: si falla, no es desa res
    d = carrega()
    k = f"{clau_i}|{c}"
    p = d["perfils"].setdefault(k, {"instrument": clau_i, "curs": re.sub(r"\s+", " ", curs).strip(), "historial": []})
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
    i = inst.obtenir(instrument)
    cap = f"Perfil de {i.nom} per a «{p['curs']}» (guardat a la carpeta de dades, no a la biblioteca):"
    falten = camps_que_falten(p)
    return [cap] + ll + ([f"Encara falta saber: {', '.join(NOM_CAMP[c] for c in falten)}."] if falten else [])


def _text(v) -> str:
    return ", ".join(v) if isinstance(v, list) else str(v)


def text_mostra(instrument: str | None = None, curs: str | None = None) -> str:
    propis = carrega()["perfils"]
    comuns = compartits()
    claus = sorted(set(propis) | set(comuns))
    filtre_i = inst.obtenir(instrument).clau if instrument else None
    filtre_c = norm(curs) if curs else None
    ll = []
    for k in claus:
        ci, cc = k.split("|", 1)
        if (filtre_i and ci != filtre_i) or (filtre_c and filtre_c not in cc):
            continue
        p = perfil(ci, cc)
        if p is None:
            continue
        ll.append(f"{inst.obtenir(ci).nom}, {p['curs']}:")
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
    try:
        return fitxer_preferencies().read_text(encoding="utf-8-sig")
    except OSError:
        return ""


def text_preferencies() -> str:
    t = mostra_preferencies().strip()
    return t if t else "Encara no he après cap preferència."


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
