"""Proves dels paquets 6 i 7: tipus d'acompanyament per estil i nivell, i disposició de les notes (clàssic i jazz)."""
import pytest
from music21 import key, meter, pitch

from partitures import acompanyament as ac
from partitures import arranjador as arr
from partitures import instruments as inst
from partitures import voicing as vo


def acord(figura: str) -> arr.Acord:
    """Acords de prova: arrel, 3a, 5a i (si en té) 7a, com els fa l'eina."""
    taula = {
        "C": ("C", (0, 4, 7)), "F": ("F", (5, 9, 0)), "G": ("G", (7, 11, 2)), "Am": ("A", (9, 0, 4)),
        "Dm7": ("D", (2, 5, 9, 0)), "G7": ("G", (7, 11, 2, 5)), "Cmaj7": ("C", (0, 4, 7, 11)),
        "C7": ("C", (0, 4, 7, 10)),
    }
    arrel, pcs = taula[figura]
    return arr.Acord(pitch.Pitch(arrel), pcs, figura)


def peca(acords, ts="4/4", pols_per_compas=None):
    """Un compàs per acord (o una llista de llistes per a diversos acords en un compàs)."""
    t = meter.TimeSignature(ts)
    dur = t.barDuration.quarterLength
    compassos, segs = [], []
    for i, ll in enumerate(acords):
        c = arr.Compas(i + 1, i * dur, dur, t)
        compassos.append(c)
        ll = ll if isinstance(ll, list) else [ll]
        pas = dur / len(ll)
        for j, f in enumerate(ll):
            segs.append(arr.Segment(i * dur + j * pas, i * dur + (j + 1) * pas, c, acord(f)))
    return segs


def melodia(*notes):
    """(inici, durada, midi)"""
    return [arr.Ev(i, d, [pitch.Pitch(midi=m)]) for i, d, m in notes]


def genera(estil, acords, instrument="piano", curs=None, ts="4/4", **kw):
    segs = peca(acords, ts)
    e, b = arr.rol_acompanyament(segs, inst.obtenir(instrument), curs, estil, key.Key("C"), **kw)
    return e, b


def atacs(evs, a, b):
    return [(float(e.ini), len(e.alt), min(p.midi for p in e.alt)) for e in evs if a <= e.ini < b]


# --------------------------------------------------------------------------- paquet 6: tipus d'acompanyament

def test_nivell_de_curs():
    assert ac.nivell_de("4t elemental") == "elemental"
    assert ac.nivell_de("2n professional") == "avançat"
    assert ac.nivell_de(None) == "mitja" and ac.nivell_de("grau mitjà") == "mitja"


@pytest.mark.parametrize("estil,nivell,esperat", [
    ("ragtime", "mitja", [(0.0, "R"), (1.0, "C"), (2.0, "R"), (3.0, "C")]),       # stride (ST01)
    ("ragtime", "avançat", [(0.0, "D"), (1.0, "C"), (2.0, "D"), (3.0, "C")]),     # dècimes
    ("swing", "mitja", [(0.0, "R"), (1.5, "Q"), (2.0, "R"), (3.5, "Q")]),         # acords avançats mig temps (CP01)
    ("swing", "elemental", [(0.0, "R"), (1.0, "C"), (2.0, "R"), (3.0, "C")]),     # sense anticipació en elemental
    ("marxa", "mitja", [(0.0, "B"), (1.0, "C"), (2.0, "B"), (3.0, "C")]),
    ("pop", "mitja", [(0.0, "A"), (1.0, "A"), (2.0, "A"), (3.0, "A")]),
    ("rock", "mitja", [(0.0, "c"), (1.0, "c"), (2.0, "c"), (3.0, "c")]),
    ("rock", "elemental", [(0.0, "C"), (1.0, "C"), (2.0, "C"), (3.0, "C")]),
    ("classic", "elemental", [(0.0, "L")]),
    ("classic", "mitja", [(0.0, "AL"), (1.0, "AL"), (2.0, "AL"), (3.0, "AL")]),
])
def test_patrons_de_4_4_per_estil_i_nivell(estil, nivell, esperat):
    assert [(o, t) for o, t, _ in ac.patro(estil, nivell, 4)] == esperat


def test_patro_de_vals_i_marxa_en_altres_compassos():
    assert [(o, t) for o, t, _ in ac.patro("vals", "mitja", 3)] == [(0.0, "B"), (1.0, "C"), (2.0, "C")]
    assert [(o, t) for o, t, _ in ac.patro("marxa", "mitja", 2)] == [(0.0, "B"), (1.0, "C")]
    # 6 pulsacions: dos compassos de tres, sense inventar un patró nou
    assert len(ac.patro("vals", "mitja", 6)) == 6


def test_vals_baix_al_temps_1_i_acords_al_2_i_3_en_tota_la_peca():
    e, b = genera("vals", ["C", "F", "G", "C", "Am", "F", "G7", "C"], ts="3/4")
    for c in range(7):                       # tots els compassos menys el final
        ini = c * 3.0
        dins = [x for x in e if ini <= x.ini < ini + 3]
        assert [float(x.ini) - ini for x in dins] == [0.0, 1.0, 2.0]
        assert len(dins[0].alt) == 1 and len(dins[1].alt) >= 2 and len(dins[2].alt) >= 2
    # el compàs final: acord de tornada, no el patró
    assert len([x for x in e if x.ini >= 21]) == 1


def test_marxa_en_2_4_baix_i_acord():
    e, _ = genera("marxa", ["C", "G7", "C", "C"], ts="2/4")
    assert [float(x.ini) for x in e if x.ini < 2] == [0.0, 1.0]
    assert len(next(x for x in e if x.ini == 0).alt) == 1 and len(next(x for x in e if x.ini == 1).alt) >= 2


def test_ragtime_stride_arrel_als_forts_i_acord_als_febles():
    e, b = genera("ragtime", ["C", "G7", "C", "C"])
    c1 = atacs(e, 0, 4)
    assert [t for t, _, _ in c1] == [0.0, 1.0, 2.0, 3.0]
    assert c1[0][1] == 1 and c1[2][1] == 1 and c1[1][1] >= 2 and c1[3][1] >= 2
    assert c1[0][2] % 12 == 0 and c1[2][2] % 12 == 0          # arrel als dos forts (ST01)


def test_ragtime_avancat_usa_decimes_en_piano():
    e, _ = genera("ragtime", ["C", "F", "G7", "C"], curs="2n professional")
    primer = next(x for x in e if x.ini == 0)
    assert [p.midi for p in primer.alt][1] - [p.midi for p in primer.alt][0] == 16 or \
        [p.midi for p in primer.alt][1] - [p.midi for p in primer.alt][0] in (15, 16)    # arrel i 3a una dècima amunt


def test_swing_acords_curts_avancats_mig_temps():
    e, _ = genera("swing", ["C", "F", "G7", "C"], amb_baix=True)
    c1 = [x for x in e if x.ini < 4]
    # sense arrels (hi ha baix a part): dos acords curts al & del 2 i al & del 4
    assert [float(x.ini) for x in c1] == [1.5, 3.5]
    assert all(float(x.dur) == 0.5 for x in c1)
    # el del & del 4 porta l'acord del compàs següent (F), no el de C (Levine CP01)
    assert {p.pitchClass for p in c1[1].alt} <= {5, 9, 0, 4}
    assert 5 in {p.pitchClass for p in c1[1].alt} or 9 in {p.pitchClass for p in c1[1].alt}


def test_swing_sense_baix_a_part_porta_arrel_i_en_elemental_va_al_temps():
    e, _ = genera("swing", ["C", "F", "G7", "C"])
    assert [float(x.ini) for x in e if x.ini < 4] == [0.0, 1.5, 2.0, 3.5]
    e, _ = genera("swing", ["C", "F", "G7", "C"], curs="4t elemental", amb_baix=True)
    assert [float(x.ini) for x in e if x.ini < 4] == [1.0, 3.0]        # acords al temps, sense anticipar


def test_swing_avancat_omple_si_la_melodia_calla():
    mel_calla = melodia((0, 0.5, 72))       # compàs 1: només una nota curta al principi
    e, _ = genera("swing", ["C", "F", "G7", "C"], curs="2n professional", amb_baix=True, melodia=mel_calla)
    assert 2.0 in [float(x.ini) for x in e if x.ini < 4]               # temps 3: complement (CP04)
    mel_ple = melodia(*[(i, 1.0, 72) for i in range(16)])
    e, _ = genera("swing", ["C", "F", "G7", "C"], curs="2n professional", amb_baix=True, melodia=mel_ple)
    assert 2.0 not in [float(x.ini) for x in e if x.ini < 4]


def test_classic_elemental_nota_llarga_nomes_baix():
    mel = melodia((0, 4.0, 72), (4, 4.0, 74), (8, 1.0, 72), (9, 1.0, 74), (10, 1.0, 76), (11, 1.0, 77),
                  (12, 4.0, 72))
    e, b = genera("classic", ["C", "F", "G7", "C"], curs="4t elemental", melodia=mel)
    c1 = [x for x in e if x.ini < 4]
    assert len(c1) == 1 and len(c1[0].alt) == 1                         # només el baix (AC-02)
    c3 = [x for x in e if 8 <= x.ini < 12]
    assert len(c3) == 1 and len(c3[0].alt) >= 3                         # melodia en moviment: acord sencer
    # sense dades de melodia no s'omet res
    e, _ = genera("classic", ["C", "F", "G7", "C"], curs="4t elemental")
    assert len(e[0].alt) >= 3


def test_classic_mitja_alberti_i_motiu_estable():
    e, b = genera("classic", ["C", "C", "F", "F", "G7", "G7", "C", "C"])
    # compassos 1 a 4: sempre vuit notes soles, baixa-alta-mitjana-alta
    for c in range(4):
        dins = [x for x in e if c * 4 <= x.ini < c * 4 + 4]
        assert len(dins) == 8 and all(len(x.alt) == 1 for x in dins)
        m = [x.alt[0].midi for x in dins]
        assert m[0] < m[2] < m[1] == m[3] and m[4] == m[0]
    # el motiu es manté fins i tot en canviar l'acord
    assert [round(float(x.ini) % 1, 2) for x in e if x.ini < 4] == [0.0, 0.5] * 4


def test_cadencia_de_frase_canvia_el_motiu_i_el_final_es_sosté():
    segs = peca(["C", "F", "G7", "C", "C", "F", "G7", "C"])
    e, _ = arr.rol_acompanyament(segs, inst.obtenir("piano"), None, "classic", key.Key("C"), fi_frases=[16.0, 32.0])
    comp4 = [x for x in e if 12 <= x.ini < 16]
    assert len(comp4) == 1 and float(comp4[0].dur) == 4.0              # cadència de la frase: acord sostingut
    comp5 = [x for x in e if 16 <= x.ini < 20]
    assert len(comp5) == 8                                            # la frase següent torna al motiu
    final = [x for x in e if x.ini >= 28]
    assert len(final) == 1 and float(final[0].dur) == 4.0


def test_rock_quinta_buida_i_pop_arpegi():
    e, _ = genera("rock", ["C", "G"], instrument="guitarra")
    primer = e[0]
    assert sorted({p.pitchClass for p in primer.alt}) == [0, 7]        # arrel i 5a (REH-04)
    e, _ = genera("pop", ["C", "G", "Am", "F"], instrument="xilofon")
    assert len([x for x in e if x.ini < 4]) in (4, 8)                  # una nota per pulsació o per corxera


def test_corxeres_no_surten_en_elemental():
    e, _ = genera("pop", ["C", "G", "Am", "F"], instrument="xilofon", curs="4t elemental")
    assert all(float(x.dur) == 1.0 for x in e if x.ini < 12)      # el compàs final sosté l'acord


def test_pad_usa_el_coral_sostingut():
    segs = peca(["C", "F", "G7", "C"])
    e, _ = arr.rol_acompanyament(segs, inst.obtenir("piano"), None, "coral", key.Key("C"))
    assert [float(x.ini) for x in e if x.ini < 4] == [0.0, 2.0]


# --------------------------------------------------------------------------- paquet 7: voicing

def _ii_v_i():
    return [acord("Dm7"), acord("G7"), acord("Cmaj7")]


def test_ii_v_i_en_jazz_la_sisena_baixa_mig_to():
    prev, voz = None, []
    for i, a in enumerate(_ii_v_i()):
        v = vo.disposicio(a, 2, 58, 76, prev, "swing", "elemental", prev_acord=_ii_v_i()[i - 1] if i else None)
        voz.append(v)
        prev = v
    for x, y in zip(voz, voz[1:]):
        assert all(abs(p - q) <= 4 for p, q in zip(x, y)), (x, y)      # cap salt de més d'una 3a
    # la 7a de Dm7 (Do) baixa un semitò (Si) en G7 i la de G7 (Fa) baixa a Mi en Cmaj7
    assert {p % 12 for p in voz[0]} == {5, 0} and {p % 12 for p in voz[1]} == {11, 5}
    assert {p % 12 for p in voz[2]} == {4, 11}
    assert [q for q in voz[1] if q % 12 == 11][0] == [q for q in voz[0] if q % 12 == 0][0] - 1


def test_jazz_ometre_la_5a_i_triar_posicio_mes_propera():
    v = vo.disposicio(acord("G7"), 3, 58, 76, None, "swing", "mitja")
    assert {p % 12 for p in v} == {11, 5}                              # 3a i 7a, mai la 5a (Re)
    assert vo.triar_pcs(acord("C"), 2, "swing", "mitja") == [4, 7]     # tríada: 3a i 5a


def test_classic_sense_septima_en_elemental_i_amb_sèptima_despres():
    assert vo.triar_pcs(acord("G7"), 3, "classic", "elemental") == [11, 2, 7]
    assert vo.triar_pcs(acord("G7"), 3, "classic", "mitja") == [11, 5, 7]
    assert vo.triar_pcs(acord("G7"), 3, "pop", "mitja") == [11, 2, 7]       # pop: 7a només en avançat
    assert vo.triar_pcs(acord("G7"), 3, "pop", "avançat") == [11, 5, 7]
    assert vo.triar_pcs(acord("C"), 3, "rock", "mitja") == [0, 7, 0]


def test_classic_notes_comunes_es_mantenen():
    v1 = vo.disposicio(acord("C"), 3, 60, 79, None, "classic", "mitja")
    v2 = vo.disposicio(acord("Am"), 3, 60, 79, v1, "classic", "mitja")
    comunes = set(v1) & set(v2)
    assert len(comunes) >= 2                                           # Do i Mi es queden (Zamacois VE10)


def test_final_v_i_tripica_la_fonamental_sense_5a():
    v = vo.disposicio(acord("C"), 3, 60, 79, None, "classic", "mitja", final_dominant=True)
    assert sorted(p % 12 for p in v) == [0, 0, 4]


def test_la_melodia_no_es_dobla_a_l_acompanyament():
    for m in (64, 67, 72, 76):
        v = vo.disposicio(acord("C"), 3, 55, 79, None, "classic", "mitja", melodia=m)
        assert m not in v
        assert all(abs(p - m) > 1 for p in v)
    # i queda per sota de la melodia quan hi ha lloc
    v = vo.disposicio(acord("C"), 3, 55, 79, None, "classic", "mitja", melodia=76)
    assert max(v) < 76


def test_cap_segona_ni_setena_per_sota_de_do3():
    for f in ("C", "F", "G7", "Dm7", "Cmaj7"):
        for estil in ("classic", "swing", "pop"):
            v = vo.disposicio(acord(f), 3, 36, 76, None, estil, "avançat")
            parelles = [(a, b) for a, b in zip(v, v[1:]) if a < vo.LIMIT_GREU_FANG]
            assert all((b - a) % 12 not in (1, 2, 10, 11) for a, b in parelles), (f, estil, v)


def test_tessitura_dins_de_l_abast_de_l_instrument():
    for instrument in ("piano", "guitarra", "xilofon", "marimba"):
        i = inst.obtenir(instrument)
        for estil in arr.ESTILS:
            e, _ = genera(estil, ["C", "F", "G7", "C", "Am", "Dm7", "G7", "C"], instrument=instrument)
            lo, hi = (x + i.semitons() for x in inst.rang_midi(i.abast))      # so real (la guitarra sona una octava avall)
            assert all(lo <= p.midi <= hi for x in e for p in x.alt), (instrument, estil)


def test_compacte_retorna_un_acord_complet_en_el_registre():
    v = vo.compacte(acord("F"), 60, 79)
    assert sorted(p % 12 for p in v) == [0, 5, 9] and 60 <= min(v) and max(v) <= 79


def test_cap_estil_dona_compassos_buits_ni_errors_en_compassos_compostos():
    for estil in arr.ESTILS:
        e, _ = genera(estil, ["C", "F", "G7", "C"], ts="6/8")
        assert e
        e, _ = genera(estil, ["C", "F", "G7", "C"], ts="2/2")
        assert e
