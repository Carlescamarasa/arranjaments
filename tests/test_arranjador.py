"""Proves de l'ordre «arranja»: crea parts noves a partir d'una melodia (esborrany determinista)."""
import pytest
from music21 import clef, corpus, harmony, note, percussion, stream

from partitures import arranjador as arr
from partitures import biblioteca as bib
from partitures import cli, eines, musica, rutes
from partitures import instruments as inst
from partitures.errors import ErrorUsuari

ROLS_RAG = "melodia=trompeta-sib,contracant=flauta,acompanyament=xilofon,percussio=bateria"


@pytest.fixture(autouse=True)
def dades(tmp_path, monkeypatch):
    """Cap perfil de nivell real: dades buides i sense biblioteca compartida."""
    monkeypatch.setenv("ARRANJAMENTS_DADES", str(tmp_path / "dades"))
    monkeypatch.delenv("ARRANJAMENTS_BIBLIOTECA", raising=False)
    monkeypatch.setattr(bib, "_plataforma", lambda: "altre")
    monkeypatch.setenv("HOME", str(tmp_path / "buit"))


def executar(*args):
    return cli.main([str(a) for a in args])


def actual(capsys) -> tuple[str, str]:
    out = capsys.readouterr().out
    linies = out.strip().splitlines()
    assert linies[-1].startswith("Fitxer actual: ")
    return linies[-1].removeprefix("Fitxer actual: "), out


def _desa(tmp_path_factory, obj, nom):
    if isinstance(obj, stream.Opus):
        obj = obj.scores[0]
    ruta = tmp_path_factory.mktemp("dades") / nom
    obj.write("musicxml", fp=str(ruta))
    return ruta


@pytest.fixture(scope="session")
def ragtime(tmp_path_factory):
    """Alexander's Ragtime Band (Irving Berlin), full de melodia amb acords del corpus de music21."""
    return _desa(tmp_path_factory, corpus.parse("leadSheet/berlinAlexandersRagtime.mxl"), "ragtime.musicxml")


@pytest.fixture(scope="session")
def bressol(tmp_path_factory):
    """Cançó popular alemanya «Schlaf, Kindlein, schlaf» (només melodia, sense acords)."""
    return _desa(tmp_path_factory, corpus.parse("essenFolksong/kinder"), "bressol.musicxml")


def _parts(score):
    return {musica.nom_part(p, i): p for i, p in enumerate(score.parts)}


def _notes(part):
    return [n for n in part.flatten().notes if not isinstance(n, harmony.Harmony)]


# --------------------------------------------------------------------------- ragtime (cas real del professorat)

def test_ragtime_crea_les_quatre_parts(ragtime, capsys):
    assert executar("arranja", ragtime, "--rols", ROLS_RAG, "--estil", "ragtime", "--nivell", "4t elemental") == 0
    ruta, out = actual(capsys)
    assert ruta == "eixida/ragtime/ragtime.musicxml"
    s = musica.carregar(ruta)
    noms = _parts(s)
    assert set(noms) == {"Flauta", "Trompeta en Si bemoll", "Xilòfon", "Bateria"}
    assert "(esborrany d'arranjament)" in s.metadata.bestTitle
    # informe: acords, tessitures, comprovacions i l'avís d'esborrany
    assert "Acords" in out and "Fa" in out and "Do7" in out
    assert "Revisa-ho amb MuseScore: és un esborrany." in out
    assert "Quintes o octaves paral·leles" in out
    assert "—" not in out and " · " not in out
    # cap compàs incomplet en cap part
    for p in s.parts:
        assert len(p.getElementsByClass(stream.Measure)) == 34


def test_ragtime_transposicio_de_la_trompeta(ragtime, capsys):
    executar("arranja", ragtime, "--rols", ROLS_RAG, "--estil", "ragtime")
    ruta, _ = actual(capsys)
    s = musica.carregar(ruta)
    tpt = _parts(s)["Trompeta en Si bemoll"]
    original = [n.pitch.midi for n in _notes(corpus.parse("leadSheet/berlinAlexandersRagtime.mxl").parts[0])]
    escrites = [n.pitch.midi for n in _notes(tpt)]
    # la melodia es manté (mateixa octava) i s'escriu una segona major amunt
    assert escrites[:10] == [m + 2 for m in original[:10]]
    sons = [n.pitch.midi for n in _notes(musica.part_sonora(tpt))]
    assert sons[:10] == original[:10]
    # armadura escrita de la trompeta: Sol major (la peça sona en Fa major)
    ks = tpt.recurse().getElementsByClass("KeySignature")[0]
    assert ks.sharps == 1
    fl = _parts(s)["Flauta"]
    assert fl.recurse().getElementsByClass("KeySignature")[0].sharps == -1


def test_ragtime_xilofon_sona_una_octava_amunt_i_porta_els_acords(ragtime, capsys):
    executar("arranja", ragtime, "--rols", ROLS_RAG, "--estil", "ragtime")
    ruta, _ = actual(capsys)
    s = musica.carregar(ruta)
    xil = _parts(s)["Xilòfon"]
    ins = xil.getInstrument(returnDefault=False)
    assert ins.transposition is not None and ins.transposition.semitones == 12
    assert not xil.recurse().getElementsByClass(harmony.ChordSymbol)   # els acords van a la melodia
    # dues baquetes: mai més de dues notes alhora
    assert all(len(n.pitches) <= 2 for n in _notes(xil))
    lo, hi = inst.rang_midi(inst.obtenir("xilofon").abast)
    assert all(lo <= p.midi <= hi for n in _notes(xil) for p in n.pitches)


def test_ragtime_bateria_es_percussio_valida(ragtime, capsys):
    executar("arranja", ragtime, "--rols", ROLS_RAG, "--estil", "ragtime")
    ruta, _ = actual(capsys)
    text = (rutes.arrel() / ruta).read_text(encoding="utf-8")
    assert "<sign>percussion</sign>" in text and "<unpitched>" in text and "<notehead" in text
    s = musica.carregar(ruta)
    bat = _parts(s)["Bateria"]
    assert any(isinstance(c, clef.PercussionClef) for c in bat.recurse().getElementsByClass(clef.Clef))
    unp = [x for x in bat.recurse().notes if isinstance(x, (note.Unpitched, percussion.PercussionChord))]
    assert len(unp) > 100
    # cap semicorxera en una bateria d'elemental
    assert all(x.quarterLength >= 0.5 for x in bat.recurse().notesAndRests)
    # la tessitura no es queixa de la percussió
    d = musica.tessitura(s)
    assert any("percussió sense altura" in (r["avis"] or "") for r in d["parts"])


def test_ragtime_dins_d_abast_i_sense_quintes_paral_leles(ragtime):
    s = musica.carregar(ragtime)
    r, informe = arr.arranjar(s, arr.parse_rols(ROLS_RAG), estil="ragtime")
    for p in r.parts:
        if p.partName == "Bateria":
            continue
        i = inst.obtenir(p.partName)
        lo, hi = inst.rang_midi(i.abast)
        assert all(lo <= q.midi <= hi for n in _notes(p) for q in n.pitches), p.partName
    assert "Quintes o octaves paral·leles del contracant: cap." in "\n".join(informe)


def test_compassos_acords_i_to(ragtime, capsys):
    assert executar("arranja", ragtime, "--rols", "melodia=flauta,acompanyament=piano,baix=contrabaix",
                    "--compassos", "2-9", "--to", "Sol major", "--estil", "pop") == 0
    ruta, out = actual(capsys)
    assert "de Fa major a Sol major" in out
    s = musica.carregar(ruta)
    assert len(s.parts[0].getElementsByClass(stream.Measure)) == 8
    # el piano és UNA part de dos pentagrames
    d = musica.info(s)
    assert [p["pentagrames"] for p in d["parts"] if p["nom"] == "Piano"] == [2]
    assert "Sol" in d["tonalitat"]


@pytest.fixture(scope="session")
def full_acords(tmp_path_factory):
    """Full de melodia en Fa major amb els acords F, C7 i Bb (un per compàs)."""
    p = stream.Part()
    for fig, alt in (("F", "A4"), ("C7", "G4"), ("B-", "D5"), ("F", "F4")):
        m = stream.Measure()
        m.insert(0, harmony.ChordSymbol(fig))
        m.insert(0, note.Note(alt, quarterLength=4))
        p.append(m)
    sc = stream.Score()
    sc.insert(0, p)
    return _desa(tmp_path_factory, sc, "full.musicxml")


def _figures(part):
    return [c.figure.replace("-", "b") for c in part.recurse().getElementsByClass(harmony.ChordSymbol)]


@pytest.mark.parametrize("instrument, esperat", [
    ("trompeta-sib", ["G", "D7", "C", "G"]),     # una segona major amunt
    ("trompa-fa", ["C", "G7", "F", "C"]),        # una quinta justa amunt
    ("flauta", ["F", "C7", "Bb", "F"]),          # so real: sense canvis
])
def test_acords_escrits_a_l_altura_de_la_part_de_melodia(full_acords, instrument, esperat):
    s = musica.carregar(full_acords)
    r, _ = arr.arranjar(s, arr.parse_rols(f"melodia={instrument},acompanyament=xilofon,baix=violoncel"), estil="pop")
    nom = inst.obtenir(instrument).nom
    mel = next(p for p in r.parts if p.partName == nom)
    assert _figures(mel) == esperat
    # només la melodia porta els acords (la partitura general és coherent)
    assert sum(len(p.recurse().getElementsByClass(harmony.ChordSymbol)) for p in r.parts) == 4
    # i sobreviuen a desar i tornar a llegir
    ruta = rutes.carpeta("eixida") / "acords.musicxml"
    musica.desar(r, ruta)
    llegida = next(p for p in musica.carregar(ruta).parts if p.partName == nom)
    assert _figures(llegida) == esperat


def test_elemental_sense_perfil_limita_la_zona_comoda(ragtime):
    (lo, hi), font = arr.rang_comode(inst.obtenir("trompeta-sib"), "4t elemental")
    assert musica.nom_nota(hi) == "Do4" and "elemental" in font
    (_, hi2), _ = arr.rang_comode(inst.obtenir("trompeta-sib"), "1r professional")
    assert musica.nom_nota(hi2) == "Sol4"
    r, informe = arr.arranjar(musica.carregar(ragtime), arr.parse_rols(ROLS_RAG), estil="ragtime", curs="4t elemental")
    text = "\n".join(informe)
    assert "dos terços de baix" in text
    assert "limitada per a elemental" in text
    # la melodia no baixa d'octava per a cabre: es queda i s'avisa
    tpt = next(p for p in r.parts if p.partName.startswith("Trompeta"))
    assert max(q.midi for n in _notes(tpt) for q in n.pitches) == 79   # Sol4 escrit (Sol5 internacional)


# --------------------------------------------------------------------------- altres entrades

def test_coral_de_bach_dedueix_l_harmonia_de_les_veus(coral):
    s = musica.carregar(coral)
    r, informe = arr.arranjar(s, arr.parse_rols("melodia=trompeta-sib,contracant=flauta,baix=violoncel"),
                              estil="classic")
    text = "\n".join(informe)
    assert "de les notes de totes les veus" in text
    assert "Fa# menor" in text
    sop = [n.pitch.midi for n in _notes(s.parts[0])]
    tpt = next(p for p in r.parts if p.partName.startswith("Trompeta"))
    sons = [n.pitch.midi for n in _notes(musica.part_sonora(tpt))]
    assert sons == sop     # la melodia és el soprano, nota per nota
    vc = next(p for p in r.parts if p.partName == "Violoncel")
    assert any(isinstance(c, clef.BassClef) for c in vc.recurse().getElementsByClass(clef.Clef))


def test_melodia_sola_s_harmonitza_amb_cadencia(bressol):
    s = musica.carregar(bressol)
    r, informe = arr.arranjar(s, arr.parse_rols("melodia=clarinet-sib,acompanyament=lamines,percussio=caixa"),
                              estil="marxa")
    text = "\n".join(informe)
    assert "harmonització per regles" in text
    linies_acords = [l for l in informe if l.startswith("  c. ")]
    ultima = linies_acords[-1].split("|")[-1].strip()
    assert ultima.rstrip("*") == "Fa"            # acaba en el I
    assert "Do7" in linies_acords[-1] or "Do" in linies_acords[-1]   # precedit del V
    assert any(p.partName == "Xilòfon alt (Orff)" for p in r.parts)


def test_bordo_orff_tonica_i_quinta(bressol):
    s = musica.carregar(bressol)
    r, _ = arr.arranjar(s, arr.parse_rols("melodia=flauta,acompanyament=metalofon"), bordo=True)
    met = next(p for p in r.parts if p.partName.startswith("Metal"))
    acords = {tuple(sorted(q.name for q in n.pitches)) for n in _notes(met)}
    assert acords == {("C", "F")}


def test_resultat_determinista(ragtime):
    a, _ = arr.arranjar(musica.carregar(ragtime), arr.parse_rols(ROLS_RAG), estil="ragtime")
    b, _ = arr.arranjar(musica.carregar(ragtime), arr.parse_rols(ROLS_RAG), estil="ragtime")
    for pa, pb in zip(a.parts, b.parts):
        assert [str(n.pitches) for n in pa.recurse().notes] == [str(n.pitches) for n in pb.recurse().notes]


@pytest.mark.parametrize("estil", arr.ESTILS)
def test_tots_els_estils_sense_errors(bressol, estil):
    s = musica.carregar(bressol)
    rols = arr.parse_rols("melodia=trompeta-sib,contracant=saxo-alt,acompanyament=guitarra,baix=fagot,percussio=bateria")
    r, informe = arr.arranjar(s, rols, estil=estil)
    assert "compassos incomplets" not in "\n".join(informe)
    assert len(r.parts) == 5


# --------------------------------------------------------------------------- comprovacions i errors

def test_detecta_quintes_paral_leles():
    a = [arr.Ev(0, 1, [musica.pitch.Pitch("G4")]), arr.Ev(1, 1, [musica.pitch.Pitch("A4")])]
    b = [arr.Ev(0, 1, [musica.pitch.Pitch("C4")]), arr.Ev(1, 1, [musica.pitch.Pitch("D4")])]
    c = [arr.Compas(1, 0, 4, musica.meter.TimeSignature("4/4"))]
    assert arr.paral_leles(a, b, c) == [(1, "quintes")]
    b2 = [arr.Ev(0, 1, [musica.pitch.Pitch("E4")]), arr.Ev(1, 1, [musica.pitch.Pitch("F4")])]
    assert arr.paral_leles(a, b2, c) == []


def test_rols_amb_errors_clars():
    with pytest.raises(ErrorUsuari, match="percussió"):
        arr.parse_rols("melodia=flauta,percussio=xilofon")
    with pytest.raises(ErrorUsuari, match="percussió sense altura"):
        arr.parse_rols("melodia=bateria")
    with pytest.raises(ErrorUsuari, match="No conec el rol"):
        arr.parse_rols("melodia=flauta,harmonia=piano")
    with pytest.raises(ErrorUsuari, match="melodia"):
        arr.parse_rols("contracant=flauta")


def test_lamines_es_un_grup():
    rols = arr.parse_rols("melodia=flauta,acompanyament=làmines")
    assert rols[1].instr.clau == "xilofon-orff"
    assert any("grup" in a for a in arr.parse_rols.avisos)
    assert inst.obtenir("Làmines").clau == "xilofon-orff"


def test_cataleg_nou_i_transposicions():
    assert inst.obtenir("xilòfon").semitons() == 12
    assert inst.obtenir("glockenspiel").semitons() == 24
    assert inst.obtenir("metal·lòfon").semitons() == 0
    for c in ("bateria", "caixa", "percussio"):
        assert inst.obtenir(c).percussio


def test_llista_d_instruments_mostra_percussio_i_grup(capsys):
    assert executar("instruments") == 0
    out = capsys.readouterr().out
    assert "bateria" in out and "percussió sense altura" in out
    assert "xilofon" in out and "una octava més agut" in out
    assert "làmines" in out


def test_no_es_pot_assignar_percussio_a_una_part_amb_notes(coral, capsys):
    assert executar("instruments", coral, "--assigna", "1=bateria") == 1
    assert "arranja" in capsys.readouterr().err


def test_estil_i_tonalitat_desconeguts(ragtime, capsys):
    assert executar("arranja", ragtime, "--rols", ROLS_RAG, "--to", "Fa lidi") == 1
    assert "No entenc la tonalitat" in capsys.readouterr().err
    assert executar("arranja", ragtime, "--rols", ROLS_RAG, "--to", "Re menor") == 1
    assert "mode" in capsys.readouterr().err


def test_arranja_reemplaça_i_nova_versio_conserva(ragtime, capsys):
    executar("arranja", ragtime, "--rols", ROLS_RAG)
    a, _ = actual(capsys)
    executar("arranja", ragtime, "--rols", ROLS_RAG)
    b, _ = actual(capsys)
    assert a == b == "eixida/ragtime/ragtime.musicxml"
    executar("arranja", ragtime, "--rols", ROLS_RAG, "--nova-versio")
    c, _ = actual(capsys)
    assert c == "eixida/ragtime-2/ragtime-2.musicxml"


# --------------------------------------------------------------------------- nivell

def test_nivell_amb_perfil_comprova_i_simplifica(ragtime, capsys):
    executar("nivell", "desa", "--instrument", "trompeta-sib", "--curs", "4t elemental",
             "--tessitura", "Do3-Re4", "--figures", "blanca, negra")
    capsys.readouterr()
    assert executar("arranja", ragtime, "--rols", "melodia=trompeta-sib", "--nivell", "4t elemental") == 0
    _, out = actual(capsys)
    assert "segons el perfil de 4t elemental" in out
    assert "per damunt del nivell" in out           # hi ha corxeres i notes agudes: s'avisa, no es canvia
    assert executar("arranja", ragtime, "--rols", "melodia=trompeta-sib", "--nivell", "4t elemental",
                    "--simplifica") == 0
    ruta, out = actual(capsys)
    assert "He simplificat el ritme" in out
    tpt = musica.carregar(ruta).parts[0]
    assert all(n.quarterLength >= 1 or n.tie is not None for n in _notes(tpt))


# --------------------------------------------------------------------------- PDF

def _te(f):
    try:
        f()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _te(eines.trobar_musescore), reason="MuseScore no instal·lat")
def test_arranjament_s_exporta_a_pdf(ragtime, capsys, projecte):
    executar("arranja", ragtime, "--rols", ROLS_RAG, "--estil", "ragtime", "--compassos", "1-8")
    ruta, _ = actual(capsys)
    assert executar("exportar", ruta) == 0
    pdfs = list((projecte / "eixida").glob("*/*.pdf")) + list((projecte / "eixida").glob("*/*/*.pdf"))
    assert len(pdfs) == 1 + 4      # guió i 4 particel·les
