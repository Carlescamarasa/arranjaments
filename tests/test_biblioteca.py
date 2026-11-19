import os
import shutil
import sys
import unicodedata

import pytest

from partitures import biblioteca as bib
from partitures import cli


@pytest.fixture(autouse=True)
def dades(tmp_path, monkeypatch):
    d = tmp_path / "dades"
    monkeypatch.setenv("ARRANJAMENTS_DADES", str(d))
    monkeypatch.delenv("ARRANJAMENTS_BIBLIOTECA", raising=False)
    return d


def executar(*args):
    return cli.main([str(a) for a in args])


def _fer(carpeta, *ruta, text=b"x"):
    p = carpeta.joinpath(*ruta)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text)
    return p


def _mac(tmp_path, nom_org="OneDrive-EscolaMusica"):
    home = tmp_path / "casa"
    arrel = home / "Library" / "CloudStorage" / nom_org
    return home, arrel


# ----------------------------------------------------------------------- detecció

def test_mac_troba_la_carpeta_dins_de_onedrive(tmp_path):
    home, arrel = _mac(tmp_path)
    lib = arrel / "Biblioteca d'arranjaments"
    lib.mkdir(parents=True)
    r = bib.localitzar(home, {}, "mac")
    assert r["ruta"] == lib


@pytest.mark.parametrize("nom", ["biblioteca d’arranjaments", "BIBLIOTECA D ARRANJAMENTS", "Biblioteca d'arranjaments (1)",
                                 "Biblioteca darranjaments", "Escola - Biblioteca d'arranjaments"])
def test_variants_del_nom(tmp_path, nom):
    home, arrel = _mac(tmp_path)
    (arrel / "Documents" / nom).mkdir(parents=True)
    assert bib.localitzar(home, {}, "mac")["ruta"] == arrel / "Documents" / nom


def test_nom_amb_accents_nfc_i_nfd(tmp_path):
    for forma in ("NFC", "NFD"):
        home = tmp_path / forma
        nom = unicodedata.normalize(forma, "Biblioteca d'arranjaments Música")
        (home / "Library" / "CloudStorage" / "OneDrive-X" / nom).mkdir(parents=True)
        assert bib.localitzar(home, {}, "mac")["ruta"] is not None
    assert bib.es_la_biblioteca(unicodedata.normalize("NFD", "Biblioteca d’arranjaments"))


def test_mac_carpeta_de_sharepoint_amb_nom_de_organitzacio(tmp_path):
    home = tmp_path / "casa"
    lib = home / "Library" / "CloudStorage" / "Conservatori Mestre" / "Biblioteca d'arranjaments"
    lib.mkdir(parents=True)
    (home / "Library" / "CloudStorage" / "GoogleDrive-a@b.c" / "Biblioteca d'arranjaments").mkdir(parents=True)
    assert bib.localitzar(home, {}, "mac")["ruta"] == lib


def test_windows_variables_i_carpetes_del_perfil(tmp_path):
    home = tmp_path / "usuari"
    onedrive = home / "OneDrive - Escola"
    lib = onedrive / "Biblioteca d'arranjaments"
    lib.mkdir(parents=True)
    assert bib.localitzar(home, {"OneDriveCommercial": str(onedrive)}, "windows")["ruta"] == lib
    assert bib.localitzar(home, {"USERPROFILE": str(home)}, "windows")["ruta"] == lib
    sp = home / "Escola - Departament"
    (sp / "Biblioteca d'arranjaments").mkdir(parents=True)
    r = bib.localitzar(home, {"USERPROFILE": str(home)}, "windows")
    assert r["ruta"] == lib and (sp / "Biblioteca d'arranjaments") in r["altres"]


def test_profunditat_limitada(tmp_path):
    home, arrel = _mac(tmp_path)
    fons = arrel.joinpath(*"abcdefgh") / "Biblioteca d'arranjaments"
    fons.mkdir(parents=True)
    assert bib.localitzar(home, {}, "mac")["ruta"] is None


def test_variable_i_config_manen(tmp_path, dades):
    lib = tmp_path / "lloc" / "meua"
    lib.mkdir(parents=True)
    r = bib.localitzar(tmp_path / "buit", {"ARRANJAMENTS_BIBLIOTECA": str(lib)}, "mac")
    assert r["ruta"] == lib
    dades.mkdir()
    (dades / "biblioteca.txt").write_text(str(lib) + "\n", encoding="utf-8")
    assert bib.localitzar(tmp_path / "buit", {}, "mac")["ruta"] == lib
    r = bib.localitzar(tmp_path / "buit", {"ARRANJAMENTS_BIBLIOTECA": str(tmp_path / "no")}, "mac")
    assert r["ruta"] is None and "no existeix" in r["avis"]


def test_on_es_sense_biblioteca_explica_els_passos(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(bib, "_plataforma", lambda: "mac")
    monkeypatch.setenv("HOME", str(tmp_path / "buit"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "buit"))
    assert executar("biblioteca", "on-es") == 0
    out = capsys.readouterr().out
    assert "Afegeix una drecera a Els meus fitxers" in out and "Add shortcut to My files" in out


def test_on_es_linux_diu_que_no(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(bib, "_plataforma", lambda: "altre")
    monkeypatch.setenv("HOME", str(tmp_path / "buit"))
    assert executar("biblioteca", "on-es") == 0
    assert "LliureX" in capsys.readouterr().out


def test_on_es_amb_biblioteca(tmp_path, monkeypatch, capsys):
    lib = tmp_path / "lib"
    _fer(lib, "a.pdf")
    monkeypatch.setenv("ARRANJAMENTS_BIBLIOTECA", str(lib))
    assert executar("biblioteca", "on-es") == 0
    out = capsys.readouterr().out
    assert "He trobat la biblioteca" in out and "1 PDF" in out


# ----------------------------------------------------------------------- fitxers al núvol

def test_detecta_marcadors_del_nuvol():
    class St:
        st_file_attributes = 0x00400000
    class Mac:
        st_flags = 0x40000000
    class Local:
        st_file_attributes = 0x20
        st_flags = 0
    assert bib.al_nuvol(St()) and bib.al_nuvol(Mac()) and not bib.al_nuvol(Local())


# ----------------------------------------------------------------------- etiquetes

def test_etiquetes_de_carpetes_noms_i_text(tmp_path):
    lib = tmp_path / "lib"
    _fer(lib, "4t elemental", "jazz", "Blues [Trompeta] [5è professional].musicxml")
    _fer(lib, "4t elemental", "jazz", "Blues [Trompeta] [5è professional].musicxml.txt",
         text="estil: swing, bossa\nnivell: grau mitjà\nTitol: El blues\nuna nota lliure".encode())
    e = bib.etiquetes_de("4t elemental/jazz/Blues [Trompeta] [5è professional].musicxml", lib)
    assert "4t elemental" in e["nivell"] and "5è professional" in e["nivell"] and "grau mitjà" in e["nivell"]
    assert "jazz" in e["estil"] and "Trompeta" in e["estil"] and "swing" in e["estil"] and "bossa" in e["estil"]
    assert e["titol_f"] == "El blues" and "nota lliure" in e["nota"]


def test_etiquetes_sidecar_amb_el_nom_sense_extensio(tmp_path):
    lib = tmp_path / "lib"
    _fer(lib, "peça.mxl")
    _fer(lib, "peça.txt", text=b"[jazz] [2n elemental]")
    e = bib.etiquetes_de("peça.mxl", lib)
    assert e["estil"] == ["jazz"] and e["nivell"] == ["2n elemental"]


# ----------------------------------------------------------------------- índex, cerca, còpia

@pytest.fixture
def lib(tmp_path, coral, piano_trompeta, monkeypatch):
    base = tmp_path / "lib"
    (base / "4t elemental" / "jazz").mkdir(parents=True)
    (base / "Cambra").mkdir()
    shutil.copy(coral, base / "Cambra" / "Coral de Bach [barroc].musicxml")
    shutil.copy(piano_trompeta, base / "4t elemental" / "jazz" / "Trompeta i piano.musicxml")
    _fer(base, "Cambra", "Escaneig antic.pdf", text=b"%PDF-1.4")
    _fer(base, "Cambra", "Quintet.mscz", text=b"PK")
    _fer(base, "Cambra", "trencada.musicxml", text=b"no es xml")
    _fer(base, "notes.docx")
    monkeypatch.setenv("ARRANJAMENTS_BIBLIOTECA", str(base))
    return base


def foto(arrel):
    return sorted((str(p.relative_to(arrel)), p.stat().st_mtime_ns, p.read_bytes() if p.is_file() else b"")
                  for p in arrel.rglob("*"))


def test_actualitza_metadades_i_lectura_nomes(lib, capsys):
    abans = foto(lib)
    assert executar("biblioteca", "actualitza") == 0
    out = capsys.readouterr().out
    assert "5 fitxers" in out and "1 que no he pogut llegir" in out and "Tot al dia" in out
    assert foto(lib) == abans                                   # res canviat, res creat dins la biblioteca
    idx = bib.llig_index(lib)["fitxers"]
    c = idx["Cambra/Coral de Bach [barroc].musicxml"]
    assert c["estat"] == "ok" and c["tonalitat"].startswith("Fa# menor") and c["compas"] == "4/4"
    assert len(c["parts"]) == 4 and c["parts"][3]["mes_greu"] == "Fa#1" and c["compassos"] > 5
    assert c["estil"] == ["Cambra", "barroc"] or "barroc" in c["estil"]
    assert idx["Cambra/Escaneig antic.pdf"]["estat"] == "nomes-nom"
    assert idx["Cambra/trencada.musicxml"]["estat"] == "error"
    assert "notes.docx" not in idx


@pytest.mark.skipif(sys.platform.startswith("win") or (hasattr(os, "geteuid") and os.geteuid() == 0),
                    reason="permisos de només lectura")
def test_funciona_amb_la_biblioteca_realment_de_nomes_lectura(lib, capsys):
    for p in [lib, *lib.rglob("*")]:
        os.chmod(p, 0o555 if p.is_dir() else 0o444)
    try:
        assert executar("biblioteca", "actualitza") == 0
        assert executar("biblioteca", "cerca", "bach") == 0
    finally:
        for p in [lib, *lib.rglob("*")]:
            os.chmod(p, 0o755 if p.is_dir() else 0o644)


def test_index_incremental_i_limit_per_vegada(lib, capsys, monkeypatch):
    cridades = []
    original = bib._analitza
    monkeypatch.setattr(bib, "_analitza", lambda r: (cridades.append(r.name), original(r))[1])
    r1 = bib.actualitza(lib, maxim_noves=1, sortida=lambda *_: None)
    assert r1["analitzades"] + r1["errors"] == 1 and r1["queden"] == 2
    r2 = bib.actualitza(lib, maxim_noves=10, sortida=lambda *_: None)
    assert r2["queden"] == 0 and len(cridades) == 3
    r3 = bib.actualitza(lib, sortida=lambda *_: None)             # res de nou: no s'analitza res
    assert r3["analitzades"] == 0 and len(cridades) == 3
    p = lib / "4t elemental" / "jazz" / "Trompeta i piano.musicxml"
    os.utime(p, (p.stat().st_atime, p.stat().st_mtime + 100))      # canviat: es torna a analitzar només este
    bib.actualitza(lib, sortida=lambda *_: None)
    assert cridades[3:] == ["Trompeta i piano.musicxml"]


def test_pendents_ja_es_poden_cercar_pel_nom(lib):
    bib.actualitza(lib, maxim_noves=0, sortida=lambda *_: None)
    assert [r for _, r, _ in bib.cerca("bach", arrel=lib)] == ["Cambra/Coral de Bach [barroc].musicxml"]


def test_etiqueta_nova_no_requereix_tornar_a_analitzar(lib):
    bib.actualitza(lib, sortida=lambda *_: None)
    _fer(lib, "Cambra", "Coral de Bach [barroc].txt", text=b"estil: luteria")
    r = bib.actualitza(lib, sortida=lambda *_: None)
    assert r["analitzades"] == 0
    assert bib.cerca("", estil="luteria", arrel=lib)[0][1].startswith("Cambra/Coral")


def test_cerca_sense_accents_filtres_i_ordre(lib, capsys):
    bib.actualitza(lib, sortida=lambda *_: None)
    assert [r for _, r, _ in bib.cerca("PEÇA bach", arrel=lib)] == []
    assert bib.cerca("trompeta", arrel=lib)[0][1].startswith("4t elemental/jazz")
    assert [r for _, r, _ in bib.cerca("", nivell="elemental", arrel=lib)] == ["4t elemental/jazz/Trompeta i piano.musicxml"]
    assert [r for _, r, _ in bib.cerca("", nivell="4T ELEMENTAL", estil="jàzz", arrel=lib)]
    assert bib.cerca("", instrument="piano", arrel=lib)[0][1].endswith("Trompeta i piano.musicxml")
    assert bib.cerca("", estil="jazz", instrument="piano", nivell="superior", arrel=lib) == []
    # el títol pesa més que la carpeta: «cambra» a la carpeta, «coral» al nom
    r = [x for _, x, _ in bib.cerca("coral cambra", arrel=lib)]
    assert r[0].startswith("Cambra/Coral")
    # el PDF només per nom
    assert "Cambra/Escaneig antic.pdf" in [x for _, x, _ in bib.cerca("escaneig", arrel=lib)]


def test_ordre_cerca_mostra_metadades(lib, capsys):
    assert executar("biblioteca", "actualitza") == 0
    capsys.readouterr()
    assert executar("biblioteca", "cerca", "coral", "bach") == 0
    out = capsys.readouterr().out
    assert "Fa# menor" in out and "4/4" in out and "compassos" in out and "Cambra/Coral de Bach [barroc].musicxml" in out
    assert "[Cambra | barroc]" in out
    assert executar("biblioteca", "cerca", "escaneig") == 0
    assert "PDF: cal importar" in capsys.readouterr().out
    assert executar("biblioteca", "cerca", "quintet") == 0
    assert "MuseScore" in capsys.readouterr().out


def test_cerca_sense_index_demana_actualitzar(lib, capsys):
    assert executar("biblioteca", "cerca", "bach") == 1
    assert "actualitza" in capsys.readouterr().err


def test_copia_va_a_entrada_i_no_toca_la_biblioteca(lib, projecte, capsys):
    executar("biblioteca", "actualitza")
    executar("biblioteca", "cerca", "bach")
    capsys.readouterr()
    abans = foto(lib)
    assert executar("biblioteca", "copia", 1) == 0
    out = capsys.readouterr().out.strip().splitlines()[-1]
    assert out == "Fitxer actual: entrada/Coral de Bach.musicxml"
    assert (projecte / "entrada" / "Coral de Bach.musicxml").read_bytes() == (lib / "Cambra" / "Coral de Bach [barroc].musicxml").read_bytes()
    assert executar("biblioteca", "copia", 1) == 0                # mai sobreescriu
    assert (projecte / "entrada" / "Coral de Bach-2.musicxml").exists()
    assert foto(lib) == abans
    assert executar("biblioteca", "copia", 7) == 1
    assert "no coincideix" in capsys.readouterr().err


def test_copia_sense_cerca_prèvia(lib, capsys):
    assert executar("biblioteca", "copia", 1) == 1
    assert "Primer cal fer una cerca" in capsys.readouterr().err


def test_canvi_de_biblioteca_descarta_l_index(lib, tmp_path, monkeypatch):
    bib.actualitza(lib, sortida=lambda *_: None)
    altra = tmp_path / "altra"
    _fer(altra, "x.pdf")
    assert bib.llig_index(altra)["fitxers"] == {}
