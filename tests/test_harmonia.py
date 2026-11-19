"""Fitxes d'harmonia: cada exemple MusicXML fa el que diu la fitxa, i les ordres `harmonia` funcionen."""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from harmonia_dades import EXEMPLES, GENERALS, PROVES, comprovacions  # noqa: E402
from music21 import converter  # noqa: E402

from partitures import harmonia as h  # noqa: E402
from partitures.cli import main  # noqa: E402
from partitures.errors import ErrorUsuari  # noqa: E402

ARREL = Path(__file__).resolve().parent.parent
REF = ARREL / "referencies" / "harmonia"
_LINIA_FITXA = re.compile(r"\[(exemple-[\w-]+)\.musicxml\]\([^)]*\)[^`]*`([^`]+)`")


def _veus_musicxml(ruta):
    parts = list(converter.parse(str(ruta)).parts)
    assert len(parts) == 4
    veus = {v: [n.pitch for n in p.recurse().notes] for v, p in zip(h.ORDRE_VEUS, parts)}
    return veus, h._tonalitat_de(parts)


def _id(ex):
    return f"{ex['tema']}/{ex['fitxer']}"


@pytest.mark.parametrize("ex", EXEMPLES, ids=_id)
def test_exemple_falla_exactament_la_seua_regla(ex):
    veus, k = _veus_musicxml(REF / ex["tema"] / f"{ex['fitxer']}.musicxml")
    fallades = [c for c in comprovacions(ex) if h.COMPROVACIONS[c](veus, k)]
    assert sorted(fallades) == sorted(ex["falla"])
    if ex.get("tipus"):
        assert h.sisena_augmentada(veus, k)[0] == ex["tipus"]


@pytest.mark.parametrize("ex", EXEMPLES, ids=_id)
def test_linia_de_la_fitxa_coincideix_amb_el_musicxml(ex):
    text = (REF / ex["tema"] / "fitxa.md").read_text(encoding="utf-8")
    linies = {m.group(1): m.group(2).strip() for m in _LINIA_FITXA.finditer(text)}
    veus, _ = _veus_musicxml(REF / ex["tema"] / f"{ex['fitxer']}.musicxml")
    assert linies.get(ex["fitxer"]) == h.escriure_linia(veus)


def test_tots_els_musicxml_tenen_exemple_i_tot_exemple_existeix():
    en_disc = {(p.parent.name, p.stem) for p in REF.glob("*/exemple-*.musicxml")}
    assert en_disc == {(e["tema"], e["fitxer"]) for e in EXEMPLES}
    for tema in {e["tema"] for e in EXEMPLES}:
        assert (REF / tema / "fitxa.md").is_file()


@pytest.mark.parametrize("pr", PROVES, ids=lambda p: p["nom"][:40])
def test_proves_internes_de_les_excepcions(pr):
    veus, k = h.llegir_linia(pr["linia"]), h.a_tonalitat(pr["tonalitat"])
    assert sorted(c for c in GENERALS if h.COMPROVACIONS[c](veus, k)) == sorted(pr["falla"])


def test_les_fitxes_no_porten_text_dels_llibres_ni_eines_antigues():
    for f in REF.glob("*/fitxa.md"):
        t = f.read_text(encoding="utf-8")
        assert "eines/" not in t and ".venv" not in t
        assert "partitures harmonia comprova" in t, f.name


# ---------- l'ordre ----------

def test_comprova_exemple_incorrecte_diu_compas_i_cita_la_fitxa(capsys):
    r = REF / "quintes-octaves-paraleles" / "exemple-2-incorrecte.musicxml"
    assert main(["harmonia", "comprova", str(r)]) == 0
    out = capsys.readouterr().out
    assert "Compàs 1" in out and "quintes successives entre T i B" in out
    assert "referencies/harmonia/quintes-octaves-paraleles/fitxa.md" in out


def test_comprova_exemple_correcte_no_troba_res(capsys):
    r = REF / "quintes-octaves-paraleles" / "exemple-1-correcte.musicxml"
    assert main(["harmonia", "comprova", str(r)]) == 0
    assert "cap problema" in capsys.readouterr().out


def test_sisena_augmentada_amb_tonalitat_menor(capsys):
    r = REF / "sisena-augmentada" / "exemple-5-incorrecte.musicxml"
    assert main(["harmonia", "comprova", str(r), "--tonalitat", "la menor"]) == 0
    out = capsys.readouterr().out
    assert "no puja un semitò" in out and "sisena-augmentada/fitxa.md" in out


def test_comprova_amb_ritme_diu_el_compas_i_el_temps(tmp_path, capsys):
    """Dos compassos de 4/4 en negres: les quintes T-B surten amb el compàs i el temps."""
    from music21 import clef, key, meter, note, stream
    sc = stream.Score()
    linies = {"S": "Mi4 Re4 Mi4 Re4 Fa4 Re4 Mi4 Do4", "A": "Sol3 Sol3 Sol3 Sol3 La3 Si3 Sol3 Sol3",
              "T": "Do3 Si2 Do3 Si2 Do3 Re3 Do3 Do3", "B": "Do2 Sol1 Do2 Sol1 Fa2 Sol2 Do2 Do2"}
    for v, txt in linies.items():
        p = stream.Part()
        for i, n in enumerate(txt.split()):
            if i % 4 == 0:
                m = stream.Measure(number=i // 4 + 1)
                if i == 0:
                    m.append(key.Key("C")); m.append(meter.TimeSignature("4/4"))
                    m.append(clef.BassClef() if v == "B" else clef.TrebleClef())
                p.append(m)
            m.append(note.Note(h.a_pitch(n), type="quarter"))
        sc.insert(0, p)
    f = tmp_path / "coral.musicxml"
    sc.write("musicxml", fp=str(f))
    assert main(["harmonia", "comprova", str(f)]) == 0
    out = capsys.readouterr().out
    assert "Compàs 2" in out and "temps 1: quintes successives entre T i B" in out


def test_comprova_errors_clars(tmp_path):
    r = REF / "quintes-octaves-paraleles" / "exemple-1-correcte.musicxml"
    with pytest.raises(ErrorUsuari):
        h.comprova(converter.parse(str(r)), "SAT")
    with pytest.raises(ErrorUsuari):
        h.comprova(converter.parse(str(r)), "TASB")


def test_fitxa_mostra_el_text_i_accepta_un_tros_del_nom(capsys):
    assert main(["harmonia", "fitxa", "quintes-octaves-paraleles"]) == 0
    assert "Quintes i octaves paral" in capsys.readouterr().out
    assert main(["harmonia", "fitxa", "sisena"]) == 0
    assert "Acords de sisena augmentada" in capsys.readouterr().out
    assert main(["harmonia", "fitxa"]) == 0
    assert "sensible-i-setena-v7" in capsys.readouterr().out
    assert main(["harmonia", "fitxa", "rondo"]) == 1


def test_fitxes_no_instal·lades_diuen_que_cal_actualitzar(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PARTITURES_REFERENCIES", str(tmp_path))
    assert main(["harmonia", "fitxa", "sisena"]) == 1
    assert "actualitzar" in capsys.readouterr().err


# ---------- empaquetat i instal·ladors ----------

def test_el_paquet_d_actualitzacio_porta_les_fitxes_i_no_el_treball(tmp_path):
    from partitures import actualitzar as act
    z = act.crea_paquet(ARREL, "9.9.9", tmp_path)
    import zipfile
    noms = zipfile.ZipFile(z).namelist()
    assert "referencies/harmonia/sisena-augmentada/fitxa.md" in noms
    assert sum(n.endswith(".musicxml") and n.startswith("referencies/harmonia/") for n in noms) == len(EXEMPLES)
    assert not any("_fonts-text" in n for n in noms)
    assert "referencies" in act.ELEMENTS_DADES and "referencies" not in [a for a, _ in act.ELEMENTS_TREBALL]


def test_els_instal·ladors_copien_les_referencies_a_la_carpeta_de_dades_i_el_zip_les_inclou():
    for nom in ("instalar-mac.sh", "instalar-linux.sh", "instalar-windows.ps1"):
        t = (ARREL / "instalacio" / nom).read_text(encoding="utf-8")
        assert "referencies" in t, nom
    paquets = (ARREL / "instalacio" / "visual" / "paquets.py").read_text(encoding="utf-8")
    assert '"referencies"' not in paquets  # no s'exclou del ZIP del projecte
    assert not (ARREL / "_fonts-text").exists()
