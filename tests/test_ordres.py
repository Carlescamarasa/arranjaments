import shutil

import pytest
from music21 import clef, converter

from partitures import eines
from partitures import cli, musica
from partitures.errors import ErrorUsuari

QUARTET = "1=trompeta-sib,2=trompeta-sib,3=trompa-fa,4=trombo"


def executar(*args):
    return cli.main([str(a) for a in args])


def actual(capsys) -> str:
    """Ruta de l'última línia «Fitxer actual: ...» (i comprova que és l'última línia de la sortida)."""
    linies = capsys.readouterr().out.strip().splitlines()
    assert linies[-1].startswith("Fitxer actual: ")
    return linies[-1].removeprefix("Fitxer actual: ")


def test_info_text(coral, capsys):
    assert executar("info", coral) == 0
    sortida = capsys.readouterr().out
    assert "Parts: 4" in sortida
    assert "Tonalitat: Fa# menor" in sortida
    assert "Do central és Do3" in sortida


def test_info_json_te_4_parts(coral):
    d = musica.info(musica.carregar(coral))
    assert len(d["parts"]) == 4
    assert d["parts"][3]["mes_greu"] == "Fa#1"   # F#2 de music21 = Fa#1 (Do central = Do3)


def test_fitxer_inexistent_dona_error_en_valencia(tmp_path, capsys):
    assert executar("info", tmp_path / "no-hi-es.musicxml") == 1
    assert "No trobe el fitxer" in capsys.readouterr().err


def test_pdf_es_rebutja_amb_ajuda(tmp_path, capsys):
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    assert executar("info", pdf) == 1
    assert "importar" in capsys.readouterr().err


def test_transport_semitons(coral, capsys):
    assert executar("transport", coral, "--semitons", 2) == 0
    out = actual(capsys)
    assert out == "eixida/coral/coral.musicxml"
    orig = musica.carregar(coral).parts[0].flatten().notes[0].pitch.midi
    nou = musica.carregar(out).parts[0].flatten().notes[0].pitch.midi
    assert nou == orig + 2


def test_transport_octava_nomes_una_part(coral, capsys):
    assert executar("transport", coral, "--octava", -1, "--part", "4") == 0
    out = actual(capsys)
    a, b = musica.carregar(coral), musica.carregar(out)
    assert b.parts[3].flatten().notes[0].pitch.midi == a.parts[3].flatten().notes[0].pitch.midi - 12
    assert b.parts[0].flatten().notes[0].pitch.midi == a.parts[0].flatten().notes[0].pitch.midi


def test_transport_sense_arguments_error(coral, capsys):
    assert executar("transport", coral) == 1
    assert "quant transportar" in capsys.readouterr().err


def test_interval_amb_nom(coral, capsys):
    assert executar("transport", coral, "--interval", "m-3") == 0
    out = actual(capsys)
    a, b = musica.carregar(coral), musica.carregar(out)
    assert b.parts[0].flatten().notes[0].pitch.midi == a.parts[0].flatten().notes[0].pitch.midi - 3


def test_llista_instruments(capsys):
    assert executar("instruments") == 0
    sortida = capsys.readouterr().out
    assert "trompeta-sib" in sortida and "trompa-fa" in sortida


def test_assignar_escriu_altura_escrita_i_conserva_so_real(coral, capsys):
    assert executar("instruments", coral, "--assigna", QUARTET) == 0
    out = actual(capsys)
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


def test_tessitura_usa_altura_escrita_en_transpositors(coral, capsys):
    executar("instruments", coral, "--assigna", QUARTET)
    out = actual(capsys)
    d = musica.tessitura(musica.carregar(out))
    assert [p["instrument"] for p in d["parts"]] == ["trompeta-sib", "trompeta-sib", "trompa-fa", "trombo"]
    assert d["parts"][0]["escrit_min"] == "Fa#3"   # Mi3 real (E4 a music21) + 2 semitons


def test_tessitura_part_sense_instrument_avisa(coral):
    d = musica.tessitura(musica.carregar(coral))
    assert d["parts"][0]["instrument"] is None and "--instruments" in d["parts"][0]["avis"]


def test_reduir_mantindre(coral, capsys):
    assert executar("reduir", coral, "--mantin", "1,4") == 0
    assert len(musica.carregar(actual(capsys)).parts) == 2


def test_reduir_a_piano_ja_no_existeix(coral):
    with pytest.raises(SystemExit):
        executar("reduir", coral, "--a-piano")


def test_corpus_cerca_i_copia_a_entrada(capsys):
    assert executar("corpus", "bwv66.6", "--copia", 1) == 0
    assert actual(capsys) == "entrada/bwv66.6.musicxml"


def test_corpus_text_amb_diverses_paraules_i_sense_accents(capsys):
    assert executar("corpus", "BACH", "bwv66.6") == 0
    assert "bwv66.6" in capsys.readouterr().out


def test_corpus_mostra_compositor_i_no_nomes_el_fitxer(capsys):
    assert executar("corpus", "palestrina", "--maxim", 2) == 0
    sortida = capsys.readouterr().out
    assert "Palestrina" in sortida   # compositor de les metadades, no només el nom del fitxer


def test_corpus_sense_text_error(capsys):
    assert executar("corpus") == 1
    assert "Digues què busque" in capsys.readouterr().err


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
def test_exportar_pdf_complet_i_parts(coral, capsys, projecte):
    executar("instruments", coral, "--assigna", QUARTET)
    q = actual(capsys)
    assert executar("exportar", q) == 0
    carpeta = projecte / "eixida" / "coral"
    assert (carpeta / "coral - Guió.pdf").exists() and (carpeta / "coral.mscz").exists()
    assert len(list((carpeta / "Particel·les").glob("*.pdf"))) == 4
    assert not list(carpeta.glob(".tmp-*"))
    # una segona vegada reemplaça: la mateixa carpeta
    assert executar("exportar", q) == 0
    assert not (projecte / "eixida" / "coral-2").exists()


@pytest.mark.skipif(not (_te(eines.trobar_musescore) and _te(eines.trobar_audiveris)),
                    reason="MuseScore o Audiveris no instal·lats")
def test_cicle_pdf_a_musicxml(coral, projecte):
    executar("exportar", coral, "--sense-parts")
    pdf = next((projecte / "eixida").glob("*/*Guió.pdf"))
    assert executar("importar", pdf) == 0
    mxl = next((projecte / "eixida").rglob("*-omr/*.mxl"))
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


# ---- peces i carpeta (ordres deterministes del guió de la conversa)

def test_peces_llista_numerada_de_l_entrada(projecte, capsys):
    assert executar("peces") == 0
    assert "no hi ha cap partitura" in capsys.readouterr().out
    (projecte / "entrada" / "Zeta.musicxml").write_text("<x/>", encoding="utf-8")
    (projecte / "entrada" / "alfa.mxl").write_text("x", encoding="utf-8")
    (projecte / "entrada" / "nota.txt").write_text("x", encoding="utf-8")
    (projecte / "entrada" / "escanejat.pdf").write_text("x", encoding="utf-8")
    assert executar("peces") == 0
    linies = capsys.readouterr().out.strip().splitlines()
    assert linies[0] == "1. alfa.mxl" and linies[1].startswith("2. escanejat.pdf") and "PDF" in linies[1]
    assert linies[2] == "3. Zeta.musicxml" and len(linies) == 3


def test_peces_eixida_diu_si_cada_peca_te_pdf(projecte, capsys):
    assert executar("peces", "--eixida") == 0
    assert "Encara no hi ha cap peça" in capsys.readouterr().out
    fet = projecte / "eixida" / "ragtime"
    (fet / "Particel·les").mkdir(parents=True)
    (fet / "ragtime - Guió.pdf").write_text("x", encoding="utf-8")
    (fet / "Particel·les" / "ragtime - 1. Flauta.pdf").write_text("x", encoding="utf-8")
    (projecte / "eixida" / "blues").mkdir()
    (projecte / "eixida" / "solt.musicxml").write_text("<x/>", encoding="utf-8")   # fitxer solt: no és una peça
    assert executar("peces", "--eixida") == 0
    linies = capsys.readouterr().out.strip().splitlines()
    assert linies == ["1. blues   [sense PDF encara]", "2. ragtime   [amb guió i 1 particel·les en PDF]"]


def test_carpeta_obri_la_carpeta_de_la_peca_sense_bloquejar(projecte, monkeypatch, capsys):
    import subprocess
    cridades = []
    monkeypatch.setattr(subprocess, "Popen", lambda ordre, **kw: cridades.append(ordre))
    (projecte / "eixida" / "ragtime").mkdir()
    assert executar("carpeta", "ragtime") == 0
    assert cridades[0][0] in ("open", "explorer", "xdg-open")
    assert cridades[0][1] == str((projecte / "eixida" / "ragtime").resolve())
    assert "ragtime" in capsys.readouterr().out
    # també per ruta, i un fitxer obri la carpeta que el conté
    (projecte / "eixida" / "ragtime" / "x.pdf").write_text("x", encoding="utf-8")
    assert executar("carpeta", "eixida/ragtime/x.pdf") == 0 and cridades[1][1] == cridades[0][1]


def test_carpeta_nomes_dins_de_la_carpeta_de_treball(projecte, tmp_path, monkeypatch, capsys):
    import subprocess
    cridades = []
    monkeypatch.setattr(subprocess, "Popen", lambda ordre, **kw: cridades.append(ordre))
    assert executar("carpeta", str(tmp_path)) == 1
    assert "Només obric carpetes" in capsys.readouterr().err
    assert executar("carpeta", "no-existeix") == 1
    assert executar("carpeta", "..") == 1
    assert cridades == []
