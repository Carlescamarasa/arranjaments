---
name: preparar-ordinador
description: Comprova i repara la instal·lació (uv, MuseScore, Audiveris) amb els instal·ladors del projecte. Usa-la quan la persona diga "comprova que tot va bé" o quan una instal·lació falle.
---

# Comprovar i reparar

No es fa servir al principi: tot s'instal·la sota demanda. Només és per a comprovar o arreglar. No improvises cap ordre d'instal·lació: només els instal·ladors del projecte.

## Procediment

1. Comprova l'estat sense canviar res: Mac `bash "instalacio/instalar-mac.sh" --prova`; Windows `powershell -ExecutionPolicy Bypass -File "instalacio\instalar-windows.ps1" -Prova`. Llig la llista [fet] / [falta].
2. Si tot està bé, digues «Tot a punt» i para. Audiveris només cal si vol convertir PDF.
3. Si falta alguna cosa, explica en una frase què és i pregunta si l'instal·les. Si diu que sí, instal·la només això: Mac `bash "instalacio/instalar-mac.sh" --nomes uv` (o `musescore`, `audiveris`); Windows `powershell -ExecutionPolicy Bypass -File "instalacio\instalar-windows.ps1" -Nomes uv`.
4. Avisa del que pot passar: Mac pot demanar la contrasenya del Mac (no es veu res mentre l'escrius, és normal); Windows mostra una finestra blava de permís: cal prémer «Sí».
5. Si l'instal·lador diu que no ha pogut, llig el missatge i els passos manuals a la persona.
6. Si s'ha instal·lat uv, demana que tanque OpenCode i el torne a obrir. Després: `uv run partitures comprovar`.
