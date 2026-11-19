# Baix que camina (swing) i baix amb inversions

Convenció: notes en solfeig, Do central = Do3. Codi: `scripts/partitures/baix.py`.

## Avís: el baix caminant és una inferència

Cap dels llibres de referència ensenya a escriure un baix caminant. Un d'ells (Levine, BX01) avisa expressament que no ho fa. Herrera (BAX-01) només l'esbossa: arrel, altres notes de l'acord i una nota d'aproximació. Tot el que ve a continuació sobre el caminant és una **[inferència]** nostra a partir d'aquest esbós i de la pràctica habitual. No hi ha cap pàgina de llibre que el recolze. Si el professor el troba massa jazzístic, es pot desactivar triant nivell elemental o l'opció `--sense-rotacio`.

## Què fa el baix segons el nivell

| Nivell | Què fa |
|---|---|
| Elemental | Baix senzill: arrel, i quinta en els estils de dos temps. No es toca. |
| Mitjà (o sense curs) | Inversions quan milloren la línia, aproximació a un grau de l'acord següent, caminant en swing amb notes de l'acord i de pas. |
| Avançat (professional, superior) | A més: 7a al baix en els acords de sèptima, aproximació a un semitò. |

## Inversions i graus conjunts (Herrera BAX-02 i BAX-03, Perricone R65 i R66, Zamacois EN01)

Per a cada canvi d'acord, l'eina tria entre arrel, 3a i 5a (i 7a a nivell avançat) la nota que fa la línia de baix més suau. Cada candidata té un cost i la programació dinàmica troba el recorregut més barat de tota la peça (sempre el mateix resultat).

- Salt petit (grau conjunt) no costa res. Els salts grans costen més.
- L'arrel és la preferida; la 3a i la 5a tenen un petit cost addicional, de manera que només guanyen si milloren la línia. Amb C, G, Am, F el baix és Do, Si, La, Fa (mitjà) o Do, Sol, La, Fa (elemental).
- Dues inversions seguides a la mateixa inversió no s'accepten.
- La 3a no va al baix si la melodia ja hi és en aquell moment.
- Si baix i melodia es mouen en sentit contrari, hi ha un petit premi; en paral·lel a la 5a o l'8a, un petit càstig.
- La 5a al baix (6/4) només s'admet si és cadencial (I abans de V), de pas, o després de IV en pop i ragtime (Zamacois Q07, Herrera BAX-03).
- La cadència V a I va sempre en estat fonamental, perquè quede clara.
- Un acord que dura més d'un compàs prefereix l'estat fonamental.
- Si l'acord s'escriu amb barra (C/E), el baix el mana (Levine BX06).
- Rock queda només amb arrels (Perricone R72).

Els pesos són constants al principi de `baix.py` i es poden ajustar.

## Caminant en swing [inferència]

Només en 4/4 amb pols de negra i només a nivell mitjà o avançat. En compassos de 2/4 o 3/4 i en compostos es cau al patró de sempre.

1. Cada temps té una nota.
2. Temps 1: l'arrel de l'acord (sense inversions, per tal que la línia es llegisca com un baix de swing).
3. Temps 3 (fort): una nota de l'acord.
4. Temps 2 (i 4 si no és l'últim): nota de l'acord o nota de pas de l'escala.
5. Últim temps: aproximació a l'arrel següent, a un grau de l'escala (mitjà) o a un semitò (avançat).

Si el mateix acord dura diversos compassos (els fulls de melodia el parteixen sovint per mig compàs), s'ajunten en un sol tram i es camina de debò. La ruta entre el primer temps i l'aproximació es calcula amb programació dinàmica de segon ordre: evita repetir la nota, evita l'anada i tornada (Fa La Fa) i prefereix continuar en la mateixa direcció.

## Altres estils

- Ragtime i marxa: arrel i quinta als temps 1 i 3 (baix de stride), però amb la nota d'inversió quan la línia ho demana; ragtime afegeix aproximació a l'últim temps quan canvia l'acord.
- Marxa: a la cadència V a I, l'últim temps fa un salt d'octava cap a l'arrel següent (Schoenberg AC-07 [inferència] per a la posició exacta).
- Pop, vals i clàssic: mateixos patrons de sempre (arrel, quinta, tercera), però sobre la nota d'inversió escollida.

## Què no fa encara

- Pedal de tònica o dominant (paquet 9, introducció i coda).
- Redoblar el baix a l'octava només en tutti (Zamacois Z4-08) ni evitar la zona on dues notes de l'acompanyament fan 2a o 7a (Z5-14).
