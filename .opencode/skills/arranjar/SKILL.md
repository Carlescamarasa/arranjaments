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
- `--harmonia simple|modal`: només si la melodia va sola. `simple` fa un acord per compàs (I, IV, V); `modal` és per a cançons sense sensible (la detecta sola).
- `--sense-rotacio`: la melodia, el contracant i el baix es queden sempre en el mateix instrument. Per defecte la melodia va canviant de veu cada frase (8 compassos, 4 si la peça és curta): comença i acaba l'instrument de la melodia, el baix la porta una vegada si hi cap, i quan un altre la porta, qui feia la melodia passa al contracant. Els instruments de percussió sense altura mai la porten. L'informe diu «Qui porta la melodia: c. 1-8 trompeta; c. 9-16 flauta...» i a cada particel·la ix la paraula «melodia» on l'instrument la comença. El baix també toca patrons de l'estil, amb respostes curtes en les notes llargues de la melodia.
- `--tutti-final`: en l'última frase, el contracant també porta la melodia.
- `--melodia-part 2`: si la melodia no és a la part més aguda.

L'ordre mostra l'informe: la tonalitat, els **acords** (els que porta la partitura i, amb `*`, els que ha posat l'eina), la tessitura de cada part, el que passa del nivell i les comprovacions (quintes i octaves paral·leles, compassos buits). Mostra els avisos importants tal com apareixen (Pas 4). Digues SEMPRE que és un esborrany i que cal revisar-lo amb MuseScore (`partitures obrir "<fitxer>"`).

### La conversa: un guió fix, curt i amb final

Esta skill continua el camí «arranjament nou» d'AGENTS.md. La persona no està acostumada a la IA i tu portes la conversa. Totes les preguntes amb opcions es fan amb l'eina `question` (un selector que la persona clica), MAI amb a), b), c) escrits al text.

**Pas 0. Mira què ja saps.** Llig `partitures nivell mostra` i `partitures info "<fitxer>"`. El que la persona ja ha dit (instruments, estil, curs) no ho tornes a preguntar.

**Pas 1. UNA sola crida a `question`, amb una pregunta per pestanya.** Només les que falten, en este ordre (header curt de com a molt 30 caràcters):
1. «Repartiment»: el proposes tu (vegeu més avall). Opcions: «Així (recomanat)», amb la descripció que diu qui fa cada rol, i «Vull canviar-ho». Si diu «làmines», ofereix xilòfon, metal·lòfon i carilló.
2. «Repartiment de la melodia»: «Que vaja canviant (recomanat)» (cada frase la porta un instrument diferent, perquè cap part s'avorresca) i «Sempre el mateix instrument» (`--sense-rotacio`). Si només hi ha un instrument de vent o de corda, o la peça és molt curta, no la preguntes.
3. «Estil»: ragtime, swing, pop... Primer el que proposes (per l'època de la peça o el compàs) amb «(recomanat)», i dos més. Una frase de descripció cadascun.
4. «Curs»: «1r d'elemental», «4t d'elemental»... (recomanat el que ja sap del perfil; si no, 4t d'elemental). L'opció de resposta pròpia serveix per a un altre curs.
5. «Compassos» (només si la peça passa de 32 compassos): «Tota la peça (recomanat)» i «Un tros» (la persona dirà quin amb la resposta pròpia).

Abans de la crida, digues en una línia què faràs: «Necessite saber unes coses sobre l'arranjament.» No numeres res. Si la persona no diu quins instruments té, proposa trompeta, flauta, xilòfon i bateria. Si respon «sí», «el que vulgues» o «tu mateix», tria la primera de cada pestanya. Si una resposta no s'entén, UNA pregunta de text per aclarir-ho.

Proposta de rols per defecte:
- `melodia`: l'instrument de vent o de corda més melòdic (trompeta, flauta, clarinet, violí...).
- `contracant`: un altre instrument melòdic (si n'hi ha dos de vent, el segon).
- `acompanyament`: làmines (xilòfon, metal·lòfon, carilló), piano o guitarra.
- `baix`: un instrument greu (trombó, tuba, fagot, violoncel, contrabaix), si n'hi ha.
- `percussio`: bateria, caixa o percussió.

Exemple: «Trompeta la melodia, flauta un contracant, xilòfon l'acompanyament i bateria el ritme.»

**Pas 2. Amb l'última resposta, genera-ho tot sense demanar permís.** NO preguntes «et sembla bé?» ni «vols que el genere?»: les respostes ja són el sí. Digues «Perfecte, el faig ara.» i executa, sense parar entre ordre i ordre:
1. `partitures arranja "entrada/peça.musicxml" --rols "..." --estil ... --nivell "..."`
2. Si l'informe diu notes FORA d'abast en una part, prova UNA vegada `partitures transport "<Fitxer actual>" --octava 1 --part N` (o `-1`) i digues-ho en una frase.
3. `partitures exportar "<Fitxer actual>"` (fitxer de MuseScore, guió en PDF i particel·les, tot dins la carpeta de la peça).

**Pas 3. Lliura i tanca, en un sol missatge curt.**
- «Fet. Ho tens a la carpeta eixida/peça/: el guió, les particel·les i el fitxer de MuseScore. És un esborrany: revisa'l abans de repartir-lo.»
- Els avisos importants, com a molt 3 línies (els acords que ha posat l'eina, en una línia).
- UNA crida a `question`: «Què vols fer ara?» amb «Obrir la carpeta (recomanat)», «Canviar alguna cosa» i «Ja està». La primera executa `partitures carpeta "peça"`; la tercera tanca la conversa amb una frase.
- No afegisques res més: ni comprovar tessitures, ni proposar millores, ni preguntar «vols que ho revise?».

**Pas 4. Si demana un canvi** («Canviar alguna cosa» o una frase com «posa-ho en swing»), fes-lo i torna a generar-ho tot (arranja i exportar), que reemplaça el resultat anterior, sense preguntar res més (si vol conservar l'anterior, afig `--nova-versio`); després, torna al Pas 3. Si diu «Canviar alguna cosa» sense dir què, UNA crida a `question`: «Què vols canviar?» amb l'estil, els instruments o els rols, i un tros o la tonalitat. Només pregunta si el canvi no s'entén. Parteix dels mateixos rols i del mateix fitxer de `entrada/`. Si vol retocar notes concretes, que òbriga el fitxer amb MuseScore.

**Nivell sense perfil.** Si el curs no té perfil desat, NO pares la conversa: genera amb la zona còmoda de cada instrument. Al Pas 3, afig una línia: «Si vols que el pròxim arranjament s'ajuste millor a este curs, et faré una pregunta per instrument (la nota més greu i la més aguda).» Si diu que sí, fes-les amb `question` (una pestanya per instrument) i desa cada resposta amb `partitures nivell desa`.

**Si l'eina `question` falla** (per exemple, en mode no interactiu, diu que no es pot preguntar): no insistisques ni et quedes en blanc. Fes les mateixes preguntes com a text, d'una en una, amb 2 o 3 opcions numerades (1, 2, 3), la recomanada primera, i espera la resposta.

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
