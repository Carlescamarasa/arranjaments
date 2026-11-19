"""Paquet 5: baix amb personalitat (inversions per grau conjunt, aproximació i baix caminant [inferència])."""
import pytest
from music21 import corpus, harmony, key, meter, stream

from partitures import arranjador as arr
from partitures import baix, musica
from partitures import instruments as inst

LO, HI, MARGE = 40, 59, 19      # zona del baix (Mi2 a Si3)
K_DO = key.Key("C")
ROLS_BAIX = "melodia=trompeta-sib,contracant=flauta,acompanyament=xilofon,baix=trombo,percussio=bateria"


def _segs(simbols, ts="4/4", compassos_per_acord=1):
    """Un segment per acord (un o més compassos cada un), amb la mateixa estructura que fa servir l'arranjador."""
    t = meter.TimeSignature(ts)
    dur = float(t.barDuration.quarterLength) * compassos_per_acord
    segs, x = [], 0.0
    for i, s in enumerate(simbols):
        c = arr.Compas(i + 1, x, dur, t)
        segs.append(arr.Segment(x, x + dur, c, arr._acord_de_simbol(harmony.ChordSymbol(s))))
        x += dur
    return segs


def _linia(simbols, estil, curs=None, **kw):
    return baix.linia(_segs(simbols, **kw), estil, curs, LO, HI, MARGE, 0, {0, 2, 4, 5, 7, 9, 11})


def _noms(res):
    return [m % 12 for _, _, m in res]


def test_nivell_del_curs():
    assert baix.nivell("4t elemental") == "elemental"
    assert baix.nivell("2n professional") == "avancat"
    assert baix.nivell(None) == "mitja" and baix.nivell("3r grau mitjà") == "mitja"


def test_elemental_i_rock_no_usen_el_baix_nou():
    assert _linia(["C", "G", "Am", "F"], "pop", "4t elemental") is None
    assert _linia(["C", "G", "Am", "F"], "rock") is None


def test_do_sol_la_fa_segons_nivell():
    # mitjà: la inversió G/B (Si) millora la línia C-B-A-F; el 6/4 no és mai l'opció
    res = _linia(["C", "G", "Am", "F"], "pop", "3r grau mitjà")
    primers = [m % 12 for ini, _, m in res if ini in (0.0, 4.0, 8.0, 12.0)]
    assert primers == [0, 11, 9, 5]


def test_cap_salt_mes_gran_que_una_quinta_i_dominant_en_fonamental():
    seq = ["C", "F", "G7", "C", "Am", "Dm", "G7", "C"]
    for estil in ("ragtime", "marxa", "pop", "vals", "classic"):
        res = _linia(seq, estil, ts="3/4" if estil == "vals" else "4/4")
        # vals i clàssic fan arpegi dins del compàs: el límit de la quinta només s'exigeix als altres estils
        mids = [m for _, _, m in res]
        if estil not in ("vals", "classic"):
            assert all(abs(b - a) <= 7 or abs(b - a) == 12 for a, b in zip(mids, mids[1:])), estil
        # la dominant abans de la tònica va sempre en estat fonamental (cadència clara)
        c = 3 if estil == "vals" else 4
        g = [m for ini, _, m in res if 2 * c <= ini < 3 * c]
        assert g and g[0] % 12 == 7, estil
        assert res[0][2] % 12 == 0 and res[-1][2] % 12 == 0


def test_no_hi_ha_sis_quatre_si_no_es_cadencial_ni_de_pas():
    # dues tòniques seguides amb IV al mig: la quinta al baix no és legítima aquí
    res = _linia(["F", "C", "F", "C", "G", "C"], "classic")
    primers = {ini: m % 12 for ini, _, m in res}
    assert primers[4.0] != 7          # el segon C no va en 6/4 (després de F només ho permet pop/ragtime)


def test_no_repeteix_la_mateixa_inversio_dues_vegades():
    res = _linia(["C", "G", "Am", "Em", "F", "C", "G", "C"], "pop")
    funcs = baix.tria_inversions(
        [baix.Pas(s, s.acord.pcs[0], baix._tons(s.acord), None) for s in _segs(["C", "G", "Am", "Em", "F", "C", "G", "C"])],
        "pop", "mitja", 0, LO, MARGE)
    for (_, a), (_, b) in zip(funcs, funcs[1:]):
        assert not (a == b and a != "R")
    assert res


def test_barra_mana_al_baix():
    res = _linia(["C", "C/E", "F", "C/G", "G", "C"], "pop")
    por_ini = {ini: m % 12 for ini, _, m in res}
    assert por_ini[4.0] == 4 and por_ini[12.0] == 7


def test_swing_caminant_una_nota_per_temps_arrel_al_primer_i_aproximacio_al_quart():
    seq = ["C", "F", "G7", "C", "Am", "Dm", "G7", "C"]
    for curs in (None, "2n professional"):
        res = _linia(seq, "swing", curs)
        assert [round(d, 3) for _, d, _ in res[:-1]] == [1.0] * (len(res) - 1)
        per_compas = [[m for ini, _, m in res if 4 * i <= ini < 4 * (i + 1)] for i in range(len(seq) - 1)]
        arrels = [0, 5, 7, 0, 9, 2, 7, 0]
        for i, notes in enumerate(per_compas):
            assert len(notes) == 4
            assert notes[0] % 12 == arrels[i]                       # temps 1: l'arrel
            nxt = res[4 * (i + 1)][2]
            assert abs(notes[3] - nxt) <= (1 if curs else 2)        # temps 4: a un semitò (avançat) o un grau
        assert all(abs(b[2] - a[2]) <= 12 for a, b in zip(res, res[1:]))


def test_swing_en_2_4_o_3_4_no_camina():
    res = _linia(["C", "G7"], "swing", ts="3/4")
    assert res is not None and all(d == 1.0 for _, d, _ in res)   # no peta; usa el patró de sempre


def test_ragtime_real_de_berlin_el_baix_va_per_graus_conjunts(tmp_path, monkeypatch):
    o = corpus.parse("leadSheet/berlinAlexandersRagtime.mxl")
    o = o.scores[0] if isinstance(o, stream.Opus) else o
    ruta = tmp_path / "rag.musicxml"
    o.write("musicxml", fp=str(ruta))
    captat = []
    orig = baix.linia

    def espia(*a, **k):
        r = orig(*a, **k)
        captat.append(r)
        return r

    monkeypatch.setattr(baix, "linia", espia)
    for estil in ("ragtime", "swing"):
        captat.clear()
        arr.arranjar(musica.carregar(ruta), arr.parse_rols(ROLS_BAIX), estil=estil, curs="3r grau mitjà")
        res = next(c for c in captat if c)
        mids = [m for _, _, m in res]
        assert res[-1][2] % 12 == 5 or res[-1][2] % 12 == 0
        if estil == "ragtime":
            assert all(abs(b - a) <= 12 for a, b in zip(mids, mids[1:]))
        else:
            assert all(abs(b - a) <= 7 for a, b in zip(mids, mids[1:]))


def test_elemental_manté_el_baix_de_sempre(tmp_path):
    # amb curs elemental, `rol_baix_viu` no passa pel mòdul nou: arrel i quinta
    segs = _segs(["C", "G", "Am", "F"], ts="4/4")
    instr = inst.obtenir("trombo")
    e = arr.rol_baix_viu(segs, instr, "4t elemental", "ragtime", K_DO)
    assert e and all(len(x.alt) == 1 for x in e)
