---
name: exportar
description: Genera en PDF la partitura general i les parts soltes de cada instrument amb MuseScore. Usa-la quan l'arranjament està acabat i es vol imprimir o repartir.
---

# Exportar a PDF

## Procediment

1. Pregunta quin fitxer vol exportar (normalment l'últim de `eixida/`; mira'l amb `ls eixida`).
2. Si encara no s'ha comprovat la tessitura (skill `arranjar`), proposa fer-ho abans. Si la partitura ve d'un PDF, comprova que s'ha revisat a MuseScore.
3. Executa: `uv run partitures exportar "eixida/nom.musicxml"`
   Això crea, dins `eixida/nom/`, un PDF de la partitura completa i un PDF per cada part, amb nom `nom - 1. Trompeta en Si bemoll.pdf`, etc. (Per a la partitura sola: afegir `--sense-parts`.)
4. Escriu la ruta completa de cada PDF que s'ha creat.
5. Si diu que no troba MuseScore, llig el missatge tal com és i explica a la persona com instal·lar-lo (README del projecte).

## Notes

- Les parts es generen una a una a partir de la partitura; les parts de piano no se separen.
- Si la persona vol canviar la presentació (mida, salts de pàgina, noms), que òbriga el fitxer amb MuseScore i òbriga el menú Format. Tu no ho pots fer des d'ací.
- Cal recordar que els arranjaments d'obres amb drets d'autor no es poden compartir públicament sense permís.
