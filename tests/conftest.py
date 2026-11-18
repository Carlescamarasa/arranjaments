import pytest
from music21 import corpus, harmony, instrument, layout, note, stream


@pytest.fixture(autouse=True)
def projecte(tmp_path, monkeypatch):
    """Cada prova treballa dins d'un projecte buit (amb entrada/ i eixida/), mai dins del projecte real."""
    arrel = tmp_path / "projecte"
    (arrel / "entrada").mkdir(parents=True)
    (arrel / "eixida").mkdir()
    monkeypatch.setenv("PARTITURES_ARREL", str(arrel))
    monkeypatch.chdir(arrel)
    monkeypatch.delenv("PARTITURES_DEBUG", raising=False)
    return arrel


@pytest.fixture(scope="session")
def coral(tmp_path_factory):
    """Un coral de Bach (domini públic) del corpus de music21, desat com a MusicXML."""
    s = corpus.parse("bach/bwv66.6")
    ruta = tmp_path_factory.mktemp("dades") / "coral.musicxml"
    s.write("musicxml", fp=str(ruta))
    return ruta


def _compas(*notes):
    m = stream.Measure()
    for n in notes:
        m.append(n)
    return m


@pytest.fixture(scope="session")
def piano_trompeta(tmp_path_factory):
    """Trompeta + piano (dos pentagrames amb clau) en MusicXML."""
    sc = stream.Score()
    tr = stream.Part()
    tr.insert(0, instrument.Trumpet())
    tr.append(_compas(note.Note("C5", type="whole")))
    dreta, esquerra = stream.PartStaff(), stream.PartStaff()
    dreta.insert(0, instrument.Piano())
    esquerra.insert(0, instrument.Piano())
    dreta.append(_compas(note.Note("E5", type="whole")))
    esquerra.append(_compas(note.Note("C3", type="whole")))
    for p in (tr, dreta, esquerra):
        sc.insert(0, p)
    sc.insert(0, layout.StaffGroup([dreta, esquerra], symbol="brace", name="Piano"))
    ruta = tmp_path_factory.mktemp("dades") / "piano-trompeta.musicxml"
    sc.write("musicxml", fp=str(ruta))
    return ruta


@pytest.fixture(scope="session")
def amb_acords(tmp_path_factory):
    """Una part amb dues notes reals i símbols d'acord (C7, Dm) que no són notes."""
    sc = stream.Score()
    p = stream.Part()
    m = stream.Measure()
    m.insert(0, harmony.ChordSymbol("C7"))
    m.insert(0, note.Note("C4", quarterLength=2))
    m.insert(2, harmony.ChordSymbol("Dm"))
    m.insert(2, note.Note("D4", quarterLength=2))
    p.append(m)
    sc.insert(0, p)
    ruta = tmp_path_factory.mktemp("dades") / "acords.musicxml"
    sc.write("musicxml", fp=str(ruta))
    return ruta
