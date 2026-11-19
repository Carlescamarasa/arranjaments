"""Proves dels paquets 3 i 12: parts llegibles (lletres d'assaig, multicompàs, estil, claudàtors) i cues, girs de pàgina."""
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
from music21 import expressions, layout, meter, note, stream, tempo

from partitures import arranjador as arr
from partitures import cues, eines, externs, girs, musica, parts
from partitures import instruments as inst


# --------------------------------------------------------------------------- ajudes

def _part(buits=(), n=16, notes=("C4",), ts="4/4"):
    """Part amb n compassos; els índexs de `buits` porten només un silenci."""
    p = stream.Part()
    dur = meter.TimeSignature(ts).barDuration.quarterLength
    for i in range(n):
        m = stream.Measure(number=i + 1)
        if i == 0:
            m.timeSignature = meter.TimeSignature(ts)
        if i in buits:
            m.append(note.Rest(quarterLength=dur))
        else:
            for k, nom in enumerate(notes):
                m.append(note.Note(nom, quarterLength=dur / len(notes)))
        p.append(m)
    return p


def _rol(rol, clau):
    return arr.Rol(rol, next(i for i in inst.CATALEG if i.clau == clau))


def _construides(*especs):
    """especs: (rol, clau, part)."""
    return [(_rol(r, c), [p], None) for r, c, p in especs]


def _rang(instr):
    lo, hi = inst.rang_midi(instr.abast)
    t = instr.semitons()
    return lo + t, hi + t


def _mscore_real():
    try:
        return eines.trobar_musescore()
    except Exception:
        return None


# --------------------------------------------------------------------------- lletres d'assaig

def test_lletres_assaig_a_z_i_despres_dobles():
    assert [parts.lletra_assaig(i) for i in (0, 1, 25, 26, 27, 52)] == ["A", "B", "Z", "AA", "BB", "AAA"]


def test_lletres_es_posen_a_l_inici_de_cada_seccio_i_es_copien_a_totes_les_parts():
    sc = stream.Score()
    for _ in range(2):
        sc.insert(0, _part(n=24))
    posades = parts.posar_lletres(sc.parts[0], [0, 8, 16])
    assert posades == [(0, "A"), (8, "B"), (16, "C")]
    assert parts.lletres_de(sc) == {0: "A", 8: "B", 16: "C"}
    # només a la pauta de dalt del guió
    assert not list(sc.parts[1].recurse().getElementsByClass(expressions.RehearsalMark))
    # cada particel·la repeteix les mateixes lletres a la mateixa posició
    for _nom, ps in musica.parts_separades(sc):
        assert parts.lletres_de(ps) == {0: "A", 8: "B", 16: "C"}


def test_amb_una_sola_seccio_no_hi_ha_lletres():
    assert parts.posar_lletres(_part(n=8), [0]) == []


def test_amb_anacrusi_la_primera_lletra_va_al_primer_compas_complet():
    posades = parts.posar_lletres(_part(n=10), [0, 5], anacrusi=True)
    assert posades == [(1, "A"), (5, "B")]


def test_arranjar_posa_lletres_a_la_pauta_de_dalt_i_les_parts_les_hereten(bressol_llarg):
    s = musica.carregar(bressol_llarg)
    rols = arr.parse_rols("melodia=trompeta-sib,contracant=flauta,acompanyament=clarinet-sib,baix=trombo")
    for rotacio in (True, False):
        r, informe = arr.arranjar(s, rols, estil="marxa", curs="4t elemental", rotacio=rotacio)
        marques = parts.lletres_de(r)
        assert len(marques) >= 2 and list(marques.values())[0] == "A"
        amb = [p for p in r.parts if list(p.recurse().getElementsByClass(expressions.RehearsalMark))]
        assert len(amb) == 1                      # al guió només la pauta de dalt
        assert any(l.startswith("Lletres d'assaig:") for l in informe)
        for _nom, ps in musica.parts_separades(r):
            assert parts.lletres_de(ps) == marques


@pytest.fixture(scope="module")
def bressol_llarg(tmp_path_factory):
    """Una melodia de 24 compassos en 4/4 (do major), prou llarga per a tenir diverses frases."""
    sc = stream.Score()
    p = stream.Part()
    notes = ["C5", "D5", "E5", "G5", "E5", "D5", "C5", "E5"]
    for i in range(24):
        m = stream.Measure(number=i + 1)
        if i == 0:
            m.timeSignature = meter.TimeSignature("4/4")
        for k in range(4):
            m.append(note.Note(notes[(i + k) % 8], quarterLength=1))
        p.append(m)
    p.measure(24).rightBarline = None
    sc.insert(0, p)
    ruta = tmp_path_factory.mktemp("dades") / "llarga.musicxml"
    sc.write("musicxml", fp=str(ruta))
    return ruta


# --------------------------------------------------------------------------- silencis multicompàs i salts de sistema

def test_un_silenci_de_10_compassos_es_un_sol_grup_i_una_lletra_el_parteix():
    p = _part(buits=range(2, 12), n=14)
    assert parts.grups_buits(p) == [(2, 11)]
    p.measure(8).insert(0, expressions.RehearsalMark("B"))
    assert parts.grups_buits(p) == [(2, 6), (7, 11)]


def test_un_sol_compas_buit_no_es_agrupa():
    assert parts.grups_buits(_part(buits=[3], n=8)) == []


def test_salts_de_sistema_cada_4_compassos_i_a_cada_seccio():
    p = _part(n=18)
    posats = parts.posar_salts_sistema(p, [0, 10])
    assert posats == [4, 8, 10, 14]


def test_salts_de_sistema_un_silenci_multicompas_compta_com_una_caixa():
    p = _part(buits=range(1, 9), n=16)
    posats = parts.posar_salts_sistema(p, [0])
    # caixes: c0, [1-8], c9, c10 | el salt cau abans de c11 (el silenci de 8 compassos compta com una sola)
    assert posats[0] == 11


def test_l_anacrusi_no_obliga_a_sistema_nou_a_la_lletra_a():
    p = _part(n=10)
    ms = list(p.getElementsByClass(stream.Measure))
    ms[0].remove(list(ms[0].notes)[0])
    ms[0].append(note.Note("C4", quarterLength=1))   # compàs 0 de només 1 pulsació: anacrusi
    assert 1 not in parts.posar_salts_sistema(p, [1, 5])


# --------------------------------------------------------------------------- estil dins del .mscz

def _mscz_minim(ruta: Path) -> Path:
    with zipfile.ZipFile(ruta, "w") as z:
        z.writestr("score_style.mss", '<?xml version="1.0" encoding="UTF-8"?>\n<museScore version="4.70"><Style>'
                   '<spatium>1.75</spatium><createMultiMeasureRests>0</createMultiMeasureRests></Style></museScore>')
        z.writestr("x.mscx", "<museScore/>")
    return ruta


def test_estil_de_part_es_escriu_dins_del_mscz(tmp_path):
    f = _mscz_minim(tmp_path / "a.mscz")
    parts.aplica_estil_mscz(f, parts.estil_part(2.1, "Clarinet en Si bemoll"))
    e = parts.llig_estil_mscz(f)
    assert e["createMultiMeasureRests"] == "1" and e["minEmptyMeasures"] == "2" and e["spatium"] == "2.1"
    assert e["measureNumberSystem"] == "1"          # número a l'inici de cada sistema
    assert e["oddHeaderC"] == "Clarinet en Si bemoll" and e["headerFirstPage"] == "0"
    with zipfile.ZipFile(f) as z:
        assert "x.mscx" in z.namelist()


def test_estil_de_guio_sense_multicompas_i_pauta_petita(tmp_path):
    f = _mscz_minim(tmp_path / "a.mscz")
    parts.aplica_estil_mscz(f, parts.estil_guio())
    e = parts.llig_estil_mscz(f)
    assert e["createMultiMeasureRests"] == "0" and e["spatium"] == "1.375"


def test_mides_de_pauta_dels_perfils():
    assert parts.perfil("elemental")["spatium"] > parts.perfil("normal")["spatium"] > parts.perfil("guio")["spatium"]
    # alumne petit entre 8 i 9,2 mm d'alçada de pauta (spatium x 4), normal entre 6,7 i 7, guió entre 5 i 6
    assert 8 <= 4 * parts.perfil("elemental")["spatium"] <= 9.2
    assert 6.7 <= 4 * parts.perfil("normal")["spatium"] <= 7
    assert 5 <= 4 * parts.perfil("guio")["spatium"] <= 6


def test_el_nivell_viatja_dins_del_musicxml(tmp_path):
    sc = stream.Score()
    sc.insert(0, _part(n=2))
    parts.desa_nivell(sc, "4t elemental")
    f = tmp_path / "a.musicxml"
    sc.write("musicxml", fp=str(f))
    assert parts.nivell_de(musica.carregar(f)) == "4t elemental"


# --------------------------------------------------------------------------- ordre i claudàtors

def test_ordre_del_guio_segons_gould():
    claus = ["violoncel", "piano", "xilofon", "trombo", "trompeta-sib", "clarinet-sib", "flauta"]
    rols = [arr.Rol("melodia", next(i for i in inst.CATALEG if i.clau == c)) for c in claus]
    ordenats = [r.instr.clau for r in sorted(rols, key=arr._ordre)]
    assert ordenats == ["flauta", "clarinet-sib", "trompeta-sib", "trombo", "xilofon", "piano", "violoncel"]


def test_claudators_per_familia_si_hi_ha_6_pautes_o_mes():
    u = [(c, [object()]) for c in ("flauta", "clarinet-sib", "trompeta-sib", "trombo", "xilofon", "violoncel")]
    g = dict(parts.grups_claudators(u))
    assert set(g) == {"fusta", "metall", "percussio", "corda"} and len(g["fusta"]) == 2


def test_un_sol_claudator_en_un_guio_petit_i_cap_si_hi_ha_piano():
    petit = [(c, [object()]) for c in ("flauta", "trompeta-sib", "trombo")]
    assert [n for n, _ in parts.grups_claudators(petit)] == ["conjunt"]
    amb_piano = petit + [("piano", [object(), object()])]
    assert parts.grups_claudators(amb_piano) == []


def test_arranjar_porta_claudators_a_part_dels_claus(bressol_llarg):
    s = musica.carregar(bressol_llarg)
    rols = arr.parse_rols("melodia=trompeta-sib,contracant=flauta,acompanyament=clarinet-sib,baix=trombo,"
                          "percussio=bateria,acompanyament=piano")
    r, _ = arr.arranjar(s, rols, estil="marxa", curs="4t elemental")
    simbols = sorted(g.symbol for g in r.getElementsByClass(layout.StaffGroup))
    assert simbols.count("bracket") >= 2 and simbols.count("brace") == 1


# --------------------------------------------------------------------------- cues d'orientació

def test_cue_d_orientacio_despres_de_8_compassos_de_silenci_transposada_a_sib():
    cl = _part(buits=range(0, 8), n=12, notes=("C4",))
    fl = _part(n=12, notes=("C5", "D5", "E5", "F5"))
    c = _construides(("melodia", "flauta", fl), ("acompanyament", "clarinet-sib", cl))
    fetes = cues.cues_orientacio(c, _rang, elemental=False)
    assert [f.compassos for f in fetes] == [[7, 8]]
    ms = list(cl.getElementsByClass(stream.Measure))
    for k in (6, 7):
        notes = list(ms[k].notes)
        assert notes and all(n.style.noteSize == "cue" for n in notes)
    assert not list(ms[5].notes)                       # els compassos anteriors continuen en silenci
    etiq = [t.content for t in ms[6].getElementsByClass(expressions.TextExpression)]
    assert etiq == ["+ Fl."]
    # en vestir la part, la cue es transposa al clarinet en Si bemoll (so real Do5 -> escrit Re5)
    instr = next(i for i in inst.CATALEG if i.clau == "clarinet-sib")
    arr._vestir(cl, instr, None, None)
    primera = list(cl.getElementsByClass(stream.Measure))[6].notes[0]
    assert primera.pitch.nameWithOctave == "D5"


def test_cue_no_en_elemental_amb_silenci_de_2_compassos():
    cl = _part(buits=[3, 4], n=12)
    fl = _part(n=12, notes=("C5", "D5"))
    assert cues.cues_orientacio(_construides(("melodia", "flauta", fl), ("acompanyament", "clarinet-sib", cl)),
                                _rang, elemental=True) == []


def test_en_elemental_un_silenci_de_4_compassos_ja_te_cue_i_en_general_no():
    def fes():
        cl = _part(buits=range(2, 6), n=12)
        fl = _part(n=12, notes=("C5", "D5"))
        return cl, _construides(("melodia", "flauta", fl), ("acompanyament", "clarinet-sib", cl))
    cl, c = fes()
    assert len(cues.cues_orientacio(c, _rang, elemental=True)) == 1
    cl, c = fes()
    assert cues.cues_orientacio(c, _rang, elemental=False) == []


def test_la_cue_triada_es_la_de_qui_porta_la_melodia_i_no_un_acord():
    cl = _part(buits=range(0, 6), n=10)
    acords = _part(n=10, notes=("C4",))
    for m in acords.getElementsByClass(stream.Measure):
        for n in list(m.notes):
            m.remove(n)
        from music21 import chord
        m.append(chord.Chord(["C4", "E4", "G4"], quarterLength=4))
    fl = _part(n=10, notes=("C5", "E5"))
    c = _construides(("acompanyament", "guitarra", acords), ("melodia", "flauta", fl),
                     ("contracant", "clarinet-sib", cl))
    fetes = cues.cues_orientacio(c, _rang, elemental=True)
    assert len(fetes) == 1 and fetes[0].origen == "Flauta"


def test_una_cue_que_no_cap_al_registre_del_receptor_es_baixa_d_octava_o_es_descarta():
    tuba = _part(buits=range(0, 6), n=10)
    fl = _part(n=10, notes=("C6", "E6"))
    fetes = cues.cues_orientacio(_construides(("melodia", "flauta", fl), ("baix", "tuba", tuba)), _rang, True)
    lo, hi = _rang(next(i for i in inst.CATALEG if i.clau == "tuba"))
    for m in tuba.getElementsByClass(stream.Measure):
        assert all(lo <= n.pitch.midi <= hi for n in m.notes)
    assert all(abs(f.transposicio) % 12 == 0 for f in fetes)


# --------------------------------------------------------------------------- cues d'instrument absent

def test_sense_baix_la_seva_linia_apareix_com_a_cue_al_trombo_amb_l_etiqueta():
    trb = _part(buits=range(0, 8), n=12, notes=("E2", "G2"))   # si falta el fagot
    fag = _part(n=12, notes=("C2", "G2"))
    for m in list(fag.getElementsByClass(stream.Measure))[8:]:
        for n in list(m.notes):
            m.remove(n)
        m.append(note.Rest(quarterLength=4))
    c = _construides(("melodia", "trombo", trb), ("baix", "fagot", fag))
    # el fagot (baix) toca als compassos 1-8; el trombó calla: el fagot s'hi cuea
    fetes = cues.cues_absents(c, _rang, article=arr._amb_article)
    assert fetes and fetes[0].tipus == "absent" and fetes[0].receptor == "Trombó"
    ms = list(trb.getElementsByClass(stream.Measure))
    txt = [t.content for m in ms for t in m.getElementsByClass(expressions.TextExpression)]
    assert any(t.startswith("Toqueu les notes petites si falta el fagot") for t in txt)
    assert all(n.style.noteSize == "cue" for n in ms[0].notes)


def test_cues_de_so_real_no_toquen_percussio():
    bat = _part(buits=range(0, 8), n=10)
    fl = _part(n=10, notes=("C5", "D5"))
    c = [(_rol("melodia", "flauta"), [fl], None), (_rol("percussio", "bateria"), [bat], None)]
    assert cues.cues_orientacio(c, _rang, True) == []
    assert not list(bat.measure(1).notes) and not list(bat.measure(8).notes)


# --------------------------------------------------------------------------- MusicXML: cues sense so

def test_les_notes_petites_porten_cue_al_musicxml(tmp_path):
    p = _part(n=2)
    n = list(p.measure(1).notes)[0]
    n.style.noteSize = "cue"
    sc = stream.Score()
    sc.insert(0, p)
    f = tmp_path / "a.musicxml"
    sc.write("musicxml", fp=str(f))
    assert cues.silencia_cues_xml(f) == 1
    t = f.read_text(encoding="utf-8")
    assert t.count("<cue />") == 1 and 'size="cue"' in t
    assert cues.silencia_cues_xml(f) == 0            # idempotent


# --------------------------------------------------------------------------- girs de pàgina

MPOS = '<score><elements>' + "".join(f'<element id="{i}" x="1" y="1" sx="1" sy="1" page="{p}"></element>'
                                     for i, p in enumerate([0, 0, 0, 1, 1])) + '</elements></score>'


def test_pagines_de_mpos():
    assert girs.pagines_de_mpos(MPOS) == [0, 0, 0, 1, 1]


def test_pagines_per_compas_amb_multicompas_i_desquadrament():
    p = _part(buits=range(1, 5), n=8)           # c0 | [1-4] | c5 c6 c7  -> 5 caixes
    assert girs.pagines_per_compas(p, [0, 0, 0, 1, 1]) == [0, 0, 0, 0, 0, 0, 1, 1]
    assert girs.pagines_per_compas(p, [0, 0, 1]) is None        # no quadra: no s'endevina


def test_un_gir_en_silenci_llarg_es_bo_i_un_gir_en_notes_no():
    p = _part(buits=range(4, 8), n=12)          # 4/4 a negra=60: 4 s per compàs
    pc = [0] * 8 + [1] * 4
    g = girs.avalua_girs(p, pc, 60, 4.0)
    assert len(g) == 1 and g[0].be and g[0].compas_nou == 8
    pc2 = [0] * 3 + [1] * 9
    g2 = girs.avalua_girs(p, pc2, 60, 4.0)
    assert not g2[0].be and g2[0].segons == 0


def test_el_gir_necessita_4_segons_i_depen_del_tempo():
    p = _part(buits=range(6, 8), n=12)
    pc = [0] * 8 + [1] * 4
    assert girs.avalua_girs(p, pc, 120, 4.0)[0].be          # 2 compassos a 120: 2 x 2 s = 4 s
    assert not girs.avalua_girs(p, pc, 240, 4.0)[0].be      # a 240: 2 s


def test_el_contrabaix_necessita_5_segons():
    assert girs.segons_minims("contrabaix") == 5.0 and girs.segons_minims("flauta") == 4.0


def test_proposa_un_salt_al_silenci_llarg_i_mai_a_mitja_nota():
    p = _part(buits=[5, 6, 7], n=14)             # silenci als compassos 5-7 (c. 8 ja hi ha notes)
    pc = [0] * 10 + [1] * 4                      # el gir (c. 10) cau enmig de notes
    g = girs.avalua_girs(p, pc, 60, 4.0)[0]
    assert not g.be
    salt = girs.proposa_salt(p, g, pc, 60, 4.0)
    assert salt == 8                              # pàgina nova just després del silenci
    girs.posa_salt_pagina(p, salt)
    assert list(p.measure(9).getElementsByClass(layout.PageLayout))


def test_no_proposa_cap_salt_si_no_hi_ha_silenci_de_4_segons():
    p = _part(buits=[5], n=14)                   # un compàs de 4/4 a negra=120 són 2 s
    pc = [0] * 10 + [1] * 4
    g = girs.avalua_girs(p, pc, 120, 4.0)[0]
    assert girs.proposa_salt(p, g, pc, 120, 4.0) is None


def test_un_salt_que_deixaria_la_pagina_quasi_buida_no_es_proposa():
    p = _part(buits=[1, 2, 3], n=14)             # silenci al principi de la pàgina
    pc = [0] * 12 + [1] * 2
    g = girs.avalua_girs(p, pc, 60, 4.0)[0]
    assert girs.proposa_salt(p, g, pc, 60, 4.0) is None


def test_bpm_del_tempo_de_la_partitura():
    sc = stream.Score()
    p = _part(n=2)
    p.measure(1).insert(0, tempo.MetronomeMark(number=80))
    sc.insert(0, p)
    assert girs.bpm_de(sc) == (80.0, False)
    sc2 = stream.Score()
    sc2.insert(0, _part(n=2))
    assert girs.bpm_de(sc2) == (girs.BPM_PER_DEFECTE, True)


# --------------------------------------------------------------------------- exportar amb MuseScore fals

def test_exportar_aplica_estil_de_guio_al_mscz_i_de_part_a_les_particelles(tmp_path, projecte, monkeypatch):
    estils = []
    crides_pos = []

    def fals(mscore, origen, desti, temps_maxim=300):
        Path(desti).parent.mkdir(parents=True, exist_ok=True)
        if Path(desti).suffix == ".mscz":
            _mscz_minim(Path(desti))
        else:
            Path(desti).write_bytes(b"pdf")

    def fals_pos(mscore, origen, pdf, mpos, temps_maxim=300):
        estils.append(parts.llig_estil_mscz(origen))
        crides_pos.append(Path(pdf).name)
        Path(pdf).write_bytes(b"pdf")
        Path(mpos).write_text('<score><elements><element id="0" page="0"></element></elements></score>')
    monkeypatch.setattr(eines, "trobar_musescore", lambda: "/fals/mscore")
    monkeypatch.setattr(externs, "_mscore_a_pdf", fals)
    monkeypatch.setattr(externs, "_mscore_pdf_amb_posicions", fals_pos)
    sc = stream.Score()
    sc.insert(0, _part(n=6))
    sc.insert(0, _part(n=6))
    for p, nom in zip(sc.parts, ("Flauta", "Trompeta")):
        p.partName = nom
    xml = projecte / "entrada" / "dos.musicxml"
    sc.write("musicxml", fp=str(xml))
    r = externs.exportar(xml)
    assert len(r["parts"]) == 2
    assert parts.llig_estil_mscz(r["mscz"])["createMultiMeasureRests"] == "0"       # guió: sense multicompàs
    assert len(estils) == 2 and all(e["createMultiMeasureRests"] == "1" for e in estils)
    assert all(float(e["spatium"]) > 1.6 for e in estils)


def test_exportar_en_elemental_dona_pauta_gran_i_en_la_resta_la_normal(tmp_path, projecte, monkeypatch):
    mides = []

    def fals(mscore, origen, desti, temps_maxim=300):
        Path(desti).parent.mkdir(parents=True, exist_ok=True)
        _mscz_minim(Path(desti)) if Path(desti).suffix == ".mscz" else Path(desti).write_bytes(b"pdf")

    def fals_pos(mscore, origen, pdf, mpos, temps_maxim=300):
        mides.append(float(parts.llig_estil_mscz(origen)["spatium"]))
        Path(pdf).write_bytes(b"pdf")
        Path(mpos).write_text('<score><elements><element id="0" page="0"></element></elements></score>')
    monkeypatch.setattr(eines, "trobar_musescore", lambda: "/fals/mscore")
    monkeypatch.setattr(externs, "_mscore_a_pdf", fals)
    monkeypatch.setattr(externs, "_mscore_pdf_amb_posicions", fals_pos)
    for curs, esperada in (("4t elemental", parts.perfil("elemental")["spatium"]), (None, parts.perfil("normal")["spatium"])):
        sc = stream.Score()
        sc.insert(0, _part(n=6))
        sc.insert(0, _part(n=6))
        parts.desa_nivell(sc, curs)
        xml = projecte / "entrada" / f"x{curs is None}.musicxml"
        sc.write("musicxml", fp=str(xml))
        mides.clear()
        externs.exportar(xml)
        assert mides == [esperada, esperada]


# --------------------------------------------------------------------------- amb MuseScore de veritat (si hi és)

@pytest.mark.skipif(_mscore_real() is None, reason="MuseScore no està instal·lat")
def test_musescore_agrupa_silencis_amb_l_estil_escrit_al_mscz(tmp_path):
    sc = stream.Score()
    p = _part(buits=range(1, 11), n=12)
    p.measure(1).insert(0, tempo.MetronomeMark(number=100))
    sc.insert(0, p)
    xml = tmp_path / "p.musicxml"
    sc.write("musicxml", fp=str(xml))
    ms = _mscore_real()
    mscz = tmp_path / "p.mscz"
    externs._mscore_a_pdf(ms, xml, mscz)
    pdf, mpos = tmp_path / "a.pdf", tmp_path / "a.mpos"
    externs._mscore_pdf_amb_posicions(ms, mscz, pdf, mpos)
    sense = len(girs.pagines_de_mpos(mpos.read_text()))
    parts.aplica_estil_mscz(mscz, parts.estil_part(2.1, "Flauta"))
    externs._mscore_pdf_amb_posicions(ms, mscz, pdf, mpos)
    amb = girs.pagines_de_mpos(mpos.read_text())
    assert sense == 12 and len(amb) == 3                     # c0 | multicompàs de 10 | c11
    assert len(amb) == len(parts.unitats_de_lectura(p))      # el que calcula el codi i el que fa MuseScore coincideixen
    assert pdf.exists() and pdf.stat().st_size > 0
