# Tipus d'acompanyament i disposició de les notes

Convenció: notes en solfeig, Do central = Do3. Una pulsació és el temps del compàs (la negra en 4/4 i 3/4, la negra amb puntet en 6/8).

## Resum

L'acompanyament no és només "posar els acords": el tipus de ritme decideix el caràcter de la peça. Una marxa no sona a marxa amb acords sostinguts, ni un adagio amb un ritme inquiet (Schoenberg AC-14). L'eina tria el tipus segons l'estil i el nivell, el manté tota la frase i només el canvia a les cadències. Després decideix quines notes de l'acord toca cada instrument.

## Tipus i quin estil els usa

- Stride (ragtime): l'arrel greu als temps 1 i 3, l'acord als temps 2 i 4 (Levine ST01). En nivell avançat, el baix pot ser una dècima (arrel i 3a una dècima amunt, ST02).
- Acords curts avançats mig temps (swing): l'acord arriba una corxera abans del temps on canvia, a la "i" del 2 i a la "i" del 4 (Levine CP01). Mai endarrerit. En nivell elemental, els acords van al temps, sense avançar.
- Baix i acord (marxa i vals): baix al temps fort i acords als febles. Marxa en 4/4: baix en 1 i 3, acords en 2 i 4. Marxa en 2/4: baix en 1 i acord en 2. Vals: baix en 1 i acords en 2 i 3 (Schoenberg AC-07).
- Arpegi (pop): una nota de l'acord per pulsació, o dues en corxeres.
- Acords repetits (rock): acords curts a cada pulsació, en corxeres si el nivell les admet.
- Alberti (clàssic, nivell mitjà i avançat): nota baixa, alta, mitjana, alta, sempre el mateix motiu (Schoenberg AC-05).
- Intermitent (clàssic, elemental): un acord per compàs, sostingut (AC-08).
- Coral (fons dels instruments d'una sola veu): acords sostinguts (AC-04).

## Regles que aplica l'eina

1. El motiu es manté diversos compassos (AC-03). Canvia només a l'últim compàs de frase de pop i clàssic, on l'acord es sosté, i al compàs final.
2. En elemental, pop i clàssic, si la melodia fa una nota llarga i hi ha un sol acord al compàs, l'acompanyament deixa només el baix (AC-02). En marxa, vals, ragtime, swing i rock el pols no s'omet, perquè és el que dona el caràcter.
3. Swing avançat: si la melodia calla en el temps 1 o 3, entra un acord curt perquè no hi haja un forat (AC-09, Levine CP04).
4. Elemental vol figures senzilles: sense corxeres, i en estils que no són de jazz sense 7a (tríades).
5. L'acompanyament sosté un nivell per sota de la melodia i no la dobla (Zamacois Z5-15).

## Quines notes toca cada instrument

- Clàssic, marxa i vals (Zamacois): acord complet en posició propera, amb l'arrel al baix i les notes comunes mantingudes entre acords. La 7a es posa a partir del nivell mitjà i ha de baixar per grau. Al V-I final, l'arrel es triplica i s'omet la 5a (DU08).
- Swing i ragtime (Levine): 3a i 7a sobre l'arrel del baix, sense la 5a. Entre les dues posicions possibles (7a a dalt o 3a a dalt), tria la que es mou menys. La 7a d'un acord baixa mig to i fa de 3a del següent (VC01, VC02, VC08). Si l'acord és una tríada, 3a i 5a.
- Pop: tríada en posició propera; 7a només en nivell avançat.
- Rock: quinta buida, arrel i 5a (Herrera REH-04).
- Registre: cap segona ni sèptima juntes per sota de Do2, perquè sona fangós (VC06, Z5-14).

## Què no és de llibre

Els llindars següents són decisions de l'eina i es poden ajustar a `scripts/partitures/acompanyament.py` i `voicing.py`: quants atacs de melodia fan que s'ometi l'acompanyament, la mida del complement de swing, l'amplada màxima d'un acord, la mida de les penalitzacions i el límit del greu. Bossa i salsa no estan fetes: caldria verificar abans els exemples del llibre de Levine.
