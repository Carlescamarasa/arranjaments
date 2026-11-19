import json

import pytest
from music21 import duration, instrument, key, meter, note, stream

from partitures import biblioteca as bib
from partitures import cli, nivells


@pytest.fixture(autouse=True)
def dades(tmp_path, monkeypatch):
    monkeypatch.setenv("ARRANJAMENTS_DADES", str(tmp_path / "dades"))
    monkeypatch.delenv("ARRANJAMENTS_BIBLIOTECA", raising=False)
    monkeypatch.setattr(bib, "_plataforma", lambda: "altre")
    monkeypatch.setenv("HOME", str(tmp_path / "buit"))
    return tmp_path / "dades"


def executar(*args):
    return cli.main([str(a) for a in args])


def desa(*extra, instrument="flauta", curs="4t elemental"):
    return executar("nivell", "desa", "--instrument", instrument, "--curs", curs, *extra)


# ----------------------------------------------------------------------- validació

def test_notes_en_solfeig_amb_do_central_do3():
    assert nivells.nota_a_midi("Do3") == 60 and nivells.nota_a_midi("sib2") == 58 and nivells.nota_a_midi("Fa#2") == 54
    assert nivells.normalitza_tessitura("sol4 a do3") == "Do3-Sol4"
    assert nivells.normalitza_tessitura("La3 - Mi5") == "La3-Mi5"
    for dolent in ("C4", "Do", "Sol9x"):
        with pytest.raises(Exception):
            nivells.nota_a_midi(dolent)


def test_tessitura_dolenta_no_desa_res(capsys, dades):
    assert desa("--tessitura", "C4-G5") == 1
    assert "solfeig" in capsys.readouterr().err
    assert not (dades / "perfil" / "nivells.json").exists()


def test_tonalitats_i_figures_i_compassos_validats(capsys):
    assert nivells.alteracions_de_tonalitat("Do major") == {0}
    assert nivells.alteracions_de_tonalitat("Sib major") == {-2}
    assert nivells.alteracions_de_tonalitat("la menor") == {0}
    assert nivells.alteracions_de_tonalitat("fins a 2 alteracions") == {-2, -1, 0, 1, 2}
    assert nivells.normalitza_figura("Corxera AMB puntet") == "corxera amb puntet"
    assert nivells.normalitza_figura("croma") == "corxera"
    assert desa("--tonalitats", "Xyz major") == 1 and desa("--figures", "bolet") == 1 and desa("--compassos", "quatre") == 1
    assert "No entenc" in capsys.readouterr().err


# ----------------------------------------------------------------------- desa / mostra

def test_desa_suma_mostra_i_historial(capsys, dades):
    assert executar("nivell", "mostra") == 0
    assert "Encara no he après" in capsys.readouterr().out
    assert desa("--tessitura", "Do3-Sol4", "--tonalitats", "Do major, Sol major", "--figures", "negra") == 0
    assert "desat Do3-Sol4" in capsys.readouterr().out
    assert desa("--tessitura", "do3 a la4", "--tonalitats", "Fa major, DO MAJOR", "--curs", "4T  Elemental", "--instrument", "Flauta travessera") == 0
    out = capsys.readouterr().out
    assert "abans Do3-Sol4, ara Do3-La4" in out
    p = json.loads((dades / "perfil" / "nivells.json").read_text(encoding="utf-8"))
    assert list(p["perfils"]) == ["flauta|4 elemental"]                  # curs i instrument normalitzats
    perfil = p["perfils"]["flauta|4 elemental"]
    assert perfil["tonalitats"] == ["Do major", "Sol major", "Fa major"]  # suma, sense repetir
    assert [h["camp"] for h in perfil["historial"]].count("tessitura") == 2 and perfil["historial"][0]["data"]
    assert executar("nivell", "mostra", "--instrument", "flauta", "--curs", "elemental") == 0
    out = capsys.readouterr().out
    assert "Do3-La4" in out and "Falta saber: compassos" in out
    assert desa("--tonalitats", "Re major", "--substitueix") == 0
    assert nivells.carrega()["perfils"]["flauta|4 elemental"]["tonalitats"] == ["Re major"]
    assert executar("nivell", "mostra", "--instrument", "trompeta") == 0
    assert "Encara no sé res" in capsys.readouterr().out


def test_preferencies(capsys, dades):
    assert executar("preferencia", "mostra") == 0
    assert "Encara no" in capsys.readouterr().out
    assert executar("preferencia", "desa", "A 4t elemental la flauta no passa de Re5") == 0
    assert executar("preferencia", "desa", "a 4t elemental la flauta no passa de re5") == 0
    assert "Ja ho tenia" in capsys.readouterr().out.splitlines()[-1]
    assert executar("preferencia", "desa", "Prefereix la trompa en Fa sense armadura") == 0
    text = (dades / "perfil" / "preferencies.md").read_text(encoding="utf-8")
    assert text.count("\n- ") == 2 and "Re5" in text
    assert executar("preferencia", "mostra") == 0
    assert "trompa en Fa" in capsys.readouterr().out


# ----------------------------------------------------------------------- comprovació

@pytest.fixture
def flauta(tmp_path):
    p = stream.Part()
    p.insert(0, instrument.Flute())
    m1 = stream.Measure(number=1)
    m1.append(key.KeySignature(0))
    m1.append(meter.TimeSignature("4/4"))
    for x in ("C6", "D6", "E6", "F6"):
        m1.append(note.Note(x, type="quarter"))
    m2 = stream.Measure(number=2)
    m2.append(key.KeySignature(3))
    m2.append(meter.TimeSignature("5/4"))
    m2.append(note.Note("C4", type="quarter"))        # Do central = Do3 escrit: dins
    m2.append(note.Note("B3", type="quarter"))        # Si2: massa greu
    m2.append(note.Note("C7", type="eighth"))          # molt agut
    n = note.Note("D5", type="quarter"); n.duration = duration.Duration(type="eighth", dots=1)
    m2.append(n)
    for k in (1, 2, 3):
        t = note.Note("E5", type="eighth"); t.duration.appendTuplet(duration.Tuplet(3, 2)); m2.append(t)
    p.append(m1); p.append(m2)
    sc = stream.Score(); sc.insert(0, p)
    r = tmp_path / "flauta.musicxml"
    sc.write("musicxml", fp=str(r))
    return r


def test_tessitura_sense_perfil_diu_que_falta(flauta, capsys):
    assert executar("tessitura", flauta, "--instruments", "1=flauta", "--nivell", "4t elemental") == 0
    out = capsys.readouterr().out
    assert "No tinc el perfil complet de Flauta" in out and "partitures nivell desa --instrument flauta" in out
    assert "tessitura" in out and "compassos" in out


def test_tessitura_amb_perfil_llista_el_que_excedeix(flauta, capsys):
    desa("--tessitura", "Do3-Re5", "--tonalitats", "Do major, fins a 1 alteracions", "--compassos", "2/4, 3/4, 4/4",
         "--figures", "negra, corxera", "--articulacions", "picat")
    capsys.readouterr()
    assert executar("tessitura", flauta, "--instruments", "1=flauta", "--nivell", "4t elemental") == 0
    out = capsys.readouterr().out
    assert "per damunt del nivell" in out
    assert "compàs 1: Mi5 és més agut que Re5 (tessitura)" in out and "compàs 1: Fa5 és més agut que Re5 (tessitura)" in out
    assert "compàs 2: Si2 és més greu que Do3" in out
    assert "compàs 2: armadura de 3 sostinguts" in out and "compàs 2: compàs 5/4" in out
    assert "compàs 2: corxera amb puntet (figura)" in out and "compàs 2: tresillo (figura)" in out
    assert "Articulacions del nivell: picat" in out


def test_tessitura_json_porta_el_nivell(flauta, capsys):
    desa("--tessitura", "Do3-Sol6")
    capsys.readouterr()
    assert executar("tessitura", flauta, "--instruments", "1=flauta", "--nivell", "4t elemental", "--json") == 0
    d = json.loads(capsys.readouterr().out)
    n = d["parts"][0]["nivell"]
    assert n["perfil"] and n["mancant"] == ["tonalitats", "figures", "compassos", "articulacions"]
    assert any(p["tipus"] == "tessitura" for p in n["problemes"])


def test_transpositor_compara_en_so_escrit(tmp_path, capsys):
    p = stream.Part()
    p.insert(0, instrument.Trumpet())
    m = stream.Measure(number=1)
    m.append(key.KeySignature(0))
    m.append(note.Note("C7", type="whole"))
    p.append(m)
    sc = stream.Score(); sc.insert(0, p)
    r = tmp_path / "t.musicxml"
    sc.write("musicxml", fp=str(r))
    desa("--tessitura", "Do3-Do5", "--tonalitats", "Do major", instrument="trompeta-sib")
    capsys.readouterr()
    assert executar("tessitura", r, "--instruments", "1=trompeta-sib", "--nivell", "4t elemental") == 0
    out = capsys.readouterr().out
    assert "armadura" not in out
    assert "més agut que Do5" in out


# ----------------------------------------------------------------------- compartir

def test_exporta_i_perfils_compartits_de_la_biblioteca(tmp_path, monkeypatch, capsys, projecte):
    desa("--tessitura", "Do3-Re5", "--figures", "negra")
    capsys.readouterr()
    assert executar("nivell", "exporta") == 0
    out = capsys.readouterr().out
    assert "Fitxer creat: eixida/nivells.json" in out
    exportat = json.loads((projecte / "eixida" / "nivells.json").read_text(encoding="utf-8"))
    assert "historial" not in exportat["perfils"]["flauta|4 elemental"]
    # una altra persona, sense perfil propi, el llig de la biblioteca (només lectura)
    lib = tmp_path / "lib"
    (lib / "nivells").mkdir(parents=True)
    (lib / "nivells" / "departament.json").write_bytes((projecte / "eixida" / "nivells.json").read_bytes())
    monkeypatch.setenv("ARRANJAMENTS_BIBLIOTECA", str(lib))
    monkeypatch.setenv("ARRANJAMENTS_DADES", str(tmp_path / "altres-dades"))
    antes = (lib / "nivells" / "departament.json").read_bytes()
    assert executar("nivell", "mostra", "--instrument", "flauta") == 0
    out = capsys.readouterr().out
    assert "Do3-Re5" in out and "de la biblioteca: nivells/departament.json" in out
    # el propi guanya sobre el compartit, camp a camp
    desa("--tessitura", "Do3-Mi5")
    assert nivells.perfil("flauta", "4t elemental")["tessitura"] == "Do3-Mi5"
    assert nivells.perfil("flauta", "4t elemental")["figures"] == ["negra"]
    assert (lib / "nivells" / "departament.json").read_bytes() == antes


def test_exporta_sense_perfils(capsys):
    assert executar("nivell", "exporta") == 1


def test_cerca_de_biblioteca_avisa_si_passa_del_perfil(tmp_path, monkeypatch, capsys, piano_trompeta):
    import shutil
    lib = tmp_path / "lib"
    (lib / "4t elemental").mkdir(parents=True)
    shutil.copy(piano_trompeta, lib / "4t elemental" / "Trompeta i piano.musicxml")
    monkeypatch.setenv("ARRANJAMENTS_BIBLIOTECA", str(lib))
    desa("--tessitura", "Do3-Si3", instrument="trompeta-sib")
    assert executar("biblioteca", "actualitza") == 0
    capsys.readouterr()
    assert executar("biblioteca", "cerca", "trompeta", "--nivell", "4t elemental") == 0
    out = capsys.readouterr().out
    assert "Ull: Trumpet" in out
