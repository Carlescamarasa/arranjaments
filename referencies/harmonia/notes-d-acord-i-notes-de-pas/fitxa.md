# Notes d'acord i notes de pas (notes estranyes)

Convenció: notes en solfeig, Do central = Do3. Veus: S (soprano), A (contralt), T (tenor), B (baix). Cada nota de la línia és una sonoritat.

## Resum

En una sonoritat hi ha notes que pertanyen a l'acord (notes reals) i notes que no (notes estranyes). Les estranyes no són errors: adornen la melodia entre dues notes de l'acord. Per això, quan l'eina compara dues sonoritats seguides per a trobar quintes o octaves paral·leles, no considera les notes estranyes que ho són de debò. Si ho féu, avisaria de falsos errors a qualsevol línia amb adorns.

Una nota es considera estranya només si compleix les condicions juntes. Si en falta una, es tracta com una nota real i es comprova com sempre. Així l'eina no amaga un error per ser massa generosa.

## Tipus que reconeix l'eina

| Tipus | Com és | Exemple en Do major sobre l'acord de Do |
|---|---|---|
| Nota de pas | No és de l'acord, hi arribes i en surts per graus conjunts en la mateixa direcció, en temps feble, i resol a una nota de l'acord següent | Mi, Re, Do |
| Bordadura | Surt d'una nota de l'acord, puja o baixa un grau i torna a la mateixa nota | Mi, Re, Mi |
| Anticipació | És la nota de l'acord següent, avançada en temps feble | Sol, Do, Do (la segona ja sona abans de l'acord de Do) |
| Escapada | S'hi arriba per grau conjunt i se'n surt per salt en direcció contrària | Mi, Re, Si |
| Apoiatura | Cau en temps fort, no és de l'acord i resol per grau conjunt a una nota de l'acord | Fa (temps fort), Mi |

## Regles

Regla 1: Una nota de pas o una bordadura no compta per a les quintes i octaves paral·leles ni directes.
Per què: la nota no forma part de l'acord i passa de pressa, de manera que l'oïda no la sent com una veu estructural. Els tractats d'harmonia ho accepten com a pràctica normal.

- Es comprova amb les proves de `tests/test_p04_10_harmonia.py` (cant a 4 veus amb nota de pas al soprano).

Regla 2: En el perfil `escolar` només s'accepten com a estranyes la nota de pas i la bordadura. En el perfil `arranjament` també s'accepten l'anticipació, l'escapada i l'apoiatura.
Per què: en un exercici d'escola es vol veure que l'alumne controla els casos més clars. En un arranjament, els compositors usen tots els adorns i no té sentit tractar-los com a errors.

Regla 3: Una nota que no és de l'acord i no encaixa en cap tipus, o que no resol a una nota de l'acord, queda com a nota estranya sense classificar i es comprova com una nota real.
Per què: pot ser un error d'escriptura. És millor un avís de més que un error amagat.

## Com ho veu l'eina

`partitures harmonia comprova` mira una sonoritat per pols. Dedueix l'acord que explica millor les veus (triada o setena) i marca com a candidates les notes que hi sobren. Si no sap en quin temps cau cada sonoritat, suposa que és feble; amb un fitxer amb compassos sí que ho sap, i només accepta l'apoiatura en el temps 1.

## On és a l'eina

- Fitxa: `partitures harmonia fitxa notes-d-acord`.
- Codi: `classifica_notes` a `scripts/partitures/harmonia.py`.
- Ordre: `partitures harmonia comprova coral.musicxml --perfil escolar` (o `arranjament`).
