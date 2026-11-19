"""Punt d'entrada únic: `partitures <ordre> ...` (dins del repositori, `uv run partitures <ordre> ...`)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import instruments as inst
from . import musica, rutes
from .errors import ErrorUsuari


def _actual(ruta) -> None:
    """Última línia de tota ordre que escriu un fitxer: el fitxer amb què cal continuar."""
    print(rutes.linia_actual(ruta))


def cmd_info(a):
    d = musica.info(musica.carregar(a.fitxer))
    print(json.dumps(d, ensure_ascii=False, indent=2) if a.json else musica.text_info(d))


def cmd_transport(a):
    s = musica.carregar(a.fitxer)
    r = musica.transportar(s, a.semitons, a.interval, a.octava or 0, a.part)
    ruta = musica.desar(r, rutes.eixida_peca(a.fitxer, a.eixida, a.nova_versio))
    _actual(ruta)


def cmd_instruments(a):
    if not a.assigna:
        print("Instruments que conec (nom per a escriure a l'ordre, nom complet, transposició):")
        for i in inst.CATALEG:
            if i.percussio:
                t = "percussió sense altura"
            elif i.semitons() == 0:
                t = "sona igual que s'escriu"
            else:
                n = abs(i.semitons())
                quant = {12: "una octava", 24: "dues octaves"}.get(n, f"{n} semitons")
                t = f"sona {quant} {'més greu' if i.semitons() < 0 else 'més agut'} del que s'escriu"
            print(f"  {i.clau:20} {i.nom} ({t})")
        for g, claus in inst.GRUPS.items():
            print(f"Grup «{'làmines' if g == 'lamines' else g}»: {', '.join(claus)} (si només dius el grup, tria el primer).")
        print("Les tessitures són orientatives.")
        return
    if not a.fitxer:
        raise ErrorUsuari("Cal dir el fitxer: partitures instruments FITXER --assigna \"1=trompeta-sib,...\".")
    s = musica.carregar(a.fitxer)
    r, avisos = musica.assignar(s, a.assigna)
    ruta = musica.desar(r, rutes.eixida_peca(a.fitxer, a.eixida, a.nova_versio))
    print("\n".join(avisos))
    print("Recorda: ara convé mirar la tessitura amb l'ordre «tessitura».")
    _actual(ruta)


def cmd_tessitura(a):
    d = musica.tessitura(musica.carregar(a.fitxer), a.instruments, a.nivell)
    print(json.dumps(d, ensure_ascii=False, indent=2) if a.json else musica.text_tessitura(d))


def cmd_arranja(a):
    from . import arranjador as arr
    rols = arr.parse_rols(a.rols)
    for x in arr.parse_rols.avisos:
        print(x)
    s = musica.carregar(a.fitxer)
    r, informe = arr.arranjar(s, rols, estil=a.estil, curs=a.nivell, compassos_sel=arr.parse_compassos(a.compassos),
                              melodia_part=a.melodia_part, a_tonalitat=a.to, simplifica=a.simplifica, bordo=a.bordo,
                              rotacio=not a.sense_rotacio, tutti_final=a.tutti_final,
                              harmonia=a.harmonia)
    ruta = musica.desar(r, rutes.eixida_peca(a.fitxer, a.eixida, a.nova_versio))
    print("\n".join(informe))
    _actual(ruta)


def cmd_harmonia(a):
    from . import harmonia
    if a.accio == "fitxa":
        print(harmonia.text_fitxa(a.tema) if a.tema else harmonia.llista_temes())
    else:
        print(harmonia.comprova(musica.carregar(a.fitxer), a.veus, a.tonalitat, a.perfil))


def cmd_nivell(a):
    from . import nivells
    if a.accio == "mostra":
        print(nivells.text_mostra(a.instrument, a.curs))
    elif a.accio == "desa":
        if not a.instrument or not a.curs:
            raise ErrorUsuari("Cal dir l'instrument i el curs: partitures nivell desa --instrument flauta --curs \"4t elemental\" --tessitura \"Do3-Sol4\".")
        camps = {c: getattr(a, c) for c in nivells.CAMPS}
        print("\n".join(nivells.desa(a.instrument, a.curs, camps, a.substitueix)))
    elif a.accio == "esborra":
        if not a.instrument or not a.curs:
            raise ErrorUsuari("Cal dir l'instrument i el curs: partitures nivell esborra --instrument flauta --curs \"4t elemental\" "
                              "(i, si només vols treure una dada, --camp tessitura).")
        print(nivells.esborra(a.instrument, a.curs, a.camp))
    elif a.accio == "exporta":
        r = nivells.exporta(a.eixida)
        print(f"Fitxer creat: {rutes.relativa(r)}")
        print("És un fitxer amb els perfils de nivell (no una partitura). Es pot compartir: si el deixes a la carpeta "
              "«nivells» de la biblioteca, tot el professorat el podrà usar.")


def cmd_preferencia(a):
    from . import nivells
    if a.accio == "desa":
        print(nivells.desa_preferencia(" ".join(a.text)))
    elif a.accio == "esborra":
        print(nivells.esborra_preferencia(" ".join(a.text)))
    else:
        print(nivells.text_preferencies())


def cmd_reduir(a):
    s = musica.carregar(a.fitxer)
    r = musica.reduir(s, a.mantin)
    ruta = musica.desar(r, rutes.eixida_peca(a.fitxer, a.eixida, a.nova_versio))
    _actual(ruta)


def cmd_importar(a):
    from . import externs
    resultats = externs.importar_pdf(a.fitxer)
    if len(resultats) > 1:
        print(f"Audiveris ha creat {len(resultats)} fitxers (potser un per cada moviment o obra):")
    for r in resultats:
        print(f"Fitxer creat: {rutes.relativa(r)}")
    print("IMPORTANT: el reconeixement automàtic comet errors. Obri el fitxer amb MuseScore i revisa'l "
          "nota per nota abans de continuar.")
    _actual(resultats[0])


def cmd_exportar(a):
    from . import externs
    r = externs.exportar(a.fitxer, amb_parts=not a.sense_parts)
    if r["avis"]:
        print(r["avis"])
    print(f"Guió: {rutes.relativa(r['guio'])}")
    for p in r["parts"]:
        print(f"Particel·la: {rutes.relativa(p)}")
    if r["mscz"]:
        print(f"Fitxer de MuseScore: {rutes.relativa(r['mscz'])}")
    _actual(a.fitxer)   # per a continuar treballant, la partitura editable, no els PDF


def cmd_obrir(a):
    from . import externs
    r = externs.obrir(a.fitxer)
    print(f"He obert «{r.name}» amb MuseScore.")


def cmd_corpus(a):
    text = " ".join(a.text).strip()
    if not text:
        raise ErrorUsuari("Digues què busque, per exemple: partitures corpus bach")
    trobats = musica.cercar_corpus(text)
    if not trobats:
        print(f"Cap resultat al corpus de music21 per a «{text}». (Està format sobretot per música antiga i clàssica "
              "de domini públic: coral de Bach, quartets de Beethoven, Palestrina, Monteverdi...)")
        return
    for k, t in enumerate(trobats[: a.maxim], 1):
        comp = f", {t['compositor']}" if t["compositor"] else ""
        print(f"{k}. {musica._curt(t['titol'], 70)}{comp}   [{t['ruta']}]")
    if len(trobats) > a.maxim:
        print(f"... i {len(trobats) - a.maxim} més. Afina la cerca.")
    if a.copia:
        n = int(a.copia)
        if not 1 <= n <= min(len(trobats), a.maxim):
            raise ErrorUsuari("El número de --copia no coincideix amb cap resultat de la llista.")
        from music21 import corpus
        s = corpus.parse(trobats[n - 1]["ruta"])
        s = s.scores[0] if hasattr(s, "scores") else s
        desti = rutes.eixida_per_defecte(trobats[n - 1]["ruta"], "", sol_licitada=a.eixida, nom_carpeta="entrada")
        _actual(musica.desar(s, desti))


def cmd_suggereix(a):
    from . import suggeriments as sug
    if a.copia:
        _actual(sug.copia(int(a.copia)))
        return
    text = " ".join(a.text).strip()
    if not text:
        raise ErrorUsuari("Digues què busques, per exemple: partitures suggereix \"trio de canyes clàssic\" --nivell \"4t elemental\"")
    candidates, linies = sug.suggereix(text, a.nivell, a.instruments, a.maxim)
    sug.desa_ultims(candidates)
    print("\n".join(linies))


def cmd_descarrega(a):
    from . import baixades
    _actual(baixades.descarrega(a.url))


EXT_PARTITURA = (".musicxml", ".xml", ".mxl", ".mscz", ".mscx")


def cmd_peces(a):
    """Llista numerada, sempre igual: les partitures d'entrada/ o les carpetes de peça d'eixida/."""
    if a.eixida:
        base = rutes.carpeta("eixida")
        peces = sorted((d for d in base.iterdir() if d.is_dir() and not d.name.startswith(".")),
                       key=lambda d: d.name.lower()) if base.is_dir() else []
        if not peces:
            print("Encara no hi ha cap peça a eixida/.")
            return
        for k, d in enumerate(peces, 1):
            guio = any(d.glob("*Guió*.pdf"))
            parts = d / "Particel·les"
            n = len(list(parts.glob("*.pdf"))) if parts.is_dir() else 0
            estat = f"amb guió i {n} particel·les en PDF" if guio and n else ("amb guió en PDF" if guio else "sense PDF encara")
            print(f"{k}. {d.name}   [{estat}]")
        return
    base = rutes.carpeta("entrada")
    fitxers = sorted((f for f in base.iterdir() if f.is_file() and f.suffix.lower() in EXT_PARTITURA + (".pdf",)),
                     key=lambda f: f.name.lower()) if base.is_dir() else []
    if not fitxers:
        print("Ara mateix no hi ha cap partitura a entrada/.")
        return
    for k, f in enumerate(fitxers, 1):
        nota = "   [PDF: cal passar-lo a partitura editable]" if f.suffix.lower() == ".pdf" else ""
        print(f"{k}. {f.name}{nota}")


def cmd_carpeta(a):
    """Obri una carpeta de la carpeta de treball (normalment eixida/<peça>/) amb el navegador de fitxers."""
    import subprocess
    text = " ".join(a.ruta).strip()
    if not text:
        raise ErrorUsuari("Digues quina carpeta, per exemple: partitures carpeta berlinAlexandersRagtime")
    arrel = rutes.arrel()
    candidats = [Path(text).expanduser(), arrel / text, arrel / "eixida" / text]
    trobada = None
    for c in candidats:
        c = c if c.is_absolute() else arrel / c
        if c.exists():
            trobada = c.resolve()
            break
    if trobada is None:
        raise ErrorUsuari(f"No trobe cap carpeta «{text}». Mira les peces amb: partitures peces --eixida")
    if trobada.is_file():
        trobada = trobada.parent
    try:
        trobada.relative_to(arrel)
    except ValueError:
        raise ErrorUsuari("Només obric carpetes de la carpeta de treball (entrada/ i eixida/).") from None
    if sys.platform == "darwin":
        ordre = ["open", str(trobada)]
    elif sys.platform.startswith("win"):
        ordre = ["explorer", str(trobada)]
    else:
        ordre = ["xdg-open", str(trobada)]
    try:
        subprocess.Popen(ordre, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    except OSError:
        raise ErrorUsuari(f"No he pogut obrir la carpeta. Està ací: {rutes.relativa(trobada)}") from None
    print(f"He obert la carpeta «{rutes.relativa(trobada)}».")


def cmd_comprovar(a):
    from . import eines
    falten = 0
    avisos = []
    for nom, ok, msg in eines.comprovar():
        if ok:
            print(f"  [fet]  {nom}")
        elif eines.es_opcional(nom):
            print(f"  [avís]  {nom}: {msg}")
            avisos.append(nom)
        else:
            print(f"  [falta]  {nom}: {msg}")
            falten += 1
    if falten:
        print(f"\nFalten {falten} cosa(es). Es poden instal·lar amb «partitures instalar musescore» "
              "o tornant a obrir «Instal·lar Arranjaments».")
        raise ErrorUsuari("L'ordinador encara no està preparat del tot.")
    if any("MuseScore" in n for n in avisos):
        print("\nTot a punt, però encara no podràs fer PDF ni obrir partitures: falta MuseScore "
              "(«partitures instalar musescore»; a Windows demana permís d'administrador).")
    elif avisos:
        print("\nTot a punt. (Audiveris només cal si vols convertir PDF.)")
    else:
        print("\nTot a punt.")


def cmd_instalar(a):
    from . import eines
    if not a.prova and not a.cosa:
        raise ErrorUsuari("Digues què cal instal·lar, per exemple: partitures instalar audiveris "
                          "(o partitures instalar --prova per a només comprovar).")
    codi = eines.instalar(a.cosa, prova=a.prova)
    if codi != 0:
        raise ErrorUsuari("La instal·lació no ha acabat bé. Llig els avisos [falta] de dalt.")


def cmd_actualitzar(a):
    from . import actualitzar as act
    inst = act.instalacio_actual()
    if inst is None:
        raise ErrorUsuari("Això s'executa des del repositori, no des d'una instal·lació: no hi ha res a actualitzar. "
                          "Dins del repositori, usa git.")
    if a.torna_enrere:
        r = act.torna_enrere(inst)
    else:
        r = act.actualitza(inst, forca=True)
    print(r.missatge)
    if not r.be:
        raise ErrorUsuari("Si continua passant, torna a obrir «Instal·lar Arranjaments».")


def cmd_versio(a):
    from . import actualitzar as act
    print(act.text_versio(act.instalacio_actual()))


def cmd_biblioteca(a):
    from . import biblioteca as bib
    if a.accio == "on-es":
        if a.ruta:
            print(f"Ruta desada: {bib.guarda_ruta(a.ruta)}")
        print(bib.text_on_es())
    elif a.accio == "actualitza":
        if not bib.hi_ha_biblioteca():
            print(bib.SENSE_BIBLIOTECA)
            return
        print(bib.text_actualitza(bib.actualitza(maxim_noves=a.noves, segons=a.segons)))
    elif a.accio == "cerca":
        bib.ordre_cerca(" ".join(a.text), a.nivell, a.estil, a.instrument, a.maxim)
    elif a.accio == "copia":
        _actual(bib.copia(a.numero))


def nivells_camps():
    from . import nivells
    return list(nivells.CAMPS)


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"Ep! No he entés l'ordre ({message}). Prova amb --help per a veure com s'escriu.", file=sys.stderr)
        raise SystemExit(2)


def crear_parser() -> argparse.ArgumentParser:
    p = _Parser(prog="partitures", description="Eines per a fer arranjaments de cambra.")
    sub = p.add_subparsers(dest="ordre", required=True, parser_class=_Parser)

    s = sub.add_parser("info", help="Mostra què hi ha dins d'una partitura")
    s.add_argument("fitxer"); s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_info)

    s = sub.add_parser("transport", help="Transporta (tota la partitura o algunes parts)")
    s.add_argument("fitxer")
    s.add_argument("--semitons", type=int, help="Semitons (positiu cap amunt, negatiu cap avall)")
    s.add_argument("--interval", help="Interval amb nom: M2, m-3, P-5...")
    s.add_argument("--octava", type=int, help="Octaves (1 = una amunt, -1 = una avall)")
    s.add_argument("--part", help="Només estes parts (números o noms, separats per comes)")
    s.add_argument("--eixida", help="Ruta del resultat, dins d'eixida/ (per defecte, un nom automàtic)")
    s.add_argument("--nova-versio", action="store_true", dest="nova_versio",
                   help="Conserva la versió anterior i crea una carpeta nova (peça-2)")
    s.set_defaults(f=cmd_transport)

    s = sub.add_parser("instruments", help="Llista instruments o assigna parts a instruments")
    s.add_argument("fitxer", nargs="?")
    s.add_argument("--assigna", help='Per exemple "1=trompeta-sib,2=trompeta-sib,3=trompa-fa,4=trombo"')
    s.add_argument("--nova-versio", action="store_true", dest="nova_versio",
                   help="Conserva la versió anterior i crea una carpeta nova (peça-2)")
    s.add_argument("--eixida"); s.set_defaults(f=cmd_instruments)

    s = sub.add_parser("tessitura", help="Comprova l'abast de cada instrument (orientatiu)")
    s.add_argument("fitxer")
    s.add_argument("--instruments", help='Si el fitxer no diu quin instrument és cada part: "1=trompeta-sib,..."')
    s.add_argument("--nivell", help='Curs per a comparar amb el perfil desat, per exemple "4t elemental"')
    s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_tessitura)

    s = sub.add_parser("arranja", help="Crea parts noves (melodia, contracant, acompanyament, baix, percussió): esborrany")
    s.add_argument("fitxer")
    s.add_argument("--rols", required=True,
                   help='Rol=instrument: "melodia=trompeta-sib,contracant=flauta,acompanyament=xilofon,percussio=bateria" '
                        "(rols: melodia, contracant, acompanyament, baix, percussio)")
    s.add_argument("--estil", choices=("ragtime", "swing", "pop", "rock", "marxa", "vals", "classic"))
    s.add_argument("--nivell", help='Curs, per exemple "4t elemental" (usa el perfil desat si n\'hi ha)')
    s.add_argument("--compassos", help="Només estos compassos, per exemple 1-16")
    s.add_argument("--melodia-part", type=int, dest="melodia_part", help="Número de la part que porta la melodia")
    s.add_argument("--to", help='Transporta abans a esta tonalitat, per exemple "Sol major"')
    s.add_argument("--simplifica", action="store_true", help="Simplifica el ritme de la melodia a les figures del nivell")
    s.add_argument("--bordo", action="store_true", help="Acompanyament amb bordó (tònica i quinta), estil Orff")
    s.add_argument("--harmonia", choices=("auto", "simple", "modal"), default="auto",
                   help="Si la melodia va sola: auto (segons el nivell), simple (un acord per compàs: I, IV, V) o modal")
    s.add_argument("--sense-rotacio", action="store_true", dest="sense_rotacio",
                   help="La melodia, el contracant i el baix es queden sempre en el mateix instrument (per defecte van canviant)")
    s.add_argument("--tutti-final", action="store_true", dest="tutti_final",
                   help="L'última frase, la melodia també en el contracant (tot el conjunt)")
    s.add_argument("--nova-versio", action="store_true", dest="nova_versio",
                   help="Conserva la versió anterior i crea una carpeta nova (peça-2)")
    s.add_argument("--eixida"); s.set_defaults(f=cmd_arranja)

    s = sub.add_parser("harmonia", help="Fitxes d'harmonia i comprovació de corals (quintes paral·leles, sensible...)")
    h = s.add_subparsers(dest="accio", required=True)
    x = h.add_parser("fitxa", help="Mostra la fitxa d'un tema (sense tema, la llista)")
    x.add_argument("tema", nargs="?")
    x = h.add_parser("comprova", help="Comprova un coral a 4 veus (o menys), compàs a compàs")
    x.add_argument("fitxer"); x.add_argument("--veus", default="SATB", help="Veus, de dalt a baix (per defecte SATB)")
    x.add_argument("--tonalitat", help="Si l'armadura no ho diu (per exemple «la menor»)")
    x.add_argument("--perfil", choices=("escolar", "arranjament"), default="escolar",
                   help="escolar (estricte, per defecte) o arranjament (més permissiu)")
    s.set_defaults(f=cmd_harmonia)

    s = sub.add_parser("nivell", help="Perfils de nivell (curs i instrument) que l'ajudant va aprenent")
    n = s.add_subparsers(dest="accio", required=True, parser_class=_Parser)
    x = n.add_parser("mostra", help="Mostra el que sap")
    x.add_argument("--instrument"); x.add_argument("--curs")
    x = n.add_parser("desa", help="Desa (suma) dades d'un instrument i curs")
    x.add_argument("--instrument"); x.add_argument("--curs")
    for c, h in (("tessitura", "Do3-Sol4"), ("tonalitats", "Do major, Sol major, fins a 2 alteracions"),
                 ("figures", "negra, corxera, blanca amb puntet"), ("compassos", "2/4, 3/4, 4/4"),
                 ("articulacions", "picat, lligat"), ("notes", "text lliure")):
        x.add_argument(f"--{c}", help=f"Per exemple: {h}")
    x.add_argument("--substitueix", action="store_true", help="Canvia les llistes en lloc de sumar-hi")
    x = n.add_parser("esborra", help="Esborra un perfil (o una dada d'un perfil) que s'ha desat malament")
    x.add_argument("--instrument"); x.add_argument("--curs")
    x.add_argument("--camp", choices=nivells_camps(), help="Només esta dada (si no, tot el perfil)")
    x = n.add_parser("exporta", help="Crea un fitxer a eixida/ per a compartir els perfils")
    x.add_argument("--eixida")
    s.set_defaults(f=cmd_nivell)

    s = sub.add_parser("preferencia", help="Preferències del professor o professora que l'ajudant recorda")
    pf = s.add_subparsers(dest="accio", required=True, parser_class=_Parser)
    x = pf.add_parser("desa", help="Desa una preferència (frase entre cometes)")
    x.add_argument("text", nargs="+")
    x = pf.add_parser("esborra", help="Esborra una preferència (unes paraules d'ella)")
    x.add_argument("text", nargs="+")
    pf.add_parser("mostra", help="Mostra les preferències desades")
    s.set_defaults(f=cmd_preferencia)

    s = sub.add_parser("reduir", help="Redueix: quedar-se només amb algunes parts")
    s.add_argument("fitxer")
    s.add_argument("--mantin", help='Parts que es queden: "1,3"')
    s.add_argument("--nova-versio", action="store_true", dest="nova_versio",
                   help="Conserva la versió anterior i crea una carpeta nova (peça-2)")
    s.add_argument("--eixida"); s.set_defaults(f=cmd_reduir)

    s = sub.add_parser("importar", help="PDF a MusicXML amb Audiveris (després, revisar amb MuseScore)")
    s.add_argument("fitxer"); s.set_defaults(f=cmd_importar)

    s = sub.add_parser("exportar", help="Fitxer de MuseScore, guió i particel·les en PDF, dins la carpeta de la peça")
    s.add_argument("fitxer"); s.add_argument("--sense-parts", action="store_true", dest="sense_parts")
    s.set_defaults(f=cmd_exportar)

    s = sub.add_parser("obrir", help="Obri una partitura amb MuseScore")
    s.add_argument("fitxer"); s.set_defaults(f=cmd_obrir)

    s = sub.add_parser("comprovar", help="Comprova que tot el programari necessari està instal·lat")
    s.set_defaults(f=cmd_comprovar)

    s = sub.add_parser("instalar", help="Instal·la una cosa que falta (musescore, audiveris...) amb l'instal·lador oficial")
    from .eines import COSES_INSTALABLES
    s.add_argument("cosa", nargs="?", choices=COSES_INSTALABLES)
    s.add_argument("--prova", action="store_true", help="Només comprova què hi ha instal·lat, no canvia res")
    s.set_defaults(f=cmd_instalar)

    s = sub.add_parser("actualitzar", help="Busca i instal·la la versió nova d'Arranjaments (o torna a l'anterior)")
    s.add_argument("--torna-enrere", action="store_true", dest="torna_enrere", help="Torna a la versió anterior")
    s.set_defaults(f=cmd_actualitzar)

    s = sub.add_parser("versio", help="Mostra la versió d'Arranjaments que tens")
    s.set_defaults(f=cmd_versio)

    s = sub.add_parser("biblioteca", help="Biblioteca compartida del professorat (Teams/OneDrive): només lectura")
    b = s.add_subparsers(dest="accio", required=True, parser_class=_Parser)
    x = b.add_parser("on-es", help="Diu on és la biblioteca (o com fer que hi aparega)")
    x.add_argument("--ruta", help="Desa la carpeta de la biblioteca si té un altre nom o és en un altre lloc")
    x = b.add_parser("actualitza", help="Posa al dia l'índex (analitza les partitures noves, per tandes)")
    x.add_argument("--noves", type=int, default=200, help="Màxim de partitures noves per vegada")
    x.add_argument("--segons", type=int, default=60, help="Temps màxim per vegada")
    x = b.add_parser("cerca", help="Cerca per paraules (títol, compositor, carpeta, instrument...)")
    x.add_argument("text", nargs="*")
    x.add_argument("--nivell"); x.add_argument("--estil"); x.add_argument("--instrument")
    x.add_argument("--maxim", type=int, default=10)
    x = b.add_parser("copia", help="Copia un resultat de l'última cerca a entrada/")
    x.add_argument("numero", type=int)
    s.set_defaults(f=cmd_biblioteca)

    s = sub.add_parser("peces", help="Llista numerada de les partitures d'entrada/ (o, amb --eixida, les peces ja fetes)")
    s.add_argument("--eixida", action="store_true", help="Llista les carpetes de peça d'eixida/")
    s.set_defaults(f=cmd_peces)

    s = sub.add_parser("carpeta", help="Obri la carpeta d'una peça (eixida/peça/) al Finder o a l'Explorador")
    s.add_argument("ruta", nargs="*", help="Nom de la peça o ruta dins de la carpeta de treball")
    s.set_defaults(f=cmd_carpeta)

    s = sub.add_parser("corpus", help="Busca en el corpus de música lliure que ve amb music21")
    s.add_argument("text", nargs="*", help="Què busques (compositor, títol o nom de fitxer)")
    s.add_argument("--maxim", type=int, default=15)
    s.add_argument("--copia", help="Número del resultat que vols copiar a entrada/")
    s.add_argument("--eixida", help="Ruta de la còpia, dins d'entrada/")
    s.set_defaults(f=cmd_corpus)

    s = sub.add_parser("suggereix", help="Suggereix peces reals (biblioteca, corpus, entrada) per a una petició lliure")
    s.add_argument("text", nargs="*", help="La petició tal com la diu la persona (època, estil, compositor...)")
    s.add_argument("--nivell", help="Curs, per exemple «4t elemental»")
    s.add_argument("--instruments", help="Els instruments, per exemple «oboè, clarinet, fagot»")
    s.add_argument("--maxim", type=int, default=6)
    s.add_argument("--copia", help="Número del suggeriment que vols deixar a entrada/")
    s.set_defaults(f=cmd_suggereix)

    s = sub.add_parser("descarrega", help="Baixa un MusicXML o fitxer de MuseScore lliure (CPDL, Mutopia, OpenScore) a entrada/")
    s.add_argument("url", help="Adreça https del fitxer")
    s.set_defaults(f=cmd_descarrega)
    return p


def _utf8() -> None:
    """A Windows la consola pot ser cp1252: forcem UTF-8 (amb substitució) perquè mai falle en escriure."""
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def main(argv: list[str] | None = None) -> int:
    _utf8()
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
    except Exception as e:  # cap traça de Python davant d'una persona no tècnica
        if os.environ.get("PARTITURES_DEBUG") == "1":
            raise
        print(f"Ep! Ha passat una cosa inesperada ({type(e).__name__}). Torna-ho a provar; si continua, "
              "explica-ho a qui t'ajuda amb el programa.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
