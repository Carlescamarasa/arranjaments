"""Punt d'entrada únic: `uv run partitures <ordre> ...`"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import instruments as inst
from . import musica
from .errors import ErrorUsuari

EIXIDA_PER_DEFECTE = "eixida"


def _eixida_per_a(origen: str, sufix: str, out: str | None) -> Path:
    if out:
        return Path(out)
    p = Path(origen)
    return Path(EIXIDA_PER_DEFECTE) / f"{p.stem}{sufix}.musicxml"


def _ruta_final(r: Path) -> str:
    return f"Fitxer creat: {r}"


def cmd_info(a):
    d = musica.info(musica.carregar(a.fitxer))
    print(json.dumps(d, ensure_ascii=False, indent=2) if a.json else musica.text_info(d))


def cmd_transport(a):
    s = musica.carregar(a.fitxer)
    r = musica.transportar(s, a.semitons, a.interval, a.octava or 0, a.part)
    suf = f"-transportat"
    ruta = musica.desar(r, _eixida_per_a(a.fitxer, suf, a.eixida))
    print(_ruta_final(ruta))


def cmd_instruments(a):
    if not a.assigna:
        print("Instruments que conec (nom per a escriure a l'ordre, nom complet, transposició):")
        for i in inst.CATALEG:
            t = "sona igual que s'escriu" if i.semitons() == 0 else f"sona {abs(i.semitons())} semitons {'més greu' if i.semitons() < 0 else 'més agut'} del que s'escriu"
            print(f"  {i.clau:14} {i.nom} ({t})")
        return
    if not a.fitxer:
        raise ErrorUsuari("Cal dir el fitxer: partitures instruments FITXER --assigna \"1=trompeta-sib,...\".")
    s = musica.carregar(a.fitxer)
    r, avisos = musica.assignar(s, a.assigna)
    ruta = musica.desar(r, _eixida_per_a(a.fitxer, "-instruments", a.eixida))
    print("\n".join(avisos))
    print(_ruta_final(ruta))
    print("Recorda: ara convé mirar la tessitura amb l'ordre «tessitura».")


def cmd_tessitura(a):
    d = musica.tessitura(musica.carregar(a.fitxer), a.instruments)
    print(json.dumps(d, ensure_ascii=False, indent=2) if a.json else musica.text_tessitura(d))


def cmd_reduir(a):
    s = musica.carregar(a.fitxer)
    r = musica.reduir(s, a.mantin, a.a_piano)
    ruta = musica.desar(r, _eixida_per_a(a.fitxer, "-reduccio", a.eixida))
    print(_ruta_final(ruta))


def cmd_importar(a):
    from . import externs
    r = externs.importar_pdf(a.fitxer, a.eixida or EIXIDA_PER_DEFECTE)
    print(_ruta_final(r))
    print("IMPORTANT: el reconeixement automàtic comet errors. Obri el fitxer amb MuseScore i revisa'l "
          "nota per nota abans de continuar.")


def cmd_exportar(a):
    from . import externs
    r = externs.exportar(a.fitxer, a.eixida or EIXIDA_PER_DEFECTE, amb_parts=not a.sense_parts)
    print(f"Partitura completa: {r['completa']}")
    for p in r["parts"]:
        print(f"Part: {p}")


def cmd_corpus(a):
    from music21 import corpus
    trobats = corpus.search(a.text) if a.text else []
    if not a.text:
        raise ErrorUsuari("Digues què busque, per exemple: partitures corpus bach")
    rutes = []
    for t in trobats:
        rutes.append(str(t.sourcePath))
    if not rutes:
        print(f"Cap resultat al corpus de music21 per a «{a.text}». (Està format sobretot per música antiga i clàssica de domini públic.)")
        return
    for k, r in enumerate(rutes[: a.maxim], 1):
        print(f"{k}. {Path(r).name}   [{Path(r).parent.name}]")
    if len(rutes) > a.maxim:
        print(f"... i {len(rutes) - a.maxim} més. Afina la cerca.")
    if a.copia:
        n = int(a.copia)
        if not 1 <= n <= min(len(rutes), a.maxim):
            raise ErrorUsuari("El número de --copia no coincideix amb cap resultat de la llista.")
        s = corpus.parse(rutes[n - 1])
        s = s.scores[0] if hasattr(s, 'scores') else s
        ruta = musica.desar(s, Path(a.eixida or "entrada") / (Path(rutes[n - 1]).stem + ".musicxml"))
        print(_ruta_final(ruta))


def cmd_comprovar(a):
    from . import eines
    falten = 0
    opcionals = 0
    for nom, ok, msg in eines.comprovar():
        print(f"  [{'fet' if ok else 'falta'}]  {nom}" + ("" if ok else f": {msg}"))
        if not ok:
            if "opcional" in nom:
                opcionals += 1
            else:
                falten += 1
    if falten:
        print(f"\nFalten {falten} cosa(es). Executa l'instal·lador del projecte (carpeta instalacio) o mira el README.")
        raise ErrorUsuari("L'ordinador encara no està preparat del tot.")
    print("\nTot a punt." + (" (Audiveris només cal si vols convertir PDF.)" if opcionals else ""))


def crear_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="partitures", description="Eines per a fer arranjaments de cambra.")
    sub = p.add_subparsers(dest="ordre", required=True)

    s = sub.add_parser("info", help="Mostra què hi ha dins d'una partitura")
    s.add_argument("fitxer"); s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_info)

    s = sub.add_parser("transport", help="Transporta (tota la partitura o algunes parts)")
    s.add_argument("fitxer")
    s.add_argument("--semitons", type=int, help="Semitons (positiu cap amunt, negatiu cap avall)")
    s.add_argument("--interval", help="Interval amb nom: M2, m-3, P-5...")
    s.add_argument("--octava", type=int, help="Octaves (1 = una amunt, -1 = una avall)")
    s.add_argument("--part", help="Només estes parts (números o noms, separats per comes)")
    s.add_argument("--eixida", help="Fitxer de sortida (per defecte, dins d'eixida/)")
    s.set_defaults(f=cmd_transport)

    s = sub.add_parser("instruments", help="Llista instruments o assigna parts a instruments")
    s.add_argument("fitxer", nargs="?")
    s.add_argument("--assigna", help='Per exemple "1=trompeta-sib,2=trompeta-sib,3=trompa-fa,4=trombo"')
    s.add_argument("--eixida"); s.set_defaults(f=cmd_instruments)

    s = sub.add_parser("tessitura", help="Comprova l'abast de cada instrument")
    s.add_argument("fitxer")
    s.add_argument("--instruments", help='Si el fitxer no diu quin instrument és cada part: "1=trompeta-sib,..."')
    s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_tessitura)

    s = sub.add_parser("reduir", help="Redueix: quedar-se amb algunes parts o fer una reducció per a piano")
    s.add_argument("fitxer")
    s.add_argument("--mantin", help='Parts que es queden: "1,3"')
    s.add_argument("--a-piano", action="store_true", dest="a_piano")
    s.add_argument("--eixida"); s.set_defaults(f=cmd_reduir)

    s = sub.add_parser("importar", help="PDF → MusicXML amb Audiveris (després, revisar amb MuseScore)")
    s.add_argument("fitxer"); s.add_argument("--eixida"); s.set_defaults(f=cmd_importar)

    s = sub.add_parser("exportar", help="Partitura completa i parts soltes en PDF amb MuseScore")
    s.add_argument("fitxer"); s.add_argument("--sense-parts", action="store_true", dest="sense_parts")
    s.add_argument("--eixida"); s.set_defaults(f=cmd_exportar)

    s = sub.add_parser("comprovar", help="Comprova que tot el programari necessari està instal·lat")
    s.set_defaults(f=cmd_comprovar)

    s = sub.add_parser("corpus", help="Busca en el corpus de música lliure que ve amb music21")
    s.add_argument("text", nargs="?"); s.add_argument("--maxim", type=int, default=15)
    s.add_argument("--copia", help="Número del resultat que vols copiar a entrada/")
    s.add_argument("--eixida"); s.set_defaults(f=cmd_corpus)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = crear_parser()
    a = parser.parse_args(argv)
    try:
        a.f(a)
    except ErrorUsuari as e:
        print(f"Ep! {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Aturat.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
