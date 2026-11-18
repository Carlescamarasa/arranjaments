"""Proves sobre els fitxers del projecte: text net, instal·ladors i configuració d'OpenCode."""
import json
import re
from pathlib import Path

import pytest

ARREL = Path(__file__).resolve().parent.parent
TEXTOS = ([ARREL / "README.md", ARREL / "AGENTS.md", ARREL / "opencode.json", ARREL / "pyproject.toml",
           ARREL / "instalacio" / "instalar-mac.sh", ARREL / "instalacio" / "instalar-windows.ps1",
           ARREL / "Instalar-Mac.command", ARREL / "Instalar-Windows.bat"]
          + list((ARREL / ".opencode" / "skills").rglob("SKILL.md"))
          + list((ARREL / "scripts").rglob("*.py")) + list((ARREL / ".github").rglob("*.yml")))


def _text(f):
    return f.read_text(encoding="utf-8-sig")


@pytest.mark.parametrize("f", TEXTOS, ids=lambda f: str(f.relative_to(ARREL)))
def test_text_net_sense_guions_llargs_punts_volats_emojis_ni_rutes_personals(f):
    t = _text(f)
    assert "—" not in t, "guió llarg"
    assert " · " not in t, "punt volat com a separador"
    assert not re.search("[\U0001F300-\U0001FAFF☀-➿]", t), "emoji"
    assert "/Users/" not in t and not re.search(r"[A-Z]:\\Users\\(?!el-teu-nom|<)", t), "ruta personal"


def test_agents_curt_i_amb_les_instruccions_essencials():
    t = _text(ARREL / "AGENTS.md")
    assert len(t.strip().splitlines()) <= 80
    for clau in ("timeout", "900000", "Fitxer actual", "&&", ".local/bin/uv", "DADA", "entrenar",
                 "uv run partitures info", "uv run partitures exportar", "--assigna", "tessitura", "transport"):
        assert clau in t, clau


def test_les_skills_diuen_el_timeout_de_les_operacions_llargues():
    for nom in ("importar-pdf", "preparar-ordinador"):
        assert "900000" in _text(ARREL / ".opencode" / "skills" / nom / "SKILL.md")


def test_un_sol_recordatori_de_drets_d_autor_a_les_skills():
    amb = [f.parent.name for f in (ARREL / ".opencode" / "skills").rglob("SKILL.md") if "drets" in _text(f).lower()]
    assert amb == ["buscar-partitura"]


def test_el_ps1_es_utf8_amb_bom():
    assert (ARREL / "instalacio" / "instalar-windows.ps1").read_bytes().startswith(b"\xef\xbb\xbf")


def test_installadors_sense_sudo_i_amb_ruta_de_usuari():
    mac = _text(ARREL / "instalacio" / "instalar-mac.sh")
    assert "sudo " not in mac and "$HOME/Applications" in mac and "MuseScore*.app" in mac
    win = _text(ARREL / "instalacio" / "instalar-windows.ps1")
    assert "MuseScore*" in win and "LOCALAPPDATA" in win and "UAC" in win


def test_readme_avisos_importants():
    t = _text(ARREL / "README.md")
    assert "esborrar fitxers està prohibit" not in t and "Permetre" not in t
    assert "sense MuseHub" in t and "OneDrive" in t and "AGENTS.md" in t and "entrenar" in t
    assert "Do3" in t and "administrador" in t


def test_opencode_json_format_v2_amb_les_regles_clau():
    cfg = json.loads(_text(ARREL / "opencode.json"))
    assert "permission" not in cfg and isinstance(cfg["permissions"], list)
    regles = [(r["action"], r["resource"], r["effect"]) for r in cfg["permissions"]]
    assert ("shell", "uv run partitures *", "allow") in regles
    for ordre in ("rm *", "del *", "rmdir *", "Remove-Item *", "mv *"):
        assert ("shell", ordre, "deny") in regles
    assert ("edit", "*", "deny") in regles and ("webfetch", "*", "ask") in regles
    assert ("external_directory", "*", "ask") in regles
    # l'ordre importa (guanya l'última regla que coincideix): la general primer, les excepcions després
    assert regles.index(("shell", "*", "ask")) < regles.index(("shell", "uv run partitures *", "allow")) \
        < regles.index(("shell", "rm *", "deny"))


def test_ci_a_windows_i_mac():
    t = _text(ARREL / ".github" / "workflows" / "proves.yml")
    assert "windows-latest" in t and "macos-latest" in t and "pytest" in t and "uv" in t
    assert "Instalar-Mac.command" in t and "Instalar-Windows.bat" in t


def test_lanzadors_de_la_carpeta_arrel():
    mac = (ARREL / "Instalar-Mac.command").read_bytes()
    assert mac.startswith(b"#!/bin/bash") and b"\r\n" not in mac and b"instalar-mac.sh" in mac
    bat = (ARREL / "Instalar-Windows.bat").read_bytes()
    assert bat.isascii() and b"\r\n" in bat
    assert b"-ExecutionPolicy Bypass" in bat and b'-File "%~dp0instalacio\\instalar-windows.ps1"' in bat and b"pause" in bat


def test_el_command_es_executable_a_git():
    import shutil
    import subprocess
    if not shutil.which("git") or not (ARREL / ".git").exists():
        pytest.skip("sense git")
    r = subprocess.run(["git", "ls-files", "-s", "Instalar-Mac.command"], cwd=ARREL, capture_output=True, text=True)
    assert r.stdout.startswith("100755"), "el bit d'execució ha d'estar a git perquè sobrevisca al ZIP"


def test_installadors_creen_la_icona_i_tenen_mode_sense_preguntes():
    mac = _text(ARREL / "instalacio" / "instalar-mac.sh")
    assert "osacompile" in mac and "--sense-preguntes" in mac and "opencode-desktop-mac-" in mac
    win = _text(ARREL / "instalacio" / "instalar-windows.ps1")
    assert "WScript.Shell" in win and "GetFolderPath('Desktop')" in win and "-SensePreguntes" in win
    assert "opencode-desktop-win-x64.exe" in win and '"/S"' in win


def test_readme_explica_la_instalacio_amb_doble_clic_i_els_avisos():
    t = _text(ARREL / "README.md")
    for clau in ("Instalar-Mac.command", "Instalar-Windows.bat", "Obrir igualment", "Executar igualment",
                 "Desbloquejar", "Arranjaments", "Privacitat i seguretat", "Instal·lació manual"):
        assert clau in t, clau
