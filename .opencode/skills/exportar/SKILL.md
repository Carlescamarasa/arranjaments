---
name: exportar
description: Genera en PDF la partitura general i les parts soltes de cada instrument amb MuseScore. Usa-la quan l'arranjament està acabat i es vol imprimir o repartir.
---

# Exportar a PDF

## Procediment

1. Pregunta quin fitxer vol exportar (normalment l'últim «Fitxer actual»; si no el tens, mira `ls eixida`).
2. Si encara no s'ha comprovat la tessitura (skill `arranjar`), proposa fer-ho abans. Si la partitura ve d'un PDF, comprova que s'ha revisat a MuseScore.
3. Executa: `partitures exportar "eixida/nom.musicxml"`
   Això crea, dins una carpeta nova `eixida/nom/` (si ja existeix, `nom-2`...), un PDF de la partitura completa i un PDF per cada instrument, amb nom `nom - 1. Trompeta en Si bemoll.pdf`, etc. (Per a la partitura sola: afegir `--sense-parts`.)
4. Escriu la ruta completa de cada PDF que s'ha creat.
5. Si diu que no troba MuseScore, llig el missatge tal com és, explica que cal MuseScore (gratuït, https://musescore.org/ca/download) i ofereix instal·lar-lo amb `partitures instalar musescore` (vegeu `preparar-ordinador`, amb `timeout` 900000).

## Notes

- Els PDF de les parts es generen un a un; un instrument de dos pentagrames (piano) va en un sol PDF.
- Si la persona vol canviar la presentació (mida, salts de pàgina, noms), que òbriga el fitxer amb MuseScore (`partitures obrir "<fitxer>"`) i òbriga el menú Format. Tu no ho pots fer des d'ací.
