# Arranjaments de cambra amb OpenCode

Un ajudant per a professors i professores de música que volen fer arranjaments de cambra (per exemple, passar un coral a quartet de metalls) sense saber programar. Li parles en valencià, com a una persona, i ell s'encarrega de les gestions: buscar la partitura, transportar, comprovar que cada instrument pot tocar el que li toca i generar els PDF.

Una cosa important: la intel·ligència artificial NO escriu les notes. Tot el treball musical el fan unes eines normals, provades i previsibles. L'ajudant només tria quina eina toca i t'explica el resultat. Així, si el model gratuït que fas servir un dia és poc llest, no et fa malbé la música.

## Instal·lació: 3 passos, sense Terminal

**Pas 1. Baixa el projecte i descomprimeix-lo.** Baixa este fitxer: **[arranjaments.zip](https://github.com/Carlescamarasa/arranjaments/releases/latest/download/arranjaments.zip)** (no el botó verd «Code» d'esta pàgina: aquell ZIP no porta l'instal·lador).

- Mac: fes doble clic al ZIP (potser el Mac ja l'ha descomprimit sol). Es crea la carpeta `arranjaments`.
- Windows: **abans de descomprimir**, fes clic dret al ZIP, «Propietats», marca la casella **«Desbloquejar»** (Unblock) a baix de tot, «Aplica» i «D'acord». Així Windows no et farà avisos. Després, clic dret, «Extreure-ho tot».
- A dins de la carpeta pot haver-hi una altra `arranjaments`: és normal. **La carpeta bona és aquella on veus el fitxer `README.md` i «Instal·lar Arranjaments».**
- Esta carpeta només fa falta per a instal·lar. Quan acabes, la pots esborrar (i el ZIP també).

**Pas 2. Fes doble clic a «Instal·lar Arranjaments»** (la icona d'un pentagrama amb dues notes).

- Mac: és l'aplicació `Instal·lar Arranjaments`. El fitxer del mateix nom acabat en `.exe` és el de Windows, no el toques.
- Windows: és el programa `Instal·lar Arranjaments` (acabat en `.exe`, si veus les extensions). La carpeta del mateix nom acabada en `.app` és la de Mac, no la toques.
- La primera vegada, el sistema avisa perquè el programa ve d'internet i no està signat per cap empresa. Mira més avall [què cal prémer](#avisos). Si la carpeta t'ha arribat en un llapis USB i no baixada d'internet, potser no apareix cap avís.

S'obri una finestra amb la llista del que s'instal·larà. Prem **«Instal·lar»**. Cada pas es marca quan acaba: les eines musicals, l'aplicació OpenCode, MuseScore, la teua carpeta de treball i la icona de l'Escriptori. Pot tardar uns minuts la primera vegada. Quan acaba diu **«Tot a punt»**. A «Veure detalls» pots llegir tot el que ha fet.

Què t'ha deixat a l'ordinador:

- Una carpeta **`Arranjaments` dins de Documents**, amb dues carpetes: `entrada` (on poses els teus PDF o MusicXML) i `eixida` (on apareixen les partitures que crees). És l'única cosa que has de tocar.
- Una icona **«Arranjaments»** a l'Escriptori, per a obrir l'ajudant.
- Les eines musicals, guardades dins de l'ordinador com les de qualsevol aplicació. No cal que les busques.

Si tornes a obrir «Instal·lar Arranjaments» (per exemple, amb un ZIP més nou), actualitza les eines i fa el que falte. **Les partitures d'`entrada` i `eixida` no les toca mai.**

- Mac: no demana contrasenya. Les aplicacions van a la carpeta Aplicacions de la teua usuària (`~/Applications`). Si el Mac pregunta si «Instal·lar Arranjaments» pot accedir a l'Escriptori, a Documents o a Descàrregues, prem «Permet»: és per a deixar la icona a l'Escriptori i crear la carpeta de treball a Documents.
- Windows: OpenCode s'instal·la sense permisos especials, però **MuseScore demana permís d'administrador** (finestra blava, prem «Sí»), perquè s'instal·la per a tots els usuaris de l'ordinador. Si la finestra blava no apareix, mira si parpelleja una icona a la barra de tasques i prem-la. Si l'ordinador és de la feina o del centre i no et deixa, consulta-ho amb qui l'administra.
- Si alguna cosa no es pot instal·lar sola, la finestra t'ho diu i té un botó amb els passos per a fer-ho a mà.

**Pas 3. Fes doble clic a la icona «Arranjaments» de l'Escriptori.** S'obri OpenCode. **La primera vegada**, obri la teua carpeta de treball: botó «Obrir projecte» (en anglés, «Open project») i selecciona la carpeta **`Arranjaments` de Documents**. Les vegades següents ja apareix a la llista de projectes recents. Després escriu el que vols, per exemple: «Busca'm un coral de Bach». Ja està.

(Ara per ara OpenCode no té cap manera documentada d'obrir-se directament dins d'una carpeta, per això la icona només obri l'aplicació i cal triar la carpeta una vegada.)

L'ajudant et dirà, només quan faça falta, si has d'instal·lar alguna cosa més (per exemple, el programa que llig PDF el dia que en portes un) i t'ho preguntarà abans. Si l'aplicació et demana permís per a fer una cosa que no entens, **digues que no** i pregunta a l'ajudant què volia fer i per què.

Els models gratuïts ja venen preparats: no cal compte ni clau. Les partitures que crees apareixen a la carpeta `eixida` de la teua carpeta de treball (Documents, Arranjaments). Posa els teus fitxers (PDF, MusicXML) a `entrada`.

**Privacitat.** Tot el que escrius a l'ajudant viatja a l'empresa que ofereix el model, i els models gratuïts poden fer servir les converses per a entrenar-se. No escrigues mai noms d'alumnes ni dades personals.

<a id="avisos"></a>

### Si el Mac o el Windows no deixa obrir l'instal·lador

És normal: «Instal·lar Arranjaments» és un programa baixat d'internet i no està signat per cap empresa (signar-lo costa diners cada any), i els sistemes avisen amb tots els programes així. El codi és públic en este mateix lloc (carpeta `instalacio/`) i només instal·la el que s'ha descrit ací. Els noms dels botons canvien segons l'idioma de l'ordinador: ací van en valencià i en castellà.

**Mac** (macOS 15 Sequoia o més nou):

1. Fes doble clic a `Instal·lar Arranjaments`. Apareix un avís que diu que Apple no ha pogut verificar l'aplicació. Prem «Fet» (en castellà, «Aceptar»). No la mogues a la paperera.
2. Menú Apple, «Configuració del Sistema» («Ajustes del Sistema»), «Privacitat i seguretat» («Privacidad y seguridad»).
3. Baixa fins a la secció «Seguretat». Hi veuràs que «Instal·lar Arranjaments» s'ha bloquejat: prem **«Obre de tota manera»** (en castellà, **«Abrir igualmente»**). El botó només apareix durant una hora, més o menys, després de l'intent del pas 1.
4. Escriu la contrasenya de l'ordinador (o usa Touch ID) i confirma.

Només cal fer-ho la primera vegada. Font: Apple, [Obrir una app que Apple no ha verificat](https://support.apple.com/ca-es/guide/mac-help/mh40617/mac).

**Windows** (10 i 11):

- Si has desbloquejat el ZIP abans de descomprimir (pas 1), normalment no apareix cap avís.
- Si apareix una finestra blava «Windows ha protegit el teu PC» (SmartScreen), prem **«Més informació»** i després **«Executa igualment»** (en castellà, «Más información» i «Ejecutar de todas formas»).
- Si ja has descomprimit sense desbloquejar, també pots desbloquejar només el programa: clic dret a `Instal·lar Arranjaments`, «Propietats», «Desbloquejar».
- Si Windows 11 diu que el **Control intel·ligent d'aplicacions** (Smart App Control) ha bloquejat el programa i no hi ha cap botó per a continuar, o si l'ordinador és d'un centre i no deixa: usa l'alternativa de més avall.

Fonts: Microsoft, [SmartScreen i els programes sense signar](https://learn.microsoft.com/windows/apps/package-and-deploy/smartscreen-reputation) i [com treure la marca d'internet (Mark of the Web) d'un fitxer](https://learn.microsoft.com/en-us/microsoft-365-apps/security/internet-macros-blocked#remove-mark-of-the-web-from-a-file).

**Alternativa sense finestra bonica.** Si «Instal·lar Arranjaments» no s'obri de cap manera, dins de la carpeta `instalacio` hi ha els instal·ladors d'abans, que fan exactament el mateix en una finestra de text: `Instalar-Mac.command` (Mac) i `Instalar-Windows.bat` (Windows). Doble clic, i s'obri una finestra negra amb text: és normal. Al Mac, el primer avís es resol igual que en els passos de dalt.

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
- Les eines **no canvien mai l'original ni sobreescriuen res**: sempre creen un fitxer nou a `eixida/` (si el nom ja existeix, afigen -2, -3...) i no escriuen fora de la carpeta de treball. L'última línia de cada ordre diu «Fitxer actual», el fitxer amb què continuar.

## Per a qui vol saber-ne més (no cal)

On queda cada cosa després d'instal·lar:

| Què | Mac | Windows |
| --- | --- | --- |
| Carpeta de treball (l'única visible) | `~/Documents/Arranjaments` | `Documents\Arranjaments` |
| Configuració de l'ajudant (amagada) | `.opencode` dins de la carpeta de treball | igual, amb l'atribut d'amagat |
| Eines musicals i el seu Python | `~/Library/Application Support/Arranjaments` | `%LOCALAPPDATA%\Arranjaments` |
| Ordre `partitures` | `~/.local/bin/partitures` | `%USERPROFILE%\.local\bin\partitures.cmd` |

- A Windows, Documents pot estar dins d'OneDrive: no passa res, allí només hi ha partitures. Les eines van a una carpeta que OneDrive no sincronitza.
- `.opencode/AGENTS.md` (dins de la carpeta de treball): les instruccions que llig l'ajudant. `.opencode/skills/`: les guies de procediment (buscar, importar PDF, arranjar, exportar i comprovar la instal·lació).
- `.opencode/opencode.json`: els permisos i el model per defecte (`opencode/big-pickle`, gratuït; si algun dia desapareix, OpenCode usa el model més nou disponible). Format de permisos d'OpenCode 2. Les ordres `partitures ...` s'executen sense preguntar, excepte `partitures instalar ...`, que pregunta; les ordres d'esborrar o moure fitxers (`rm`, `del`, `rmdir`, `Remove-Item`, `mv`...) estan bloquejades; qualsevol altra ordre pregunta primer, igual que baixar una pàgina web o accedir fora de la carpeta. L'ajudant no pot editar fitxers directament. Aquests permisos són una xarxa de seguretat, no una garantia: per això convé llegir el que et demana abans d'acceptar.
- L'ordre `partitures` treballa sempre sobre la carpeta des d'on s'executa: llig i escriu només a `entrada/` i `eixida/` d'eixa carpeta. `partitures --help` mostra totes les ordres; `partitures comprovar` diu què hi ha instal·lat; `partitures instalar audiveris` (o `musescore`) instal·la el que falta.
- Si Audiveris o MuseScore estan en un lloc inusual, pots indicar la ruta amb les variables d'entorn `AUDIVERIS_PATH` i `MUSESCORE_PATH`.
- Per a desinstal·lar: esborra la carpeta de les eines i el fitxer de l'ordre `partitures` (taula de dalt), la icona de l'Escriptori i, si vols, OpenCode i MuseScore. La carpeta de treball és teua: guarda-la o esborra-la.

En este repositori (per a qui vol canviar el programa):

- `AGENTS.md`, `opencode.json` i `.opencode/skills/`: el que l'instal·lador copia dins de `.opencode` a la carpeta de treball.
- `scripts/partitures/`: les eines musicals (Python + music21). Dins del repositori s'executen amb `uv run partitures ...`.
- `instalacio/`: els instal·ladors de veritat (`instalar-mac.sh` i `instalar-windows.ps1`). «Instal·lar Arranjaments» és només una finestra que executa estos mateixos fitxers i en mostra el progrés; el seu codi és a `instalacio/visual/` (Swift per a Mac, C# per a Windows) i es construeix sol a GitHub cada vegada que canvia el projecte, juntament amb el ZIP de «Releases». Es poden usar a mà, per separat si vols: `bash "instalacio/instalar-mac.sh" --nomes uv` (o `opencode`, `musescore`, `eines`, `carpeta`, `icona`; `audiveris` només si cal convertir PDF); Windows: `powershell -ExecutionPolicy Bypass -File "instalacio\instalar-windows.ps1" -Nomes uv`. Amb `--prova` (Windows `-Prova`) només comprova. No cal Homebrew. Audiveris porta Java inclòs.
- Proves: `uv run pytest` (a GitHub també s'executen a Mac i a Windows, amb una instal·lació de veritat en ordinadors nets).
- Alternativa amb línia d'ordres (Terminal): `curl -fsSL https://opencode.ai/v2/install | bash`, i després `opencode` dins de la carpeta de treball. El format de `opencode.json` és el d'OpenCode 2; amb OpenCode 1 caldria el format antic (`permission`).

<a id="manual"></a>

## Instal·lació manual (si l'instal·lador automàtic no funciona)

1. **OpenCode.** Mac: [per a Mac amb xip Apple (M1, M2, M3...)](https://opencode.ai/update/api/latest/desktop/opencode/opencode-desktop-mac-arm64.dmg) o [per a Mac amb Intel](https://opencode.ai/update/api/latest/desktop/opencode/opencode-desktop-mac-x64.dmg); obri el fitxer i arrossega OpenCode a Aplicacions (si no saps quin Mac tens: menú Apple, «Sobre este Mac»). Windows: [descarrega per a Windows](https://opencode.ai/update/api/latest/desktop/opencode/opencode-desktop-win-x64.exe) i fes-hi doble clic. Totes les opcions: https://opencode.ai/download
2. **MuseScore** (gratuït; potser ja el tens): https://musescore.org/ca/download. Tria l'opció «sense MuseHub» (MuseScore Studio «without MuseHub»), que és l'aplicació sola.
3. **Les eines musicals i la carpeta de treball:** instal·la [uv](https://docs.astral.sh/uv/getting-started/installation/) i després executa l'instal·lador només per a estes dues coses. Mac: `bash "instalacio/instalar-mac.sh" --nomes eines` i `bash "instalacio/instalar-mac.sh" --nomes carpeta`. Windows: `powershell -ExecutionPolicy Bypass -File "instalacio\instalar-windows.ps1" -Nomes eines` i el mateix amb `-Nomes carpeta`.
4. Obri OpenCode, tria «Obrir projecte» i selecciona la carpeta `Arranjaments` de Documents.

## Llicència

MIT: es pot usar, copiar i adaptar lliurement, també en altres conservatoris. Vegeu `LICENSE`.
