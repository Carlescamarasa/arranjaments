import shutil

import pytest
from music21 import converter

from partitures import eines
from partitures import cli, musica
from partitures.errors import ErrorUsuari

QUARTET = "1=trompeta-sib,2=trompeta-sib,3=trompa-fa,4=trombo"


def executar(*args):
    return cli.main([str(a) for a in args])


def test_info_text(coral, capsys):
    assert executar("info", coral) == 0
    sortida = capsys.readouterr().out
    assert "Parts: 4" in sortida
    assert "A major" in sortida


def test_info_json_te_4_parts(coral):
    d = musica.info(musica.carregar(coral))
    assert len(d["parts"]) == 4
    assert d["parts"][3]["mes_greu"] == "F#2"


def test_fitxer_inexistent_dona_error_en_valencia(tmp_path, capsys):
    assert executar("info", tmp_path / "no-hi-es.musicxml") == 1
    assert "No trobe el fitxer" in capsys.readouterr().err


def test_pdf_es_rebutja_amb_ajuda(tmp_path, capsys):
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    assert executar("info", pdf) == 1
    assert "importar" in capsys.readouterr().err


def test_transport_semitons(coral, tmp_path):
    out = tmp_path / "t.musicxml"
    assert executar("transport", coral, "--semitons", 2, "--eixida", out) == 0
    orig = musica.carregar(coral).parts[0].flatten().notes[0].pitch.midi
    nou = musica.carregar(out).parts[0].flatten().notes[0].pitch.midi
    assert nou == orig + 2


def test_transport_octava_nomes_una_part(coral, tmp_path):
    out = tmp_path / "t.musicxml"
    assert executar("transport", coral, "--octava", -1, "--part", "4", "--eixida", out) == 0
    a, b = musica.carregar(coral), musica.carregar(out)
    assert b.parts[3].flatten().notes[0].pitch.midi == a.parts[3].flatten().notes[0].pitch.midi - 12
    assert b.parts[0].flatten().notes[0].pitch.midi == a.parts[0].flatten().notes[0].pitch.midi


def test_transport_sense_arguments_error(coral, capsys):
    assert executar("transport", coral) == 1
    assert "quant transportar" in capsys.readouterr().err


def test_interval_amb_nom(coral, tmp_path):
    out = tmp_path / "t.musicxml"
    assert executar("transport", coral, "--interval", "m-3", "--eixida", out) == 0
    a, b = musica.carregar(coral), musica.carregar(out)
    assert b.parts[0].flatten().notes[0].pitch.midi == a.parts[0].flatten().notes[0].pitch.midi - 3


def test_llista_instruments(capsys):
    assert executar("instruments") == 0
    sortida = capsys.readouterr().out
    assert "trompeta-sib" in sortida and "trompa-fa" in sortida


def test_assignar_escriu_altura_escrita_i_conserva_so_real(coral, tmp_path):
    out = tmp_path / "q.musicxml"
    assert executar("instruments", coral, "--assigna", QUARTET, "--eixida", out) == 0
    orig = musica.carregar(coral)
    nou = converter.parse(str(out))
    # trompeta en Sib: escrit una segona major més alt que el so real
    escrit = nou.parts[0].flatten().notes[0].pitch.midi
    real = musica.part_sonora(nou.parts[0]).flatten().notes[0].pitch.midi
    assert real == orig.parts[0].flatten().notes[0].pitch.midi
    assert escrit == real + 2
    # trompa en Fa: escrit una quinta més alt
    escrit_t = nou.parts[2].flatten().notes[0].pitch.midi
    real_t = musica.part_sonora(nou.parts[2]).flatten().notes[0].pitch.midi
    assert escrit_t == real_t + 7
    # trombó: no transposa
    assert nou.parts[3].flatten().notes[0].pitch.midi == orig.parts[3].flatten().notes[0].pitch.midi


def test_assignar_instrument_desconegut(coral, capsys):
    assert executar("instruments", coral, "--assigna", "1=kazoo") == 1
    assert "No conec l'instrument" in capsys.readouterr().err


def test_assignar_part_inexistent(coral, capsys):
    assert executar("instruments", coral, "--assigna", "9=tuba") == 1
    assert "no existeix" in capsys.readouterr().err


def test_tessitura_detecta_notes_fora_d_abast(coral):
    # el baix (F#2..D4) a la flauta (C4..C7 escrit) queda quasi tot massa greu
    d = musica.tessitura(musica.carregar(coral), "4=flauta,1=trompeta-sib,2=trompeta-sib,3=trompeta-sib")
    flauta = d["parts"][3]
    assert flauta["fora_abast"] > 30
    assert all(p["tipus"] == "massa greu" for p in flauta["problemes"] if not p["tipus"].startswith("zona"))
    assert all(isinstance(p["compas"], int) for p in flauta["problemes"][:5])


def test_tessitura_dins_d_abast(coral):
    d = musica.tessitura(musica.carregar(coral), "1=flauta,2=viola,3=violoncel,4=violoncel")
    assert all(p["fora_abast"] == 0 for p in d["parts"])


def test_tessitura_usa_altura_escrita_en_transpositors(coral, tmp_path):
    out = tmp_path / "q.musicxml"
    executar("instruments", coral, "--assigna", QUARTET, "--eixida", out)
    d = musica.tessitura(musica.carregar(out))
    assert [p["instrument"] for p in d["parts"]] == ["trompeta-sib", "trompeta-sib", "trompa-fa", "trombo"]
    assert d["parts"][0]["escrit_min"] == "F#4"   # E4 real + 2 semitons


def test_tessitura_part_sense_instrument_avisa(coral):
    d = musica.tessitura(musica.carregar(coral))
    assert d["parts"][0]["instrument"] is None and "--instruments" in d["parts"][0]["avis"]


def test_reduir_mantindre(coral, tmp_path):
    out = tmp_path / "r.musicxml"
    assert executar("reduir", coral, "--mantin", "1,4", "--eixida", out) == 0
    assert len(musica.carregar(out).parts) == 2


def test_reduir_a_piano_dos_pentagrames_i_mateixes_altures(coral, tmp_path):
    out = tmp_path / "p.musicxml"
    assert executar("reduir", coral, "--a-piano", "--eixida", out) == 0
    r = musica.carregar(out)
    assert len(r.parts) == 2
    tots = [p.midi for p in r.flatten().pitches]
    assert min(tots) == 42  # F#2 del baix
    assert max(tots) == 76  # E5 de la soprano


def test_corpus_cerca_i_copia(tmp_path, capsys):
    assert executar("corpus", "bwv66.6", "--copia", 1, "--eixida", tmp_path) == 0
    assert (tmp_path / "bwv66.6.musicxml").exists()


def test_noms_de_programes_externs_amb_variable_d_entorn(monkeypatch, tmp_path):
    f = tmp_path / "fals-mscore"
    f.write_text("x")
    monkeypatch.setenv("MUSESCORE_PATH", str(f))
    assert eines.trobar_musescore() == str(f)


def test_error_clar_si_manca_musescore(monkeypatch):
    monkeypatch.delenv("MUSESCORE_PATH", raising=False)
    monkeypatch.setattr(eines, "_candidats_musescore", lambda: [])
    monkeypatch.setattr(shutil, "which", lambda n: None)
    with pytest.raises(ErrorUsuari) as e:
        eines.trobar_musescore()
    assert "No trobe MuseScore" in str(e.value) and "musescore.org" in str(e.value)


def test_error_clar_si_manca_audiveris(monkeypatch):
    monkeypatch.delenv("AUDIVERIS_PATH", raising=False)
    monkeypatch.setattr(eines, "_candidats_audiveris", lambda: [])
    monkeypatch.setattr(shutil, "which", lambda n: None)
    with pytest.raises(ErrorUsuari) as e:
        eines.trobar_audiveris()
    assert "No trobe Audiveris" in str(e.value)


def test_ruta_forcada_inexistent(monkeypatch):
    monkeypatch.setenv("MUSESCORE_PATH", "/ruta/que/no/existeix")
    with pytest.raises(ErrorUsuari):
        eines.trobar_musescore()


# ---- proves amb els programes reals (s'ometen si no estan instal·lats)

def _te(fn):
    try:
        fn()
        return True
    except ErrorUsuari:
        return False


@pytest.mark.skipif(not _te(eines.trobar_musescore), reason="MuseScore no instal·lat")
def test_exportar_pdf_complet_i_parts(coral, tmp_path):
    q = tmp_path / "q.musicxml"
    executar("instruments", coral, "--assigna", QUARTET, "--eixida", q)
    assert executar("exportar", q, "--eixida", tmp_path / "pdf") == 0
    pdfs = sorted(p.name for p in (tmp_path / "pdf" / "q").glob("*.pdf"))
    assert len(pdfs) == 5 and any("completa" in p for p in pdfs)
    assert not list((tmp_path / "pdf" / "q").glob(".tmp-*"))


@pytest.mark.skipif(not (_te(eines.trobar_musescore) and _te(eines.trobar_audiveris)),
                    reason="MuseScore o Audiveris no instal·lats")
def test_cicle_pdf_a_musicxml(coral, tmp_path):
    executar("exportar", coral, "--eixida", tmp_path, "--sense-parts")
    pdf = next(tmp_path.glob("*/*completa.pdf"))
    assert executar("importar", pdf, "--eixida", tmp_path / "omr") == 0
    mxl = next((tmp_path / "omr").rglob("*.mxl"))
    d = musica.info(musica.carregar(mxl))
    assert len(d["parts"]) == 4


def test_comprovar_llista_tot_i_falla_si_manca_algo(monkeypatch, capsys):
    monkeypatch.setattr(eines, "comprovar", lambda: [("MuseScore 4", True, "ok"), ("Audiveris", False, "falta")])
    assert executar("comprovar") == 1
    eixida = capsys.readouterr()
    assert "[falta]  Audiveris" in eixida.out and "[fet]  MuseScore 4" in eixida.out


def test_comprovar_tot_be(monkeypatch, capsys):
    monkeypatch.setattr(eines, "comprovar", lambda: [("MuseScore 4", True, "ok")])
    assert executar("comprovar") == 0
    assert "Tot a punt." in capsys.readouterr().out
