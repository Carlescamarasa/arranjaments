"""Fa els paquets d'un sol fitxer que baixa la professora (menys el DMG de Mac, que es fa amb mac/fes-dmg.sh).

Ús:
  python3 instalacio/visual/paquets.py projecte CARPETA ZIP TAR_GZ
      El projecte (CARPETA, ja amb la VERSION posada) sense el que no cal per a instal·lar, en dos formats:
      ZIP (per a Windows) i tar.gz (per a Mac i Linux).
  python3 instalacio/visual/paquets.py windows EXE ZIP EIXIDA.exe
      «Arranjaments-Windows.exe»: l'instal·lador amb el ZIP enganxat al final i 16 bytes de tancament
      (mida del ZIP en 8 bytes petit endian + «ARRPAYL1»). L'instal·lador se'l llig a si mateix.
  python3 instalacio/visual/paquets.py linux CAPCALERA TAR_GZ EIXIDA.run
      «Arranjaments-LliureX.run»: el guió de capçalera (linux/capcalera.sh, que acaba amb la línia __ARXIU__) i
      el tar.gz enganxat a continuació. Sense makeself ni cap altre programa.
"""
import os
import struct
import sys
import tarfile
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from empaqueta import empaqueta  # noqa: E402

# El que no cal per a instal·lar (ni per a actualitzar): proves, imatges del README, CI i el .desktop de l'alternativa de Linux
EXCLOU = frozenset({"docs", "tests", ".github", ".gitignore", ".gitattributes", "Instal·lar Arranjaments (Linux).desktop",
                    "Instal·lar Arranjaments.app", "Instal·lar Arranjaments.exe", "entrada", "eixida"})


def projecte(carpeta: Path, zip_eixida: Path, tar_eixida: Path) -> None:
    n = empaqueta(carpeta, zip_eixida, arrel="", exclou=EXCLOU)
    # entrada i eixida no van al paquet, però la carpeta de treball es crea sola; no cal cap fitxer buit
    ncarpeta = 0
    with tarfile.open(tar_eixida, "w:gz", compresslevel=9, format=tarfile.PAX_FORMAT) as t:
        for actual, carpetes, noms in os.walk(carpeta):
            if Path(actual) == Path(carpeta):
                carpetes[:] = [c for c in carpetes if c not in EXCLOU]
                noms = [x for x in noms if x not in EXCLOU]
            carpetes.sort()
            for nom in sorted(noms):
                ruta = Path(actual) / nom
                if ruta.is_symlink():
                    raise SystemExit(f"Enllaç simbòlic no admés: {ruta}")
                info = t.gettarinfo(str(ruta), arcname=unicodedata.normalize("NFC", ruta.relative_to(carpeta).as_posix()))
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                info.mode = 0o755 if ruta.stat().st_mode & 0o111 else 0o644
                with open(ruta, "rb") as f:
                    t.addfile(info, f)
                ncarpeta += 1
    print(f"{zip_eixida}: {n} fitxers; {tar_eixida}: {ncarpeta} fitxers")


def windows(exe: Path, zip_ruta: Path, eixida: Path) -> None:
    dades = zip_ruta.read_bytes()
    eixida.write_bytes(exe.read_bytes() + dades + struct.pack("<Q", len(dades)) + b"ARRPAYL1")
    print(f"{eixida}: {eixida.stat().st_size} bytes")


def linux(capcalera: Path, tar_gz: Path, eixida: Path) -> None:
    cap = capcalera.read_bytes()
    if b"\r" in cap:
        raise SystemExit("La capçalera no pot portar salts de línia de Windows")
    if not cap.endswith(b"\n__ARXIU__\n"):
        raise SystemExit("La capçalera ha d'acabar amb la línia __ARXIU__")
    eixida.write_bytes(cap + tar_gz.read_bytes())
    eixida.chmod(0o755)
    print(f"{eixida}: {eixida.stat().st_size} bytes")


if __name__ == "__main__":
    ordres = {"projecte": (projecte, 3), "windows": (windows, 3), "linux": (linux, 3)}
    if len(sys.argv) < 2 or sys.argv[1] not in ordres or len(sys.argv) != 2 + ordres[sys.argv[1]][1]:
        raise SystemExit(__doc__)
    f, _ = ordres[sys.argv[1]]
    f(*[Path(a) for a in sys.argv[2:]])
