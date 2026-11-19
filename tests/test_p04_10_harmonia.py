"""Paquets 4 i 10: comprovació d'harmonia amb notes estranyes, dominants secundaris i perfils;
harmonització de la melodia sola per nivell, ritme harmònic i mode modal."""
import pytest
from music21 import key, meter, note, stream

from partitures import arranjador as A
from partitures import harmonia as h
from partitures import harmonitzacio as hz
from partitures.cli import main
from partitures.errors import ErrorUsuari

DO = h.a_tonalitat("Do major")


def veus(linia):
    return h.llegir_linia(linia)


def comps(inc, nom):
    return [r for r in inc if r["comprovacio"] == nom]


# ---------- paquet 4 ----------

COR_AMB_PAS = "S: Mi4 Re4 Do4 | A: Mi3 Sol3 Fa3 | T: Mi3 Do3 Do3 | B: Do2 Do2 Fa1"


def test_nota_de_pas_al_soprano_no_dona_paraleles():
    v = veus(COR_AMB_PAS)
    assert h.paraleles(v, DO)   # sense filtre, la nota de pas fa unes quintes que no ho són
    assert h.classifica_notes(v)["S"] == ["real", "pas", "real"]
    for perfil in h.PERFILS:
        assert not comps(h.comprova_veus(v, DO, perfil=perfil), "paraleles")


def test_una_quinta_real_continua_sent_error():
    v = veus("S: Sol3 La3 | A: Mi3 Fa3 | T: Do3 Re3 | B: Do2 Re2")
    assert h.paraleles(v, DO)
    assert comps(h.comprova_veus(v, DO), "paraleles")


@pytest.mark.parametrize("tipus,linia,acords,llocs", [
    ("bordadura", "S: Mi4 Re4 Mi4", [{0, 4, 7}] * 3, None),
    ("pas", "S: Mi4 Re4 Do4", [{0, 4, 7}] * 3, None),
    ("anticipació", "S: Re4 Do4 Do4", [{7, 11, 2}, {7, 11, 2}, {0, 4, 7}], None),
    ("escapada", "S: Mi4 Re4 Sol4", [{0, 4, 7}] * 3, None),
    ("apoiatura", "S: Sol4 Fa4 Mi4", [{0, 4, 7}] * 3, [(1, 1), (2, 1), (2, 2)]),
])
def test_classifica_cada_tipus(tipus, linia, acords, llocs):
    nom, _, notes = linia.partition(":")
    v = {"S": [h.a_pitch(n) for n in notes.split()]}
    assert h.classifica_notes(v, acords=acords, llocs=llocs)["S"][1] == tipus


def test_nota_estranya_que_no_resol_no_s_amaga():
    v = {"S": [h.a_pitch(n) for n in "Mi4 Re4 Re4".split()]}
    assert h.classifica_notes(v, acords=[{0, 4, 7}] * 3)["S"][1] == "estranya"


def test_en_part_forta_una_nota_de_pas_no_ho_es():
    v = {"S": [h.a_pitch(n) for n in "Mi4 Re4 Do4".split()]}
    et = h.classifica_notes(v, acords=[{0, 4, 7}] * 3, llocs=[(1, 4), (2, 1), (2, 2)])
    assert et["S"][1] != "pas"


def test_setena_que_no_baixa_es_error_a_l_escola_i_info_a_l_arranjament():
    v = veus("S: Fa3 Sol3 | A: Re3 Mi3 | T: Si2 Do3 | B: Sol1 Do2")
    nivells = {p: [r["nivell"] for r in comps(h.comprova_veus(v, DO, perfil=p), "setena")] for p in h.PERFILS}
    assert nivells == {"escolar": ["error"], "arranjament": ["info"]}


V7_DE_V = "S: Fa#3 Sol3 | A: Do3 Si2 | T: La2 Sol2 | B: Re2 Sol1"


def test_dominant_secundari_no_dona_errors_de_sensible():
    v = veus(V7_DE_V)
    assert h._dominant_secundari(v, 0, DO).tonic.name == "G"
    for perfil in h.PERFILS:
        inc = h.comprova_veus(v, DO, perfil=perfil)
        assert not [r for r in inc if r["nivell"] == "error"]
        assert not comps(inc, "sensible_duplicada")


def test_dominant_secundari_es_avis_a_l_escola_i_res_a_l_arranjament():
    v = veus(V7_DE_V)
    assert [r["nivell"] for r in comps(h.comprova_veus(v, DO, perfil="escolar"), "dominant_secundari")] == ["avís"]
    assert not comps(h.comprova_veus(v, DO, perfil="arranjament"), "dominant_secundari")


def test_la_sensible_del_dominant_secundari_s_avalua_contra_el_seu_objectiu():
    v = veus("S: Fa#3 Mi3 | A: Do3 Si2 | T: La2 Sol2 | B: Re2 Sol1")
    assert any("Fa#3" in t for _, t in h.sensible(v, DO))


def test_sensible_duplicada_del_dominant_secundari():
    v = veus("S: Fa#3 Sol3 | A: Fa#3 Sol3 | T: Do3 Si2 | B: Re2 Sol1")
    assert h.sensible_duplicada(v, DO)


def test_falsa_relacio_i_registre_greu():
    assert h.falsa_relacio(veus("S: Mi3 Mi3 | A: Do3 Do3 | T: Sol2 Mi2 | B: Do2 Fa#1"), DO) == []
    assert h.falsa_relacio(veus("S: Do4 Do4 | A: Fa3 Sol3 | T: La2 Fa#3 | B: Do2 Do2"), DO)
    assert h.registre_greu(veus("S: Mi3 | A: Do3 | T: Fa1 | B: Mi1"), DO)
    assert not h.registre_greu(veus("S: Mi3 | A: Do3 | T: Sol2 | B: Do2"), DO)


def test_pesos_de_z5_07_baixen_amb_modificadors():
    # veu interior: el mateix error pesa un graó menys
    a = h.pes_incidencia("paraleles", 0, "quintes successives entre S i B", veus(COR_AMB_PAS), DO, "escolar")
    b = h.pes_incidencia("paraleles", 0, "quintes successives entre A i T", veus(COR_AMB_PAS), DO, "escolar")
    assert a - b == 1.0
    assert h.nivell_de_pes(a) == "error" and h.nivell_de_pes(1.4) == "avís" and h.nivell_de_pes(0.4) == "info"


def test_solidifica_agrupa_un_arpegi():
    notes = [h.a_pitch(n) for n in "Do2 Sol2 Mi3 Sol2 Do2 Mi3".split()]
    assert [[h.nom_nota(p) for p in g] for g in h.solidifica(notes, 3)] == [["Do2", "Sol2", "Mi3"], ["Do2", "Sol2", "Mi3"]]
    with pytest.raises(ValueError):
        h.solidifica(notes, 0)


def test_cli_perfil(tmp_path, capsys):
    sc = stream.Score()
    for v, txt in {"S": "Fa3 Sol3", "A": "Re3 Mi3", "T": "Si2 Do3", "B": "Sol1 Do2"}.items():
        p = stream.Part()
        p.append(key.Key("C")); p.append(meter.TimeSignature("4/4"))
        for n in txt.split():
            p.append(note.Note(h.a_pitch(n), type="quarter"))
        sc.insert(0, p)
    f = tmp_path / "c.musicxml"
    sc.write("musicxml", fp=str(f))
    assert main(["harmonia", "comprova", str(f), "--perfil", "arranjament"]) == 0
    assert "perfil arranjament" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        main(["harmonia", "comprova", str(f), "--perfil", "inventat"])


def test_fitxes_noves_es_poden_mostrar():
    assert "notes estranyes" in h.text_fitxa("notes-d-acord")
    assert "Dominants secundaris" in h.text_fitxa("dominants-secundaris")


# ---------- paquet 10 ----------

ODE = [("E4", 1), ("E4", 1), ("F4", 1), ("G4", 1), ("G4", 1), ("F4", 1), ("E4", 1), ("D4", 1),
       ("C4", 1), ("C4", 1), ("D4", 1), ("E4", 1), ("E4", 1.5), ("D4", .5), ("D4", 2),
       ("E4", 1), ("E4", 1), ("F4", 1), ("G4", 1), ("G4", 1), ("F4", 1), ("E4", 1), ("D4", 1),
       ("C4", 1), ("C4", 1), ("D4", 1), ("E4", 1), ("D4", 1.5), ("C4", .5), ("C4", 2)]


def _melodia(notes, tonalitat="C", ts="4/4"):
    s = stream.Score()
    p = stream.Part()
    p.append(key.Key(tonalitat)); p.append(meter.TimeSignature(ts))
    for n, d in notes:
        p.append(note.Rest(quarterLength=d) if n is None else note.Note(n, quarterLength=d))
    p.makeMeasures(inPlace=True)
    s.insert(0, p)
    return s


def _harm(notes, curs=None, mode="auto", tonalitat="C", fixa=None, estil="pop"):
    s = _melodia(notes, tonalitat)
    staff = s.parts[0]
    segs = A._segments(A._compassos(staff), [])
    evs = A._linia_superior(staff)
    k = fixa or A.analitzar_tonalitat(evs, segs, s, False)
    descripcio = A.harmonitzar(evs, segs, k, estil, curs, mode)
    return k, evs, segs, descripcio


def _noms(segs):
    return [s.acord.nom() for s in segs if s.acord]


def test_nivell_harmonic():
    assert [hz.nivell_harmonic(c) for c in (None, "4t elemental", "2n professional", "5e")] == \
        ["mitja", "elemental", "avancat", "mitja"]


def test_ode_a_l_alegria_acaba_amb_cadencia_i_noms_acords_diatonics():
    _, _, segs, d = _harm(ODE)
    n = _noms(segs)
    assert n[0] == "Do" and n[-1] == "Do" and n[-2] in ("Sol", "Sol7")
    assert set(n) <= {"Do", "Rem", "Mim", "Fa", "Sol", "Sol7", "Lam"}
    assert "harmonització per regles" in d
    assert any(x.startswith("Sol") for x in n[:8]) and any(x.startswith("Sol") for x in n[8:])


def test_la_nota_de_temps_fort_es_de_l_acord():
    _, evs, segs, _ = _harm(ODE)
    for s in segs:
        notes = A._notes_entre(evs, s.ini, s.ini + 0.01)
        if notes:
            pc = notes[0][0].alt[0].pitchClass
            assert pc in s.acord.pcs or (pc - s.acord.arrel.pitchClass) % 12 in (2, 9)


def test_elemental_un_acord_per_compas_i_nomes_acords_basics():
    _, _, segs, d = _harm(ODE, curs="4t elemental")
    assert set(_noms(segs)) <= {"Do", "Fa", "Sol", "Lam"}
    for c in {id(s.compas) for s in segs}:
        assert len({s.acord.figura for s in segs if id(s.compas) == c}) == 1
    assert "un acord per compàs" in d


def test_mode_simple_no_fa_servir_setenes_ni_ii():
    _, _, segs, _ = _harm(ODE, mode="simple")
    assert set(_noms(segs)) <= {"Do", "Fa", "Sol"}


MIXOLIDI = [("C4", 1), ("D4", 1), ("E4", 1), ("G4", 1), ("A4", 1), ("B-4", 1), ("G4", 1), ("E4", 1),
            ("F4", 1), ("E4", 1), ("D4", 1), ("C4", 1), ("C4", 4)]


def test_melodia_modal_no_porta_v7_ni_sensible():
    k = key.Key("C")
    s = _melodia(MIXOLIDI)
    evs = A._linia_superior(s.parts[0])
    assert hz.detecta_mode(evs, k) == "modal"
    _, _, segs, d = _harm(MIXOLIDI, fixa=k)
    n = _noms(segs)
    assert not any("7" in x for x in n)
    assert all("Si" != x[:2] or x.startswith("Sib") for x in n) and "modal" in d
    assert n[0] == "Do" and n[-1] == "Do"


def test_detecta_pentatonica_i_classica():
    k = key.Key("C")
    pent = _melodia([("C4", 1), ("D4", 1), ("E4", 1), ("G4", 1), ("A4", 1), ("G4", 1), ("E4", 1), ("C4", 1)])
    assert hz.detecta_mode(A._linia_superior(pent.parts[0]), k) == "pentatonic"
    assert hz.detecta_mode(A._linia_superior(_melodia(ODE).parts[0]), k) == "classic"


def test_avançat_posa_v7_de_v_quan_la_melodia_porta_la_sensible_de_v():
    mel = [("G4", 1), ("E4", 1), ("C4", 1), ("E4", 1), ("A4", 1), ("F#4", 1), ("D5", 2),
           ("G4", 1), ("F#4", 1), ("A4", 1), ("D5", 1), ("B4", 1), ("G4", 1), ("A4", 1), ("F#4", 1),
           ("G4", 4)]
    k = key.Key("G")
    _, _, segs, d = _harm(mel, curs="2n professional", fixa=key.Key("C"))
    assert "Re7" in _noms(segs) and "avançat" in d
    _, _, segs2, _ = _harm(mel, curs="4t elemental", fixa=key.Key("C"))
    assert not any("7" in x for x in _noms(segs2))


def test_sense_nota_cromatica_no_hi_ha_dominants_secundaris():
    _, _, segs, _ = _harm(ODE, curs="2n professional")
    assert set(_noms(segs)) <= {"Do", "Rem", "Mim", "Fa", "Sol", "Sol7", "Lam", "Re7", "Mi7", "La7", "Do7", "Sib", "Fam"} - \
        {"Re7", "Mi7", "La7", "Do7", "Sib", "Fam"}


def test_harmonitzar_es_determinista():
    a = _noms(_harm(ODE)[2])
    assert a == _noms(_harm(ODE)[2])


def test_cli_harmonia_te_opcions_valides():
    with pytest.raises(SystemExit):
        main(["arranja", "x.musicxml", "--rols", "melodia=flauta", "--harmonia", "inventada"])
