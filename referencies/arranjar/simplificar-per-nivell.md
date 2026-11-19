# Simplificar la melodia per nivell

Convenció: notes en solfeig, Do central = Do3. Les xifres entre parèntesis són els identificadors de les regles dels llibres de referència (Perricone, Levine, Gould, Herrera); el text és nostre. Els llindars marcats [inferència] són una proposta de l'eina i es poden canviar a `scripts/partitures/simplificar.py`.

## Resum

Quan una melodia és massa difícil per a un curs, no es reescriu: es queda amb l'esquelet i es treuen les notes que només adornen. L'eina ho fa només si es demana (`--simplifica`) i diu exactament què ha tocat. Si la melodia surt de la zona còmoda, es mou una frase sencera d'octava, mai nota a nota.

## Quines notes són l'esquelet

Una nota és estructural (Perricone R13) si compleix prou d'estes coses, que sumen punts (R11):
- Cau en un temps fort (el primer temps pesa més; en 4 pulsacions, el tercer també).
- És llarga, o és una nota sincopada (comença a mig temps i travessa el temps següent).
- Ve després d'un silenci.
- És la primera o l'última nota de la frase.
- És la nota més aguda o la més greu de la frase.

Les que no arriben al llindar (2 punts) són ornaments [inferència: la puntuació és de l'eina].

## Què es treu primer

L'ordre és sempre el mateix (Perricone R14) i només afecta ornaments més curts que la figura mínima del nivell:
1. Anticipacions: la nota que repeteix la següent abans d'hora.
2. Notes veïnes: sortir d'una nota i tornar-hi per un grau.
3. Notes de canvi: dues notes que van i tornen a la nota estructural.
4. Notes de pas: les que van per graus entre dues estructurals.
5. Salts a notes curtes.

El temps de cada nota treta passa a la nota anterior, així la durada total del compàs no canvia. Si el resultat no es pot escriure amb una figura normal, la nota es deixa tal com estava.

Després de treure ornaments, l'eina aplica la simplificació de ritme de sempre: queda la nota que sona a cada pols mínim del curs.

## Figura mínima i salts per nivell [inferència]

| Nivell | Figura mínima | Salt màxim recomanat | Línies addicionals |
|---|---|---|---|
| Elemental | negra | quinta justa | 2 |
| Mitjà | corxera | octava | 3 |
| Professional | cap límit | cap límit | 4 |

Si el perfil del curs té les figures desades (`partitures nivell desa`), mana el perfil. La taula només s'usa quan no n'hi ha. En els cursos professionals no es treu res.

Els salts per damunt del límit no es toquen: canviarien la melodia. L'eina només els avisa a l'informe (Perricone R16). Quan mantindre els graus conjunts demana una figura que el nivell no admet, guanya la figura permesa (R15).

## Octavar frases senceres

Si una frase queda fora de la zona còmoda de l'instrument, es mou tota una octava amunt o avall (Levine VC10 dona el cas de pujar la melodia; la tessitura de l'instrument mana sempre). Regles:
- Només es canvia d'octava en un lloc de repòs: davant d'un silenci o després d'una nota llarga, a l'inici d'un compàs. Mai enmig d'un motiu.
- Només es fa si la frase hi guanya (més notes dins de la zona i cap fora de l'abast).
- Si el canvi deixa un salt de més d'una sexta major amb la frase veïna, no es fa [inferència].
- No es posa mai el signe 8va a metalls ni a veus; només la flauta i el flautí en poden tindre, per damunt de 4 línies addicionals (Gould OC-01, TR-07). Les notes es reubiquen per octava.

## Què diu l'informe

Dues línies, que expliquen sense tecnicismes què ha canviat:
- "He simplificat la melodia al nivell: notes de pas als compassos X a Y; anticipacions al compàs Z."
- "He canviat d'octava frases senceres: compassos X a Y una octava avall."

## Quan no cal

Si el professor vol una melodia reconeixible i no un exercici, millor tocar-la un nivell més amunt o repartir-la entre instruments (rotació) que no tallar-la massa.
