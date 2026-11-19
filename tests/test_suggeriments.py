"""Suggeriments de peces (classicisme, ragtime...) i baixada segura de partitures lliures."""
import urllib.error
from pathlib import Path

import pytest

from partitures import baixades, cli, suggeriments as sug
from partitures.errors import ErrorUsuari


def executar(*args):
    return cli.main([str(a) for a in args])


@pytest.fixture
def sense_parse(monkeypatch):
    """Sense llegir cap partitura del corpus (ràpid): el detall és fix."""
    monkeypatch.setattr(sug, "_detall_corpus", lambda ref: "4 parts (Violin I, Violin II, Viola, Cello); 60 compassos")


def test_comprendre_periode_compositor_i_paraules_soltes():
    q = sug.comprendre("Vull un trio de canyes (oboè, clarinet, fagot) amb una peça del classicisme per a 4t d'elemental")
    assert q["periodes"] == ["classicisme"] and q["compositors"] == [] and q["soltes"] == []
    q = sug.comprendre("res de Mozart ni jazz")
    assert q["compositors"] == ["mozart"] and q["periodes"] == ["jazz"]
    assert sug.comprendre("clàssic")["periodes"] == ["classicisme"] and sug.comprendre("barroco")["periodes"] == ["barroc"]
    assert sug.comprendre("coral de C.P.E. Bach")["compositors"] == ["cpebach"]
    assert sug.comprendre("una peça de Telemann")["soltes"] == ["telemann"]


def test_titols_llegibles_nomes_de_la_ruta_del_corpus():
    assert sug.titol_de_ruta("haydn/opus74no1/movement2.mxl") == "Haydn: op. 74 núm. 1, moviment 2"
    assert sug.titol_de_ruta("mozart/k458/movement3.mxl") == "Mozart: K. 458, moviment 3"
    assert sug.titol_de_ruta("bach/bwv66.6") == "J.S. Bach: BWV 66.6"
    assert sug.titol_de_ruta("joplin/maple_leaf_rag.mxl") == "Scott Joplin: maple leaf rag"


def test_classicisme_nomes_compositors_classics_i_cap_ragtime_d_entrada(projecte, sense_parse, capsys):
    (projecte / "entrada" / "maple_leaf_rag.musicxml").write_text("x", encoding="utf-8")
    assert executar("suggereix", "trio de canyes classicisme", "--nivell", "4t elemental",
                    "--instruments", "oboè, clarinet, fagot") == 0
    out = capsys.readouterr().out
    assert "maple_leaf_rag" not in out and "Joplin" not in out
    numerades = [l for l in out.splitlines() if l[:1].isdigit()]
    assert 3 <= len(numerades) <= 6
    assert all(any(c in l for c in ("Haydn", "Mozart", "Beethoven", "C.P.E. Bach")) for l in numerades)
    assert "Té 4 parts i en vols 3" in out
    for font in ("OpenScore", "CPDL", "Mutopia"):
        assert font in out


def test_les_candidates_del_corpus_son_reals():
    reals = set(sug._entrades_corpus())
    for c in sug.candidates_corpus(["haydn", "mozart", "beethoven", "cpebach"], True, 8, sorted(reals)):
        assert c["ref"] in reals
    for p, (_, _, dirs, _) in sug.PERIODES.items():
        assert {r.split("/")[0] for r in reals} >= set(dirs), p


def test_nivell_elemental_prefereix_moviments_lents(sense_parse):
    c = sug.candidates_corpus(["mozart"], True, 3)
    assert all(sug._moviment(x["ref"]) in (2, 3) for x in c)


def test_entrada_nomes_si_encaixa(projecte, sense_parse, capsys):
    (projecte / "entrada" / "maple_leaf_rag.musicxml").write_text("x", encoding="utf-8")
    assert executar("suggereix", "ragtime") == 0
    out = capsys.readouterr().out
    assert "maple_leaf_rag.musicxml   [entrada/]" in out and "Scott Joplin" in out


def test_sense_resultats_ho_diu_i_dona_les_fonts_del_web(capsys):
    assert executar("suggereix", "zzzz") == 0
    out = capsys.readouterr().out
    assert "No tinc cap peça" in out and "https://github.com/OpenScore" in out and "Mutopia" in out


def test_cal_text_i_copia_demana_suggeriment_previ(capsys):
    assert executar("suggereix") == 1
    assert "Ep!" in capsys.readouterr().err
    assert executar("suggereix", "--copia", "1") == 1
    assert "Primer cal demanar" in capsys.readouterr().err


def test_copia_del_corpus_a_entrada_i_no_sobreescriu(projecte, sense_parse, capsys):
    assert executar("suggereix", "mozart", "--maxim", "2") == 0
    capsys.readouterr()
    assert executar("suggereix", "--copia", "1") == 0
    ruta = capsys.readouterr().out.strip().splitlines()[-1].removeprefix("Fitxer actual: ")
    assert ruta.startswith("entrada/mozart-k") and (projecte / ruta).is_file()
    assert executar("suggereix", "--copia", "1") == 0
    assert len(list((projecte / "entrada").glob("mozart*"))) == 2
    assert executar("suggereix", "--copia", "9") == 1


def test_les_dades_reals_del_primer_suggeriment_es_poden_llegir(projecte, capsys):
    assert executar("suggereix", "mozart", "--maxim", "1") == 0
    out = capsys.readouterr().out
    assert "Mozart: K. " in out and "4 parts" in out and "compassos" in out


# ------------------------------------------------------------------ baixada segura

class Resposta:
    def __init__(self, dades: bytes, url="https://www.cpdl.org/x/obra.mxl", cap=None):
        self._d, self._u, self.headers = dades, url, cap or {}

    def read(self, n=-1):
        return self._d[:n] if n >= 0 else self._d

    def geturl(self):
        return self._u

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


XML = b'<?xml version="1.0"?><score-partwise version="3.1"><part-list/></score-partwise>'


@pytest.mark.parametrize("url", ["http://www.cpdl.org/a.mxl", "https://evil.example.com/a.mxl", "https://user:p@www.cpdl.org/a.mxl",
                                 "https://www.cpdl.org.evil.com/a.mxl", "https://www.cpdl.org:8443/a.mxl", "file:///etc/passwd"])
def test_baixada_refusa_adreces_no_permeses(url, monkeypatch):
    monkeypatch.setattr(baixades, "_obri", lambda u: pytest.fail("no s'havia d'obrir"))
    with pytest.raises(ErrorUsuari):
        baixades.descarrega(url)


def test_baixada_desa_a_entrada_sense_sobreescriure(projecte, monkeypatch, capsys):
    monkeypatch.setattr(baixades, "_obri", lambda u: Resposta(XML, u))
    assert executar("descarrega", "https://www.cpdl.org/wiki/images/obra.xml") == 0
    assert capsys.readouterr().out.strip() == "Fitxer actual: entrada/obra.xml"
    assert executar("descarrega", "https://www.cpdl.org/wiki/images/obra.xml") == 0
    assert (projecte / "entrada" / "obra-2.xml").is_file()


def test_baixada_mxl_i_extensions(projecte, monkeypatch):
    monkeypatch.setattr(baixades, "_obri", lambda u: Resposta(b"PK\x03\x04zzz", u))
    assert baixades.descarrega("https://raw.githubusercontent.com/OpenScore/x/a.mxl").name == "a.mxl"
    for mal in ("https://www.cpdl.org/a.pdf", "https://www.cpdl.org/a.exe", "https://www.cpdl.org/a"):
        with pytest.raises(ErrorUsuari) as e:
            baixades.descarrega(mal)
        assert "MusicXML" in str(e.value)
    assert not list((projecte / "entrada").glob("a.pdf"))


def test_baixada_pagina_html_no_es_desa_i_diu_que_ho_baixe_ell(projecte, monkeypatch):
    monkeypatch.setattr(baixades, "_obri", lambda u: Resposta(b"<!DOCTYPE html><html>Comprovant que no ets un robot", u))
    with pytest.raises(ErrorUsuari) as e:
        baixades.descarrega("https://www.cpdl.org/a.mxl")
    assert "navegador" in str(e.value) and "entrada/" in str(e.value)
    assert not list((projecte / "entrada").iterdir())


def test_baixada_xml_que_no_es_musicxml_o_zip_fals(projecte, monkeypatch):
    monkeypatch.setattr(baixades, "_obri", lambda u: Resposta(b"<foo/>", u))
    with pytest.raises(ErrorUsuari):
        baixades.descarrega("https://www.cpdl.org/a.xml")
    monkeypatch.setattr(baixades, "_obri", lambda u: Resposta(b"no es zip", u))
    with pytest.raises(ErrorUsuari):
        baixades.descarrega("https://www.cpdl.org/a.mxl")


def test_baixada_mida_maxima(projecte, monkeypatch):
    monkeypatch.setattr(baixades, "MIDA_MAXIMA", 100)
    monkeypatch.setattr(baixades, "_obri", lambda u: Resposta(b"PK" + b"0" * 500, u, {"Content-Length": "502"}))
    with pytest.raises(ErrorUsuari) as e:
        baixades.descarrega("https://www.cpdl.org/a.mxl")
    assert "massa gran" in str(e.value)
    monkeypatch.setattr(baixades, "_obri", lambda u: Resposta(b"PK" + b"0" * 500, u))
    with pytest.raises(ErrorUsuari):
        baixades.descarrega("https://www.cpdl.org/a.mxl")


def test_baixada_errors_de_xarxa_son_missatges_clars(projecte, monkeypatch):
    def cau(u):
        raise urllib.error.URLError("sense xarxa")
    monkeypatch.setattr(baixades, "_obri", cau)
    with pytest.raises(ErrorUsuari) as e:
        baixades.descarrega("https://www.cpdl.org/a.mxl")
    assert "navegador" in str(e.value)


def test_redireccio_a_un_domini_no_permes_es_bloqueja():
    h = baixades._Redireccio()
    with pytest.raises(ErrorUsuari):
        h.redirect_request(None, None, 302, "Found", {}, "https://evil.example.com/a.mxl")


def test_baixada_de_musescore_es_converteix_a_musicxml(projecte, monkeypatch):
    from partitures import eines, externs
    monkeypatch.setattr(baixades, "_obri", lambda u: Resposta(b'<museScore version="4.0"><Score/></museScore>', u))
    monkeypatch.setattr(eines, "trobar_musescore", lambda: "mscore")
    crides = []

    def fals(mscore, origen, desti, temps_maxim=300):
        crides.append((Path(origen).name, Path(desti).name))
        Path(desti).write_bytes(XML)
    monkeypatch.setattr(externs, "_mscore_a_pdf", fals)
    r = baixades.descarrega("https://raw.githubusercontent.com/OpenScore/x/peca.mscx")
    assert r == projecte / "entrada" / "peca.musicxml" and crides == [("peca.mscx", "peca.musicxml")]
    assert not list((projecte / "entrada").glob("*.mscx"))
