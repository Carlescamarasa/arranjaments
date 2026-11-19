"""Operacions musicals deterministes sobre partitures (música21)."""
from __future__ import annotations

import copy
import re
from pathlib import Path

from music21 import clef, converter, corpus, harmony, interval, key, layout, metadata, meter, note, pitch, stream, tempo

from . import instruments as inst
from .errors import ErrorUsuari

EXT_MUSICXML = {".musicxml", ".xml", ".mxl"}
EXT_ACCEPTADES = EXT_MUSICXML | {".mid", ".midi", ".mscx", ".mscz", ".abc", ".krn"}


# --------------------------------------------------------------------------- càrrega

def carregar(ruta: str | Path) -> stream.Score:
    ruta = Path(ruta).expanduser()
    if not ruta.exists():
        raise ErrorUsuari(f"No trobe el fitxer «{ruta}». Comprova el nom i que estiga en la carpeta entrada/.")
    ext = ruta.suffix.lower()
    if ext == ".pdf" or ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        raise ErrorUsuari(
            "Això és un PDF o una imatge, no una partitura editable. "
            "Primer cal convertir-la amb l'ordre «importar» (i revisar el resultat amb MuseScore)."
        )
    try:
        obj = converter.parse(str(ruta))
    except Exception as e:  # music21 llança errors de molts tipus
        raise ErrorUsuari(f"No he pogut llegir «{ruta.name}» com a partitura ({type(e).__name__}). "
                          "Prova d'obrir-lo amb MuseScore i desar-lo de nou com a MusicXML.") from e
    if isinstance(obj, stream.Opus):
        obj = obj.scores[0]
    if not isinstance(obj, stream.Score):
        s = stream.Score()
        s.insert(0, obj if isinstance(obj, stream.Part) else _a_part(obj))
        obj = s
    if not obj.parts:
        raise ErrorUsuari(f"«{ruta.name}» no té cap pentagrama (part) llegible.")
    _netejar_metadades(obj, ruta)
    return obj


def _netejar_metadades(score: stream.Score, ruta: Path) -> None:
    """Evita títols tipus «fitxer.mxl» i el compositor fals «Music21» que posa la llibreria."""
    if score.metadata is None:
        score.metadata = metadata.Metadata()
    md = score.metadata
    titols = [md.title or "", md.movementName or ""]
    if all(not t or t.lower().endswith(tuple(EXT_ACCEPTADES)) for t in titols):
        nou = re.sub(r"[-_]+", " ", ruta.stem).strip() or ruta.stem
        md.title = nou
        md.movementName = nou
    elif md.movementName and md.movementName.lower().endswith(tuple(EXT_ACCEPTADES)):
        md.movementName = md.title
    if (md.composer or "").lower() == "music21":
        md.composer = ""


def _a_part(flux) -> stream.Part:
    p = stream.Part()
    p.append(flux)
    return p


def desar(score: stream.Score, ruta: str | Path) -> Path:
    """Escriu el MusicXML a una ruta ja validada per `rutes` (que és qui evita sobreescriure)."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if ruta.suffix.lower() not in EXT_MUSICXML:
        ruta = ruta.with_suffix(".musicxml")
    score.write("musicxml", fp=str(ruta))
    return ruta


# --------------------------------------------------------------------------- noms de nota i text

CONVENCIO = "Els noms de nota segueixen la convenció espanyola: el Do central és Do3."
_SOLFEIG = {"C": "Do", "D": "Re", "E": "Mi", "F": "Fa", "G": "Sol", "A": "La", "B": "Si"}


def nom_alteracio(p: pitch.Pitch) -> str:
    """Nom de la nota sense octava, en solfeig: Do, Fa#, Sib..."""
    alt = p.accidental.modifier if p.accidental is not None else ""
    return _SOLFEIG[p.step] + alt.replace("-", "b")


def nom_nota(x) -> str:
    """Nota en solfeig amb octava espanyola (Do central = Do3). Accepta pitch, nom music21 o número MIDI."""
    p = x if isinstance(x, pitch.Pitch) else pitch.Pitch(x)
    return f"{nom_alteracio(p)}{p.implicitOctave - 1}"


def _curt(text, maxim: int = 60) -> str:
    """Text d'una partitura (títol, nom de part) en una sola línia i curt: és dada, mai instrucció."""
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    return t if len(t) <= maxim else t[: maxim - 3].rstrip() + "..."


# --------------------------------------------------------------------------- parts i unitats

def notes_reals(flux) -> list:
    """Notes i acords de debò: sense símbols d'acord (C7, Dm...) ni notes sense altura."""
    return [n for n in flux.recurse().notes
            if not isinstance(n, (harmony.Harmony, note.Unpitched)) and getattr(n, "pitches", None)]


def altures(flux) -> list[pitch.Pitch]:
    return [p for n in notes_reals(flux) for p in n.pitches]


def nom_part(part: stream.Part, i: int) -> str:
    n = part.partName
    if not n:
        ins = part.getInstrument(returnDefault=False)
        n = getattr(ins, "instrumentName", None) if ins else None
    return n or f"Part {i + 1}"


def unitats(score: stream.Score) -> list[list[int]]:
    """Agrupa els pentagrames que són UN sol instrument (piano: dos pentagrames amb clau).

    Retorna llistes d'índexs de `score.parts`. Els números que veu la persona (1, 2, 3...) són les unitats.
    """
    parts = list(score.parts)
    pos = {id(p): i for i, p in enumerate(parts)}
    grup_de: dict[int, list[int]] = {}
    for sg in score.recurse().getElementsByClass(layout.StaffGroup):
        idx = sorted(pos[id(e)] for e in sg.getSpannedElements() if id(e) in pos)
        if len(idx) > 1 and all(isinstance(parts[k], stream.PartStaff) for k in idx):
            for k in idx:
                grup_de[k] = idx
    res: list[list[int]] = []
    vistos: set[int] = set()
    for i in range(len(parts)):
        if i in vistos:
            continue
        g = grup_de.get(i, [i])
        vistos.update(g)
        res.append(list(g))
    return res


def triar_parts(score: stream.Score, seleccio: str | None) -> list[int]:
    """Converteix «1,3» o «trompeta» en índexs de `score.parts` (0-based). Sense selecció, totes."""
    us = unitats(score)
    n = len(us)
    if not seleccio:
        return [k for u in us for k in u]
    seleccionades: list[int] = []
    for tros in re.split(r"[,;]\s*", seleccio.strip()):
        if not tros:
            continue
        if tros.isdigit():
            k = int(tros)
            if not 1 <= k <= n:
                raise ErrorUsuari(f"La part {k} no existeix: la partitura en té {n} (numerades de 1 a {n}).")
            seleccionades.append(k - 1)
        else:
            t = inst._norm(tros)
            trobades = [j for j, u in enumerate(us) if t in inst._norm(nom_part(score.parts[u[0]], u[0]))]
            if not trobades:
                raise ErrorUsuari(f"No trobe cap part que es diga «{tros}». Mira els noms amb l'ordre «info».")
            seleccionades += trobades
    return [k for j in seleccionades for k in us[j]]


def part_sonora(part: stream.Part) -> stream.Part:
    """Còpia de la part en altura REAL (concert). Si ja ho és, còpia sense canvis."""
    c = copy.deepcopy(part)
    ins = c.getInstrument(returnDefault=False)
    if c.atSoundingPitch is False and ins is not None and ins.transposition is not None:
        c.toSoundingPitch(inPlace=True)
    return c


def _semitons_transposicio(part: stream.Part) -> int:
    ins = part.getInstrument(returnDefault=False)
    if ins is not None and ins.transposition is not None:
        return int(ins.transposition.semitones)
    return 0


def _parse_assignacions(text: str | None) -> dict[int, str]:
    """«1=trompeta-sib,2=trompeta-sib,3=trompa-fa» → {0:'trompeta-sib',...}."""
    if not text:
        return {}
    res = {}
    for tros in re.split(r"[,;]\s*", text.strip()):
        if not tros:
            continue
        if "=" not in tros:
            raise ErrorUsuari(f"No entenc «{tros}». El format és número=instrument, per exemple 1=trompeta-sib,3=trompa-fa.")
        a, b = tros.split("=", 1)
        if not a.strip().isdigit():
            raise ErrorUsuari(f"Davant del signe = cal el número de la part, no «{a}».")
        res[int(a) - 1] = b.strip()
    return res


def _unitat(score: stream.Score, num0: int) -> list[int]:
    us = unitats(score)
    if not 0 <= num0 < len(us):
        raise ErrorUsuari(f"La part {num0 + 1} no existeix: la partitura en té {len(us)}.")
    return us[num0]


def parts_separades(score: stream.Score) -> list[tuple[str, stream.Score]]:
    """Una partitura per cada instrument (el piano, amb els dos pentagrames). Per a exportar les parts."""
    res = []
    for num, u in enumerate(unitats(score)):
        s = stream.Score()
        s.metadata = copy.deepcopy(score.metadata)
        copies = [copy.deepcopy(score.parts[k]) for k in u]
        for c in copies:
            s.insert(0, c)
        if len(copies) > 1:
            s.insert(0, layout.StaffGroup(copies, symbol="brace"))
        res.append((nom_part(score.parts[u[0]], u[0]), s))
    return res


# --------------------------------------------------------------------------- info

_MODES = {"major": "major", "minor": "menor", "dorian": "dòric", "phrygian": "frigi", "lydian": "lidi",
          "mixolydian": "mixolidi", "locrian": "locri"}


def _nom_tonalitat(ks) -> str:
    """Tonalitat llegible. Si el fitxer no diu el mode, no s'inventa: es donen les dues possibilitats."""
    def tonica(k):
        return nom_alteracio(k.tonic)
    mode = getattr(ks, "mode", None)
    if isinstance(ks, key.Key) and mode:
        return f"{tonica(ks)} {_MODES.get(mode, mode)}"
    n = ks.sharps
    if n == 0:
        q = "sense alteracions"
    elif n > 0:
        q = f"{n} sostingut" + ("s" if n > 1 else "")
    else:
        q = f"{-n} bemoll" + ("s" if n < -1 else "")
    return f"{q} ({tonica(ks.asKey('major'))} major o {tonica(ks.asKey('minor'))} menor)"


def _tonalitat_sonora(score: stream.Score):
    """Primera armadura de la partitura, llegida en so real (concert), no en l'altura escrita d'un transpositor."""
    for p in score.parts:
        ks = part_sonora(p).recurse().getElementsByClass(key.KeySignature)
        if len(ks):
            return ks[0]
    return None


def info(score: stream.Score) -> dict:
    md = score.metadata
    titol = _curt(md.title) if md and md.title else None
    compositor = _curt(md.composer) if md and md.composer else None
    parts = []
    for num, u in enumerate(unitats(score)):
        p = score.parts[u[0]]
        ins = p.getInstrument(returnDefault=False)
        nom = nom_part(p, u[0])
        det = inst.detectar(f"{nom} {getattr(ins, 'instrumentName', '') or ''}",
                            _semitons_transposicio(p) if ins is not None and ins.transposition else None)
        mids = [x.midi for k in u for x in altures(part_sonora(score.parts[k]))]
        n_notes = sum(len(notes_reals(score.parts[k])) for k in u)
        parts.append({
            "numero": num + 1,
            "nom": _curt(nom),
            "pentagrames": len(u),
            "instrument_detectat": det.clau if det else None,
            "transposicio": str(ins.transposition) if ins is not None and ins.transposition else None,
            "escrit_en_altura": "escrita (transpositor)" if p.atSoundingPitch is False and ins is not None
            and ins.transposition else "real (concert)",
            "compassos": len(p.getElementsByClass(stream.Measure)),
            "notes": n_notes,
            "mes_greu": nom_nota(min(mids)) if mids else None,
            "mes_agut": nom_nota(max(mids)) if mids else None,
        })
    ks = _tonalitat_sonora(score)
    compassos = score.recurse().getElementsByClass(meter.TimeSignature)
    tempos = score.recurse().getElementsByClass(tempo.MetronomeMark)
    return {
        "titol": titol,
        "compositor": compositor,
        "tonalitat": _nom_tonalitat(ks) if ks is not None else None,
        "compas": compassos[0].ratioString if len(compassos) else None,
        "tempo": (tempos[0].number if len(tempos) and tempos[0].number else None),
        "convencio_notes": CONVENCIO,
        "parts": parts,
    }


def text_info(d: dict) -> str:
    ll = [f"Títol: {d['titol'] or '(sense títol)'}"]
    if d["compositor"]:
        ll.append(f"Compositor: {d['compositor']}")
    ll.append(f"Tonalitat: {d['tonalitat'] or 'no indicada'}   Compàs: {d['compas'] or 'no indicat'}"
              + (f"   Tempo: {d['tempo']}" if d["tempo"] else ""))
    ll.append(f"Parts: {len(d['parts'])}")
    for p in d["parts"]:
        ins = f", instrument detectat: {p['instrument_detectat']}" if p["instrument_detectat"] else ", instrument sense identificar"
        ll.append(f"  {p['numero']}. {p['nom']}{ins}")
        ll.append(f"     {p['compassos']} compassos, {p['notes']} notes; més greu {p['mes_greu']}, "
                  f"més agut {p['mes_agut']} (so real); altura {p['escrit_en_altura']}")
    ll.append(d["convencio_notes"])
    return "\n".join(ll)


# --------------------------------------------------------------------------- transport

def transportar(score: stream.Score, semitons: int | None = None, interval_nom: str | None = None,
                octaves: int = 0, parts: str | None = None) -> stream.Score:
    if semitons is None and not interval_nom and not octaves:
        raise ErrorUsuari("Cal dir quant transportar: --semitons, --interval o --octava.")
    try:
        iv = interval.Interval(interval_nom) if interval_nom else interval.Interval(semitons or 0)
    except Exception as e:
        raise ErrorUsuari(f"No entenc l'interval «{interval_nom}». Exemples: M2 (segona major amunt), "
                          "m-3 (tercera menor avall), P-5 (quinta justa avall).") from e
    sel = triar_parts(score, parts)
    res = copy.deepcopy(score)
    for i in sel:
        p = res.parts[i]
        if semitons is not None or interval_nom:
            p.transpose(iv, inPlace=True)
        if octaves:
            p.transpose(12 * octaves, inPlace=True)
    return res


# --------------------------------------------------------------------------- assignar

def assignar(score: stream.Score, assignacions: str) -> tuple[stream.Score, list[str]]:
    mapa = _parse_assignacions(assignacions)
    if not mapa:
        raise ErrorUsuari("No m'has dit cap assignació. Exemple: --assigna \"1=trompeta-sib,2=trompeta-sib,3=trompa-fa,4=trombo\".")
    res = copy.deepcopy(score)
    avisos = []
    for num0, clau in mapa.items():
        unitat = _unitat(res, num0)
        i = inst.obtenir(clau)
        for k in unitat:
            part = res.parts[k]
            # 1) portar la part a altura real (concert)
            vella = part.getInstrument(returnDefault=False)
            if part.atSoundingPitch is False and vella is not None and vella.transposition is not None:
                part.toSoundingPitch(inPlace=True)
            # 2) canviar instrument
            for x in list(part.recurse().getElementsByClass("Instrument")):
                x.activeSite.remove(x)
            obj = inst.crear_objecte_music21(i)
            part.insert(0, obj)
            part.partName = i.nom
            part.partAbbreviation = i.nom
            part.atSoundingPitch = True
            # 3) escriure en altura escrita
            if obj.transposition is not None:
                part.toWrittenPitch(inPlace=True)
            if len(unitat) == 1:
                _posar_clau(part, i)
        avisos.append(f"Part {num0 + 1}: ara és {i.nom}")
    return res, avisos


def _clau_de(i: inst.Instrument, part: stream.Part) -> clef.Clef:
    if i.clef == "bass":
        return clef.BassClef()
    if i.clef == "alto":
        return clef.AltoClef()
    if i.clef == "treble":
        return clef.TrebleClef()
    flux = part.flatten()
    return clef.bestClef(flux, recurse=True) if len(flux.notes) else clef.TrebleClef()


def _posar_clau(part: stream.Part, i: inst.Instrument) -> None:
    for c in list(part.recurse().getElementsByClass(clef.Clef)):
        c.activeSite.remove(c)
    primer = part.getElementsByClass(stream.Measure).first()
    (primer if primer is not None else part).insert(0, _clau_de(i, part))


# --------------------------------------------------------------------------- tessitura

def tessitura(score: stream.Score, assignacions: str | None = None, curs: str | None = None) -> dict:
    forcades = _parse_assignacions(assignacions)
    resultats = []
    for num, u in enumerate(unitats(score)):
        p = score.parts[u[0]]
        nom = nom_part(p, u[0])
        ins_m21 = p.getInstrument(returnDefault=False)
        escrit = (p.atSoundingPitch is False and ins_m21 is not None and ins_m21.transposition is not None)
        clau = forcades.get(num)
        if clau:
            instr = inst.obtenir(clau)
        else:
            instr = inst.detectar(f"{nom} {getattr(ins_m21, 'instrumentName', '') or ''}",
                                  _semitons_transposicio(p) if escrit else None)
        if instr is None:
            resultats.append({"numero": num + 1, "nom": _curt(nom), "instrument": None, "problemes": [],
                              "avis": "No sé quin instrument és. Indica-ho amb --instruments \"%d=trompeta-sib\" "
                                      "(o usa l'ordre «instruments» per assignar-lo)." % (num + 1)})
            continue
        trans = instr.semitons()
        ab_lo, ab_hi = inst.rang_midi(instr.abast)
        co_lo, co_hi = inst.rang_midi(instr.comoda)
        problemes = []
        total = fora = incomodes = 0
        escrits = []
        for k in u:
            sons = part_sonora(score.parts[k])
            for n in notes_reals(sons):
                for pp in n.pitches:
                    total += 1
                    w = pp.midi - trans   # altura escrita
                    escrits.append(w)
                    comp = n.getContextByClass(stream.Measure)
                    numc = comp.number if comp is not None else "?"
                    nom_w = nom_nota(w)
                    if w < ab_lo:
                        fora += 1
                        problemes.append({"compas": numc, "nota_escrita": nom_w, "tipus": "massa greu"})
                    elif w > ab_hi:
                        fora += 1
                        problemes.append({"compas": numc, "nota_escrita": nom_w, "tipus": "massa aguda"})
                    elif w < co_lo or w > co_hi:
                        incomodes += 1
                        problemes.append({"compas": numc, "nota_escrita": nom_w,
                                          "tipus": "zona incòmoda (greu)" if w < co_lo else "zona incòmoda (aguda)"})
        resultats.append({
            "numero": num + 1, "nom": _curt(nom), "instrument": instr.clau, "instrument_nom": instr.nom,
            "abast": [nom_nota(x) for x in instr.abast], "comoda": [nom_nota(x) for x in instr.comoda],
            "notes": total, "fora_abast": fora, "incomodes": incomodes,
            "escrit_min": nom_nota(min(escrits)) if escrits else None,
            "escrit_max": nom_nota(max(escrits)) if escrits else None,
            "problemes": problemes, "avis": None,
        })
        if curs:
            from . import nivells
            resultats[-1]["nivell"] = nivells.comprova(instr, curs, [score.parts[k] for k in u])
    return {"convencio_notes": CONVENCIO,
            "nota": "Els límits de cada instrument són orientatius (de manual): decideix qui coneix l'instrument.",
            "parts": resultats}


def text_tessitura(d: dict, maxim_detall: int = 12) -> str:
    ll = [d["convencio_notes"], d["nota"]]
    for r in d["parts"]:
        if r["instrument"] is None:
            ll.append(f"{r['numero']}. {r['nom']}: {r['avis']}")
            continue
        ll.append(f"{r['numero']}. {r['nom']}: "
                  f"{'' if r['instrument_nom'] == r['nom'] else r['instrument_nom'] + ', '}escrit de {r['escrit_min']} a {r['escrit_max']}; "
                  f"abast pràctic (orientatiu) {r['abast'][0]}-{r['abast'][1]}, "
                  f"zona còmoda {r['comoda'][0]}-{r['comoda'][1]}")
        if not r["problemes"]:
            ll.append("   Tot dins de la zona còmoda.")
            ll += _text_nivell(r)
            continue
        ll.append(f"   {r['fora_abast']} notes FORA d'abast i {r['incomodes']} en zona incòmoda (de {r['notes']}).")
        for pr in sorted(r["problemes"], key=lambda x: (x["tipus"].startswith("zona"), str(x["compas"]).zfill(5)))[:maxim_detall]:
            ll.append(f"   - compàs {pr['compas']}: {pr['nota_escrita']} ({pr['tipus']})")
        if len(r["problemes"]) > maxim_detall:
            ll.append(f"   ... i {len(r['problemes']) - maxim_detall} més.")
        ll += _text_nivell(r)
    return "\n".join(ll)


def _text_nivell(r: dict) -> list[str]:
    if not r.get("nivell"):
        return []
    from . import nivells
    return nivells.text_comprovacio(r["nivell"])


# --------------------------------------------------------------------------- reducció

def reduir(score: stream.Score, mantindre: str | None = None) -> stream.Score:
    if not mantindre:
        raise ErrorUsuari("Digues quines parts vols conservar: --mantin \"1,3\".")
    sel = set(triar_parts(score, mantindre))
    res = stream.Score()
    res.metadata = copy.deepcopy(score.metadata) if score.metadata else metadata.Metadata()
    for u in unitats(score):
        triades = [k for k in u if k in sel]
        if not triades:
            continue
        copies = [copy.deepcopy(score.parts[k]) for k in triades]
        for c in copies:
            res.insert(0, c)
        if len(copies) > 1:
            res.insert(0, layout.StaffGroup(copies, symbol="brace"))
    return res


# --------------------------------------------------------------------------- corpus

def cercar_corpus(text: str) -> list[dict]:
    """Cerca al corpus de music21 per títol, compositor o nom de fitxer (sense accents ni majúscules)."""
    paraules = [w for w in re.split(r"[^\w.#]+", inst._norm(text)) if w]
    if not paraules:
        return []
    res = []
    for e in corpus.corpora.CoreCorpus().metadataBundle:
        md = e.metadata
        ruta = Path(str(e.sourcePath)).as_posix()
        titol = getattr(md, "title", None) or ""
        compositor = getattr(md, "composer", None) or ""
        pallar = inst._norm(f"{titol} {compositor} {ruta}")
        if all(w in pallar for w in paraules):
            res.append({"titol": titol or Path(ruta).stem, "compositor": compositor or None, "ruta": ruta})
    return res
