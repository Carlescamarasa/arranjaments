# Quintes i octaves paral·leles (i directes)

Convenció: notes en solfeig, Do central = Do3. Veus: S (soprano), A (contralt), T (tenor), B (baix). Cada nota de la línia és un acord.

## Resum

En l'harmonia a quatre veus, dues veus no poden fer dues octaves (o dos unísons) seguides, ni dues quintes justes seguides. Això val per a les sis parelles de veus i també si les veus es mouen per moviment contrari. A més, arribar a una quinta o a una octava amb les dues veus en la mateixa direcció (quinta o octava "directa" u "oculta") només s'accepta en uns casos concrets. Zamacois recorda, citant Koechlin, que són normes d'escola (II, p. 14): hi ha excepcions, i les donem a part.

## Regles

Regla 1: Prohibides dues octaves o dos unísons seguits entre les mateixes dues veus, tant si pugen o baixen juntes com si es mouen en direcció contrària.
Per què: les dues veus deixen de ser independents i l'acord perd una nota real; sona més pobre.

- Correcte: [exemple-1-correcte.musicxml](exemple-1-correcte.musicxml) (Do major; I IV V I): `S: Do4 Do4 Si3 Do4 | A: Mi3 Fa3 Re3 Mi3 | T: Sol2 La2 Sol2 Sol2 | B: Do2 Fa1 Sol1 Do2`
- Incorrecte: [exemple-1-incorrecte.musicxml](exemple-1-incorrecte.musicxml) (Do major; I IV): `S: Do4 Fa4 | A: Sol3 La3 | T: Mi3 Do3 | B: Do2 Fa2` (S i B: Do-Do i després Fa-Fa, octaves seguides).

Regla 2: Prohibides dues quintes seguides entre les mateixes dues veus quan la segona és justa.
Per què: dues quintes justes seguides fan que les veus sonen "buides" i paral·leles; l'oïda les sent com una sola línia doblada.

- Correcte: [exemple-2-correcte.musicxml](exemple-2-correcte.musicxml) (Do major; IV V): `S: Fa4 Re4 | A: La3 Sol3 | T: Do3 Si2 | B: Fa2 Sol2` (el baix puja i les altres veus baixen).
- Incorrecte: [exemple-2-incorrecte.musicxml](exemple-2-incorrecte.musicxml) (Do major; IV V): `S: Fa4 Re4 | A: La3 Si3 | T: Do3 Re3 | B: Fa2 Sol2` (T i B: Fa-Do i després Sol-Re, quintes justes seguides).

Regla 3: Una quinta justa seguida d'una quinta NO justa (disminuïda o augmentada) s'accepta, però mai entre S i B.
Per què: la segona quinta ja no és "buida"; el paral·lelisme gairebé no es nota. Entre les veus extremes, en canvi, es nota massa.

- Correcte: [exemple-3-correcte.musicxml](exemple-3-correcte.musicxml) (Do major; I VII6 I6): `S: Mi4 Re4 Sol3 | A: Sol3 Fa3 Mi3 | T: Do3 Si2 Do3 | B: Do2 Re2 Mi2` (T i A: Do-Sol, quinta justa, i després Si-Fa, quinta disminuïda).

Regla 4: Quinta i octava directes (arribar-hi amb les dues veus en la mateixa direcció):
- entre S i B, només si el Soprano va per grau conjunt (un to o un semitò);
- si hi ha una veu interior (A o T), només si una de les dues veus va per grau conjunt; per a la quinta, també si una de les seues notes ja sonava a l'acord anterior.
Per què: el salt en la mateixa direcció fa sentir la quinta o l'octava "amagada" com si fóra paral·lela; el grau conjunt la dissimula.

- Correcte: el pas V I de l'exemple 1 (S Si3-Do4 per grau conjunt mentre B puja Sol1-Do2: octava directa admesa).
- Incorrecte: [exemple-4-incorrecte.musicxml](exemple-4-incorrecte.musicxml) (Do major; I IV): `S: Mi4 Do4 | A: Sol3 Fa3 | T: Do3 La2 | B: Do2 Fa1` (S i B baixen i arriben a Fa-Do, quinta directa, amb el Soprano saltant una 3a).

## Excepcions (Zamacois)

- Quinta disminuïda seguida de quinta justa: s'accepta si el segon acord està en primera inversió, perquè el baix fa la 3a i neutralitza l'efecte (Zamacois II, §78).
- V7 complet cap a I complet: la 5a pot anar a la 5a, fent dues quintes, si no és entre S i B (Zamacois II, §74 b). Molts tractadistes no ho admeten.
- Sisena augmentada alemanya cap al V: les quintes s'admeten si no són entre S i B (Zamacois III, §38). Vegeu la fitxa de sisena augmentada.
- Octaves per redoblament (una melodia doblada a l'octava per a reforçar-la) no són octaves prohibides: les veus que doblen no són parts reals (Zamacois II, Apèndix, nota Y, p. 242-243). No aplica als exercicis a 4 veus.
- No s'admet l'octava directa que porta a duplicar la 3a o la 5a de l'acord (Zamacois I, §84). L'uníson directe tampoc (Zamacois I, §96).

## Errors freqüents

- Mirar només S i B. Cal mirar les 6 parelles: S-A, S-T, S-B, A-T, A-B, T-B.
- Creure que el moviment contrari les salva: Do-Do i després Fa-Fa (una veu puja, l'altra baixa) continuen sent octaves seguides.
- Oblidar les octaves compostes: Do2 i Do4 també és una octava.
- Comptar com a errors les notes repetides: si cap veu canvia de nota, no hi ha successió.
- Notes de pas o canvis de posició dins del mateix acord no amaguen unes quintes: cal comparar cada disposició amb la de l'acord següent (Zamacois I, §262).

## Com ho ha de comprovar i explicar l'ajudant

1. Escriu la línia compacta de cada acord (S, A, T, B) amb octaves.
2. Per a cada parella de veus i cada parell d'acords seguits: calcula l'interval entre les dues veus a l'acord 1 i a l'acord 2 (oblida les octaves de més).
3. Si els dos són octava o uníson: error (Regla 1). Si els dos són quinta i la segona és justa: error (Regla 2), excepte els casos d'Excepcions.
4. Si les dues veus van en la mateixa direcció i arriben a quinta justa o octava: aplica la Regla 4.
5. No ho faces de memòria si hi ha l'eina: `partitures harmonia comprova <fitxer>` mira les quintes i octaves paral·leles i directes de totes les parelles de veus. Si l'eina i el teu càlcul no coincideixen, mana l'eina.
6. En explicar-ho, digues les dues veus, els compassos i les notes ("T i B: Fa2-Do3 i després Sol2-Re3"), i proposa UNA solució: moure una de les dues veus en direcció contrària.

## Fonts

- Zamacois, Tratado de armonía I, cap. III, §§76-77 (tipus de moviment), p. 49-50.
- Zamacois, Tratado de armonía I, cap. III, §§79-81 (quintes, octaves i unísons successius), p. 50-51.
- Zamacois, Tratado de armonía I, cap. III, §§82-84 (quinta i octava directes), p. 51-53.
- Zamacois, Tratado de armonía I, cap. VII, §262 (canvis de disposició i quintes), p. 157.
- Zamacois, Tratado de armonía II, cap. II, §74 i §78, p. 58-63; Apèndix, nota Y, p. 237-247.
- Zamacois, Tratado de armonía III, cap. I, §38, p. 47-48.
