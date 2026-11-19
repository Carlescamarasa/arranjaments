# Ritmes llegibles: com es parteixen les durades i els silencis

Convenció: les durades es donen en negres (blanca = 2, negra amb punt = 1,5, corxera = 0,5). L'inici és la posició dins del compàs (0 = primer temps, 1 = segon temps, 1,5 = el "i" del segon temps).

## Resum

Una part s'ha de poder llegir d'un colp d'ull. Perquè això passe, cada figura ha de deixar veure on cauen les pulsacions: una nota llarga que comença a mitja pulsació no s'escriu amb una sola figura que amague el temps, sinó amb dues o més figures lligades. El mateix val per als silencis: s'agrupen per pulsació i per meitats de compàs. MuseScore no ho arregla: escriu exactament la durada que li arriba. Per això ho decideix l'eina abans de generar el MusicXML, en el mòdul `gravat.py`.

## Què fa MuseScore i què ha de dir l'eina

Comprovat amb MuseScore 4.7 sobre una exportació real:

| Cosa | MuseScore sol | L'eina |
|---|---|---|
| Barres de corxeres | Respecta les del MusicXML (4/4 per pulsacions, 6/8 de 3 en 3) | Deixa que music21 les poste per la mètrica |
| Una blanca que travessa el mig de 4/4 | La deixa com a una sola figura | Parteix la nota i la lliga |
| Silenci de 3 temps al principi de 4/4 | El dibuixa com a silenci de blanca amb punt | Escriu silenci de blanca i silenci de negra |
| Silenci de 2 negres en 3/4 | El deixa tal qual | Escriu dos silencis de negra |
| Lligadura entre dues notes de la mateixa altura | La conserva | Les notes parteixen com a "començament, continuació, final" |
| Matís | Només si és un element del compàs, no si penja de la nota | Insereix el matís dins del compàs, a l'inici de la nota |
| Marca de respiració | La dibuixa com una coma després de la nota | La posa a la nota que acaba la frase |
| Text d'estil i metrònom | Els dibuixa en negreta damunt de la pauta | Els posa a la primera part (i a cada particel·la) |

## Regles de les durades

Regla 1: En 4/4 res no creua el mig del compàs sense lligadura. Excepcions: la rodona, la blanca amb punt al primer temps, i la blanca (o blanca amb punt) que comença al segon temps.
Per què: la tercera pulsació té un accent secundari i s'ha de veure. Herrera és més estricte que Gould en açò, i es pren la versió de Herrera.

Regla 2: Una nota que comença en una pulsació pot ser una sola figura (negra, blanca, negra amb punt) mentre no creue el mig del compàs ni haja de ser una durada que no existeix.
Per què: l'ull troba la pulsació on comença la nota. Si hi comença, no cal res més.

Regla 3: Una nota que comença a mitja pulsació no creua la pulsació següent, llevat de la negra a contratemps (corxera, negra, corxera). Es parteix en el límit de la pulsació i es lliga.
Per què: és el patró de la síncopa habitual i es llig bé. Una negra amb punt a contratemps, en canvi, es llig millor com a corxera lligada a negra.

Regla 4: En 3/4 es veu sempre la pulsació: una blanca pot començar al primer o al segon temps, però res no s'amaga a mitges.
Per què: si no, el compàs pot semblar 6/8 o 2/4.

Regla 5: En compàs compost (6/8, 9/8, 12/8) cap valor creua una pulsació (negra amb punt), llevat de pulsacions senceres juntes. En 12/8 tampoc no es creua el mig del compàs. Una negra que comença a la tercera corxera de 6/8 es parteix en dues corxeres lligades.
Per què: tres negres seguides en 6/8 es llegirien com a 3/4.

Regla 6: En compassos irregulars (5/8, 7/8) cada nota respecta el grup de pulsacions (3+2, 2+2+3...). L'eina tria l'agrupació per defecte i és una decisió seua, no del llibre: es pot canviar a `gravat.py`.
Per què: MuseScore tria un valor per defecte sense avisar.

## Regles dels silencis

Regla 7: El compàs sencer en silenci és un únic silenci de rodona, siga quin siga el compàs.

Regla 8: En 4/4 un silenci o és d'una pulsació o ocupa una meitat sencera del compàs (temps 1 i 2, o 3 i 4). Un silenci de tres temps són dos silencis (blanca i negra). Un silenci de dues negres a partir del segon temps són dos silencis de negra.
Per què: el silenci mostra les pulsacions igual que les notes.

Regla 9: En 3/4 els silencis van sempre per pulsació.

Regla 10: En compost, un silenci és d'una pulsació sencera (negra amb punt) o va dins d'una pulsació, sense creuar-la (per exemple, dos silencis de corxera seguits en lloc d'un que passe per damunt del límit de la pulsació).
Per què: el silenci que creua una pulsació amaga on cau.

## Què es pot comprovar després

- La suma de durades de cada compàs no canvia mai: parteix no vol dir afegir ni treure temps.
- Cap nota de 4/4 creua el mig del compàs, llevat de les excepcions de la regla 1.
- Cap silenci de dues negres en 3/4.
- Els tresets i altres durades irregulars no es toquen.

## Matisos, articulacions i respiracions (el que va amb això)

Les mateixes parts que s'ordenen ací porten, per a cada estil:

- Matís: la melodia té el de l'estil (mf per defecte, f en marxa i rock, mp en vals) i la resta de veus un graó per sota (pp, p, mp, mf, f, ff). En nivell elemental només p, mf i f. El matís canvia quan una veu passa de melodia a acompanyament i al revés.
- Articulació: la marxa porta staccato al baix i a l'acompanyament, el ragtime al baix i als acords dels temps febles, el swing accent als temps febles marcats, el vals accent al primer temps del baix. Pop, rock i clàssic, res.
- Respiració en vents: al final de cada frase (marca i nota anterior una mica més curta); en nivell elemental, també cada 2 compassos si no hi ha cap silenci.

Els valors de tempo per estil i el matís base són suggeriments de l'eina (orientatius), no regles dels llibres, i es canvien a les constants de `gravat.py`.

## Fonts

- Gould, Behind Bars: agrupació de barres per mètrica (BM-06 i la taula BM-06b), silencis agrupats (RS-04), notes sostingudes i sincòpa (SU-01, SU-02, SY-01), matisos (DY-01, DY-04), articulacions (AR-01), respiracions i lligadures en vent (WW-01, WW-02).
- Herrera: escriptura del 4/4 en música popular (ENG-01) i articulacions i swing (ENG-03, ENG-04).
- Zamacois, tractat d'harmonia III: equilibri entre acompanyament i melodia (Z5-15).
- Schoenberg: el caràcter el dóna el tipus d'acompanyament (AC-14).
