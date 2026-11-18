---
name: importar-pdf
description: Converteix un PDF o imatge d'una partitura en MusicXML amb Audiveris (reconeixement òptic) i explica que cal revisar-la a MuseScore. Usa-la quan només hi ha PDF.
---

# De PDF a MusicXML

## Abans de començar

Explica en dues frases: el programa «llig» la imatge i la converteix en notes, però s'equivoca. Funciona bé amb PDF digitals nets (fets amb un programa d'edició); malament amb escanejats borrosos, fotos amb el mòbil, pàgines tortes o manuscrits.

## Procediment

1. Comprova que el PDF està a `entrada/` (`ls entrada`). Si no, demana a la persona que el deixe allí.
2. Executa: `uv run partitures importar "entrada/nom.pdf"`. Pot tardar de 1 a 10 minuts. Avisa-la que cal esperar.
3. Si va bé, l'ordre diu on ha deixat el fitxer `.mxl` (dins `eixida/`). Escriu la ruta completa.
4. Si l'ordre diu que no troba Audiveris, llig el missatge sencer a la persona: explica com instal·lar-lo (hi ha un instal·lador al README del projecte). No intentes instal·lar res tu.
5. Si falla perquè la qualitat del PDF és baixa, proposa buscar la partitura en MusicXML (skill `buscar-partitura`) o un PDF millor.

## Revisió obligatòria

Digues SEMPRE, amb claredat: «Ara cal obrir el fitxer amb MuseScore i revisar-lo compàs a compàs abans de continuar». Coses que sol fallar: alteracions (sostinguts i bemolls), figures de ritme, lligadures, indicacions de compàs, lletra i noms d'instrument. Pregunta si ho vol obrir i, només si diu que sí, executa `open "<ruta>"` (Mac) o digues-li com obrir-lo manualment (Windows: doble clic al fitxer).
No continues amb l'arranjament fins que la persona confirme que ja ho ha revisat i desat. Si el desa des de MuseScore, que ho faça com a MusicXML (Fitxer, Anomena i desa, format MusicXML) dins de `entrada/`.
