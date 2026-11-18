---
name: preparar-ordinador
description: Comprova i repara la instal·lació (eines musicals, MuseScore, Audiveris) amb l'ordre partitures instalar. Usa-la quan la persona diga "comprova que tot va bé" o quan una instal·lació falle.
---

# Comprovar i reparar

No es fa servir al principi: «Instal·lar Arranjaments» ja ho deixa tot preparat. Només és per a comprovar o arreglar. No improvises cap ordre d'instal·lació: només `partitures instalar`. A l'eina shell, passa sempre `timeout` amb el valor 900000 (15 minuts) a `partitures instalar ...`.

## Procediment

1. Comprova l'estat sense canviar res: `partitures comprovar`. Si vols més detall: `partitures instalar --prova`. Llig la llista [fet] / [falta].
2. Si tot està bé, digues «Tot a punt» i para. Audiveris només cal si vol convertir PDF.
3. Si falta alguna cosa, explica en una frase què és i pregunta si l'instal·les. Si diu que sí, instal·la només això: `partitures instalar musescore` (o `audiveris`).
4. Avisa del que pot passar: a Mac les aplicacions s'instal·len a la carpeta Aplicacions de la teua usuària (`~/Applications`) i no demanen contrasenya; a Windows MuseScore i Audiveris demanen permís d'administrador (finestra blava, cal prémer «Sí»). Si el Windows de la persona no li ho permet (ordinador de la feina o del centre), que ho consulte amb qui l'administra.
5. Si l'instal·lador diu que no ha pogut, llig el missatge i els passos manuals a la persona. A MuseScore, al web, cal triar l'opció «sense MuseHub».
6. Si el sistema no troba l'ordre `partitures`, crida-la amb la ruta completa (Mac `~/.local/bin/partitures comprovar`; Windows `& "$env:USERPROFILE\.local\bin\partitures.cmd" comprovar`) i usa eixa ruta fins que la persona tanque l'aplicació. Si tampoc funciona, cal tornar a obrir «Instal·lar Arranjaments» (el programa amb què es va instal·lar tot): ho torna a deixar a punt sense tocar les partitures.
