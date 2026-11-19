---
name: buscar-partitura
description: Ajuda a trobar una partitura en format MusicXML (editable) abans de recórrer a un PDF. Usa-la quan la persona vol una obra concreta i no té el fitxer.
---

# Buscar una partitura editable

Objectiu: aconseguir un fitxer MusicXML (`.musicxml`, `.xml` o `.mxl`) de l'obra. Si n'hi ha, és molt millor que un PDF: no té errors de reconeixement.

## Procediment (és la pregunta de la peça del camí «arranjament nou» d'AGENTS.md)

La peça es tria SEMPRE amb l'eina `question` (un selector que la persona clica), mai amb a), b), c) escrits. Les propostes han d'encaixar amb el que ha demanat (època, estil, compositor, curs, instruments) i no depenen de què hi haja a `entrada/`.

1. **Proposta.** Executa `partitures suggereix "<la petició, tal com l'ha dita>" --nivell "<curs>" --instruments "<instruments>"` (només els camps que ja coneixes). L'ordre mira, per este ordre, la biblioteca de l'escola (si n'hi ha), el corpus lliure que ja ve instal·lat (Haydn, Mozart, Beethoven, Bach, Händel, Schumann, Palestrina, Joplin, cançons populars...) i les peces d'`entrada/` NOMÉS si encaixen. Cada resultat ix amb la font i una frase de per què; les dades són reals (mai t'inventes títols).
2. **La pregunta.** UNA crida a `question`, header «Quina peça?». Fins a 3 opcions amb les millors propostes (etiqueta curta, per exemple «Mozart K. 155 mov. 2 (recomanat)»; la descripció diu font, parts i compassos), més «Buscar-ne més al web» i «Tinc el meu fitxer». Si ho vols dir amb paraules, la persona usa l'opció de resposta pròpia: ho expliques a la pregunta. Si la persona ja ha dit una peça concreta, NO fas la pregunta: la busques (pas 4) i, si no la trobes, ho dius i hi proposes el que sí hi ha.
3. **Si tria una proposta**: `partitures suggereix --copia <número>` (la deixa a `entrada/`; el número és el de la llista que va mostrar l'ordre, no el de l'ordre de les opcions de la pregunta) i continua SENSE parar amb les preguntes de rols, estil i curs (skill `arranjar`). Si tria «Tinc el meu fitxer»: que el deixe a `entrada/` i t'avise; llavors `partitures peces` i continua.
4. **Una peça que diu ella o «més al web».** Primer prova el corpus (`partitures corpus <paraules>`, sense accents ni majúscules; copia amb `--copia <número>`) i la biblioteca (skill `biblioteca`). Si no hi és, cerca al web, amb eines de lectura, en estes fonts i en este ordre:
   - OpenScore (https://github.com/OpenScore i https://musescore.com/openscore): transcripcions lliures (CC0) en fitxers de MuseScore (`.mscx`); es converteixen a MusicXML. Moltes són de cançons, cambra i corda.
   - CPDL (https://www.cpdl.org): música coral i antiga; molts arxius tenen MusicXML, però cal mirar cada edició.
   - Mutopia (https://www.mutopiaproject.org): domini públic; sobretot PDF i LilyPond, MusicXML poc habitual.
   - IMSLP (https://imslp.org): quasi tot són PDF d'escanejats; només serveix per a la via PDF, que no s'ofereix als menús.
   Pots proposar obres conegudes, però NO les ofereixes com a llestes fins que hages comprovat amb `webfetch` que hi ha un fitxer MusicXML o `.mscx` baixable (adreça real, vista per tu). Quan el tingues: `partitures descarrega "<adreça del fitxer>"` (només baixa de CPDL, Mutopia i GitHub; només MusicXML, `.mxl` o MuseScore; el deixa a `entrada/`). El `webfetch` d'estos tres llocs va sense permís; a la resta (per exemple musescore.com) demana permís a la persona: avisa-la en una frase.
5. Mai intentes saltar proteccions (comprovacions de robot, captcha, inicis de sessió). Si `descarrega` diu que la pàgina bloqueja o que no és el fitxer, o no pots llegir la pàgina, digues-ho i que la persona la baixe des del seu navegador i la deixe a `entrada/`.
6. Si el fitxer és un PDF, skill `importar-pdf` (només si insistix); si és MusicXML, skill `arranjar`.

## Drets d'autor (digues-ho sempre, amb paraules senzilles)

- Una obra és de domini públic quan l'autor va morir fa molts anys (en molts països, 70 anys), però una EDICIÓ moderna (la maquetació, les digitacions, les revisions) pot tindre drets propis.
- Mira sempre la llicència que indica la pàgina de descàrrega.
- Per a ús a classe i a l'aula, normalment no hi ha problema; per a publicar, gravar o vendre, cal revisar-ho.
- Si tens dubtes, no et poses a deduir la llicència: digues que no ho saps i que ho consulte a la pàgina de l'obra.
