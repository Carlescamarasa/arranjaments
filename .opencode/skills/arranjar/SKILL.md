---
name: arranjar
description: Fa arranjaments amb les ordres de l'eina. Crea parts noves (melodia, contracant, acompanyament, baix, percussió) per a qualsevol plantilla amb `partitures arranja`, i també transporta, assigna parts a instruments, comprova tessitures i redueix parts. Usa-la per a qualsevol canvi musical.
---

# Arranjar amb les ordres de l'eina

Tot es fa amb ordres. Tu no edites cap fitxer ni escrius codi (tampoc codi de music21 ni de Python): les ordres ja fan la música. Les ordres NO modifiquen l'original: escriuen un fitxer nou a `eixida/` (si el nom ja existeix, afigen -2, -3...) i acaben amb la línia `Fitxer actual: ...`. Usa sempre l'última.

## Dos camins: quin triar

- **La plantilla demana parts que la partitura NO té** (per exemple, una melodia sola o un full de melodia amb acords, i volen trompeta, flauta, xilòfon i bateria): usa `partitures arranja`. Crea les parts noves. MAI digues que no es pot fer ni que l'eina només reparteix parts: ara sí que en crea.
- **La partitura ja té tantes parts com instruments** (un coral a quatre veus per a quartet): usa `partitures instruments --assigna` (cada part, a un instrument).

## Crear un arranjament nou: `partitures arranja`

Cada instrument fa un **rol**:

- `melodia`: la melodia de la peça, a l'octava còmoda de l'instrument.
- `contracant`: una segona veu senzilla, de notes llargues de l'acord, a distància de tercera o sexta de la melodia; on la melodia s'atura, fa un petit pas.
- `acompanyament`: els acords amb el patró de l'estil (làmines a dues baquetes, piano en dos pentagrames, guitarra...).
- `baix`: les fonamentals (i quintes) dels acords.
- `percussio`: bateria (bombo, caixa i charles), caixa o percussió menuda, amb patrons senzills.

Ordre:

`partitures arranja "entrada/peça.musicxml" --rols "melodia=trompeta-sib,contracant=flauta,acompanyament=xilofon,percussio=bateria" --estil ragtime --nivell "4t elemental"`

Opcions:
- `--estil`: ragtime, swing, pop, rock, marxa, vals o classic (si no el dius, el tria pel compàs).
- `--nivell "4t elemental"`: usa el perfil del curs (tessitures, figures) si està desat; si no, ho diu i usa la zona còmoda de cada instrument.
- `--compassos 1-16`: només un tros (per a peces llargues).
- `--to "Sol major"`: transporta abans a una tonalitat més fàcil.
- `--simplifica`: simplifica el ritme de la melodia a les figures del nivell (només si el perfil té les figures).
- `--bordo`: acompanyament amb bordó Orff (tònica i quinta).
- `--melodia-part 2`: si la melodia no és a la part més aguda.

L'ordre mostra l'informe: la tonalitat, els **acords** (els que porta la partitura i, amb `*`, els que ha posat l'eina), la tessitura de cada part, el que passa del nivell i les comprovacions (quintes i octaves paral·leles, compassos buits). **Ensenya-li els acords i els avisos tal com surten.** Digues SEMPRE que és un esborrany i que cal revisar-lo amb MuseScore (`partitures obrir "<fitxer>"`).

### Què preguntar (una cosa cada vegada) i res més

1. Quins instruments i quin rol fa cadascun. Proposa tu un repartiment raonable i demana que el confirme. Per defecte:
   - `melodia`: l'instrument de vent o de corda més melòdic (trompeta, flauta, clarinet, violí...).
   - `contracant`: un altre instrument melòdic (si n'hi ha dos de vent, el segon).
   - `acompanyament`: làmines (xilòfon, metal·lòfon, carilló), piano o guitarra.
   - `baix`: un instrument greu (trombó, tuba, fagot, violoncel, contrabaix), si n'hi ha.
   - `percussio`: bateria, caixa o percussió.
2. L'estil (ragtime, swing, pop, rock, marxa, vals o classic).
3. El nivell (curs), si no l'ha dit.
4. Si la peça és llarga (més de 32 compassos), quins compassos.

Exemple: «Vull este ragtime per a trompeta, flauta, xilòfon i bateria, per a 4t d'elemental». Proposa: «Faria: trompeta la melodia, flauta un contracant, xilòfon l'acompanyament i bateria la percussió, en estil ragtime. Et sembla bé?». Amb el sí: `partitures arranja "entrada/ragtime.musicxml" --rols "melodia=trompeta-sib,contracant=flauta,acompanyament=xilofon,percussio=bateria" --estil ragtime --nivell "4t elemental"`.

Si la persona diu «làmines», pregunta quines té a classe (xilòfon, metal·lòfon, carilló...). Si no ho sap, `lamines` tria el xilòfon alt Orff i ho diu.

Després: comprova la tessitura si cal (ordre 4), i quan estiga conforme, skill `exportar`.

## Coses que cal saber (explica-ho si cal)

- So real (de concert) i so escrit: la trompeta en Si bemoll i el clarinet en Si bemoll sonen una segona major MÉS GREU del que s'escriu; la trompa en Fa, una quinta justa més greu; el saxo alt, una sexta major; el xilòfon sona una octava més agut i el carilló, dues. Les ordres ho fan tot soles: cada part s'escriu a l'altura que ha de llegir l'intèrpret, amb la clau habitual.
- Un instrument de dos pentagrames (el piano) compta com UNA sola part: els números de part són els que mostra l'ordre `info`.
- Les notes es diuen en solfeig amb el Do central com a Do3.

## Altres ordres

1. Veure què té el fitxer: `partitures info "entrada/nom.musicxml"`
2. Llista d'instruments (i els noms que accepta): `partitures instruments`
3. Assignar parts existents a instruments (número de part = instrument):
   `partitures instruments "entrada/nom.musicxml" --assigna "1=trompeta-sib,2=trompeta-sib,3=trompa-fa,4=trombo"`
4. Comprovar tessitures: `partitures tessitura "eixida/nom-instruments.musicxml"` (amb `--nivell "4t elemental"` per a comparar amb el curs). Si el fitxer no diu quins instruments són: afegir `--instruments "1=trompeta-sib,..."`.
5. Transportar tot el conjunt: `partitures transport "<fitxer>" --semitons -2` o `--interval m-3`. Només una part una octava més amunt: `--octava 1 --part 3`.
6. Quedar-se només amb algunes parts: `partitures reduir "<fitxer>" --mantin "1,4"`.

Si hi ha notes FORA d'abast, mostra els compassos i les notes tal com diu l'ordre i proposa UNA solució: canviar una part d'octava (`transport --octava ... --part ...`), canviar l'instrument o el rol, o transportar tot el conjunt (`arranja ... --to`). Espera la decisió de la persona. Les notes «en zona incòmoda» són un avís, no un error. Torna a comprovar després de cada canvi, sobre l'últim «Fitxer actual».

## No faces

- No escrigues codi ni partitures a mà, ni canvies notes concretes: si la persona vol retocar notes, que òbriga el fitxer amb MuseScore (`partitures obrir "<fitxer>"`).
- No inventes noms d'instrument: usa els de `partitures instruments`. Si falta un instrument, digues-ho i proposa el més semblant de la llista.
- La reducció a piano d'una partitura sencera no la fa cap ordre. Sí que pots fer un acompanyament de piano nou amb `arranja` (rol `acompanyament=piano`).
