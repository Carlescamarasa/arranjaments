---
name: biblioteca
description: Cerca partitures a la biblioteca compartida del professorat (carpeta de Teams/OneDrive) abans de recórrer al corpus lliure. Usa-la quan la persona demana una obra, o parla de la biblioteca, de partitures de l'escola o d'un nivell o estil.
---

# Biblioteca compartida del professorat

És una carpeta «Biblioteca d'arranjaments» de Teams que cada docent té dins de la seua carpeta OneDrive. Les eines només la LLIGEN: mai hi escriuen ni hi esborren res, i tu tampoc.

## Procediment (una pregunta cada vegada)

1. Quan et demanen una obra, cerca PRIMER ací: `partitures biblioteca cerca <paraules>`, amb `--nivell`, `--estil` o `--instrument` si els coneixes (pregunta només el que falta). Mostra els resultats tal com ixen (títol, tonalitat, compàs, parts i tessitures).
2. Si l'ordre diu «No hi ha biblioteca compartida en este ordinador», passa a la skill `buscar-partitura` (corpus lliure) SENSE explicar res de OneDrive ni de Teams. Només si la persona pregunta per la biblioteca, ves al pas «Si pregunta per la biblioteca».
3. Si diu que l'índex està buit, executa `partitures biblioteca actualitza`. Si diu que en queden per analitzar, torna-la a executar (fins a 2 vegades) i, si encara en queden, deixa que cerque igualment pels noms. Si diu que alguns fitxers no s'han pogut llegir (sense connexió o encara no baixats), no passa res: es troben pel nom.
4. Per a usar-ne una: `partitures biblioteca copia <número>`; el fitxer queda a `entrada/` i continues amb la skill `arranjar`. Si és un PDF, skill `importar-pdf` (i revisar amb MuseScore). Si és de MuseScore, `partitures obrir` i exportar a MusicXML.
5. Si no hi ha res a la biblioteca, ho dius i continues amb el corpus lliure.

## Si pregunta per la biblioteca, o no la troba i vol arreglar-ho

Executa `partitures biblioteca on-es`. Si diu que no la troba, l'ordre ja diu QUIN pas falta: explica només eixe pas, en paraules senzilles.

- Si falta OneDrive (cosa normal si l'instal·lació és anterior a esta funció), guia-la a instal·lar-lo a mà. Mac: l'App Store, https://apps.apple.com/app/onedrive/id823766827 (no demana contrasenya) o l'instal·lador de Microsoft, https://go.microsoft.com/fwlink/?linkid=823060 (demana la contrasenya del Mac). Windows: ve amb el sistema (si falta, https://go.microsoft.com/fwlink/?linkid=844652). Pàgina general: https://www.microsoft.com/microsoft-365/onedrive/download. Tu no baixes ni instal·les res: ho fa ella.
- Si OneDrive hi és però cal entrar-hi, que entre amb el compte de l'escola (@edu.gva.es).
- Si falta la drecera: a Teams, al canal, pestanya Fitxers, seleccionar la carpeta i «Afegeix una drecera a Els meus fitxers» (castellà: «Agregar acceso directo a Mis archivos»); el text de l'ordre ja ho explica. Després, tornar a provar `on-es`.
- L'enllaç de la biblioteca el passen les companyes en privat: no te'l inventes ni el busques. La carpeta compartida s'ha de dir EXACTAMENT «Biblioteca d'arranjaments».
- Si diu que el Mac no ha deixat mirar dins de OneDrive, cal donar permís al Mac: quan pregunte si pot accedir als fitxers de OneDrive, «Permet» (o a Configuració del Sistema, Privacitat i seguretat, Fitxers i carpetes).
- Si la persona té la carpeta en un altre lloc, pregunta-li la ruta i desa-la amb `partitures biblioteca on-es --ruta "<carpeta>"`.
- En LliureX no funciona (no hi ha OneDrive): digues-ho i usa el corpus lliure.

## Drets d'autor (digues-ho UNA vegada per conversa)

Les partitures compartides poden tindre drets d'autor: han de quedar dins del grup de l'escola. No les publiques ni les envies fora.

## Carpetes i etiquetes

El nivell i l'estil venen de les carpetes (per exemple `4t elemental/jazz/`), d'etiquetes entre claudàtors al nom del fitxer (`Blues [4t elemental] [jazz].mxl`) o d'un fitxer de text amb el mateix nom (`Blues.mxl.txt`, amb línies `nivell: ...` i `estil: ...`). Si algú vol etiquetar una partitura, explica-li-ho; tu no edites cap fitxer de la biblioteca.
