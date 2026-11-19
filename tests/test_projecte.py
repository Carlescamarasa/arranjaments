"""Proves sobre els fitxers del projecte: text net, instal·ladors i configuració d'OpenCode."""
import json
import re
from pathlib import Path

import pytest

ARREL = Path(__file__).resolve().parent.parent
TEXTOS = ([ARREL / "README.md", ARREL / "AGENTS.md", ARREL / "opencode.json", ARREL / "pyproject.toml",
           ARREL / "instalacio" / "instalar-mac.sh", ARREL / "instalacio" / "instalar-windows.ps1",
           ARREL / "instalacio" / "Instalar-Mac.command", ARREL / "instalacio" / "Instalar-Windows.bat",
           ARREL / "instalacio" / "instalar-linux.sh", ARREL / "instalacio" / "Instalar-Linux-Terminal.sh",
           ARREL / "Instal·lar Arranjaments (Linux).desktop"]
          + [f for f in (ARREL / "instalacio" / "visual").rglob("*") if f.suffix in (".swift", ".cs", ".sh", ".ps1", ".py", ".plist", ".manifest")]
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
    for clau in ("timeout", "900000", "Fitxer actual", "&&", "~/.local/bin/partitures", "partitures.cmd", "DADA", "entrenar",
                 "`partitures info", "`partitures exportar", "partitures instalar audiveris", "--assigna", "tessitura", "transport"):
        assert clau in t, clau
    # l'ajudant treballa des de la carpeta de treball amb l'ordre «partitures», no amb uv ni amb rutes del repositori
    for f in [ARREL / "AGENTS.md"] + list((ARREL / ".opencode" / "skills").rglob("SKILL.md")):
        assert "uv run" not in _text(f) and "instalacio/" not in _text(f) and "instalacio\\" not in _text(f), f


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
    assert "$HOME/Library/Application Support/Arranjaments" in mac and "$HOME/Documents/Arranjaments" in mac
    win = _text(ARREL / "instalacio" / "instalar-windows.ps1")
    assert "MuseScore*" in win and "LOCALAPPDATA" in win and "UAC" in win
    # eines fora d'OneDrive; carpeta de treball a la Documents de veritat; configuració amagada
    assert 'Join-Path $env:LOCALAPPDATA "Arranjaments"' in win and "GetFolderPath('MyDocuments')" in win and "Hidden" in win


def test_readme_avisos_importants():
    t = _text(ARREL / "README.md")
    assert "esborrar fitxers està prohibit" not in t and "Permetre" not in t
    assert "sense MuseHub" in t and "OneDrive" in t and "AGENTS.md" in t and "entrenar" in t
    assert "Do3" in t and "administrador" in t


def test_opencode_json_format_v2_amb_les_regles_clau():
    cfg = json.loads(_text(ARREL / "opencode.json"))
    assert "permission" not in cfg and isinstance(cfg["permissions"], list)
    regles = [(r["action"], r["resource"], r["effect"]) for r in cfg["permissions"]]
    assert ("shell", "partitures *", "allow") in regles and ("shell", "~/.local/bin/partitures *", "allow") in regles
    assert not [r for r in regles if r[0] == "shell" and r[2] == "allow" and "uv" in r[1].split()], "només «partitures» sense preguntar"
    # instal·lar sempre pregunta, encara que la resta d'ordres «partitures» no
    assert regles.index(("shell", "partitures *", "allow")) < regles.index(("shell", "partitures instalar *", "ask"))
    # les instruccions de l'ajudant viuen amagades dins de .opencode
    assert cfg["instructions"] == [".opencode/AGENTS.md"]
    for ordre in ("rm *", "del *", "rmdir *", "Remove-Item *", "mv *"):
        assert ("shell", ordre, "deny") in regles
    assert ("edit", "*", "deny") in regles and ("webfetch", "*", "ask") in regles
    assert ("external_directory", "*", "ask") in regles
    # l'ordre importa (guanya l'última regla que coincideix): la general primer, les excepcions després
    assert regles.index(("shell", "*", "ask")) < regles.index(("shell", "partitures *", "allow")) \
        < regles.index(("shell", "rm *", "deny"))


def test_ci_a_windows_i_mac():
    t = _text(ARREL / ".github" / "workflows" / "proves.yml")
    assert "windows-latest" in t and "macos-latest" in t and "pytest" in t and "uv" in t
    # un sol fitxer per sistema: es fa, es baixa a una carpeta amb accents i espais i s'obri com la professora
    for clau in ("Arranjaments-Windows.exe", "Arranjaments-Mac.dmg", "Arranjaments-LliureX.run", "paquets.py", "fes-dmg.sh", "hdiutil attach"):
        assert clau in t, clau
    # també a ARM64 (Windows 11 ARM i Linux ARM; macos-latest ja és Apple Silicon)
    assert "windows-11-arm" in t and "ubuntu-24.04-arm" in t
    # l'instal·lador visual es construeix, es prova en mode automàtic i es publica
    for clau in ("construir.sh", "construir.ps1", "--auto", "empaqueta.py", "arranjaments.zip", "actualitzacio.zip", "versio.json", "gh release"):
        assert clau in t, clau
    # carpeta de treball neta, partitures conservades en repetir, i ordres de veritat des de la carpeta de treball
    for clau in ("Documents/Arranjaments", "Application Support/Arranjaments", "no-tocar.txt", "partitures comprovar",
                 "corpus bach --copia 1", "MyDocuments", "LOCALAPPDATA"):
        assert clau in t, clau


def test_lanzadors_alternatius_dins_de_instalacio():
    # A la carpeta principal només hi ha d'haver l'instal·lador visual (que arriba dins del ZIP publicat)
    assert not (ARREL / "Instalar-Mac.command").exists() and not (ARREL / "Instalar-Windows.bat").exists()
    mac = (ARREL / "instalacio" / "Instalar-Mac.command").read_bytes()
    assert mac.startswith(b"#!/bin/bash") and b"\r\n" not in mac and b"instalar-mac.sh" in mac
    assert b'cd "$(dirname "$0")/.."' in mac
    bat = (ARREL / "instalacio" / "Instalar-Windows.bat").read_bytes()
    assert bat.isascii() and b"\r\n" in bat
    assert b"-ExecutionPolicy Bypass" in bat and b'-File "%~dp0instalar-windows.ps1"' in bat and b"pause" in bat


def test_els_installadors_avisen_del_progres_nomes_si_es_demana():
    """L'instal·lador visual llig línies «@@PAS nom estat»; sense la variable, el text és el de sempre."""
    mac = _text(ARREL / "instalacio" / "instalar-mac.sh")
    win = _text(ARREL / "instalacio" / "instalar-windows.ps1")
    for t in (mac, win):
        assert "ARRANJAMENTS_PROGRES" in t and "@@" in t
        for pas in ("uv", "opencode", "musescore", "eines", "carpeta", "icona", "final"):
            assert re.search(rf'(?i)inici_?pas "?{pas}"?', t), pas
    assert len(re.findall(r"(?m)^inici_pas \w+;", mac)) == mac.count("\nfi_pas\n") == 8
    assert win.count("IniciPas \"") == win.count("\nFiPas\n") == 8


def test_el_guio_de_mac_escriu_els_avisos_de_progres(tmp_path):
    import shutil
    import subprocess
    import sys
    if sys.platform != "darwin" or not shutil.which("bash"):
        pytest.skip("només a Mac")
    guio = str(ARREL / "instalacio" / "instalar-mac.sh")
    import os
    amb = subprocess.run(["bash", guio, "--prova"], capture_output=True, text=True, env={**os.environ, "ARRANJAMENTS_PROGRES": "1"})
    sense = subprocess.run(["bash", guio, "--prova"], capture_output=True, text=True,
                           env={k: v for k, v in os.environ.items() if k != "ARRANJAMENTS_PROGRES"})
    avisos = [l for l in amb.stdout.splitlines() if l.startswith("@@")]
    assert avisos[0] == "@@PAS uv inici" and avisos[-1].startswith("@@FI ")
    assert all(re.fullmatch(r"@@(PAS \w+ (inici|ok|falla)|FI (ok|falla \d+))", l) for l in avisos), avisos
    assert "@@" not in sense.stdout
    assert [l for l in amb.stdout.splitlines() if not l.startswith("@@")] == sense.stdout.splitlines()


def test_installador_visual_executa_els_mateixos_guions():
    """Les finestres no instal·len res pel seu compte: només criden els guions i lligen el progrés."""
    swift = _text(ARREL / "instalacio" / "visual" / "mac" / "InstalarArranjaments.swift")
    cs = _text(ARREL / "instalacio" / "visual" / "windows" / "InstalarArranjaments.cs")
    assert "instalacio/instalar-mac.sh" in swift and "--sense-preguntes" in swift
    assert "instalar-windows.ps1" in cs and "-ExecutionPolicy Bypass" in cs and "-SensePreguntes" in cs and "CreateNoWindow = true" in cs
    for t in (swift, cs):
        assert "ARRANJAMENTS_PROGRES" in t and "--auto" in t and "--prova" in t
        assert "Tot a punt." in t and "Obri Arranjaments a l'Escriptori." in t and "Veure detalls" in t
        for pas in ('"uv"', '"opencode"', '"musescore"', '"eines"', '"carpeta"', '"icona"'):
            assert pas in t, pas
        for prohibit in ("curl ", "msiexec", "uv sync", "Invoke-WebRequest"):
            assert prohibit not in t, prohibit
    manifest = _text(ARREL / "instalacio" / "visual" / "windows" / "app.manifest")
    assert "asInvoker" in manifest
    for icona in ("Arranjaments.icns", "Arranjaments.ico"):
        assert (ARREL / "instalacio" / "visual" / "icona" / icona).stat().st_size > 1000


def test_el_zip_conserva_noms_utf8_i_permisos(tmp_path):
    import importlib.util
    import zipfile
    spec = importlib.util.spec_from_file_location("empaqueta", ARREL / "instalacio" / "visual" / "empaqueta.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    app = tmp_path / "c" / "Instal·lar Arranjaments.app" / "Contents" / "MacOS"
    app.mkdir(parents=True)
    (app / "Instalar").write_bytes(b"x")
    (app / "Instalar").chmod(0o755)
    (tmp_path / "c" / "README.md").write_text("hola", encoding="utf-8")
    assert modul.empaqueta(tmp_path / "c", tmp_path / "a.zip") == 2
    with zipfile.ZipFile(tmp_path / "a.zip") as z:
        info = {i.filename: i for i in z.infolist()}
    exe = info["arranjaments/Instal·lar Arranjaments.app/Contents/MacOS/Instalar"]
    assert exe.flag_bits & 0x800, "nom marcat com a UTF-8"
    if not sys_es_windows():
        assert (exe.external_attr >> 16) & 0o111, "permís d'execució"
    assert (info["arranjaments/README.md"].external_attr >> 16) & 0o777 == 0o644


def sys_es_windows():
    import sys
    return sys.platform.startswith("win")


def test_el_command_es_executable_a_git():
    import shutil
    import subprocess
    if not shutil.which("git") or not (ARREL / ".git").exists():
        pytest.skip("sense git")
    r = subprocess.run(["git", "ls-files", "-s", "instalacio/Instalar-Mac.command"], cwd=ARREL, capture_output=True, text=True)
    assert r.stdout.startswith("100755"), "el bit d'execució ha d'estar a git perquè sobrevisca al ZIP"


def test_installadors_creen_la_icona_i_tenen_mode_sense_preguntes():
    mac = _text(ARREL / "instalacio" / "instalar-mac.sh")
    assert "osacompile" in mac and "--sense-preguntes" in mac and "opencode-desktop-mac-" in mac
    win = _text(ARREL / "instalacio" / "instalar-windows.ps1")
    assert "WScript.Shell" in win and "GetFolderPath('Desktop')" in win and "-SensePreguntes" in win
    assert "opencode-desktop-win-$Arq.exe" in win and '"/S"' in win
    # arquitectura del sistema, no la del procés (un PowerShell x64 dins d'un Windows ARM diu AMD64)
    assert "OSArchitecture" in win and "PROCESSOR_ARCHITEW6432" in win and "ARM64" in win


def test_readme_explica_la_instalacio_amb_doble_clic_i_els_avisos():
    t = _text(ARREL / "README.md")
    for clau in ("Instal·lar Arranjaments", "releases/latest/download/arranjaments.zip", "Instalar-Mac.command",
                 "releases/latest/download/Arranjaments-Windows.exe", "releases/latest/download/Arranjaments-Mac.dmg",
                 "releases/latest/download/Arranjaments-LliureX.run", "És executable", "sh Arranjaments-LliureX.run",
                 "`Arranjaments` de Documents", "Application Support/Arranjaments", "%LOCALAPPDATA%\\Arranjaments",
                 "Instalar-Windows.bat", "Obre de tota manera", "Abrir igualmente", "Més informació", "Executa igualment",
                 "Desbloquejar", "Privacitat i seguretat", "Instal·lació manual", "potser", 'id="manual"', 'id="avisos"'):
        assert clau in t, clau


def _instalador(*args, entorn):
    """Executa l'instal·lador d'este sistema amb les carpetes desviades a un lloc de prova (o None si no n'hi ha)."""
    import os
    import shutil
    import subprocess
    import sys
    if sys.platform == "darwin":
        ordre = ["bash", str(ARREL / "instalacio" / "instalar-mac.sh"), "--sense-preguntes"]
        ordre += [a for a in args]
    elif sys_es_windows():
        pw = shutil.which("powershell")
        if not pw:
            return None
        ordre = [pw, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ARREL / "instalacio" / "instalar-windows.ps1"), "-SensePreguntes"]
        ordre += [{"--nomes": "-Nomes", "--prova": "-Prova"}.get(a, a) for a in args]
    else:
        return None
    env = {k: v for k, v in os.environ.items() if k not in ("PSModulePath", "PARTITURES_ARREL")}
    env.update(entorn)
    return subprocess.run(ordre, capture_output=True, env=env, cwd=str(ARREL))


def test_la_carpeta_de_treball_nomes_te_entrada_i_eixida_i_no_es_toquen_les_partitures(tmp_path):
    treball = tmp_path / "Documents àè" / "Arranjaments"
    entorn = {"ARRANJAMENTS_TREBALL": str(treball), "ARRANJAMENTS_DADES": str(tmp_path / "dades"),
              "ARRANJAMENTS_BIN": str(tmp_path / "bin")}
    r = _instalador("--nomes", "carpeta", entorn=entorn)
    if r is None:
        pytest.skip("només a Mac i Windows")
    assert r.returncode == 0, r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
    assert sorted(f.name for f in treball.iterdir()) == [".opencode", "eixida", "entrada"]
    assert sorted(f.name for f in (treball / ".opencode").iterdir()) == ["AGENTS.md", "NOVETATS.md", "opencode.json", "skills"]
    assert (treball / ".opencode" / "skills" / "arranjar" / "SKILL.md").exists()
    assert json.loads(_text(treball / ".opencode" / "opencode.json"))["instructions"] == [".opencode/AGENTS.md"]
    assert not (tmp_path / "dades").exists() and not (tmp_path / "bin").exists(), "«carpeta» no ha de tocar res més"
    if sys_es_windows():
        import ctypes
        assert ctypes.windll.kernel32.GetFileAttributesW(str(treball / ".opencode")) & 2, "la configuració ha d'estar amagada"

    # Repetir: es renova la configuració amagada, però les partitures es queden com estaven
    (treball / "eixida" / "no-tocar.txt").write_text("partitura de la professora", encoding="utf-8")
    (treball / "entrada" / "coral.musicxml").write_text("<score/>", encoding="utf-8")
    (treball / ".opencode" / "AGENTS.md").write_text("vell", encoding="utf-8")
    (treball / ".opencode" / "skills" / "antiga").mkdir()
    r = _instalador("--nomes", "carpeta", entorn=entorn)
    assert r.returncode == 0
    assert (treball / "eixida" / "no-tocar.txt").read_text(encoding="utf-8") == "partitura de la professora"
    assert (treball / "entrada" / "coral.musicxml").read_text(encoding="utf-8") == "<score/>"
    assert _text(treball / ".opencode" / "AGENTS.md") == _text(ARREL / "AGENTS.md")
    assert not (treball / ".opencode" / "skills" / "antiga").exists()
    assert sorted(f.name for f in treball.iterdir()) == [".opencode", "eixida", "entrada"]


def test_ordre_instalar_del_cli(monkeypatch):
    from partitures import cli, eines
    cridat = {}
    monkeypatch.setattr(eines, "instalar", lambda cosa, prova=False: cridat.update(cosa=cosa, prova=prova) or 0)
    assert cli.main(["instalar", "audiveris"]) == 0 and cridat == {"cosa": "audiveris", "prova": False}
    assert cli.main(["instalar", "--prova"]) == 0 and cridat["prova"] is True
    assert cli.main(["instalar"]) == 1, "sense dir què, no fa res"
    monkeypatch.setattr(eines, "instalar", lambda cosa, prova=False: 1)
    assert cli.main(["instalar", "musescore"]) == 1
    # l'instal·lador es busca al costat de les eines (igual al repositori que a la carpeta de dades)
    assert (Path(eines.__file__).resolve().parents[2] / "instalacio" / "instalar-mac.sh").exists()


# ---- Linux (LliureX)

def test_installador_linux_sense_sudo_amb_appimage_descomprimida_i_mateixos_passos():
    sh = _text(ARREL / "instalacio" / "instalar-linux.sh")
    assert not re.search(r"(?m)^[^#\n]*\bsudo (?!apt install curl)", sh.replace("sudo apt install curl", "")), "cap ordre amb sudo"
    assert "--appimage-extract" in sh, "sense FUSE: l'AppImage es descomprimeix"
    assert "xdg-user-dir" in sh and "XDG_DATA_HOME" in sh and "metadata::trusted" in sh
    assert "opencode-desktop-linux-" in sh and "musescore/MuseScore" in sh and "astral.sh/uv/install.sh" in sh
    assert len(re.findall(r"(?m)^inici_pas \w+;", sh)) == sh.count("\nfi_pas\n") == 8
    for pas in ("uv", "opencode", "musescore", "eines", "carpeta", "icona", "final"):
        assert re.search(rf"(?m)^inici_pas {pas}", sh), pas


def test_el_guio_de_linux_nomes_s_executa_a_linux_i_els_fitxers_son_executables_a_git():
    import shutil
    import subprocess
    if not shutil.which("git") or not (ARREL / ".git").exists():
        pytest.skip("sense git")
    for f in ("instalacio/instalar-linux.sh", "instalacio/Instalar-Linux-Terminal.sh", "Instal·lar Arranjaments (Linux).desktop"):
        r = subprocess.run(["git", "ls-files", "-s", f], cwd=ARREL, capture_output=True, text=True)
        assert r.stdout.startswith("100755"), f
    assert "\r\n" not in (ARREL / "instalacio" / "instalar-linux.sh").read_text(encoding="utf-8")


def test_el_desktop_de_doble_clic_executa_l_instalador_des_de_qualsevol_carpeta(tmp_path):
    """L'Exec del .desktop s'interpreta com diu l'especificació de freedesktop (dues capes d'escapament)."""
    import shlex
    import shutil
    import subprocess
    import sys
    if sys.platform.startswith("win") or not shutil.which("sh"):
        pytest.skip("només on hi ha sh")
    f = ARREL / "Instal·lar Arranjaments (Linux).desktop"
    camp = dict(l.split("=", 1) for l in _text(f).splitlines() if "=" in l)
    assert camp["Terminal"] == "true" and camp["Type"] == "Application"
    # 1) valor de cadena: \\ -> \ ; 2) cometes de l'Exec: \" \$ \` \\ -> el caràcter
    valor = camp["Exec"].replace("\\\\", "\\")
    arrel_c = tmp_path / "Carpeta àè amb espais"
    (arrel_c / "instalacio").mkdir(parents=True)
    (arrel_c / "instalacio" / "Instalar-Linux-Terminal.sh").write_text("echo ARRANCA-$(basename \"$PWD\")\n")
    escapat = re.sub(r"\\([\"`$\\])", r"\1", valor)
    cas = re.fullmatch(r'sh -c "(.*)" sh %k', escapat)
    assert cas, escapat
    r = subprocess.run(["sh", "-c", cas.group(1), "sh", str(arrel_c / "Instal·lar Arranjaments (Linux).desktop")],
                       capture_output=True, text=True)
    assert r.returncode == 0 and "ARRANCA-instalacio" in r.stdout, (r.stdout, r.stderr)
    assert shlex.split(escapat.replace("%k", "x"))[0] == "sh"


def test_ci_a_linux_prova_el_fitxer_run():
    t = _text(ARREL / ".github" / "workflows" / "proves.yml")
    assert "ubuntu-22.04" in t and "ubuntu-24.04" in t and "instalacio-linux" in t
    assert "QT_QPA_PLATFORM" in t and "Arranjaments-LliureX.run" in t
    assert re.search(r"publicar:\n\s+needs: \[[^\]]*instalacio-linux", t)


def _paquets():
    import importlib.util
    spec = importlib.util.spec_from_file_location("paquets", ARREL / "instalacio" / "visual" / "paquets.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _projecte_de_prova(tmp_path):
    c = tmp_path / "muntatge"
    (c / "instalacio").mkdir(parents=True)
    (c / "instalacio" / "instalar-linux.sh").write_text("#!/bin/bash\necho INSTAL-LA \"$@\"\n")
    (c / "instalacio" / "Instalar-Linux-Terminal.sh").write_text('#!/bin/bash\ncd "$(dirname "$0")/.." || exit 1\nbash instalacio/instalar-linux.sh "$@"\n')
    (c / "instalacio" / "Instalar-Linux-Terminal.sh").chmod(0o755)
    (c / "VERSION").write_text("1.2.3\n")
    for sobra in ("docs", "tests", ".github"):
        (c / sobra).mkdir()
        (c / sobra / "x.txt").write_text("no")
    (c / "Instal·lar Arranjaments (Linux).desktop").write_text("[Desktop Entry]\n")
    return c


def test_el_paquet_del_projecte_porta_el_necessari_en_zip_i_targz(tmp_path):
    import tarfile
    import zipfile
    m = _paquets()
    c = _projecte_de_prova(tmp_path)
    m.projecte(c, tmp_path / "p.zip", tmp_path / "p.tar.gz")
    with zipfile.ZipFile(tmp_path / "p.zip") as z:
        noms = {n for n in z.namelist() if not n.endswith("/")}
    with tarfile.open(tmp_path / "p.tar.gz") as t:
        noms_tar = {i.name: i for i in t.getmembers()}
    esperats = {"VERSION", "instalacio/instalar-linux.sh", "instalacio/Instalar-Linux-Terminal.sh"}
    assert noms == esperats and set(noms_tar) == esperats
    assert noms_tar["instalacio/Instalar-Linux-Terminal.sh"].mode & 0o111 and noms_tar["VERSION"].uid == 0


def test_l_exe_de_windows_porta_el_zip_enganxat_amb_la_marca_al_final(tmp_path):
    import struct
    import zipfile
    m = _paquets()
    c = _projecte_de_prova(tmp_path)
    m.projecte(c, tmp_path / "p.zip", tmp_path / "p.tar.gz")
    (tmp_path / "base.exe").write_bytes(b"MZ" + b"\0" * 100)
    m.windows(tmp_path / "base.exe", tmp_path / "p.zip", tmp_path / "Arranjaments-Windows.exe")
    b = (tmp_path / "Arranjaments-Windows.exe").read_bytes()
    assert b.startswith(b"MZ") and b.endswith(b"ARRPAYL1")
    mida = struct.unpack("<Q", b[-16:-8])[0]
    assert mida == (tmp_path / "p.zip").stat().st_size
    (tmp_path / "dins.zip").write_bytes(b[-16 - mida:-16])
    assert "VERSION" in zipfile.ZipFile(tmp_path / "dins.zip").namelist()
    # el programa de Windows llig exactament este format
    cs = _text(ARREL / "instalacio" / "visual" / "windows" / "InstalarArranjaments.cs")
    assert '"ARRPAYL1"' in cs and "BitConverter.ToInt64" in cs and "ZipArchive" in cs


def test_el_fitxer_run_s_auto_extrau_i_executa_l_instalador(tmp_path):
    """El guió de capçalera amb el tar.gz enganxat: descomprimeix a staging, executa l'instal·lador i l'esborra."""
    import shutil
    import subprocess
    import sys
    if sys.platform.startswith("win") or not shutil.which("sh"):
        pytest.skip("només on hi ha sh")
    m = _paquets()
    c = _projecte_de_prova(tmp_path)
    m.projecte(c, tmp_path / "p.zip", tmp_path / "p.tar.gz")
    run = tmp_path / "Carpeta àè amb espais" / "Arranjaments-LliureX.run"
    run.parent.mkdir()
    m.linux(ARREL / "instalacio" / "visual" / "linux" / "capcalera.sh", tmp_path / "p.tar.gz", run)
    assert run.stat().st_mode & 0o111
    dades = tmp_path / "dades àè"
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "ARRANJAMENTS_DADES": str(dades)}
    r = subprocess.run(["sh", str(run), "--sense-terminal", "--sense-preguntes", "--prova"], capture_output=True, text=True, env=env)
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert "INSTAL-LA --sense-preguntes --prova" in r.stdout and "--sense-terminal" not in r.stdout
    assert not (dades / "staging").exists(), "la còpia temporal s'esborra"
    # un fitxer trencat no instal·la res i ho diu
    trencat = tmp_path / "trencat.run"
    trencat.write_bytes(run.read_bytes()[:-300])
    r = subprocess.run(["sh", str(trencat), "--sense-terminal"], capture_output=True, text=True, env=env)
    assert r.returncode == 1 and "trencat" in r.stderr and not (dades / "staging").exists()


def test_la_capcalera_del_run_obri_un_terminal_nomes_amb_pantalla_i_sense_terminal():
    cap = (ARREL / "instalacio" / "visual" / "linux" / "capcalera.sh").read_text(encoding="utf-8")
    assert cap.startswith("#!/bin/sh") and cap.endswith("\n__ARXIU__\n") and "\r" not in cap
    assert "konsole" in cap and "[ ! -t 1 ]" in cap and "DISPLAY" in cap and "ARRANJAMENTS_EN_TERMINAL" in cap
    assert "sudo" not in cap.replace("sense sudo", "")


def test_el_dmg_porta_el_projecte_dins_de_l_aplicacio_i_l_app_el_descomprimeix_abans_d_executar():
    sh = (ARREL / "instalacio" / "visual" / "mac" / "fes-dmg.sh").read_text(encoding="utf-8")
    assert "Contents/Resources/projecte.tar.gz" in sh and "codesign --force --deep --sign -" in sh and "hdiutil create" in sh and "UDZO" in sh
    swift = _text(ARREL / "instalacio" / "visual" / "mac" / "InstalarArranjaments.swift")
    assert 'forResource: "projecte", withExtension: "tar.gz"' in swift and "/usr/bin/tar" in swift
    assert "Application Support/Arranjaments/staging" in swift
