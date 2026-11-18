"""Fa el ZIP que es publica: la carpeta del projecte amb els dos instal·ladors visuals a dins.

Ús: python3 instalacio/visual/empaqueta.py CARPETA EIXIDA.zip
CARPETA és la carpeta ja muntada (el projecte, «Instal·lar Arranjaments.app» i «Instal·lar Arranjaments.exe»);
dins del ZIP es dirà «arranjaments».

Es fa amb Python i no amb el compressor del Mac perquè calen dues coses alhora:
- els noms amb accents o punt volat marcats com a UTF-8, perquè Windows els llija bé;
- els permisos d'execució de l'aplicació de Mac, perquè es puga obrir després de descomprimir.
"""
import os
import sys
import time
import unicodedata
import zipfile
from pathlib import Path


def empaqueta(carpeta: Path, eixida: Path, arrel: str = "arranjaments") -> int:
    fitxers = 0
    with zipfile.ZipFile(eixida, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for actual, carpetes, noms in os.walk(carpeta):
            carpetes.sort()
            for nom in sorted(noms + carpetes):
                ruta = Path(actual) / nom
                if ruta.is_symlink():
                    raise SystemExit(f"Enllaç simbòlic no admés: {ruta}")
                dins = unicodedata.normalize("NFC", f"{arrel}/{ruta.relative_to(carpeta).as_posix()}")
                mode = ruta.stat().st_mode
                data = time.localtime(ruta.stat().st_mtime)[:6]
                if ruta.is_dir():
                    info = zipfile.ZipInfo(dins + "/", date_time=data)
                    info.external_attr = ((0o40000 | 0o755) << 16) | 0x10
                    info.create_system = 3
                    z.writestr(info, b"")
                    continue
                info = zipfile.ZipInfo(dins, date_time=data)
                executable = bool(mode & 0o111)
                info.external_attr = (0o100000 | (0o755 if executable else 0o644)) << 16
                info.create_system = 3  # Unix: així el Mac respecta els permisos
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, ruta.read_bytes())
                fitxers += 1
    return fitxers


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    n = empaqueta(Path(sys.argv[1]), Path(sys.argv[2]))
    print(f"{sys.argv[2]}: {n} fitxers")
