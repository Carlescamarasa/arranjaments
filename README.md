# Arranjaments de cambra amb OpenCode

Un ajudant per a professors i professores de música que volen fer arranjaments de cambra (per exemple, passar un coral a quartet de metalls) sense saber programar. Li parles en valencià, com a una persona, i ell s'encarrega de les gestions: buscar la partitura, transportar, comprovar que cada instrument pot tocar el que li toca i generar els PDF.

Una cosa important: la intel·ligència artificial NO escriu les notes. Tot el treball musical el fan unes eines normals, provades i previsibles. L'ajudant només tria quina eina toca i t'explica el resultat. Així, si el model gratuït que fas servir un dia és poc llest, no et fa malbé la música.

## Instal·lació: 3 passos, sense Terminal

**Pas 1. Baixa el projecte i descomprimeix-lo.** En esta pàgina, botó verd «Code», després «Download ZIP». Es descarrega un fitxer `arranjaments-main.zip`.

- Mac: fes-hi doble clic. Es crea la carpeta `arranjaments-main`. Mou-la on vulgues (per exemple, a Documents) i **no la canvies de lloc després**.
- Windows: **abans de descomprimir**, fes clic dret al ZIP, «Propietats», marca la casella **«Desbloquejar»** (Unblock) a baix de tot, «Aplica» i «D'acord». Així Windows no et farà avisos per cada fitxer. Després, clic dret, «Extreure-ho tot». Descomprimeix-lo **fora d'OneDrive**, per exemple a `C:\Users\el-teu-nom\arranjaments`: OneDrive sincronitza les carpetes i trenca les eines musicals. Si «Documents» o «Escriptori» tenen el símbol d'OneDrive, no els facis servir.
- A dins de la carpeta pot haver-hi una altra `arranjaments-main`: és normal. **La carpeta bona és aquella on veus els fitxers `README.md` i `Instalar-Mac.command` (o `Instalar-Windows.bat`).**

**Pas 2. Fes doble clic a l'instal·lador.**

- Mac: `Instalar-Mac.command`
- Windows: `Instalar-Windows.bat`

S'obri una finestra negra amb text: és normal, és l'instal·lador treballant. Instal·la tot el que falta (les eines musicals, l'aplicació OpenCode i MuseScore) i, quan acaba, diu **«Tot a punt»** i ha posat una icona **«Arranjaments»** a l'Escriptori. Pot tardar uns minuts la primera vegada. Si el repetixes, només fa el que falta.

- Mac: no demana contrasenya. Les aplicacions van a la carpeta Aplicacions de la teua usuària (`~/Applications`).
- Windows: OpenCode s'instal·la sense permisos especials, però **MuseScore demana permís d'administrador** (finestra blava, prem «Sí»), perquè s'instal·la per a tots els usuaris de l'ordinador. Si l'ordinador és de la feina o del centre i no et deixa, consulta-ho amb qui l'administra.
- Si alguna cosa no es pot instal·lar sola, l'instal·lador t'ho diu i t'escriu l'enllaç exacte per a fer-ho a mà.

**Pas 3. Fes doble clic a la icona «Arranjaments» de l'Escriptori.** S'obri OpenCode. **La primera vegada**, tria la carpeta del projecte: botó «Obrir projecte» (en anglés, «Open project») i selecciona la carpeta on veus `README.md` i `AGENTS.md`. Les vegades següents, el projecte ja apareix a la llista de projectes recents. Després escriu el que vols, per exemple: «Busca'm un coral de Bach». Ja està.

(Ara per ara OpenCode no té cap manera documentada d'obrir-se directament dins d'una carpeta, per això la icona només obri l'aplicació i cal triar la carpeta una vegada. Si mous la carpeta del projecte, torna a fer doble clic a l'instal·lador: la icona s'arregla.)

L'ajudant et dirà, només quan faça falta, si has d'instal·lar alguna cosa més (per exemple, el programa que llig PDF el dia que en portes un) i t'ho preguntarà abans. Si l'aplicació et demana permís per a fer una cosa que no entens, **digues que no** i pregunta a l'ajudant què volia fer i per què.

Els models gratuïts ja venen preparats: no cal compte ni clau. Les partitures que crees apareixen a la carpeta `eixida/` del projecte. Posa els teus fitxers (PDF, MusicXML) a `entrada/`.

**Privacitat.** Tot el que escrius a l'ajudant viatja a l'empresa que ofereix el model, i els models gratuïts poden fer servir les converses per a entrenar-se. No escrigues mai noms d'alumnes ni dades personals.

### Si el Mac o el Windows no deixa obrir l'instal·lador

És normal: l'instal·lador és un fitxer baixat d'internet i no està signat per cap empresa, i els sistemes avisen amb tots els fitxers així. Pots llegir-lo abans (és text) i només instal·la el que s'ha descrit ací.

**Mac** (macOS 15 Sequoia o més nou, també Tahoe 26):

1. Fes doble clic a `Instalar-Mac.command`. Apareix un avís que diu que Apple no ha pogut verificar el fitxer. Prem «Fet» (no «Moure a la paperera»).
2. Menú Apple, «Configuració del Sistema», «Privacitat i seguretat».
3. Baixa fins a la secció «Seguretat». Hi veuràs que `Instalar-Mac.command` s'ha bloquejat: prem **«Obrir igualment»**. El botó només apareix durant una hora després de l'intent del pas 1.
4. Escriu la contrasenya de l'ordinador (o usa Touch ID) i prem «Obrir».
5. Si el Mac et pregunta si Terminal pot accedir a Documents o a l'Escriptori, prem «Permet» (és perquè deixe la icona a l'Escriptori).

Font: Apple, [Obrir una app que Apple no ha verificat](https://support.apple.com/ca-es/guide/mac-help/mh40617/mac).

**Windows**:

- Si has desbloquejat el ZIP abans de descomprimir (pas 1), normalment no apareix cap avís.
- Si apareix «Obrir fitxer - Advertència de seguretat» (no es pot verificar l'editor), prem **«Executar»**.
- Si apareix una finestra blava «Windows ha protegit el seu equip» (SmartScreen), prem **«Més informació»** i després **«Executar igualment»**.
- Si cap dels dos apareix i no passa res, obri el fitxer amb clic dret, «Executar».
- Si ja has descomprimit sense desbloquejar, també pots desbloquejar un a un: clic dret a `Instalar-Windows.bat`, «Propietats», «Desbloquejar».

Font: Microsoft, [com treure la marca d'internet (Mark of the Web) d'un fitxer](https://learn.microsoft.com/en-us/microsoft-365-apps/security/internet-macros-blocked#remove-mark-of-the-web-from-a-file).

## Frases que pots escriure

- «Busca'm un coral de Bach en format editable.» (Cerca en el corpus de música lliure que ja ve instal·lat; si l'obra no hi és, l'ajudant et proposa on buscar-la.)
- «Tinc un PDF a entrada/ i el vull convertir en partitura.»
- «Què hi ha dins d'entrada/coral.musicxml?»
- «Vull fer-ne un arranjament per a dues trompetes, trompa i trombó.»
- «Comprova si les notes els van bé a cada instrument.»
- «Passa la trompa una octava més amunt.»
- «Transporta-ho un to més avall.»
- «Obri-me la partitura amb MuseScore.»
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
- Els **noms de les notes** són en solfeig i segueixen la convenció espanyola: el Do central és Do3 (en altres llocs, Do4 o C4).
- **Drets d'autor**: treballa amb música de domini públic o amb llicència que ho permeta. Una edició moderna d'una obra antiga pot tindre drets propis.
- Les eines **no canvien mai l'original ni sobreescriuen res**: sempre creen un fitxer nou a `eixida/` (si el nom ja existeix, afigen -2, -3...) i no escriuen fora del projecte. L'última línia de cada ordre diu «Fitxer actual», el fitxer amb què continuar.

## Per a qui vol saber-ne més (no cal)

- `AGENTS.md`: les instruccions que llig l'ajudant.
- `.opencode/skills/`: les guies de procediment (buscar, importar PDF, arranjar, exportar i comprovar la instal·lació).
- `opencode.json`: els permisos i el model per defecte (`opencode/big-pickle`, gratuït; si algun dia desapareix, OpenCode usa el model més nou disponible). Format de permisos d'OpenCode 2. Les ordres `uv run partitures ...` s'executen sense preguntar; les ordres d'esborrar o moure fitxers (`rm`, `del`, `rmdir`, `Remove-Item`, `mv`...) estan bloquejades; qualsevol altra ordre pregunta primer, igual que baixar una pàgina web o accedir fora del projecte. L'ajudant no pot editar fitxers directament. Aquests permisos són una xarxa de seguretat, no una garantia: per això convé llegir el que et demana abans d'acceptar.
- `instalacio/`: els instal·ladors (Mac i Windows), que l'ajudant executa sota demanda. Es poden usar a mà i instal·len el que falta, per separat si vols: `bash "instalacio/instalar-mac.sh" --nomes uv` (o `opencode`, `musescore`, `icona`; `audiveris` només si cal convertir PDF); Windows: `powershell -ExecutionPolicy Bypass -File "instalacio\instalar-windows.ps1" -Nomes uv`. Amb `--prova` (Windows `-Prova`) només comprova. No cal Homebrew. Audiveris porta Java inclòs.
- `scripts/partitures/`: les eines musicals (Python + music21), que s'executen amb `uv run partitures ...`. `uv run partitures --help` mostra totes les ordres; `uv run partitures comprovar` diu què hi ha instal·lat.
- Proves: `uv run pytest` (a GitHub també s'executen a Mac i a Windows).
- Si Audiveris o MuseScore estan en un lloc inusual, pots indicar la ruta amb les variables d'entorn `AUDIVERIS_PATH` i `MUSESCORE_PATH`.
- Alternativa amb línia d'ordres (Terminal): `curl -fsSL https://opencode.ai/v2/install | bash`, i després `opencode` dins de la carpeta del projecte. El format de `opencode.json` és el d'OpenCode 2 (el que baixa el botó de més amunt); amb OpenCode 1 caldria el format antic (`permission`).

## Instal·lació manual (si l'instal·lador automàtic no funciona)

1. **OpenCode.** Mac: [per a Mac amb xip Apple (M1, M2, M3...)](https://opencode.ai/update/api/latest/desktop/opencode/opencode-desktop-mac-arm64.dmg) o [per a Mac amb Intel](https://opencode.ai/update/api/latest/desktop/opencode/opencode-desktop-mac-x64.dmg); obri el fitxer i arrossega OpenCode a Aplicacions (si no saps quin Mac tens: menú Apple, «Sobre este Mac»). Windows: [descarrega per a Windows](https://opencode.ai/update/api/latest/desktop/opencode/opencode-desktop-win-x64.exe) i fes-hi doble clic. Totes les opcions: https://opencode.ai/download
2. **MuseScore** (gratuït; potser ja el tens): https://musescore.org/ca/download. Tria l'opció «sense MuseHub» (MuseScore Studio «without MuseHub»), que és l'aplicació sola.
3. **Les eines musicals:** instal·la [uv](https://docs.astral.sh/uv/getting-started/installation/) i, dins de la carpeta del projecte, executa `uv sync`. Això es pot fer també amb l'instal·lador, per separat: `bash "instalacio/instalar-mac.sh" --nomes uv`.
4. Obri OpenCode, tria «Obrir projecte» i selecciona la carpeta on veus `README.md` i `AGENTS.md`.

## Llicència

MIT: es pot usar, copiar i adaptar lliurement, també en altres conservatoris. Vegeu `LICENSE`.
