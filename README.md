# Arranjaments de cambra amb OpenCode

Un ajudant per a professors i professores de música que volen fer arranjaments de cambra (per exemple, passar un coral a quartet de metalls) sense saber programar. Li parles en valencià, com a una persona, i ell s'encarrega de les gestions: buscar la partitura, transportar, comprovar que cada instrument pot tocar el que li toca i generar els PDF.

Una cosa important: la intel·ligència artificial NO escriu les notes. Tot el treball musical el fan unes eines normals, provades i previsibles. L'ajudant només tria quina eina toca i t'explica el resultat. Així, si el model gratuït que fas servir un dia és poc llest, no et fa malbé la música.

## Instal·lació: només 2 passos

**Pas 1. Instal·la OpenCode** (copia i apega UNA línia).

- **Mac**: obri l'aplicació «Terminal» (busca «Terminal» amb la lupa), apega esta línia i prem Retorn:

  `curl -fsSL https://opencode.ai/v2/install | bash`

- **Windows**: obri «PowerShell» (busca-ho al menú Inici), apega esta línia i prem Retorn (Windows et demanarà permís: accepta):

  `winget install -e --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements; $env:Path=[Environment]::GetEnvironmentVariable('Path','Machine')+';'+[Environment]::GetEnvironmentVariable('Path','User'); npm.cmd i -g '@opencode/cli@latest'`

Després, tanca la finestra i obri-la de nou.

**Pas 2. Obri OpenCode en la carpeta del projecte i escriu «prepara l'ordinador».**

1. Baixa este projecte (botó verd «Code», «Download ZIP») i descomprimeix-lo, per exemple a Documents.
2. Mac: al Terminal escriu `cd ` (amb l'espai), arrossega la carpeta del projecte a la finestra, prem Retorn i escriu `opencode`.
   Windows: obri la carpeta a l'Explorador, escriu `powershell` a la barra de dalt (on diu la ruta), prem Retorn i escriu `opencode`.
3. La primera vegada, tria un model gratuït (`/models`, vegeu més avall).
4. Escriu: **prepara l'ordinador**. L'ajudant t'anirà explicant cada pas i instal·larà MuseScore i Audiveris (gratuïts) amb l'instal·lador del projecte. Et dirà exactament què has de prémer si cal una contrasenya o un permís. Al final et diu «Tot a punt» o què falta.

Si en algun moment vols comprovar-ho, escriu «comprova que tot està instal·lat».

## Obrir l'ajudant les altres vegades

Igual que al pas 2.2: obri el Terminal (Mac) o PowerShell (Windows) dins de la carpeta del projecte i escriu `opencode`.

Posa els teus fitxers (PDF, MusicXML) a la carpeta `entrada/`. Els resultats apareixen a la carpeta `eixida/`.

## Frases que pots escriure

- «Busca'm el coral Jesu, meine Freude de Bach en format editable.»
- «Tinc un PDF a entrada/ i el vull convertir en partitura.»
- «Què hi ha dins d'entrada/coral.musicxml?»
- «Vull fer-ne un arranjament per a dues trompetes, trompa i trombó.»
- «Comprova si les notes els van bé a cada instrument.»
- «Passa la trompa una octava més amunt.»
- «Transporta-ho un to més avall.»
- «Fes-me una reducció per a piano.»
- «Genera els PDF de la partitura i de les parts.»

L'ajudant et farà preguntes d'una en una. Contesta amb frases normals.

## Quan un model gratuït deixa de funcionar

Els models gratuïts van i vénen: un dia n'hi ha un que s'acaba, va molt lent o dona errors. No és culpa teua. Per a canviar-ne:

1. Dins d'OpenCode, escriu `/models` i prem Retorn.
2. Tria un altre model de la llista (els gratuïts porten «free» en el nom, per exemple els de la secció «opencode»). Si cal, pots escriure per a filtrar la llista.
3. Torna a escriure la teua petició.

El canvi val per a la sessió actual. Per veure quins n'hi ha, també es pot escriure `opencode models` al Terminal.

## Importants

- **Revisa sempre** el que ve d'un PDF: el reconeixement automàtic s'equivoca (alteracions, ritmes, lligadures). Obri el resultat amb MuseScore i comprova-ho compàs a compàs.
- Les **tessitures** (fins on pot tocar cada instrument) són orientatives, de manual. Tu coneixes els teus alumnes i el teu instrument: tu decideixes.
- **Drets d'autor**: treballa amb música de domini públic o amb llicència que ho permeta. Una edició moderna d'una obra antiga pot tindre drets propis.
- Les eines **no canvien mai l'original**: sempre creen un fitxer nou a `eixida/`.

## Per a qui vol saber-ne més (no cal)

- `AGENTS.md`: les instruccions que llig l'ajudant.
- `.opencode/skills/`: les guies de procediment (preparar l'ordinador, buscar, importar PDF, arranjar, exportar).
- `instalacio/`: els instal·ladors (Mac i Windows). Es poden executar a mà: `bash "instalacio/instalar-mac.sh"` o `powershell -ExecutionPolicy Bypass -File "instalacio\instalar-windows.ps1"`. No cal Homebrew. Audiveris porta Java inclòs.
- Comprovar-ho tot: `uv run partitures comprovar`.
- `scripts/partitures/`: les eines musicals (Python + music21). `uv run partitures --help` mostra totes les ordres.
- `opencode.json`: els permisos. Les ordres de l'eina s'executen sense preguntar; esborrar fitxers està prohibit; qualsevol altra cosa pregunta primer. L'ajudant no pot editar fitxers directament.
- Proves: `uv run pytest`.
- Si Audiveris o MuseScore estan en un lloc inusual, pots indicar la ruta amb les variables d'entorn `AUDIVERIS_PATH` i `MUSESCORE_PATH`.
- Provat amb OpenCode 1.19 i 2.3 (la configuració es llig en les dues versions).

## Llicència

MIT: es pot usar, copiar i adaptar lliurement, també en altres conservatoris. Vegeu `LICENSE`.
