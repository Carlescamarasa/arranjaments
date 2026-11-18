---
name: arranjar
description: Transporta, assigna parts a instruments (so real o escrit), comprova la tessitura de cada instrument i fa reduccions senzilles d'una partitura MusicXML. Usa-la per a qualsevol canvi musical.
---

# Arranjar amb les ordres de l'eina

Tot es fa amb ordres. Tu no edites cap fitxer. Les ordres NO modifiquen l'original: escriuen un fitxer nou a `eixida/`.

## Coses que cal saber (explica-ho si cal)

- So real (de concert) i so escrit: la trompeta en Si bemoll i el clarinet en Si bemoll sonen una segona major MÉS GREU del que s'escriu; la trompa en Fa, una quinta justa més greu; el saxo alt, una sexta major. L'ordre `instruments` ho fa tot sola: deixa el so igual i escriu cada part a l'altura que ha de llegir l'intèrpret.
- Es dona per fet que la partitura de partida està en so real (com un coral o una partitura de piano). Si ja ve amb instruments transpositors, l'eina ho detecta.

## Ordres

1. Veure què té el fitxer: `uv run partitures info "entrada/nom.musicxml"`
2. Llista d'instruments que coneix: `uv run partitures instruments`
3. Assignar parts a instruments (número de part = instrument):
   `uv run partitures instruments "entrada/nom.musicxml" --assigna "1=trompeta-sib,2=trompeta-sib,3=trompa-fa,4=trombo"`
   Això crea `eixida/nom-instruments.musicxml`.
4. Comprovar tessitures (fa servir l'altura escrita de cada instrument):
   `uv run partitures tessitura "eixida/nom-instruments.musicxml"`
   Si el fitxer no diu quins instruments són: afegir `--instruments "1=trompeta-sib,..."`.
5. Transportar tot el conjunt: `uv run partitures transport "<fitxer>" --semitons -2` o `--interval m-3`. Només una part una octava més amunt: `--octava 1 --part 3`.
6. Reduir: només algunes parts, `uv run partitures reduir "<fitxer>" --mantin "1,4"`; o a piano (dos pentagrames), `--a-piano`.

## Com ordenar el treball (una pregunta cada vegada)

1. Pregunta per a quina plantilla vol l'arranjament i quina part va a quin instrument.
2. Fes l'assignació (ordre 3), després la tessitura (ordre 4).
3. Si hi ha notes FORA d'abast, mostra els compassos i les notes tal com diu l'ordre i proposa UNA solució: canviar una part d'octava (`transport --octava ... --part ...`), canviar l'instrument de la part, o transportar tot el conjunt. Espera la decisió de la persona. Les notes «en zona incòmoda» són un avís, no un error.
4. Torna a passar la tessitura després de cada canvi.
5. Els límits de tessitura de l'eina són orientatius (de manual). La persona, que coneix l'instrument i l'alumnat, té l'última paraula.
6. Quan estiga conforme, passa a la skill `exportar`.

## No facis

- No canvies notes concretes ni ritmes: l'eina no ho fa. Si la persona vol retocar notes, que obri el fitxer amb MuseScore.
- No inventes noms d'instrument: usa només els de la llista. Si falta un instrument, digues-ho.
