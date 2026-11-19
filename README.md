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

**Pas 3. Fes doble clic a la icona «Arranjaments» de l'Escriptori.** S'obri OpenCode. **La primera vegada**, obri la teua carpeta de treball: botó «Afegeix projecte» (en castellà, «Añadir proyecto»; en anglés, «Add project») i selecciona la carpeta **`Arranjaments` de Documents**. Les vegades següents ja apareix a la llista de projectes recents. Després escriu el que vols, per exemple: «Busca'm un coral de Bach». Ja està.

(Ara per ara OpenCode no té cap manera documentada d'obrir-se directament dins d'una carpeta, per això la icona només obri l'aplicació i cal triar la carpeta una vegada.)

L'ajudant et dirà, només quan faça falta, si has d'instal·lar alguna cosa més (per exemple, el programa que llig PDF el dia que en portes un) i t'ho preguntarà abans. Si l'aplicació et demana permís per a fer una cosa que no entens, **digues que no** i pregunta a l'ajudant què volia fer i per què.

Els models gratuïts ja venen preparats: no cal compte ni clau. Les partitures que crees apareixen a la carpeta `eixida` de la teua carpeta de treball (Documents, Arranjaments). Posa els teus fitxers (PDF, MusicXML) a `entrada`.

**Privacitat.** Tot el que escrius a l'ajudant viatja a l'empresa que ofereix el model, i els models gratuïts poden fer servir les converses per a entrenar-se. No escrigues mai noms d'alumnes ni dades personals.

<a id="pas-a-pas"></a>

## Instal·lació pas a pas

El mateix d'abans, amb imatges. Les pantalles del sistema (navegador, carpetes, avisos) són recreacions i poden canviar un poc segons la versió i l'idioma de l'ordinador. Les de l'instal·lador i les d'OpenCode són captures reals; les de Windows mostren una conversa feta en un Mac, amb les rutes adaptades.

<details>
<summary><strong>Mac</strong></summary>

1. Baixa `arranjaments.zip` des de l'enllaç de dalt.

   ![Pas 1](docs/captures/mac/01-baixa-zip.png)

2. Obri la carpeta Descàrregues. Si el Mac no ha descomprimit el ZIP, fes-hi doble clic. Entra a la carpeta `arranjaments`.

   ![Pas 2](docs/captures/mac/02-descarregues.png)

3. Fes doble clic a «Instal·lar Arranjaments» (la icona del pentagrama).

   ![Pas 3](docs/captures/mac/03-carpeta-instalador.png)

4. La primera vegada, el Mac avisa que no ha pogut verificar l'aplicació. Prem «Fet». No la mogues a la paperera.

   ![Pas 4](docs/captures/mac/04-avis-no-verificat.png)

5. Obri «Configuració del Sistema», «Privacitat i seguretat», baixa fins a «Seguretat» i prem «Obre de tota manera». Et demanarà la contrasenya de l'ordinador.

   ![Pas 5](docs/captures/mac/05-obre-de-tota-manera.png)

6. S'obri l'instal·lador. Prem «Instal·lar» i espera: cada pas es marca quan acaba.

   ![Pas 6](docs/captures/mac/06-instalant.png)

7. Quan diu «Tot a punt», ja està instal·lat.

   ![Pas 7](docs/captures/mac/07-tot-a-punt.png)

8. Fes doble clic a la icona «Arranjaments» de l'Escriptori.

   ![Pas 8](docs/captures/mac/08-icona-escriptori.png)

9. S'obri OpenCode. La primera vegada, prem «Afegeix projecte».

   ![Pas 9](docs/captures/mac/09-afegeix-projecte.png)

10. Tria la carpeta `Arranjaments` de Documents i prem «Obre».

   ![Pas 10](docs/captures/mac/10-tria-carpeta.png)

11. Crea una sessió nova, escriu el que vols amb paraules normals i envia-ho.

   ![Pas 11](docs/captures/mac/11-escriu-peticio.png)

12. L'ajudant treballa i et fa preguntes d'una en una. Tria una resposta i prem «Envia».

   ![Pas 12](docs/captures/mac/12-pregunta.png)

13. Quan acaba, et diu què ha fet i on són els fitxers.

   ![Pas 13](docs/captures/mac/13-resultat.png)

14. Els PDF són a Documents, `Arranjaments`, `eixida`.

   ![Pas 14](docs/captures/mac/14-carpeta-eixida.png)

15. Si un model deixa de contestar, prem el nom del model (o escriu `/models`) i tria'n un altre de gratuït.

   ![Pas 15](docs/captures/mac/15-models.png)

</details>

<details>
<summary><strong>Windows</strong></summary>

1. Baixa `arranjaments.zip` des de l'enllaç de dalt.

   ![Pas 1](docs/captures/windows/01-baixa-zip.png)

2. A la carpeta Baixades, fes clic dret al ZIP, «Propietats», marca «Desbloquejar», «Aplica» i «D'acord».

   ![Pas 2](docs/captures/windows/02-desbloqueja.png)

3. Torna a fer clic dret al ZIP i tria «Extreure-ho tot».

   ![Pas 3](docs/captures/windows/03-extreu.png)

4. Entra a la carpeta `arranjaments` i fes doble clic a «Instal·lar Arranjaments» (la icona del pentagrama).

   ![Pas 4](docs/captures/windows/04-carpeta-instalador.png)

5. Si apareix la finestra blava «Windows ha protegit el teu PC», prem «Més informació» i després «Executa igualment».

   ![Pas 5](docs/captures/windows/05-smartscreen.png)

6. S'obri l'instal·lador. Prem «Instal·lar» i espera: cada pas es marca quan acaba. Si MuseScore demana permís (finestra blava), prem «Sí».

   ![Pas 6](docs/captures/windows/06-instalant.png)

7. Quan diu «Tot a punt», ja està instal·lat.

   ![Pas 7](docs/captures/windows/07-tot-a-punt.png)

8. Fes doble clic a la icona «Arranjaments» de l'Escriptori.

   ![Pas 8](docs/captures/windows/08-icona-escriptori.png)

9. S'obri OpenCode. La primera vegada, prem «Afegeix projecte».

   ![Pas 9](docs/captures/windows/09-afegeix-projecte.png)

10. Tria la carpeta `Arranjaments` de Documents i prem «Selecciona una carpeta».

   ![Pas 10](docs/captures/windows/10-tria-carpeta.png)

11. Crea una sessió nova, escriu el que vols amb paraules normals i envia-ho.

   ![Pas 11](docs/captures/windows/11-escriu-peticio.png)

12. L'ajudant treballa i et fa preguntes d'una en una. Tria una resposta i prem «Envia».

   ![Pas 12](docs/captures/windows/12-pregunta.png)

13. Quan acaba, et diu què ha fet i on són els fitxers.

   ![Pas 13](docs/captures/windows/13-resultat.png)

14. Els PDF són a Documents, `Arranjaments`, `eixida`.

   ![Pas 14](docs/captures/windows/14-carpeta-eixida.png)

15. Si un model deixa de contestar, prem el nom del model (o escriu `/models`) i tria'n un altre de gratuït.

   ![Pas 15](docs/captures/windows/15-models.png)

</details>

<a id="linux"></a>

## LliureX i altres Linux (Ubuntu)

Sense finestra bonica, però amb la mateixa instal·lació i **sense contrasenya d'administradora**. Està pensat per a LliureX 23 (Ubuntu 22.04) i LliureX 25 (Ubuntu 24.04), tots dos amb l'escriptori KDE Plasma, i es prova automàticament en Ubuntu 22.04 i 24.04 nets, no en un LliureX de veritat. Només per a ordinadors de 64 bits (Intel/AMD o ARM).

1. Baixa i descomprimeix [arranjaments.zip](https://github.com/Carlescamarasa/arranjaments/releases/latest/download/arranjaments.zip) (clic dret, «Extraure ací»). La carpeta bona és on veus `README.md` i `instalacio`.
2. Fes doble clic a **`Instal·lar Arranjaments (Linux).desktop`**. S'obri una finestra de Terminal amb el progrés (és normal) i, quan acaba, diu «Tot a punt». Si el sistema pregunta si el vols executar o confiar-hi, accepta. Tarda uns minuts (baixa OpenCode i MuseScore).
3. Obri la icona **«Arranjaments»** de l'Escriptori (o del menú d'aplicacions), i després com al pas 3 de dalt: «Afegeix projecte» i tria la carpeta `Arranjaments` de Documents.

Si el doble clic no fa res: obri la carpeta amb el gestor de fitxers, prem **F4** (s'obri un terminal a baix, ja dins de la carpeta) i escriu `bash instalacio/instalar-linux.sh`. Fa el mateix. Al gestor de fitxers de KDE (Dolphin), fer doble clic en un fitxer `.sh` no obri cap terminal (només pregunta si s'executa o s'obri), per això l'entrada d'ací és un fitxer `.desktop`, que sí que ho fa.

- No cal `libfuse2` ni res d'administradora: les aplicacions (AppImage) es descomprimeixen una vegada dins de `~/.local/share/Arranjaments`.
- Documents i Escriptori són els del sistema (poden dir-se «Documentos» o «Escritorio»).
- Audiveris (només per a convertir PDF) a Linux s'instal·la a mà amb el paquet `.deb` de [la seua pàgina](https://github.com/Audiveris/audiveris/releases), cosa que necessita una administradora.
- **En ordinadors d'un centre**, l'administració pot tindre bloquejat baixar o executar programes de la carpeta personal, i llavors la instal·lació pot fallar. Si passa, consulta-ho amb qui l'administra (el mateix text de l'instal·lador diu què ha fallat).
- Per a desinstal·lar: esborra `~/.local/share/Arranjaments`, `~/.local/bin/partitures`, `arranjaments.desktop` del menú d'aplicacions i de l'Escriptori.

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

| Què | Mac | Windows | Linux |
| --- | --- | --- | --- |
| Carpeta de treball (l'única visible) | `~/Documents/Arranjaments` | `Documents\Arranjaments` | `Documents/Arranjaments` (la del sistema) |
| Configuració de l'ajudant (amagada) | `.opencode` dins de la carpeta de treball | igual, amb l'atribut d'amagat | `.opencode` dins de la carpeta de treball |
| Eines musicals i el seu Python | `~/Library/Application Support/Arranjaments` | `%LOCALAPPDATA%\Arranjaments` | `~/.local/share/Arranjaments` |
| Ordre `partitures` | `~/.local/bin/partitures` | `%USERPROFILE%\.local\bin\partitures.cmd` | `~/.local/bin/partitures` |

- A Windows, Documents pot estar dins d'OneDrive: no passa res, allí només hi ha partitures. Les eines van a una carpeta que OneDrive no sincronitza.
- `.opencode/AGENTS.md` (dins de la carpeta de treball): les instruccions que llig l'ajudant. `.opencode/skills/`: les guies de procediment (buscar, importar PDF, arranjar, exportar i comprovar la instal·lació).
- `.opencode/opencode.json`: els permisos i el model per defecte (`opencode/big-pickle`, gratuït; si algun dia desapareix, OpenCode usa el model més nou disponible). Format de permisos d'OpenCode 2. Les ordres `partitures ...` s'executen sense preguntar, excepte `partitures instalar ...`, que pregunta; les ordres d'esborrar o moure fitxers (`rm`, `del`, `rmdir`, `Remove-Item`, `mv`...) estan bloquejades; qualsevol altra ordre pregunta primer, igual que baixar una pàgina web o accedir fora de la carpeta. L'ajudant no pot editar fitxers directament. Aquests permisos són una xarxa de seguretat, no una garantia: per això convé llegir el que et demana abans d'acceptar.
- L'ordre `partitures` treballa sempre sobre la carpeta des d'on s'executa: llig i escriu només a `entrada/` i `eixida/` d'eixa carpeta. `partitures --help` mostra totes les ordres; `partitures comprovar` diu què hi ha instal·lat; `partitures instalar audiveris` (o `musescore`) instal·la el que falta.
- Si Audiveris o MuseScore estan en un lloc inusual, pots indicar la ruta amb les variables d'entorn `AUDIVERIS_PATH` i `MUSESCORE_PATH`.
- Per a desinstal·lar: esborra la carpeta de les eines i el fitxer de l'ordre `partitures` (taula de dalt), la icona de l'Escriptori i, si vols, OpenCode i MuseScore. La carpeta de treball és teua: guarda-la o esborra-la.

En este repositori (per a qui vol canviar el programa):

- `AGENTS.md`, `opencode.json` i `.opencode/skills/`: el que l'instal·lador copia dins de `.opencode` a la carpeta de treball.
- `scripts/partitures/`: les eines musicals (Python + music21). Dins del repositori s'executen amb `uv run partitures ...`.
- `instalacio/`: els instal·ladors de veritat (`instalar-mac.sh`, `instalar-windows.ps1` i `instalar-linux.sh`). «Instal·lar Arranjaments» és només una finestra que executa estos mateixos fitxers i en mostra el progrés; el seu codi és a `instalacio/visual/` (Swift per a Mac, C# per a Windows) i es construeix sol a GitHub cada vegada que canvia el projecte, juntament amb el ZIP de «Releases». Es poden usar a mà, per separat si vols: `bash "instalacio/instalar-mac.sh" --nomes uv` (o `opencode`, `musescore`, `eines`, `carpeta`, `icona`; `audiveris` només si cal convertir PDF); Windows: `powershell -ExecutionPolicy Bypass -File "instalacio\instalar-windows.ps1" -Nomes uv`. Amb `--prova` (Windows `-Prova`) només comprova. No cal Homebrew. Audiveris porta Java inclòs.
- Proves: `uv run pytest` (a GitHub també s'executen a Mac i a Windows, amb una instal·lació de veritat en ordinadors nets, i la instal·lació de Linux es prova en Ubuntu 22.04 i 24.04).
- Alternativa amb línia d'ordres (Terminal): `curl -fsSL https://opencode.ai/v2/install | bash`, i després `opencode` dins de la carpeta de treball. El format de `opencode.json` és el d'OpenCode 2; amb OpenCode 1 caldria el format antic (`permission`).

<a id="manual"></a>

## Instal·lació manual (si l'instal·lador automàtic no funciona)

1. **OpenCode.** Mac: [per a Mac amb xip Apple (M1, M2, M3...)](https://opencode.ai/update/api/latest/desktop/opencode/opencode-desktop-mac-arm64.dmg) o [per a Mac amb Intel](https://opencode.ai/update/api/latest/desktop/opencode/opencode-desktop-mac-x64.dmg); obri el fitxer i arrossega OpenCode a Aplicacions (si no saps quin Mac tens: menú Apple, «Sobre este Mac»). Windows: [descarrega per a Windows](https://opencode.ai/update/api/latest/desktop/opencode/opencode-desktop-win-x64.exe) i fes-hi doble clic. Totes les opcions: https://opencode.ai/download
2. **MuseScore** (gratuït; potser ja el tens): https://musescore.org/ca/download. Tria l'opció «sense MuseHub» (MuseScore Studio «without MuseHub»), que és l'aplicació sola.
3. **Linux:** OpenCode, «Linux (AppImage)» a https://opencode.ai/download, i MuseScore, l'AppImage de https://musescore.org/ca/download. Per a les eines i la carpeta: `bash "instalacio/instalar-linux.sh" --nomes eines` i `--nomes carpeta` (cal [uv](https://docs.astral.sh/uv/getting-started/installation/)).
4. **Les eines musicals i la carpeta de treball (Mac i Windows):** instal·la [uv](https://docs.astral.sh/uv/getting-started/installation/) i després executa l'instal·lador només per a estes dues coses. Mac: `bash "instalacio/instalar-mac.sh" --nomes eines` i `bash "instalacio/instalar-mac.sh" --nomes carpeta`. Windows: `powershell -ExecutionPolicy Bypass -File "instalacio\instalar-windows.ps1" -Nomes eines` i el mateix amb `-Nomes carpeta`.
5. Obri OpenCode, tria «Afegeix projecte» i selecciona la carpeta `Arranjaments` de Documents.

## Llicència

MIT: es pot usar, copiar i adaptar lliurement, també en altres conservatoris. Vegeu `LICENSE`.
