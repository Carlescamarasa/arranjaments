---
name: biblioteca
description: Cerca partitures a la biblioteca compartida del professorat (carpeta de Teams/OneDrive) abans de recórrer al corpus lliure. Usa-la quan la persona demana una obra, o parla de la biblioteca, de partitures de l'escola o d'un nivell o estil.
---

# Biblioteca compartida del professorat

És una carpeta «Biblioteca d'arranjaments» de Teams que cada docent té dins de la seua carpeta OneDrive. Les eines només la LLIGEN: mai hi escriuen ni hi esborren res, i tu tampoc.

## Procediment (una pregunta cada vegada)

1. Quan et demanen una obra, cerca PRIMER ací i després al corpus lliure (skill `buscar-partitura`).
2. Executa `partitures biblioteca on-es`.
   - Si diu que no la troba, l'ordre ja diu QUIN pas falta: instal·lar OneDrive, entrar-hi amb el compte de l'escola (@edu.gva.es) o afegir la drecera. Explica només eixe pas, en paraules senzilles. Si OneDrive no hi és (cosa normal si la instal·lació és anterior a esta funció, perquè el pas de OneDrive només ve en tornar a obrir «Instal·lar Arranjaments»), guia-la a instal·lar-lo a mà amb l'enllaç oficial: Mac, https://go.microsoft.com/fwlink/?linkid=823060 (instal·lador de Microsoft, demana la contrasenya del Mac) o, sense contrasenya d'administrador, l'App Store, https://apps.apple.com/app/onedrive/id823766827; Windows, ve amb el sistema (si falta, https://go.microsoft.com/fwlink/?linkid=844652). Pàgina general: https://www.microsoft.com/microsoft-365/onedrive/download. Tu no baixes ni instal·les res: ho fa ella. Després, el pas que ja explicava així:
   - L'enllaç de la biblioteca el passen les companyes en privat: no te'l inventes ni el busques. La carpeta compartida s'ha de dir EXACTAMENT «Biblioteca d'arranjaments» (qui la crea). Si té un altre nom o és en un altre lloc, es pot guardar la ruta a mà (`partitures biblioteca on-es --ruta "<carpeta>"`).
   - Per al pas de la drecera, explica en paraules senzilles el pas que s'ha de fer UNA vegada (el text de l'ordre ja el porta): a Teams, al canal, pestanya Fitxers, seleccionar la carpeta i «Afegeix una drecera a Els meus fitxers» (castellà: «Agregar acceso directo a Mis archivos»), i tindre OneDrive instal·lat amb el compte de l'escola. Després, tornar a provar `on-es`. En LliureX no funciona (no hi ha OneDrive): digues-ho i passa al corpus lliure.
   - Si la persona té la carpeta en un altre lloc, pregunta-li la ruta i desa-la amb `partitures biblioteca on-es --ruta "<carpeta>"`.
3. Executa `partitures biblioteca actualitza`. Si diu que en queden per analitzar, torna-la a executar (fins a 2 vegades) i, si encara en queden, deixa que cerque igualment pels noms.
4. Cerca: `partitures biblioteca cerca <paraules>`, amb `--nivell`, `--estil` o `--instrument` si els coneixes (pregunta només el que falta). Mostra els resultats tal com surten (títol, tonalitat, compàs, parts i tessitures).
5. Per a usar-ne una: `partitures biblioteca copia <número>`; el fitxer queda a `entrada/` i continues amb la skill `arranjar`. Si és un PDF, skill `importar-pdf` (i revisar amb MuseScore). Si és de MuseScore, `partitures obrir` i exportar a MusicXML.
6. Si no hi ha res a la biblioteca, ho dius i continues amb el corpus lliure.

## Drets d'autor (digues-ho UNA vegada per conversa)

Les partitures compartides poden tindre drets d'autor: han de quedar dins del grup de l'escola. No les publiques ni les envies fora.

## Carpetes i etiquetes

El nivell i l'estil venen de les carpetes (per exemple `4t elemental/jazz/`), d'etiquetes entre claudàtors al nom del fitxer (`Blues [4t elemental] [jazz].mxl`) o d'un fitxer de text amb el mateix nom (`Blues.mxl.txt`, amb línies `nivell: ...` i `estil: ...`). Si algú vol etiquetar una partitura, explica-li-ho; tu no edites cap fitxer de la biblioteca.
