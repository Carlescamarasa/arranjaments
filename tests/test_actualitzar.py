"""Proves de l'actualització silenciosa: versions, sha256, sense xarxa, fitxers de la persona i tornar enrere."""
import functools
import hashlib
import http.server
import json
import threading
import zipfile
from pathlib import Path

import pytest

from partitures import actualitzar as act


def _escriu(ruta: Path, text: str) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(text, encoding="utf-8")


def _arbre(arrel: Path, versio: str, marca: str, lock: str = "lock-1") -> None:
    """Un 'projecte' mínim amb tot el que forma part d'una actualització."""
    _escriu(arrel / "VERSION", versio + "\n")
    _escriu(arrel / "scripts/partitures/__init__.py", "")
    _escriu(arrel / "scripts/partitures/actualitzar.py", f"# {marca}")
    _escriu(arrel / "scripts/partitures/marca.txt", marca)
    _escriu(arrel / "pyproject.toml", "[project]\nname='partitures'\n")
    _escriu(arrel / "uv.lock", lock)
    _escriu(arrel / ".python-version", "3.12\n")
    _escriu(arrel / "AGENTS.md", f"agents {marca}")
    _escriu(arrel / "opencode.json", "{}")
    _escriu(arrel / "NOVETATS.md", f"novetats {marca}")
    _escriu(arrel / ".opencode/skills/arranjar/SKILL.md", f"skill {marca}")
    _escriu(arrel / "instalacio/instalar-linux.sh", f"# {marca}")
    _escriu(arrel / "referencies/harmonia/tema/fitxa.md", f"fitxa {marca}")


@pytest.fixture
def entorn(tmp_path):
    dades, treball, servidor = tmp_path / "dades", tmp_path / "Arranjaments", tmp_path / "servidor"
    _arbre(dades, "0.1.1", "vella")
    for c in ("entrada", "eixida", ".opencode"):
        (treball / c).mkdir(parents=True)
    _escriu(treball / "eixida/meva.musicxml", "la meua partitura")
    _escriu(treball / "entrada/original.pdf", "pdf")
    _escriu(treball / ".opencode/AGENTS.md", "agents vella")
    _escriu(treball / ".opencode/NOVETATS.md", "novetats vella")
    _escriu(treball / ".opencode/opencode.json", "{}")
    _escriu(treball / ".opencode/skills/arranjar/SKILL.md", "skill vella")
    servidor.mkdir()
    inst = act.Instalacio(dades, treball, servidor.as_uri(), proves=True)
    inst.servidor = servidor  # type: ignore[attr-defined]
    return inst


def _publica(inst, tmp_path, versio, marca, lock="lock-1"):
    font = tmp_path / f"font-{versio}"
    _arbre(font, "0", marca, lock)
    act.crea_paquet(font, versio, inst.servidor)


def _sense_sync(_):
    return True


def _foto(carpeta: Path) -> dict:
    return {p.relative_to(carpeta).as_posix(): p.read_bytes() for p in sorted(carpeta.rglob("*")) if p.is_file()}


def test_compara_versions():
    assert act.compara("0.1.12", "0.1.9") == 1
    assert act.compara("0.1.9", "0.1.12") == -1
    assert act.compara("0.1", "0.1.0") == 0
    assert act.compara("2.0.0", "1.99.99") == 1
    with pytest.raises(ValueError):
        act.parseja("1.x")


def test_actualitza_canvia_eines_i_configuracio_i_no_toca_res_de_la_persona(entorn, tmp_path):
    _publica(entorn, tmp_path, "0.1.2", "nova")
    persona_abans = _foto(entorn.treball / "eixida") | _foto(entorn.treball / "entrada")
    r = act.actualitza(entorn, forca=True, sync=_sense_sync)
    assert r.codi == "actualitzada", r
    assert act.versio_de(entorn.dades) == "0.1.2"
    assert (entorn.dades / "scripts/partitures/marca.txt").read_text(encoding="utf-8") == "nova"
    assert (entorn.treball / ".opencode/AGENTS.md").read_text(encoding="utf-8") == "agents nova"
    assert (entorn.treball / ".opencode/skills/arranjar/SKILL.md").read_text(encoding="utf-8") == "skill nova"
    assert (entorn.dades / ".opencode/skills/arranjar/SKILL.md").read_text(encoding="utf-8") == "skill nova"
    assert (entorn.dades / "referencies/harmonia/tema/fitxa.md").read_text(encoding="utf-8") == "fitxa nova"
    assert (_foto(entorn.treball / "eixida") | _foto(entorn.treball / "entrada")) == persona_abans
    assert sorted(p.name for p in entorn.treball.iterdir()) == [".opencode", "eixida", "entrada"]
    assert sorted(p.name for p in (entorn.treball / ".opencode").iterdir()) == ["AGENTS.md", "NOVETATS.md", "opencode.json", "skills"]
    # el que s'ha deixat en preparar no es queda
    assert not (entorn.dades / ".actualitzacio").exists()
    assert (entorn.dades / "anterior/ESTAT.json").exists()


def test_al_dia_no_fa_res(entorn, tmp_path):
    _publica(entorn, tmp_path, "0.1.1", "igual")
    r = act.actualitza(entorn, forca=True, sync=_sense_sync)
    assert r.codi == "al_dia"
    assert not (entorn.dades / "anterior").exists()
    assert (entorn.dades / "scripts/partitures/marca.txt").read_text(encoding="utf-8") == "vella"


def test_versio_mes_vella_o_igual_no_es_baixa(entorn, tmp_path):
    _publica(entorn, tmp_path, "0.1.0", "enrere")
    assert act.actualitza(entorn, forca=True, sync=_sense_sync).codi == "al_dia"


def test_sha_diferent_es_rebutja(entorn, tmp_path):
    _publica(entorn, tmp_path, "0.1.2", "nova")
    ruta = entorn.servidor / act.FITXER_VERSIO
    d = json.loads(ruta.read_text(encoding="utf-8"))
    d["sha256"] = hashlib.sha256(b"altra cosa").hexdigest()
    ruta.write_text(json.dumps(d))
    r = act.actualitza(entorn, forca=True, sync=_sense_sync)
    assert r.codi == "error"
    assert not (entorn.dades / "anterior").exists()
    assert (entorn.dades / "scripts/partitures/marca.txt").read_text(encoding="utf-8") == "vella"
    assert act.versio_de(entorn.dades) == "0.1.1"
    assert "sha256" in (entorn.dades / "actualitzacio.log").read_text(encoding="utf-8")


def test_paquet_amb_ruta_fora_es_rebutja(entorn, tmp_path):
    _publica(entorn, tmp_path, "0.1.2", "nova")
    ruta_zip = entorn.servidor / act.FITXER_PAQUET
    with zipfile.ZipFile(ruta_zip, "a") as z:
        z.writestr("../fora.txt", "mal")
    d = json.loads((entorn.servidor / act.FITXER_VERSIO).read_text(encoding="utf-8"))
    d["sha256"] = hashlib.sha256(ruta_zip.read_bytes()).hexdigest()
    d["mida"] = ruta_zip.stat().st_size
    (entorn.servidor / act.FITXER_VERSIO).write_text(json.dumps(d))
    assert act.actualitza(entorn, forca=True, sync=_sense_sync).codi == "error"
    assert not (entorn.dades.parent / "fora.txt").exists()
    assert act.versio_de(entorn.dades) == "0.1.1"


def test_sense_xarxa_no_falla_i_ho_registra(entorn):
    entorn.url = (entorn.servidor / "no-hi-ha-res").as_uri()
    r = act.actualitza(entorn, forca=True, sync=_sense_sync)
    assert r.codi == "sense_xarxa"
    assert r.be
    assert act.versio_de(entorn.dades) == "0.1.1"
    assert "Sense connexió" in (entorn.dades / "actualitzacio.log").read_text(encoding="utf-8")


def test_servidor_http_inaccessible(entorn):
    entorn.url = "http://127.0.0.1:9"   # port on no escolta ningú
    assert act.actualitza(entorn, forca=True, sync=_sense_sync).codi == "sense_xarxa"


def test_http_real_amb_servidor_local(entorn, tmp_path):
    _publica(entorn, tmp_path, "0.1.2", "nova")
    gestor = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(entorn.servidor))
    gestor.func.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), gestor)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        entorn.url = f"http://127.0.0.1:{srv.server_port}"
        assert act.actualitza(entorn, forca=True, sync=_sense_sync).codi == "actualitzada"
    finally:
        srv.shutdown()
    assert act.versio_de(entorn.dades) == "0.1.2"


def test_sense_mode_proves_nomes_s_admet_https(entorn):
    entorn.proves = False
    entorn.url = entorn.servidor.as_uri()
    assert act.actualitza(entorn, forca=True, sync=_sense_sync).codi == "error"


def test_torna_enrere_restaura_tot(entorn, tmp_path):
    antes = _foto(entorn.dades) | {"T/" + k: v for k, v in _foto(entorn.treball).items()}
    _publica(entorn, tmp_path, "0.1.2", "nova")
    assert act.actualitza(entorn, forca=True, sync=_sense_sync).codi == "actualitzada"
    r = act.torna_enrere(entorn, sync=_sense_sync)
    assert r.codi == "enrere", r
    assert act.versio_de(entorn.dades) == "0.1.1"
    despres = {k: v for k, v in _foto(entorn.dades).items() if not k.startswith("anterior/") and not k.endswith((".log", "estat.json"))}
    despres |= {"T/" + k: v for k, v in _foto(entorn.treball).items()}
    assert despres == antes
    # i l'actualització automàtica no torna a posar la mateixa versió que s'ha rebutjat
    assert act.actualitza(entorn, forca=False, sync=_sense_sync).codi in ("omesa", "recent")
    assert act.versio_de(entorn.dades) == "0.1.1"


def test_torna_enrere_treu_les_peces_que_la_versio_vella_no_tenia(entorn, tmp_path):
    (entorn.dades / "NOVETATS.md").unlink()
    (entorn.treball / ".opencode/NOVETATS.md").unlink()
    _publica(entorn, tmp_path, "0.1.2", "nova")
    act.actualitza(entorn, forca=True, sync=_sense_sync)
    assert (entorn.treball / ".opencode/NOVETATS.md").exists()
    act.torna_enrere(entorn, sync=_sense_sync)
    assert not (entorn.treball / ".opencode/NOVETATS.md").exists()
    assert not (entorn.dades / "NOVETATS.md").exists()


def test_torna_enrere_sense_versio_anterior(entorn):
    assert act.torna_enrere(entorn, sync=_sense_sync).codi == "error"


def test_si_falla_el_canvi_tot_queda_com_estava(entorn, tmp_path, monkeypatch):
    _publica(entorn, tmp_path, "0.1.2", "nova")
    abans = _foto(entorn.dades) | {"T/" + k: v for k, v in _foto(entorn.treball).items()}
    reals = act._mou

    def trenca(origen, desti):
        if desti == entorn.treball / ".opencode" / "skills" and ".actualitzacio-nou" in str(origen):
            raise PermissionError("fitxer en ús")
        reals(origen, desti)

    monkeypatch.setattr(act, "_mou", trenca)
    r = act.actualitza(entorn, forca=True, sync=_sense_sync)
    assert r.codi == "error"
    despres = {k: v for k, v in _foto(entorn.dades).items() if not k.startswith("anterior/") and k not in ("actualitzacio.log", "actualitzacio-estat.json")}
    despres |= {"T/" + k: v for k, v in _foto(entorn.treball).items()}
    assert despres == {k: v for k, v in abans.items() if not k.startswith("anterior/")}


def test_uv_sync_nomes_si_canvia_el_lock(entorn, tmp_path):
    crides = []
    _publica(entorn, tmp_path, "0.1.2", "nova", lock="lock-1")
    act.actualitza(entorn, forca=True, sync=lambda d: crides.append(d) or True)
    assert crides == []
    _publica(entorn, tmp_path, "0.1.3", "mes-nova", lock="lock-2")
    if not act.troba_uv():
        pytest.skip("uv no és al PATH")
    act.actualitza(entorn, forca=True, sync=lambda d: crides.append(d) or True)
    assert crides == [entorn.dades]


def test_si_falla_uv_sync_es_torna_a_la_versio_vella(entorn, tmp_path, monkeypatch):
    monkeypatch.setattr(act, "troba_uv", lambda: "uv")
    _publica(entorn, tmp_path, "0.1.2", "nova", lock="lock-2")
    r = act.actualitza(entorn, forca=True, sync=lambda d: False)
    assert r.codi == "error"
    assert act.versio_de(entorn.dades) == "0.1.1"
    assert (entorn.dades / "uv.lock").read_text(encoding="utf-8") == "lock-1"
    assert (entorn.treball / ".opencode/AGENTS.md").read_text(encoding="utf-8") == "agents vella"


def test_python_diferent_demana_reinstalar(entorn, tmp_path):
    _publica(entorn, tmp_path, "0.1.2", "nova")
    font = tmp_path / "font-py"
    _arbre(font, "0", "nova")
    _escriu(font / ".python-version", "3.13\n")
    act.crea_paquet(font, "0.1.2", entorn.servidor)
    r = act.actualitza(entorn, forca=True, sync=_sense_sync)
    assert r.codi == "cal_reinstalar"
    assert act.versio_de(entorn.dades) == "0.1.1"


def test_consulta_com_a_molt_una_vegada_per_hora(entorn, tmp_path):
    _publica(entorn, tmp_path, "0.1.1", "igual")
    assert act.actualitza(entorn, sync=_sense_sync, ara=lambda: 10000.0).codi == "al_dia"
    _publica(entorn, tmp_path, "0.1.2", "nova")
    assert act.actualitza(entorn, sync=_sense_sync, ara=lambda: 10100.0).codi == "recent"
    assert act.versio_de(entorn.dades) == "0.1.1"
    assert act.actualitza(entorn, sync=_sense_sync, ara=lambda: 10000.0 + 3700).codi == "actualitzada"


def test_el_llancador_obri_sempre_el_programa(entorn, monkeypatch):
    obert = []
    monkeypatch.setattr(act, "obri_programa", lambda ruta, cwd=None: obert.append(ruta))
    # sense xarxa
    monkeypatch.setenv("ARRANJAMENTS_DADES", str(entorn.dades))
    monkeypatch.setenv("ARRANJAMENTS_TREBALL", str(entorn.treball))
    monkeypatch.setenv(act.VAR_URL, (entorn.servidor / "res").as_uri())
    fals = entorn.dades / "OpenCode.exe"
    fals.write_text("x")
    assert act.main(["--silenci", "--obri", str(fals)]) == 0
    assert obert == [str(fals)]
    # i amb un error inesperat dins de l'actualitzador
    def explota(*a, **k):
        raise RuntimeError("bum")
    monkeypatch.setattr(act, "actualitza", explota)
    assert act.main(["--silenci", "--obri", str(fals)]) == 0
    assert obert == [str(fals), str(fals)]
    assert "bum" in (entorn.dades / "actualitzacio.log").read_text(encoding="utf-8")


def test_des_del_repositori_no_es_toca_res(monkeypatch):
    monkeypatch.delenv("ARRANJAMENTS_DADES", raising=False)
    assert act.instalacio_actual() is None


def test_crea_paquet_no_porta_res_de_la_persona(tmp_path):
    font = tmp_path / "f"
    _arbre(font, "0", "x")
    _escriu(font / "entrada/secret.pdf", "no")
    _escriu(font / "eixida/secret.xml", "no")
    _escriu(font / "scripts/partitures/__pycache__/a.pyc", "no")
    act.crea_paquet(font, "3.1.4", tmp_path / "o")
    with zipfile.ZipFile(tmp_path / "o" / act.FITXER_PAQUET) as z:
        noms = z.namelist()
    assert "VERSION" in noms
    assert not [n for n in noms if n.startswith(("entrada", "eixida")) or "__pycache__" in n]
    d = json.loads((tmp_path / "o" / act.FITXER_VERSIO).read_text(encoding="utf-8"))
    assert d["versio"] == "3.1.4" and len(d["sha256"]) == 64
