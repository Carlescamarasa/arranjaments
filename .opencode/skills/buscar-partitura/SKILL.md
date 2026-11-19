---
name: buscar-partitura
description: Ajuda a trobar una partitura en format MusicXML (editable) abans de recórrer a un PDF. Usa-la quan la persona vol una obra concreta i no té el fitxer.
---

# Buscar una partitura editable

Objectiu: aconseguir un fitxer MusicXML (`.musicxml`, `.xml` o `.mxl`) de l'obra. Si n'hi ha, és molt millor que un PDF: no té errors de reconeixement.

## Procediment (una pregunta cada vegada)

1. Pregunta quina obra vol (compositor i títol) i per a quina plantilla (instruments).
2. Pregunta si ja té algun fitxer. Si el té, demana-li que el deixe a la carpeta `entrada/` i ves a la skill `arranjar`.
3. Cerca primer al corpus que ja ve instal·lat (no necessita internet): `partitures corpus <paraules>` (per exemple `corpus bach`, `corpus beethoven quartet` o `corpus bwv66.6`). Cerca per compositor, títol o nom de fitxer, sense mirar accents ni majúscules, i mostra títol i compositor. Per copiar un resultat a `entrada/`: `partitures corpus <paraules> --copia <número>`. El corpus és limitat (sobretot coral de Bach, quartets clàssics, música antiga i cançons populars): si l'obra no hi és, no passa res, vés al pas següent.
4. Si no hi ha res, proposa-li (d'una en una) estes fonts, perquè ho cerque ell o ella al navegador. Tu NO inventes enllaços ni diràs que una obra hi és si no ho has comprovat:
   - OpenScore (https://musescore.com/openscore): transcripcions fetes per voluntaris, publicades sota CC0 (sense restriccions). Es poden baixar en MusicXML amb compte gratuït a MuseScore.com. Moltes són de cançons, cambra i piano.
   - CPDL, Choral Public Domain Library (https://www.cpdl.org): sobretot música coral i antiga. Molts arxius tenen versió MusicXML, però no tots: cal mirar cada edició.
   - Mutopia Project (https://www.mutopiaproject.org): música de domini públic o amb llicència Creative Commons. Ofereix sobretot PDF, LilyPond i MIDI; el MusicXML no és habitual.
   - IMSLP (https://imslp.org): biblioteca enorme, però quasi tot són PDF d'escanejats. Serveix per a la via PDF (skill `importar-pdf`).
5. Tu no intentes baixar res saltant proteccions (comprovacions de robot, captcha, inicis de sessió). Si una pàgina bloqueja la baixada, digues-ho i que la persona la baixe des del seu navegador.
6. Si baixa un fitxer, que el deixe a la carpeta `entrada/`. Si és un PDF, passa a la skill `importar-pdf`; si és MusicXML, a `arranjar`.

## Drets d'autor (digues-ho sempre, amb paraules senzilles)

- Una obra és de domini públic quan l'autor va morir fa molts anys (en molts països, 70 anys), però una EDICIÓ moderna (la maquetació, les digitacions, les revisions) pot tindre drets propis.
- Mira sempre la llicència que indica la pàgina de descàrrega.
- Per a ús a classe i a l'aula, normalment no hi ha problema; per a publicar, gravar o vendre, cal revisar-ho.
- Si tens dubtes, no et poses a deduir la llicència: digues que no ho saps i que ho consulte a la pàgina de l'obra.
