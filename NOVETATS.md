# Novetats d'Arranjaments

Cada vegada que s'obri la icona, Arranjaments busca sol si hi ha una versió nova i, si n'hi ha, l'instal·la sense preguntar res. Les teues partitures (carpetes `entrada` i `eixida`) no es toquen mai.

## 0.1 (prototip, en proves)

Esta és una primera versió de proves: pot canviar i tindre errors. Ens ho pots dir.

- Ordre nova `partitures arranja`: a partir d'una melodia (o un full de melodia amb acords) crea les parts que falten, cadascuna amb un rol: melodia, contracant, acompanyament, baix i percussió (bateria, caixa o percussió menuda). Estils ragtime, swing, pop, rock, marxa, vals i clàssic; té en compte el nivell, i mostra els acords i les comprovacions. És un esborrany per a revisar amb MuseScore.
- Instruments nous: xilòfon, xilòfon alt Orff, metal·lòfon, carilló, marimba, vibràfon, bateria, caixa i percussió. «Làmines» és un grup (xilòfon, metal·lòfon, carilló).
- L'ajudant, si no coneix una paraula o una manera de fer (per exemple «làmines»), ara et pregunta de seguida què vol dir i com ho feu a classe.
- Actualització automàtica en obrir la icona «Arranjaments».
- Ordres noves: `partitures versio` (quina versió tens) i `partitures actualitzar` (busca novetats ara). Per a tornar a la versió anterior: `partitures actualitzar --torna-enrere`.
- Biblioteca compartida del professorat (Teams/OneDrive, només lectura): l'ajudant hi cerca partitures per títol, compositor, nivell, estil i instrument. Ordres `partitures biblioteca on-es`, `actualitza`, `cerca` i `copia`. Mira «Biblioteca compartida» al README per a la preparació d'una sola vegada.
- L'ajudant aprén els nivells: quan necessita saber fins on arriba un instrument a un curs, t'ho pregunta i ho recorda (`partitures nivell mostra` i `desa`), igual que les teues preferències. L'ordre `tessitura --nivell "4t elemental"` comprova la partitura contra el nivell. Mira «L'ajudant aprén els nivells» al README.
- L'instal·lador té un pas opcional nou, OneDrive (per a la biblioteca compartida de l'escola): mai fa fallar la instal·lació, i en acabar t'explica com entrar i afegir la drecera. Qui ja tenia Arranjaments instal·lat rep l'ajudant nou sol i, si falta OneDrive, l'ajudant t'explica com instal·lar-lo a mà. La carpeta compartida s'ha de dir «Biblioteca d'arranjaments»; si no, `partitures biblioteca on-es --ruta "carpeta"`.
