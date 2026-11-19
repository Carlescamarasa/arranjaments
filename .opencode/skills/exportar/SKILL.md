---
name: exportar
description: Genera el fitxer de MuseScore, el guió en PDF i les particel·les (un PDF per instrument) amb MuseScore. Usa-la quan l'arranjament està acabat i es vol imprimir o repartir.
---

# Exportar a PDF

## Procediment

0. Si véns del guió de la skill `arranjar` o d'un canvi, no preguntes res: exporta directament l'últim «Fitxer actual» (pas 3).
1. Si no, executa `partitures peces --eixida` i pregunta quina peça amb l'eina `question` (una opció per peça, com a molt 4; el fitxer és `eixida/peça/peça.musicxml`).
2. No proposes comprovar tessitures ni res més abans d'exportar. Només si la partitura ve d'un PDF, comprova que s'ha revisat a MuseScore.
3. Executa: `partitures exportar "eixida/nom.musicxml"`
   Això deixa dins la carpeta de la peça, `eixida/nom/`, el fitxer de MuseScore `nom.mscz`, el guió en PDF `nom - Guió.pdf` i, a la subcarpeta `Particel·les/`, un PDF per cada instrument (`nom - 1. Trompeta en Si bemoll.pdf`, etc.). Una exportació nova reemplaça l'anterior i esborra les particel·les velles. (Per al guió sol: afegir `--sense-parts`.)
   Si la persona havia retocat el fitxer de MuseScore, l'ordre el guarda com `nom (retocat a MuseScore).mscz` i ho avisa: digues-ho clarament, perquè els PDF nous venen del MusicXML i no tenen eixos retocs.
4. Lliura amb el missatge d'AGENTS.md: «Fet. Ho tens a la carpeta eixida/peça/: el guió, les particel·les i el fitxer de MuseScore. És un esborrany: revisa'l abans de repartir-lo.» i la pregunta final amb l'eina `question`: «Què vols fer ara?» amb «Obrir la carpeta (recomanat)», «Canviar alguna cosa» i «Ja està» (la primera: `partitures carpeta "peça"`).
5. Si diu que no troba MuseScore, llig el missatge tal com és, explica que cal MuseScore (gratuït, https://musescore.org/ca/download) i ofereix instal·lar-lo amb `partitures instalar musescore` (vegeu `preparar-ordinador`, amb `timeout` 900000).

## Notes

- Els PDF de les parts es generen un a un; un instrument de dos pentagrames (piano) va en un sol PDF.
- Si la persona vol canviar la presentació (mida, salts de pàgina, noms), que òbriga el fitxer amb MuseScore (`partitures obrir "<fitxer>"`) i òbriga el menú Format. Tu no ho pots fer des d'ací.
