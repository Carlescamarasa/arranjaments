"""Proves del paquet 9: frases i forma (sentència, període, irregular) més introducció i coda."""
import pytest
from music21 import corpus, key, meter, pitch, stream

from partitures import arranjador as arr
from partitures import cli, forma, musica
from partitures.arranjador import Compas, Ev

ROLS = "melodia=trompeta-sib,contracant=flauta,acompanyament=xilofon,percussio=bateria"
DO = {"C": 60, "D": 62, "E": 64, "F": 65, "G": 67, "A": 69, "B": 71, "c": 72, "d": 74, "e": 76}


@pytest.fixture(autouse=True)
def dades(tmp_path, monkeypatch):
    monkeypatch.setenv("ARRANJAMENTS_DADES", str(tmp_path / "dades"))
    monkeypatch.setenv("HOME", str(tmp_path / "buit"))


def _melodia(compas_txt, compassos_notes):
    """compassos_notes: llista de compassos; cada compàs és una llista de (nom d'altura o None, durada en negres)."""
    ts = meter.TimeSignature(compas_txt)
    bar = float(ts.barDuration.quarterLength)
    cs, evs = [], []
    for i, notes in enumerate(compassos_notes):
        c = Compas(i + 1, i * bar, bar, ts, False, i == 0)
        cs.append(c)
        t = c.ini
        for nom, d in notes:
            if nom is not None:
                evs.append(Ev(t, d, [pitch.Pitch(midi=DO[nom] if isinstance(nom, str) else nom)]))
            t += d
    return cs, evs


def _talls(compas_txt, compassos_notes, bpm=None):
    cs, evs = _melodia(compas_txt, compassos_notes)
    segs = arr._segments(cs, [])
    return forma.divideix(cs, evs, segs, key.Key("C"), bpm), cs, evs


def _q(*noms):
    return [(n, 1.0) for n in noms]


def test_llargada_de_frase_segons_metrica_i_tempo():
    assert forma.llargada_frase(meter.TimeSignature("4/4"), 100) == 4
    assert forma.llargada_frase(meter.TimeSignature("6/8"), 100) == 2
    assert forma.llargada_frase(meter.TimeSignature("2/4"), 120) == 8     # compàs molt curt: frase del doble
    assert forma.llargada_frase(meter.TimeSignature("4/4"), 40) == 2      # molt lent: la meitat
    assert forma.llargada_frase(meter.TimeSignature("4/4"), None) == 4    # sense tempo, el per defecte


def test_melodia_de_8_compassos_tipus_sentencia_es_detecta_com_a_sentencia():
    idea = [_q("C", "E", "G", "E"), _q("D", "F", "A", "G")]
    rep = [_q("D", "F", "A", "F"), _q("E", "G", "B", "A")]       # repetició transposada (seqüència)
    cont = [[("c", .5), ("B", .5), ("A", .5), ("G", .5), ("F", 2)], [("E", 2), ("D", 1), ("E", 1)],
            [("D", 2), ("E", 2)], [("C", 4)]]                   # continuació condensada, acaba en la tònica
    talls, _, _ = _talls("4/4", idea + rep + cont)
    assert [(a, b, t) for a, b, t, _ in talls] == [(0, 8, "sentencia")]


def test_periode_amb_semicadencia_al_compas_4_es_periode():
    ante = [_q("C", "E", "G", "E"), _q("F", "A", "G", "F"), _q("E", "G", "c", "G"), [("G", 4)]]   # acaba en Sol
    cons = [_q("C", "E", "G", "E"), _q("F", "A", "G", "F"), _q("E", "D", "E", "F"), [("C", 4)]]    # acaba en Do
    talls, cs, evs = _talls("4/4", ante + cons)
    assert [(a, b, t) for a, b, t, _ in talls] == [(0, 8, "periode")]
    seccions = arr.dividir_seccions(cs, evs, arr._segments(cs, []), key.Key("C"))
    assert [s.tipus for s in seccions] == ["periode"]
    assert seccions[0].tancada is True


def test_blues_de_12_compassos_no_es_talla_a_8_mes_4():
    linia = [_q("C", "E", "G", "E"), _q("C", "E", "G", "E"), _q("D", "F", "A", "F"), [("C", 4)]]
    talls, _, _ = _talls("4/4", linia * 3)
    assert [b - a for a, b, _, _ in talls] == [4, 4, 4]


def test_peca_en_6_8_te_unitats_de_2_compassos():
    compas = [(("E", .5),) * 6][0]
    talls, _, _ = _talls("6/8", [list(compas) for _ in range(10)])
    assert [b - a for a, b, _, _ in talls] == [2] * 5
    llarga, _, _ = _talls("6/8", [list(compas) for _ in range(12)])      # peça llarga: de dues en dues frases
    assert all((b - a) % 2 == 0 for a, b, _, _ in llarga)


def test_peca_curta_no_es_talla():
    talls, _, _ = _talls("4/4", [_q("C", "D", "E", "F")] * 6)
    assert len(talls) == 1


def test_tall_per_cadencia_gana_a_la_llargada_fixa():
    """Una frase de 5 compassos acabada en nota llarga i tònica no es talla a 4."""
    f4 = [_q("C", "E", "G", "E"), _q("D", "F", "A", "G"), _q("E", "G", "c", "G"), _q("F", "A", "G", "F")]
    talls, _, _ = _talls("4/4", f4 + [[("C", 4)]] + f4 + [[("C", 4)]])
    assert [b - a for a, b, _, _ in talls] == [5, 5]


# --------------------------------------------------------------------------- intro i coda
@pytest.fixture(scope="module")
def ragtime(tmp_path_factory):
    s = corpus.parse("leadSheet/berlinAlexandersRagtime.mxl")
    if isinstance(s, stream.Opus):
        s = s.scores[0]
    return s


def _mesures(r):
    return [len(list(p.getElementsByClass(stream.Measure))) for p in r.parts]


def test_sense_intro_ni_coda_res_no_canvia(ragtime):
    r, inf = arr.arranjar(ragtime, arr.parse_rols(ROLS))
    n = len(list(ragtime.parts[0].getElementsByClass(stream.Measure)))
    assert set(_mesures(r)) == {n}
    assert not any(s.tipus in ("intro", "coda") for s in arr.arranjar.pla)


def test_intro_i_coda_afegeixen_compassos_a_totes_les_parts_i_la_coda_acaba_en_la_tonica(ragtime):
    r0, _ = arr.arranjar(ragtime, arr.parse_rols(ROLS))
    n0 = _mesures(r0)[0]
    r, inf = arr.arranjar(ragtime, arr.parse_rols(ROLS), intro=True, coda=True)
    assert len(set(_mesures(r))) == 1                      # totes les parts acaben en el mateix compàs
    n = _mesures(r)[0]
    assert 4 <= n - n0 <= 8
    # numeració contínua
    nums = [m.number for m in r.parts[0].getElementsByClass(stream.Measure)]
    assert nums == list(range(1, n + 1))
    tipus = [s.tipus for s in arr.arranjar.pla]
    assert tipus[0] == "intro" and tipus[-1] == "coda"
    assert arr.arranjar.pla[-1].tancada is True
    # l'última nota de la melodia és la tònica, al primer temps de l'últim compàs
    mel = next(p for p in r.parts if p.partName.startswith("Trompeta"))
    sonor = musica.part_sonora(mel)
    ult = list(sonor.getElementsByClass(stream.Measure))[-1]
    notes = [x for x in ult.notes]
    assert notes and notes[0].offset == 0
    assert "Introducció de" in "\n".join(inf) and "Coda de" in "\n".join(inf)


def test_la_coda_acaba_en_la_tonica_de_la_peca(ragtime):
    r, inf = arr.arranjar(ragtime, arr.parse_rols(ROLS), coda=True)
    tonica = next(l for l in inf if l.startswith("Tonalitat:"))
    assert "Fa major" in tonica
    mel = musica.part_sonora(next(p for p in r.parts if p.partName.startswith("Trompeta")))   # so real
    ult = list(mel.getElementsByClass(stream.Measure))[-1]
    sons = [x for x in ult.notes if x.isNote]
    assert sons and sons[0].pitch.name == "F" and sons[0].offset == 0


def test_intro_amb_anacrusi_numera_be(coral):
    s = musica.carregar(coral)
    r, _ = arr.arranjar(s, arr.parse_rols("melodia=trompeta-sib,contracant=flauta,baix=violoncel"), estil="classic",
                        intro=True, coda=True)
    assert len(set(_mesures(r))) == 1
    nums = [m.number for m in r.parts[0].getElementsByClass(stream.Measure)]
    assert nums == list(range(1, len(nums) + 1))


def test_intro_i_coda_sense_rotacio(ragtime):
    r, _ = arr.arranjar(ragtime, arr.parse_rols(ROLS), rotacio=False, intro=True, coda=True)
    assert len(set(_mesures(r))) == 1
    assert arr.arranjar.pla == []


def test_l_ordre_accepta_intro_i_coda(ragtime, tmp_path, projecte):
    ruta = projecte / "entrada" / "ragtime.musicxml"
    ragtime.write("musicxml", fp=str(ruta))
    cli.main(["arranja", str(ruta), "--rols", ROLS, "--intro", "--coda"])
    assert (projecte / "eixida").exists()


def test_desplacament_diatonic():
    k = key.Key("C")
    assert forma.desplaca_diatonic(60, 4, k) == 67      # Do -> Sol
    assert forma.desplaca_diatonic(64, -2, k) == 60     # Mi -> Do
    assert forma.desplaca_diatonic(61, 0, k) == 60      # Do# compta com Do
