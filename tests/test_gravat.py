"""Proves del gravat (paquets 1 i 2): durades i silencis per la mètrica, matisos, articulacions i respiracions."""
import pytest
from music21 import articulations, corpus, dynamics, meter, note, stream, tempo, tie

from partitures import arranjador as arr
from partitures import cli, gravat, musica
from partitures import instruments as inst


def ts(t):
    return meter.TimeSignature(t)


# --------------------------------------------------------------------------- paquet 2: durades

@pytest.mark.parametrize("compas, inici, dur, esperat", [
    # 4/4 (Herrera ENG-01)
    ("4/4", 0, 4, [4]),
    ("4/4", 0, 3, [3]),                    # blanca amb punt al temps 1
    ("4/4", 1, 2, [2]),                    # blanca al temps 2: no es lliga
    ("4/4", 1, 3, [3]),                    # blanca amb punt al temps 2
    ("4/4", 0.5, 2, [0.5, 1, 0.5]),        # res creua la pulsació des d'un contratemps
    ("4/4", 1.5, 2, [0.5, 1.5]),           # blanca que comença al "i" del temps 2
    ("4/4", 1.5, 1, [0.5, 0.5]),           # la negra a contratemps del temps 2 creua el mig
    ("4/4", 0.5, 1, [1]),                  # corxera-negra-corxera: es queda
    ("4/4", 2.5, 1, [1]),
    ("4/4", 0, 2.5, [2, 0.5]),
    ("4/4", 1, 1.5, [1, 0.5]),             # la negra amb punt al temps 2 creua el mig
    ("4/4", 0.5, 3, [0.5, 1, 1.5]),
    ("4/4", 2, 2, [2]),
    ("4/4", 3, 1, [1]),
    # 3/4 (Gould SU-01)
    ("3/4", 0, 3, [3]),
    ("3/4", 0, 2, [2]),
    ("3/4", 1, 2, [2]),
    ("3/4", 0.5, 2, [0.5, 1.5]),
    ("3/4", 0.5, 2.5, [0.5, 2]),
    # 2/4
    ("2/4", 0, 2, [2]),
    ("2/4", 0.5, 1.5, [0.5, 1]),
    ("2/4", 0.25, 0.5, [0.5]),             # semicorxera-corxera-semicorxera (ragtime)
    # compostos (Gould SU-02)
    ("6/8", 0, 3, [3]),
    ("6/8", 0, 1.5, [1.5]),
    ("6/8", 0, 2, [1.5, 0.5]),
    ("6/8", 1, 1, [0.5, 0.5]),             # una negra que comença a la tercera corxera creua la pulsació
    ("6/8", 0.5, 1, [1]),
    ("12/8", 0, 6, [6]),
    ("12/8", 1.5, 3, [1.5, 1.5]),          # no creua el mig del compàs
    ("9/8", 0, 4.5, [1.5, 3]),
    # irregulars (Gould BM-06b)
    ("5/8", 0, 2.5, [1.5, 1]),
])
def test_parteix_durada(compas, inici, dur, esperat):
    assert gravat.parteix_durada(inici, dur, ts(compas)) == esperat


@pytest.mark.parametrize("compas", ["2/4", "3/4", "4/4", "6/8", "9/8", "12/8", "5/8", "7/8"])
def test_la_suma_de_durades_no_canvia(compas):
    t = ts(compas)
    barra = float(t.barDuration.quarterLength)
    pas = 0.25
    n = int(barra / pas)
    for i in range(n):
        for k in range(1, n - i + 1):
            trossos = gravat.parteix_durada(i * pas, k * pas, t)
            assert sum(float(x) for x in trossos) == pytest.approx(k * pas)
            assert all(any(abs(float(x) - f) < 1e-6 for f in gravat.FIGURES) for x in trossos)


@pytest.mark.parametrize("compas, inici, dur, esperat", [
    ("4/4", 0, 3, [2, 1]),                 # silenci de 3 temps: blanca i negra, no blanca amb punt
    ("4/4", 1, 3, [1, 2]),
    ("4/4", 1, 2, [1, 1]),                 # no un silenci de dues negres que travessa el mig
    ("4/4", 0, 4, [4]),
    ("4/4", 0, 2, [2]),
    ("4/4", 2, 2, [2]),
    ("4/4", 0.5, 0.5, [0.5]),
    ("3/4", 0, 2, [1, 1]),                 # en 3/4 mai un silenci de dues negres
    ("3/4", 1, 2, [1, 1]),
    ("3/4", 0, 3, [3]),
    ("2/4", 0, 2, [2]),
    ("6/8", 0, 3, [3]),
    ("6/8", 0, 1.5, [1.5]),
    ("6/8", 0.5, 1, [0.5, 0.5]),           # no creua la pulsació
    ("12/8", 0, 4.5, [3, 1.5]),
])
def test_parteix_silenci(compas, inici, dur, esperat):
    assert gravat.parteix_silenci(inici, dur, ts(compas)) == esperat


def test_els_tresets_es_deixen_com_arriben():
    assert gravat.parteix_durada(0, 2 / 3, ts("4/4")) == [pytest.approx(2 / 3)]


def test_talla_nota_lliga_les_figures_i_conserva_les_lligadures_d_entrada():
    x = note.Note("C5")
    res = gravat.talla_nota(x, 1.5, 2, ts("4/4"), ve=True, va=True)
    assert [float(n.quarterLength) for n in res] == [0.5, 1.5]
    assert [n.tie.type for n in res] == ["continue", "continue"]
    res = gravat.talla_nota(note.Note("C5"), 0.5, 3, ts("4/4"))
    assert [n.tie.type for n in res] == ["start", "continue", "stop"]
    res = gravat.talla_nota(note.Note("C5"), 0, 1, ts("4/4"))
    assert res[0].tie is None


def test_regrafia_part_reescriu_una_peca_importada():
    p = stream.Part()
    m = stream.Measure(number=1)
    m.timeSignature = ts("4/4")
    m.append(note.Note("C5", quarterLength=1))
    m.append(note.Note("D5", quarterLength=0.5))
    n = note.Note("E5", quarterLength=2)
    n.offset = 1.5
    m.insert(1.5, n)
    m.insert(3.5, note.Rest(quarterLength=0.5))
    p.append(m)
    assert gravat.regrafia_part(p) == 1
    durs = [(float(x.offset), float(x.quarterLength)) for x in p.recurse().notesAndRests]
    assert durs == [(0.0, 1.0), (1.0, 0.5), (1.5, 0.5), (2.0, 1.5), (3.5, 0.5)]
    assert sum(d for _, d in durs) == 4


# --------------------------------------------------------------------------- les parts que genera «arranja»

@pytest.fixture(scope="module")
def ragtime_xml(tmp_path_factory):
    s = corpus.parse("leadSheet/berlinAlexandersRagtime.mxl")
    s = s.scores[0] if isinstance(s, stream.Opus) else s
    ruta = tmp_path_factory.mktemp("rag") / "ragtime.musicxml"
    s.write("musicxml", fp=str(ruta))
    return ruta


def _arranja(ruta, rols, estil="ragtime", nivell=None):
    return arr.arranjar(musica.carregar(ruta), arr.parse_rols(rols), estil=estil, curs=nivell)


ROLS = "melodia=trompeta-sib,contracant=flauta,acompanyament=xilofon,baix=tuba,percussio=bateria"


def _duracions_per_compas(res):
    out = {}
    for p in res.parts:
        out[p.partName] = [round(float(m.duration.quarterLength), 3) for m in p.getElementsByClass(stream.Measure)]
    return out


def test_cada_part_te_almenys_un_matis_i_el_xml_porta_dynamics(ragtime_xml, tmp_path):
    res, _ = _arranja(ragtime_xml, ROLS)
    for p in res.parts:
        assert list(p.recurse().getElementsByClass(dynamics.Dynamic)), p.partName
    f = tmp_path / "r.musicxml"
    res.write("musicxml", fp=str(f))
    t = f.read_text(encoding="utf-8")
    assert "<dynamics" in t and "<breath-mark" in t


def test_matis_nomes_sobre_notes_i_la_melodia_va_un_punt_per_damunt(ragtime_xml):
    res, _ = _arranja(ragtime_xml, ROLS)
    escala = gravat.ESCALA_MATISOS
    seccions = arr.arranjar.pla
    rols = arr.parse_rols(ROLS)
    assert seccions
    for p in res.parts:
        for d in p.recurse().getElementsByClass(dynamics.Dynamic):
            m = d.getContextByClass(stream.Measure)
            sonant = [n for n in m.recurse().notes if abs(float(n.getOffsetInHierarchy(m)) - float(d.offset)) < 1e-6]
            assert sonant, "matís sobre un silenci"
    # a cada frase, qui porta la melodia té el matís més alt
    nivell = {}
    for p in res.parts:
        punts = sorted((float(d.getOffsetInHierarchy(p)), d.value) for d in p.recurse().getElementsByClass(dynamics.Dynamic))
        nivell[p.partName] = punts

    def en(nom, t):
        actual = None
        for off, v in nivell[nom]:
            if off <= t + 1e-6:
                actual = v
        return actual

    for s in seccions:
        port = rols[s.portador].instr.nom
        t = s.ini + 1.0
        mel = en(port, t)
        for r_i, r in enumerate(rols):
            if r.instr.nom == port or r.instr.nom not in nivell:
                continue
            altre = en(r.instr.nom, t)
            if mel is None or altre is None:
                continue
            assert escala.index(altre) < escala.index(mel), (s.num0, r.instr.nom, altre, mel)


def test_elemental_nomes_p_mf_f(ragtime_xml):
    res, _ = _arranja(ragtime_xml, ROLS, nivell="4t elemental")
    valors = {d.value for p in res.parts for d in p.recurse().getElementsByClass(dynamics.Dynamic)}
    assert valors and valors <= set(gravat.MATISOS_ELEMENTAL)


def test_nivell_de_matis_per_estil_i_funcio():
    assert gravat.nivell_matis("pop", "melodia", False) == "mf"
    assert gravat.nivell_matis("pop", "acompanyament", False) == "mp"
    assert gravat.nivell_matis("marxa", "melodia", False) == "f"
    assert gravat.nivell_matis("marxa", "baix", False) == "mf"
    assert gravat.nivell_matis("vals", "melodia", False) == "mp"
    assert gravat.nivell_matis("vals", "acompanyament", True) == "p"
    assert gravat.nivell_matis("vals", "melodia", True) == "mf"


def test_ragtime_porta_staccato_al_baix_i_la_melodia_no(ragtime_xml):
    res, _ = arr.arranjar(musica.carregar(ragtime_xml), arr.parse_rols(ROLS), estil="ragtime", rotacio=False)
    parts = {p.partName: p for p in res.parts}
    assert any(isinstance(a, articulations.Staccato) for n in parts["Tuba"].recurse().notes for a in n.articulations)
    assert not any(isinstance(a, articulations.Staccato) for n in parts["Trompeta en Si bemoll"].recurse().notes
                   for a in n.articulations)


def test_swing_porta_accents_a_l_acompanyament(ragtime_xml):
    res, _ = arr.arranjar(musica.carregar(ragtime_xml), arr.parse_rols(ROLS), estil="swing", rotacio=False)
    parts = {p.partName: p for p in res.parts}
    assert any(isinstance(a, articulations.Accent) for n in parts["Xilòfon"].recurse().notes for a in n.articulations)


def test_pop_no_porta_articulacions(ragtime_xml):
    res, _ = arr.arranjar(musica.carregar(ragtime_xml), arr.parse_rols(ROLS), estil="pop", rotacio=False)
    for p in res.parts:
        assert not [a for n in p.recurse().notes for a in n.articulations
                    if isinstance(a, (articulations.Staccato, articulations.Accent))]


def test_respiracions_dels_vents_i_nota_anterior_mes_curta(ragtime_xml):
    res, _ = _arranja(ragtime_xml, "melodia=trompeta-sib,acompanyament=piano")
    tpt = res.parts[0]
    amb = [n for n in tpt.recurse().notes if any(isinstance(a, articulations.BreathMark) for a in n.articulations)]
    assert amb
    for n in amb:
        m = n.getContextByClass(stream.Measure)
        fi = float(m.offset) + float(n.getOffsetInHierarchy(m)) + float(n.quarterLength)
        # després de la nota hi ha un silenci (el temps de la respiració), si no és el final de la peça
        seg = [x for x in tpt.recurse().notesAndRests
               if fi - 1e-6 <= float(x.getOffsetInHierarchy(tpt)) < fi + 0.1]
        assert seg and seg[0].isRest


def test_elemental_respira_mes_que_la_resta(ragtime_xml):
    def marques(nivell):
        res, _ = _arranja(ragtime_xml, "melodia=trompeta-sib,acompanyament=piano", nivell=nivell)
        return [n for n in res.parts[0].recurse().notes if any(isinstance(a, articulations.BreathMark)
                                                                 for a in n.articulations)]
    assert len(marques("4t elemental")) > len(marques(None)) >= 1


def test_cap_lligadura_de_frase_en_un_vent(ragtime_xml):
    res, _ = _arranja(ragtime_xml, ROLS)
    for p in res.parts:
        assert not list(p.recurse().getElementsByClass("Slur")), p.partName


def test_peca_sense_tempo_en_porta_un_d_estil_i_el_xml_el_guarda(ragtime_xml, tmp_path):
    s = musica.carregar(ragtime_xml)
    for mm in list(s.recurse().getElementsByClass(tempo.MetronomeMark)):
        s.remove(mm, recurse=True)
    res, informe = arr.arranjar(s, arr.parse_rols(ROLS), estil="swing")
    marques = list(res.recurse().getElementsByClass(tempo.MetronomeMark))
    assert len(marques) == 1 and marques[0].text == "Swing" and marques[0].number == 120
    assert any("suggeriment" in x for x in informe)


def test_les_particelles_porten_el_tempo():
    sc = stream.Score()
    for nom in ("A", "B"):
        p = stream.Part()
        p.partName = nom
        m = stream.Measure(number=1)
        m.timeSignature = ts("4/4")
        if nom == "A":
            m.insert(0, tempo.MetronomeMark(text="Swing", number=120))
        m.append(note.Note("C4", quarterLength=4))
        p.append(m)
        sc.insert(0, p)
    for _, s in musica.parts_separades(sc):
        assert list(s.recurse().getElementsByClass(tempo.MetronomeMark))


def test_les_durades_dels_compassos_no_canvien_i_les_notes_respecten_la_metrica(ragtime_xml):
    res, _ = _arranja(ragtime_xml, ROLS)
    for p in res.parts:
        meitat_creuada = 0
        for m in p.getElementsByClass(stream.Measure):
            tsx = m.timeSignature or m.getContextByClass(meter.TimeSignature)
            if not m.recurse().getElementsByClass(stream.Voice):
                tot = sum(float(x.quarterLength) for x in m.notesAndRests)
                assert tot == pytest.approx(float(m.duration.quarterLength)) or m.number == 0
            for x in m.notesAndRests:
                if isinstance(x.activeSite, stream.Voice) or tsx.ratioString != "4/4":
                    continue
                o, d = float(x.offset), float(x.quarterLength)
                if o < 2 - 1e-6 and o + d > 2 + 1e-6 and (o, d) not in ((0, 4), (0, 3), (1, 2), (1, 3)) and not x.isRest:
                    meitat_creuada += 1
        assert meitat_creuada == 0, p.partName


def test_silencis_en_3_4_no_son_de_dues_negres():
    bressol = corpus.parse("essenFolksong/kinder")
    bressol = bressol.scores[0] if isinstance(bressol, stream.Opus) else bressol
    res, _ = arr.arranjar(bressol, arr.parse_rols("melodia=flauta,acompanyament=xilofon,baix=tuba"), estil="vals")
    for p in res.parts:
        for m in p.getElementsByClass(stream.Measure):
            tsx = m.timeSignature or m.getContextByClass(meter.TimeSignature)
            if tsx.ratioString != "3/4":
                continue
            for x in m.notesAndRests:
                if x.isRest and float(x.quarterLength) == 2.0:
                    assert False, f"silenci de dues negres a {p.partName} c. {m.number}"
