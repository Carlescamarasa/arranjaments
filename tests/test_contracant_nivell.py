import re
"""Paquets 8 i 11: contracant per nivell (terceres, complementari, guia) i simplificació de la melodia per nivell."""
import pytest
from music21 import corpus, key, meter, note, pitch, stream

from partitures import arranjador as arr
from partitures import biblioteca as bib
from partitures import contracant as con
from partitures import simplificar as sim


@pytest.fixture(autouse=True)
def dades(tmp_path, monkeypatch):
    """Cap perfil de nivell real: dades buides i sense biblioteca compartida."""
    monkeypatch.setenv("ARRANJAMENTS_DADES", str(tmp_path / "dades"))
    monkeypatch.delenv("ARRANJAMENTS_BIBLIOTECA", raising=False)
    monkeypatch.setattr(bib, "_plataforma", lambda: "altre")
    monkeypatch.setenv("HOME", str(tmp_path / "buit"))


@pytest.fixture(scope="module")
def ragtime():
    return corpus.parse("leadSheet/berlinAlexandersRagtime.mxl")


def _part(*bars):
    """Una part de 4/4 amb compassos fets de (nom, durada) (nom None = silenci)."""
    p = stream.Part()
    for i, bar in enumerate(bars):
        m = stream.Measure(number=i + 1)
        if i == 0:
            m.append(meter.TimeSignature("4/4"))
        for nom, d in bar:
            m.append(note.Rest(quarterLength=d) if nom is None else note.Note(nom, quarterLength=d))
        p.append(m)
    return p


def _evs(part):
    compassos = arr._compassos(part)
    return arr._linia_superior(part), compassos


def _midis(part):
    return [(float(n.getOffsetInHierarchy(part)), n.pitches[0].midi) for n in part.flatten().notes
            if not hasattr(n, "figure")]


# --------------------------------------------------------------------------- mode segons el curs

def test_el_curs_triar_el_mode_del_contracant():
    assert con.mode_contracant("4t elemental") == "terceres"
    assert con.mode_contracant("2n iniciacio") == "terceres"
    assert con.mode_contracant("3r mitja") == "complementari"
    assert con.mode_contracant("6e professional") == "guia"
    assert con.mode_contracant(None) == "complementari"
    assert sim.nivell_de(None) is None


def test_pentatonica_de_l_acord_i_notes_guia():
    from music21 import harmony
    do = arr._acord_de_simbol(harmony.ChordSymbol("C"))
    rem = arr._acord_de_simbol(harmony.ChordSymbol("Am"))
    sol7 = arr._acord_de_simbol(harmony.ChordSymbol("G7"))
    assert con.pentatonica(do) == {0, 2, 4, 7, 9}
    assert con.pentatonica(rem) == {9, 0, 2, 4, 7}          # La, Do, Re, Mi, Sol
    assert con.notes_guia(sol7) == {11, 5}                  # tercera (Si) i sèptima (Fa)
    assert con.notes_guia(do) == set(do.pcs)                # una tríada no té sèptima: les tres notes


def test_classifica_el_contorn_de_la_frase_i_en_dona_l_oposat():
    assert con.classifica_contorn([60, 62, 64, 67]) == "ascendent"
    assert con.classifica_contorn([67, 64, 62, 60]) == "descendent"
    assert con.classifica_contorn([60, 64, 67, 64, 60]) == "arc"
    assert con.classifica_contorn([67, 62, 60, 62, 67]) == "arc_invertit"
    assert con.classifica_contorn([60, 60, 61, 60]) == "estacionari"
    assert con.CONTORN_OPOSAT["ascendent"] == "descendent"
    assert con.CONTORN_OPOSAT["arc"] == "arc_invertit"


# --------------------------------------------------------------------------- les tres maneres, sobre una peça real

ROLS = "melodia=oboe,contracant=flauta,baix=fagot"     # oboè i flauta no transposen: l'escrit és el que sona


def _contracant(ragtime, curs, rotacio=False):
    r, informe = arr.arranjar(ragtime, arr.parse_rols(ROLS), estil="ragtime", curs=curs, rotacio=rotacio)
    parts = list(r.parts)
    mel = next(p for p in parts if "Oboè" in (p.partName or ""))
    flu = next(p for p in parts if "Flauta" in (p.partName or ""))
    return mel, flu, informe


def _sonant(part, t):
    for n in part.flatten().notes:
        if hasattr(n, "figure"):
            continue
        o = float(n.getOffsetInHierarchy(part))
        if o <= t + 1e-6 < o + float(n.quarterLength):
            return n.pitches[0].midi
    return None


def _atacs(part):
    return [float(n.getOffsetInHierarchy(part)) for n in part.flatten().notes if not hasattr(n, "figure")]


def test_elemental_es_tot_terceres_i_sextes_sense_paralleles(ragtime):
    mel, flu, informe = _contracant(ragtime, "4t elemental")
    parelles = [(t, _sonant(flu, t), _sonant(mel, t)) for t in _atacs(flu)]
    parelles = [(t, c, m) for t, c, m in parelles if c is not None and m is not None]
    assert len(parelles) > 20
    bons = [abs(c - m) % 12 in (3, 4, 8, 9) for t, c, m in parelles]
    assert sum(bons) / len(bons) >= 0.9                     # el 90% de les notes, a 3a o 6a
    assert not arr.paral_leles(_ev(flu), _ev(mel), arr._compassos(mel))
    notes = [n.pitches[0].midi for n in flu.flatten().notes if not hasattr(n, "figure")]
    assert max(abs(b - a) for a, b in zip(notes, notes[1:])) <= con.SALT_MAX_ELEMENTAL + 12   # sense salts de més d'una 6a
    assert any("terceres i sextes" in x for x in informe)


def _ev(part):
    return arr._linia_superior(part)


def test_les_terceres_no_passen_de_quatre_seguides_del_mateix_interval(ragtime):
    mel, flu, _ = _contracant(ragtime, "4t elemental")
    tipus = []
    for t in _atacs(flu):
        c, m = _sonant(flu, t), _sonant(mel, t)
        if c is not None and m is not None:
            tipus.append(3 if abs(c - m) % 12 in (3, 4) else 6)
    maxim, run = 1, 1
    for a, b in zip(tipus, tipus[1:]):
        run = run + 1 if a == b else 1
        maxim = max(maxim, run)
    assert maxim <= con.MAX_NOTES_MATEIX_INTERVAL


def test_mitja_i_professional_no_coincideixen_mes_de_la_meitat_dels_atacs(ragtime):
    for curs in ("3r mitja", "6e professional"):
        mel, flu, informe = _contracant(ragtime, curs)
        assert con.coincidencia_atacs(_ev(flu), _ev(mel)) <= con.COINCIDENCIA_MAXIMA + 1e-6, curs
        assert not any("terceres i sextes" in x for x in informe)
        assert any(x.strip().startswith("Contracant:") for x in informe)


def test_el_contracant_cau_dins_la_tessitura_del_nivell(ragtime):
    from partitures import instruments as inst
    flauta = inst.obtenir("flauta")
    for curs in ("4t elemental", "3r mitja", "6e professional"):
        _, flu, _ = _contracant(ragtime, curs)
        (lo, hi), _ = arr.rang_comode(flauta, curs)
        notes = [n.pitches[0].midi for n in flu.flatten().notes if not hasattr(n, "figure")]
        fora = [m for m in notes if not lo <= m <= hi]
        assert len(fora) / len(notes) <= 0.1, (curs, fora)


def test_amb_rotacio_els_tres_modes_funcionen_i_no_fan_quintes_paralleles(ragtime):
    for curs in ("4t elemental", "3r mitja", "6e professional"):
        _, _, informe = _contracant(ragtime, curs, rotacio=True)
        linia = next(x for x in informe if "paral·leles del contracant" in x)
        if linia.rstrip().rstrip(".").endswith("cap"):
            continue
        # tolerat: només en el primer compàs d'una frase on canvia qui porta la melodia (la línia passa a un altre
        # instrument i la nota d'abans és d'un altre timbre)
        inicis = {s.num0 for s in arr.arranjar.pla}
        nums = [int(m) for m in re.findall(r"compàs (\d+)", linia)]
        assert nums and all(n in inicis for n in nums), (curs, linia)


def test_desplaca_entrades_rebaixa_la_coincidencia():
    p = _part([("C5", 4)], [("D5", 4)], [("E5", 4)], [("F5", 4)])
    evs, compassos = _evs(p)
    segs = arr._segments(compassos, [])
    linia = [arr.Ev(e.ini, e.dur, [pitch.Pitch(midi=e.alt[0].midi - 9)]) for e in evs]
    assert con.coincidencia_atacs(linia, evs) == 1.0
    nova = con.desplaca_entrades(linia, evs, segs)
    assert con.coincidencia_atacs(nova, evs) <= 0.5
    assert sum(e.dur for e in nova if e.alt) + 0 <= sum(e.dur for e in linia)    # entra tard, no allarga


# --------------------------------------------------------------------------- simplificar

NOTES_PAS = [[("C5", 1), ("D5", .5), ("E5", .5), ("F5", 1), ("G5", 1)],
             [("A5", 1), ("G5", .5), ("F5", .5), ("E5", 1), ("D5", 1)],
             [("C5", 4)]]


def test_simplifica_treu_notes_de_pas_i_conserva_temps_forts_i_durada():
    p = _part(*NOTES_PAS)
    evs, compassos = _evs(p)
    nous, info = sim.simplifica_melodia(evs, compassos, "4t elemental")
    assert all(e.dur >= 1.0 - 1e-6 for e in nous if e.alt)
    assert sum(e.dur for e in nous) == pytest.approx(sum(e.dur for e in evs))
    assert [e.alt[0].name for e in nous if abs(e.ini - 2) < 1e-6] == ["F"]     # el temps fort del compàs 1 es manté
    assert any("notes de pas" in x for x in info)
    assert nous[0].alt[0].name == "C" and nous[-1].alt[0].name == "C"           # inici i final de frase


def test_simplifica_no_toca_el_nivell_professional():
    p = _part(*NOTES_PAS)
    evs, compassos = _evs(p)
    nous, info = sim.simplifica_melodia(evs, compassos, "6e professional")
    assert [(e.ini, e.dur, e.alt[0].midi) for e in nous] == [(e.ini, e.dur, e.alt[0].midi) for e in evs]
    assert info == []


def test_les_notes_estructurals_son_extrems_i_temps_forts():
    p = _part(*NOTES_PAS)
    evs, compassos = _evs(p)
    imp = sim.importancia(evs, compassos)
    assert imp[0] >= sim.LLINDAR_ESTRUCTURAL and imp[-1] >= sim.LLINDAR_ESTRUCTURAL
    assert imp[2] < sim.LLINDAR_ESTRUCTURAL           # la corxera de contratemps no és estructural


def test_octava_per_frases_mou_la_frase_sencera_i_no_a_mig_motiu():
    p = _part([("C5", 1), ("E5", 1), ("G5", 1), ("E5", 1)], [("C5", 4)],
              [(None, 2), ("C6", 1), ("E6", 1)], [("G6", 1), ("E6", 1), ("C6", 2)])
    evs, compassos = _evs(p)
    lo, hi = 72, 84          # zona còmoda Do5 a Do6 (so real)
    nous, canvis = sim.octava_per_frases(evs, lo, hi, 60, 96, compassos)
    assert canvis, "la frase aguda hauria de baixar"
    # la primera frase no es mou; la segona (després del silenci) baixa tota
    assert [e.alt[0].midi for e in nous[:5] if e.alt] == [e.alt[0].midi for e in evs[:5] if e.alt]
    tail = [(n.alt[0].midi - o.alt[0].midi) for n, o in zip(nous, evs) if o.alt and o.ini >= 8]
    assert set(tail) == {-12}
    assert len(nous) == len(evs)


def test_octava_per_frases_no_mou_si_no_hi_ha_millora():
    p = _part([("C5", 1), ("E5", 1), ("G5", 1), ("E5", 1)], [("C5", 4)])
    evs, compassos = _evs(p)
    nous, canvis = sim.octava_per_frases(evs, 72, 84, 60, 96, compassos)
    assert canvis == [] and [e.alt[0].midi for e in nous if e.alt] == [e.alt[0].midi for e in evs if e.alt]


def test_simplifica_a_l_arranjament_diu_que_ha_tocat(ragtime):
    r, informe = arr.arranjar(ragtime, arr.parse_rols("melodia=oboe,acompanyament=piano"), estil="ragtime",
                              curs="4t elemental", simplifica=True)
    text = "\n".join(informe)
    assert "He simplificat la melodia al nivell" in text
    assert "He simplificat el ritme de la melodia" in text
    oboe = next(p for p in r.parts if "Oboè" in (p.partName or ""))
    notes = [n for n in oboe.flatten().notes if not hasattr(n, "figure")]
    assert all(n.quarterLength >= 1 or n.tie is not None for n in notes)


def test_simplifica_sense_curs_diu_que_no_sap_el_nivell(ragtime):
    _, informe = arr.arranjar(ragtime, arr.parse_rols("melodia=oboe,acompanyament=piano"), estil="ragtime",
                              simplifica=True)
    assert any("No he simplificat el ritme" in x for x in informe)


def test_simplifica_en_nivell_professional_no_toca_la_melodia(ragtime):
    _, informe = arr.arranjar(ragtime, arr.parse_rols("melodia=oboe,acompanyament=piano"), estil="ragtime",
                              curs="6e professional", simplifica=True)
    assert any("admet totes les figures" in x for x in informe)
    assert not any("He simplificat" in x for x in informe)
