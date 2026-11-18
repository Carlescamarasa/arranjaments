# Arranjaments de cambra amb OpenCode

Un ajudant per a professors i professores de música que volen fer arranjaments de cambra (per exemple, passar un coral a quartet de metalls) sense saber programar. Li parles en valencià, com a una persona, i ell s'encarrega de les gestions: buscar la partitura, transportar, comprovar que cada instrument pot tocar el que li toca i generar els PDF.

Una cosa important: la intel·ligència artificial NO escriu les notes. Tot el treball musical el fan unes eines normals, provades i previsibles. L'ajudant només tria quina eina toca i t'explica el resultat. Així, si el model gratuït que fas servir un dia és poc llest, no et fa malbé la música.

## Instal·lació: 3 passos

**Pas 1. Baixa i instal·la OpenCode.** És una aplicació normal, com qualsevol altra.

- Mac: [descarrega per a Mac amb xip Apple (M1, M2, M3...)](https://opencode.ai/update/api/latest/desktop/opencode/opencode-desktop-mac-arm64.dmg) o [per a Mac amb Intel](https://opencode.ai/update/api/latest/desktop/opencode/opencode-desktop-mac-x64.dmg). Obri el fitxer i arrossega OpenCode a Aplicacions. (Si no saps quin Mac tens: menú Apple, «Sobre este Mac».)
- Windows: [descarrega per a Windows](https://opencode.ai/update/api/latest/desktop/opencode/opencode-desktop-win-x64.exe) i fes-hi doble clic.
- Totes les opcions: https://opencode.ai/download

**Pas 2. Instal·la MuseScore 4** (gratuït; potser ja el tens): https://musescore.org/ca/download

**Pas 3. Obri la carpeta del projecte i comença a parlar.**

1. Baixa este projecte: en esta pàgina, botó verd «Code», després «Download ZIP». Descomprimeix-lo, per exemple a Documents. Et quedarà una carpeta `arranjaments`.
2. Obri l'aplicació OpenCode, tria «Obrir projecte» (en anglés, «Open project») i selecciona la carpeta `arranjaments`.
3. Escriu el que vols, per exemple: «Busca'm un coral de Bach». Ja està.

No cal fer res més: l'ajudant et dirà, només quan faça falta, si has d'instal·lar alguna cosa (les eines musicals la primera vegada, o el programa que llig PDF el dia que en portes un) i t'ho preguntarà abans. Quan et demane permís per a executar una cosa, prem «Permetre».

Els models gratuïts ja venen preparats: no cal compte ni clau. Les partitures que crees apareixen a la carpeta `eixida/` del projecte. Posa els teus fitxers (PDF, MusicXML) a `entrada/`.

Avisos de seguretat: l'aplicació de Mac d'OpenCode i MuseScore estan signades i verificades per Apple, així que no haurien de donar cap avís. Si Windows mostra una finestra blava («Windows ha protegit el seu equip»), prem «Més informació» i després «Executar igualment».

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

Els models gratuïts van i vénen: un dia n'hi ha un que s'acaba, va molt lent o dona errors. No és culpa teua. Normalment OpenCode en tria un altre de sol. Si no ho fa, canvia'l tu:

1. A la zona on escrius, busca el nom del model i prem-lo per a veure la llista (o escriu `/models` i prem Retorn).
2. Tria un altre model de la llista (els gratuïts porten «free» en el nom, o són «Big Pickle»).
3. Torna a escriure la teua petició.

## Importants

- **Revisa sempre** el que ve d'un PDF: el reconeixement automàtic s'equivoca (alteracions, ritmes, lligadures). Obri el resultat amb MuseScore i comprova-ho compàs a compàs.
- Les **tessitures** (fins on pot tocar cada instrument) són orientatives, de manual. Tu coneixes els teus alumnes i el teu instrument: tu decideixes.
- **Drets d'autor**: treballa amb música de domini públic o amb llicència que ho permeta. Una edició moderna d'una obra antiga pot tindre drets propis.
- Les eines **no canvien mai l'original**: sempre creen un fitxer nou a `eixida/`.

## Per a qui vol saber-ne més (no cal)

- `AGENTS.md`: les instruccions que llig l'ajudant.
- `.opencode/skills/`: les guies de procediment (buscar, importar PDF, arranjar, exportar i comprovar la instal·lació).
- `opencode.json`: els permisos i el model per defecte (`opencode/big-pickle`, gratuït; si algun dia desapareix, OpenCode usa el model més nou disponible). Les ordres de l'eina s'executen sense preguntar; esborrar fitxers està prohibit; qualsevol altra cosa pregunta primer. L'ajudant no pot editar fitxers directament.
- `instalacio/`: els instal·ladors (Mac i Windows), que l'ajudant executa sota demanda. Es poden usar a mà i instal·len el que falta, per separat si vols: `bash "instalacio/instalar-mac.sh" --nomes uv` (o `musescore`, `audiveris`); Windows: `powershell -ExecutionPolicy Bypass -File "instalacio\instalar-windows.ps1" -Nomes uv`. Amb `--prova` (Windows `-Prova`) només comprova. No cal Homebrew. Audiveris porta Java inclòs.
- `scripts/partitures/`: les eines musicals (Python + music21), que s'executen amb `uv run partitures ...`. `uv run partitures --help` mostra totes les ordres; `uv run partitures comprovar` diu què hi ha instal·lat.
- Proves: `uv run pytest`.
- Si Audiveris o MuseScore estan en un lloc inusual, pots indicar la ruta amb les variables d'entorn `AUDIVERIS_PATH` i `MUSESCORE_PATH`.
- Alternativa amb línia d'ordres (Terminal): `curl -fsSL https://opencode.ai/v2/install | bash`, i després `opencode` dins de la carpeta del projecte. Provat amb OpenCode 1.19 i 2.3.

## Llicència

MIT: es pot usar, copiar i adaptar lliurement, també en altres conservatoris. Vegeu `LICENSE`.
