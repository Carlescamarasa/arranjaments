---
name: arranjar
description: Fa arranjaments amb les ordres de l'eina. Crea parts noves (melodia, contracant, acompanyament, baix, percussió) per a qualsevol plantilla amb `partitures arranja`, i també transporta, assigna parts a instruments, comprova tessitures i redueix parts. Usa-la per a qualsevol canvi musical.
---

# Arranjar amb les ordres de l'eina

Tot es fa amb ordres. Tu no edites cap fitxer ni escrius codi (tampoc codi de music21 ni de Python): les ordres ja fan la música. Les ordres NO modifiquen l'original: escriuen a la carpeta de la peça, `eixida/peça/peça.musicxml`, i el resultat nou reemplaça l'anterior; per conservar l'anterior (per exemple, un segon arranjament de la mateixa peça per a un altre grup) afig `--nova-versio` i va a `eixida/peça-2/`. Acaben amb la línia `Fitxer actual: ...`. Usa sempre l'última.

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

L'ordre mostra l'informe: la tonalitat, els **acords** (els que porta la partitura i, amb `*`, els que ha posat l'eina), la tessitura de cada part, el que passa del nivell i les comprovacions (quintes i octaves paral·leles, compassos buits). Mostra els avisos importants tal com apareixen (Pas 4). Digues SEMPRE que és un esborrany i que cal revisar-lo amb MuseScore (`partitures obrir "<fitxer>"`).

### La conversa: un guió fix, curt i amb final

Esta skill continua el camí «arranjament nou» d'AGENTS.md. Segueix-lo pas a pas: la persona no està acostumada a la IA i tu portes la conversa.

**Pas 0. Mira què ja saps.** Llig `partitures nivell mostra` i `partitures info "<fitxer>"`. El que la persona ja ha dit (instruments, estil, curs) no ho tornes a preguntar.

**Pas 1. Anuncia les preguntes.** Si encara no has anunciat el nombre (el camí d'AGENTS.md ja ho fa amb la pregunta de la peça), en un sol missatge digues quantes en faràs i fes ja la primera: «Per a fer l'arranjament necessite saber 3 coses. Te les pregunte d'una en una.» Només les que falten, d'esta llista i en este ordre:
1. El repartiment de rols (el proposes tu).
2. L'estil.
3. El curs.
4. Quins compassos (només si la peça passa de 32 compassos).

Si la peça ja s'ha triat com a pregunta 1 d'AGENTS.md, continua la numeració: «Pregunta 2 de 4», «Pregunta 3 de 4», «Pregunta 4 de 4». Si la peça ja la tenies des del principi, són 3 preguntes: «Pregunta 1 de 3», «Pregunta 2 de 3», «Pregunta 3 de 3».

**Pas 2. Una pregunta cada vegada, numerada i amb poques opcions.** Format: «Pregunta 2 de 3: quin estil vols? a) ragtime (el que et propose), b) swing, c) un altre (digues quin).» Com a molt 3 opcions, i la primera és la teua proposta. Si respon «sí», «la primera», «el que vulgues» o «tu mateix», tria la primera i passa a la següent. Si no entens la resposta, UNA pregunta per aclarir-ho i continua. La pregunta del curs: «a) 1r d'elemental, b) 4t d'elemental, c) un altre (digues quin)»; si ja ho ha dit, no la faces.

Proposta de rols per defecte:
- `melodia`: l'instrument de vent o de corda més melòdic (trompeta, flauta, clarinet, violí...).
- `contracant`: un altre instrument melòdic (si n'hi ha dos de vent, el segon).
- `acompanyament`: làmines (xilòfon, metal·lòfon, carilló), piano o guitarra.
- `baix`: un instrument greu (trombó, tuba, fagot, violoncel, contrabaix), si n'hi ha.
- `percussio`: bateria, caixa o percussió.

Exemple de pregunta del repartiment: «Pregunta 2 de 4: et propose trompeta la melodia, flauta un contracant, xilòfon l'acompanyament i bateria el ritme. a) així, b) vull canviar-ho (digues com).» Si diu «làmines», posa-ho com a opció: «a) xilòfon, b) metal·lòfon, c) carilló». Si la persona no diu quins instruments té, proposa trompeta, flauta, xilòfon i bateria.

**Pas 3. Amb l'última resposta, genera-ho tot sense demanar permís.** NO preguntes «et sembla bé?» ni «vols que el genere?»: les respostes ja són el sí. Digues «Perfecte, el faig ara.» i executa, sense parar entre ordre i ordre:
1. `partitures arranja "entrada/peça.musicxml" --rols "..." --estil ... --nivell "..."`
2. Si l'informe diu notes FORA d'abast en una part, prova UNA vegada `partitures transport "<Fitxer actual>" --octava 1 --part N` (o `-1`) i digues-ho en una frase.
3. `partitures exportar "<Fitxer actual>"` (fitxer de MuseScore, guió en PDF i particel·les, tot dins la carpeta de la peça).

**Pas 4. Lliura i tanca, en un sol missatge curt.**
- «Fet. Ho tens a la carpeta eixida/peça/: el guió, les particel·les i el fitxer de MuseScore. És un esborrany: revisa'l abans de repartir-lo.»
- Els avisos importants, com a molt 3 línies (els acords que ha posat l'eina, en una línia).
- UNA sola pregunta final: «Què vols fer ara? a) obrir la carpeta, b) canviar alguna cosa, c) ja està.» La a executa `partitures carpeta "peça"`; la c tanca la conversa.
- No afegisques res més: ni comprovar tessitures, ni proposar millores, ni preguntar «vols que ho revise?».

**Pas 5. Si demana un canvi** (opció b o una frase com «posa-ho en swing»), fes-lo i torna a generar-ho tot (arranja i exportar), que reemplaça el resultat anterior, sense preguntar res més (si vol conservar l'anterior, afig `--nova-versio`); després, torna al Pas 4. Només pregunta si el canvi no s'entén. Si el canvi és l'estil, l'instrument o un tros, parteix dels mateixos rols i del mateix fitxer de `entrada/`. Si vol retocar notes concretes, que òbriga el fitxer amb MuseScore.

**Nivell sense perfil.** Si el curs no té perfil desat, NO pares la conversa: genera amb la zona còmoda de cada instrument. Al Pas 4, afig una línia: «Si vols que el pròxim arranjament s'ajuste millor a este curs, et faré una pregunta per instrument (la nota més greu i la més aguda).» Si diu que sí, anuncia-les i fes-les numerades com al Pas 2, i desa cada resposta amb `partitures nivell desa`.

## Coses que cal saber (explica-ho si cal)

- So real (de concert) i so escrit: la trompeta en Si bemoll i el clarinet en Si bemoll sonen una segona major MÉS GREU del que s'escriu; la trompa en Fa, una quinta justa més greu; el saxo alt, una sexta major; el xilòfon sona una octava més agut i el carilló, dues. Les ordres ho fan tot soles: cada part s'escriu a l'altura que ha de llegir l'intèrpret, amb la clau habitual.
- Un instrument de dos pentagrames (el piano) compta com UNA sola part: els números de part són els que mostra l'ordre `info`.
- Les notes es diuen en solfeig amb el Do central com a Do3.

## Altres ordres

1. Veure què té el fitxer: `partitures info "entrada/nom.musicxml"`
2. Llista d'instruments (i els noms que accepta): `partitures instruments`
3. Assignar parts existents a instruments (número de part = instrument):
   `partitures instruments "entrada/nom.musicxml" --assigna "1=trompeta-sib,2=trompeta-sib,3=trompa-fa,4=trombo"`
4. Comprovar tessitures: `partitures tessitura "eixida/nom/nom.musicxml"` (amb `--nivell "4t elemental"` per a comparar amb el curs). Si el fitxer no diu quins instruments són: afegir `--instruments "1=trompeta-sib,..."`.
5. Transportar tot el conjunt: `partitures transport "<fitxer>" --semitons -2` o `--interval m-3`. Només una part una octava més amunt: `--octava 1 --part 3`.
6. Quedar-se només amb algunes parts: `partitures reduir "<fitxer>" --mantin "1,4"`.

Si hi ha notes FORA d'abast, mostra els compassos i les notes tal com diu l'ordre i proposa UNA solució: canviar una part d'octava (`transport --octava ... --part ...`), canviar l'instrument o el rol, o transportar tot el conjunt (`arranja ... --to`). Espera la decisió de la persona. Les notes «en zona incòmoda» són un avís, no un error. Torna a comprovar després de cada canvi, sobre l'últim «Fitxer actual».

## No faces

- No escrigues codi ni partitures a mà, ni canvies notes concretes: si la persona vol retocar notes, que òbriga el fitxer amb MuseScore (`partitures obrir "<fitxer>"`).
- No inventes noms d'instrument: usa els de `partitures instruments` o els del perfil de nivells. Si falta un instrument, pregunta què és i com es toca a classe.
- La reducció a piano d'una partitura sencera no la fa cap ordre. Sí que pots fer un acompanyament de piano nou amb `arranja` (rol `acompanyament=piano`).
