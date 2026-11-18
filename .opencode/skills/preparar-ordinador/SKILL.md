---
name: preparar-ordinador
description: Comprova i repara la instal·lació (uv, MuseScore, Audiveris) amb els instal·ladors del projecte. Usa-la quan la persona diga "comprova que tot va bé" o quan una instal·lació falle.
---

# Comprovar i reparar

No es fa servir al principi: tot s'instal·la sota demanda. Només és per a comprovar o arreglar. No improvises cap ordre d'instal·lació: només els instal·ladors del projecte. A l'eina shell, passa sempre `timeout` amb el valor 900000 (15 minuts) als instal·ladors.

## Procediment

1. Comprova l'estat sense canviar res: Mac `bash "instalacio/instalar-mac.sh" --prova`; Windows `powershell -ExecutionPolicy Bypass -File "instalacio\instalar-windows.ps1" -Prova`. Llig la llista [fet] / [falta].
2. Si tot està bé, digues «Tot a punt» i para. Audiveris només cal si vol convertir PDF.
3. Si falta alguna cosa, explica en una frase què és i pregunta si l'instal·les. Si diu que sí, instal·la només això: Mac `bash "instalacio/instalar-mac.sh" --nomes uv` (o `musescore`, `audiveris`); Windows `powershell -ExecutionPolicy Bypass -File "instalacio\instalar-windows.ps1" -Nomes uv`.
4. Avisa del que pot passar: a Mac les aplicacions s'instal·len a la carpeta Aplicacions de la teua usuària (`~/Applications`) i no demanen contrasenya; a Windows MuseScore i Audiveris demanen permís d'administrador (finestra blava, cal prémer «Sí»). Si el Windows de la persona no li ho permet (ordinador de la feina o del centre), que ho consulte amb qui l'administra.
5. Si l'instal·lador diu que no ha pogut, llig el missatge i els passos manuals a la persona. A MuseScore, al web, cal triar l'opció «sense MuseHub».
6. Si s'ha instal·lat uv, NO cal reiniciar OpenCode: crida uv amb la ruta completa (Mac `~/.local/bin/uv run partitures comprovar`; Windows `& "$env:USERPROFILE\.local\bin\uv.exe" run partitures comprovar`), amb `timeout` 900000, i usa eixa ruta fins que la persona tanque l'aplicació.
