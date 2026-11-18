import pytest
from music21 import corpus


@pytest.fixture(scope="session")
def coral(tmp_path_factory):
    """Un coral de Bach (domini públic) del corpus de music21, desat com a MusicXML."""
    s = corpus.parse("bach/bwv66.6")
    ruta = tmp_path_factory.mktemp("dades") / "coral.musicxml"
    s.write("musicxml", fp=str(ruta))
    return ruta
