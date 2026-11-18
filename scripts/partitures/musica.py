"""Operacions musicals deterministes sobre partitures (música21)."""
from __future__ import annotations

import copy
import re
from pathlib import Path

from music21 import clef, converter, interval, key, layout, meter, metadata, note, pitch, stream, tempo

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
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if ruta.suffix.lower() not in EXT_MUSICXML:
        ruta = ruta.with_suffix(".musicxml")
    score.write("musicxml", fp=str(ruta))
    return ruta


# --------------------------------------------------------------------------- parts

def nom_part(part: stream.Part, i: int) -> str:
    n = part.partName
    if not n:
        ins = part.getInstrument(returnDefault=False)
        n = getattr(ins, "instrumentName", None) if ins else None
    return n or f"Part {i + 1}"


def triar_parts(score: stream.Score, seleccio: str | None) -> list[int]:
    """Converteix «1,3» o «trompeta» en índexs (0-based). Sense selecció, totes."""
    n = len(score.parts)
    if not seleccio:
        return list(range(n))
    índexs: list[int] = []
    for tros in re.split(r"[,;]\s*", seleccio.strip()):
        if not tros:
            continue
        if tros.isdigit():
            k = int(tros)
            if not 1 <= k <= n:
                raise ErrorUsuari(f"La part {k} no existeix: la partitura en té {n} (numerades de 1 a {n}).")
            índexs.append(k - 1)
        else:
            t = inst._norm(tros)
            trobades = [i for i, p in enumerate(score.parts) if t in inst._norm(nom_part(p, i))]
            if not trobades:
                raise ErrorUsuari(f"No trobe cap part que es diga «{tros}». Mira els noms amb l'ordre «info».")
            índexs += trobades
    return índexs


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


# --------------------------------------------------------------------------- info

def info(score: stream.Score) -> dict:
    md = score.metadata
    titol = (md.title if md and md.title else None) or None
    compositor = (md.composer if md and md.composer else None) or None
    parts = []
    for i, p in enumerate(score.parts):
        ins = p.getInstrument(returnDefault=False)
        det = inst.detectar(f"{nom_part(p, i)} {getattr(ins, 'instrumentName', '') or ''}",
                            _semitons_transposicio(p) if ins is not None and ins.transposition else None)
        sons = part_sonora(p)
        notes = [n for n in sons.recurse().notes]
        midis = [pp.midi for n in notes for pp in (n.pitches if hasattr(n, "pitches") else [n.pitch])]
        parts.append({
            "numero": i + 1,
            "nom": nom_part(p, i),
            "instrument_detectat": det.clau if det else None,
            "transposicio": str(ins.transposition) if ins is not None and ins.transposition else None,
            "escrit_en_altura": "escrita (transpositor)" if p.atSoundingPitch is False and ins is not None
            and ins.transposition else "real (concert)",
            "compassos": len(p.getElementsByClass(stream.Measure)),
            "notes": len(notes),
            "mes_greu": str(pitch.Pitch(min(midis))) if midis else None,
            "mes_agut": str(pitch.Pitch(max(midis))) if midis else None,
        })
    tonalitats = score.recurse().getElementsByClass(key.KeySignature)
    compassos = score.recurse().getElementsByClass(meter.TimeSignature)
    tempos = score.recurse().getElementsByClass(tempo.MetronomeMark)
    return {
        "titol": titol,
        "compositor": compositor,
        "tonalitat": _nom_tonalitat(tonalitats[0]) if len(tonalitats) else None,
        "compas": compassos[0].ratioString if len(compassos) else None,
        "tempo": (tempos[0].number if len(tempos) and tempos[0].number else None),
        "parts": parts,
    }


def _nom_tonalitat(ks) -> str:
    try:
        k = ks.asKey() if hasattr(ks, "asKey") else ks
        return f"{k.tonic.name} {k.mode}".replace("-", "b")
    except Exception:
        return f"{ks.sharps:+d} alteracions"


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
    for idx, clau in mapa.items():
        if not 0 <= idx < len(res.parts):
            raise ErrorUsuari(f"La part {idx + 1} no existeix: la partitura en té {len(res.parts)}.")
        i = inst.obtenir(clau)
        part = res.parts[idx]
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
        else:
            part.atSoundingPitch = True
        _posar_clau(part)
        avisos.append(f"Part {idx + 1} → {i.nom}")
    return res, avisos


def _posar_clau(part: stream.Part) -> None:
    for c in list(part.recurse().getElementsByClass(clef.Clef)):
        c.activeSite.remove(c)
    flux = part.flatten()
    nova = clef.bestClef(flux, recurse=True) if len(flux.notes) else clef.TrebleClef()
    primer = part.getElementsByClass(stream.Measure).first()
    (primer if primer is not None else part).insert(0, nova)


# --------------------------------------------------------------------------- tessitura

def tessitura(score: stream.Score, assignacions: str | None = None) -> dict:
    forçades = _parse_assignacions(assignacions)
    resultats = []
    for i, p in enumerate(score.parts):
        ins_m21 = p.getInstrument(returnDefault=False)
        escrit = (p.atSoundingPitch is False and ins_m21 is not None and ins_m21.transposition is not None)
        clau = forçades.get(i)
        if clau:
            instr = inst.obtenir(clau)
        else:
            instr = inst.detectar(f"{nom_part(p, i)} {getattr(ins_m21, 'instrumentName', '') or ''}",
                                  _semitons_transposicio(p) if escrit else None)
        if instr is None:
            resultats.append({"numero": i + 1, "nom": nom_part(p, i), "instrument": None, "problemes": [],
                              "avis": "No sé quin instrument és. Indica-ho amb --instruments \"%d=trompeta-sib\" "
                                      "(o usa l'ordre «instruments» per assignar-lo)." % (i + 1)})
            continue
        sons = part_sonora(p)
        trans = instr.semitons()
        ab_lo, ab_hi = inst.rang_midi(instr.abast)
        co_lo, co_hi = inst.rang_midi(instr.comoda)
        problemes = []
        total = 0
        fora = 0
        incomodes = 0
        escrits = []
        for n in sons.recurse().notes:
            for pp in (n.pitches if hasattr(n, "pitches") else [n.pitch]):
                total += 1
                w = pp.midi - trans   # altura escrita
                escrits.append(w)
                comp = n.getContextByClass(stream.Measure)
                num = comp.number if comp is not None else "?"
                nom_w = str(pitch.Pitch(w)).replace("-", "b")
                if w < ab_lo:
                    fora += 1
                    problemes.append({"compas": num, "nota_escrita": nom_w, "tipus": "massa greu"})
                elif w > ab_hi:
                    fora += 1
                    problemes.append({"compas": num, "nota_escrita": nom_w, "tipus": "massa aguda"})
                elif w < co_lo or w > co_hi:
                    incomodes += 1
                    problemes.append({"compas": num, "nota_escrita": nom_w,
                                      "tipus": "zona incòmoda (greu)" if w < co_lo else "zona incòmoda (aguda)"})
        resultats.append({
            "numero": i + 1, "nom": nom_part(p, i), "instrument": instr.clau, "instrument_nom": instr.nom,
            "abast": instr.abast, "comoda": instr.comoda,
            "notes": total, "fora_abast": fora, "incomodes": incomodes,
            "escrit_min": str(pitch.Pitch(min(escrits))).replace("-", "b") if escrits else None,
            "escrit_max": str(pitch.Pitch(max(escrits))).replace("-", "b") if escrits else None,
            "problemes": problemes, "avis": None,
        })
    return {"parts": resultats}


def _bonic(nom: str) -> str:
    return re.sub(r"(?<=[A-G])-(?=\d)", "b", nom)


def text_tessitura(d: dict, maxim_detall: int = 12) -> str:
    ll = []
    for r in d["parts"]:
        if r["instrument"] is None:
            ll.append(f"{r['numero']}. {r['nom']}: {r['avis']}")
            continue
        ll.append(f"{r['numero']}. {r['nom']}: "
                  f"{'' if r['instrument_nom'] == r['nom'] else r['instrument_nom'] + ', '}escrit de {r['escrit_min']} a {r['escrit_max']}; "
                  f"abast pràctic {_bonic(r['abast'][0])}-{_bonic(r['abast'][1])}, "
                  f"zona còmoda {_bonic(r['comoda'][0])}-{_bonic(r['comoda'][1])}")
        if not r["problemes"]:
            ll.append("   Tot dins de la zona còmoda.")
            continue
        ll.append(f"   {r['fora_abast']} notes FORA d'abast i {r['incomodes']} en zona incòmoda (de {r['notes']}).")
        for pr in sorted(r["problemes"], key=lambda x: (x["tipus"].startswith("zona"), str(x["compas"]).zfill(5)))[:maxim_detall]:
            ll.append(f"   - compàs {pr['compas']}: {pr['nota_escrita']} ({pr['tipus']})")
        if len(r["problemes"]) > maxim_detall:
            ll.append(f"   ... i {len(r['problemes']) - maxim_detall} més.")
    return "\n".join(ll)


# --------------------------------------------------------------------------- reducció

def reduir(score: stream.Score, mantindre: str | None = None, a_piano: bool = False) -> stream.Score:
    if not mantindre and not a_piano:
        raise ErrorUsuari("Digues què vols: --mantin \"1,3\" (quedar-te amb algunes parts) o --a-piano.")
    res = stream.Score()
    res.metadata = copy.deepcopy(score.metadata) if score.metadata else metadata.Metadata()
    if mantindre:
        for i in triar_parts(score, mantindre):
            res.insert(0, copy.deepcopy(score.parts[i]))
        return res
    # a piano: tot en altura real i dividit per la zona do central
    sons = stream.Score()
    for i, p in enumerate(score.parts):
        sons.insert(0, part_sonora(p))
    acords = sons.chordify()
    dreta, esquerra = stream.PartStaff(), stream.PartStaff()
    for m in acords.getElementsByClass(stream.Measure):
        md, me = stream.Measure(number=m.number), stream.Measure(number=m.number)
        for el in m:
            off = el.offset
            if isinstance(el, (meter.TimeSignature, key.KeySignature)):
                md.insert(off, copy.deepcopy(el))
                me.insert(off, copy.deepcopy(el))
            elif isinstance(el, note.Rest):
                md.insert(off, note.Rest(quarterLength=el.quarterLength))
                me.insert(off, note.Rest(quarterLength=el.quarterLength))
            elif hasattr(el, "pitches"):
                alts = [x for x in el.pitches if x.midi >= 60]
                baixos = [x for x in el.pitches if x.midi < 60]
                for dest, pits in ((md, alts), (me, baixos)):
                    if not pits:
                        dest.insert(off, note.Rest(quarterLength=el.quarterLength))
                    elif len(pits) == 1:
                        dest.insert(off, note.Note(pits[0], quarterLength=el.quarterLength))
                    else:
                        from music21 import chord
                        dest.insert(off, chord.Chord(pits, quarterLength=el.quarterLength))
        dreta.append(md)
        esquerra.append(me)
    if dreta.getElementsByClass(stream.Measure).first() is not None:
        dreta.getElementsByClass(stream.Measure).first().insert(0, clef.TrebleClef())
        esquerra.getElementsByClass(stream.Measure).first().insert(0, clef.BassClef())
    from music21 import instrument as m21i
    dreta.insert(0, m21i.Piano())
    esquerra.insert(0, m21i.Piano())
    res.insert(0, dreta)
    res.insert(0, esquerra)
    res.insert(0, layout.StaffGroup([dreta, esquerra], name="Piano", abbreviation="Pno.", symbol="brace"))
    return res
