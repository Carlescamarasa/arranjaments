---
name: preparar-ordinador
description: Prepara l'ordinador (instal·la MuseScore, Audiveris i les eines musicals) executant l'instal·lador del projecte. Usa-la quan la persona diga "prepara l'ordinador", o quan una ordre diga que falta MuseScore o Audiveris.
---

# Preparar l'ordinador

IMPORTANT: no improvises cap ordre d'instal·lació. Només executes els instal·ladors que ja venen amb el projecte (estan provats). Si no funcionen, expliques què falla; no busques solucions pel teu compte.

## Procediment

1. Explica en dues frases què passarà: es comprovarà què falta i s'instal·laran MuseScore (per a veure i imprimir partitures) i Audiveris (per a llegir PDF), que són gratuïts. Pot tardar uns 5 a 10 minuts i necessita internet. Pregunta si vol continuar.
2. Mira primer l'estat, sense canviar res: Mac `bash "instalacio/instalar-mac.sh" --prova`; Windows `powershell -ExecutionPolicy Bypass -File "instalacio\instalar-windows.ps1" -Prova`. Digues què hi ha ja i què falta. Si ja està tot, digues «Tot a punt» i para.
3. Si falta alguna cosa, executa l'instal·lador sense l'opció de prova (Mac: `bash "instalacio/instalar-mac.sh"`; Windows: `powershell -ExecutionPolicy Bypass -File "instalacio\instalar-windows.ps1"`). OpenCode et demanarà permís: és normal, la persona ha de dir que sí.
4. Mentre va, avisa de les coses que poden passar:
   - Mac: pot demanar la contrasenya del Mac (és la que fa servir per a entrar). Quan l'escriu, no es veu res; és normal. Escriu-la i prem Retorn.
   - Windows: apareixerà una finestra blava de permís («Voleu permetre que esta aplicació faça canvis?»). Cal prémer «Sí».
   - Si l'instal·lador diu que no ha pogut instal·lar alguna cosa, llig a la persona el missatge i els passos manuals que mostra (normalment, baixar un fitxer d'una pàgina i obrir-lo; al Mac, arrossegar la icona a Aplicacions).
5. El final de l'instal·lador mostra una llista [fet] / [falta]. Llig-la a la persona. Si tot està [fet], digues «Tot a punt». Si falta alguna cosa, explica-ho i què ha de fer ella.
6. Si s'ha instal·lat uv per primera vegada, digues que cal tancar OpenCode i tornar-lo a obrir, perquè detecte les eines noves. Després, per a tornar a comprovar-ho quan vulga: `uv run partitures comprovar`.
