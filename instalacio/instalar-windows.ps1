# Instal·lació per a Windows. Es pot repetir sense problema: només fa el que falta.
# - uv i OpenCode s'instal·len a la teua carpeta d'usuària: NO demanen permís d'administrador.
# - MuseScore (i Audiveris, si el demanes) s'instal·len per a tots els usuaris amb el seu instal·lador MSI:
#   Windows et demana permís d'administrador (finestra blava, UAC). Si l'ordinador no et deixa, consulta qui l'administra.
# Què deixa a l'ordinador:
#   - les eines musicals, amagades com les de qualsevol aplicació: %LOCALAPPDATA%\Arranjaments (fora d'OneDrive)
#   - la carpeta de treball que veu la professora: Documents\Arranjaments (amb entrada\ i eixida\)
#   - l'ordre «partitures» a la carpeta .local\bin de la usuària, que funciona des de la carpeta de treball
#   - la icona «Arranjaments» a l'Escriptori
# Després d'instal·lar, la carpeta des d'on s'ha executat (la del ZIP) ja no cal.
# Ús: powershell -ExecutionPolicy Bypass -File "instalacio\instalar-windows.ps1"             (tot el que falta, i la icona «Arranjaments» a l'Escriptori)
#     powershell -ExecutionPolicy Bypass -File "instalacio\instalar-windows.ps1" -Nomes uv    (només una cosa: uv, opencode, musescore, audiveris, eines, carpeta, icona)
#     powershell -ExecutionPolicy Bypass -File "instalacio\instalar-windows.ps1" -Prova      (només comprova)
#     ... -SensePreguntes   (no s'atura mai a esperar una tecla; per a proves)
# Audiveris NO s'instal·la si no el demanes amb -Nomes audiveris (només cal per a convertir PDF).
# L'instal·lador visual («Instal·lar Arranjaments») executa este mateix fitxer amb la variable d'entorn
# ARRANJAMENTS_PROGRES=1. Llavors, a més del text de sempre, s'escriuen línies «@@PAS nom inici|ok|falla»
# i una «@@FI ok|falla» final, que la finestra llig per a marcar cada pas.
param([switch]$Prova, [switch]$SensePreguntes, [ValidateSet("", "uv", "opencode", "musescore", "audiveris", "eines", "carpeta", "icona")][string]$Nomes = "")

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$Carpeta = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Carpeta
# On va cada cosa (les variables ARRANJAMENTS_* només són per a proves)
$Dades = if ($env:ARRANJAMENTS_DADES) { $env:ARRANJAMENTS_DADES } else { Join-Path $env:LOCALAPPDATA "Arranjaments" }
# GetFolderPath tria la carpeta Documents bona encara que OneDrive la moga (ací només hi haurà partitures)
$Treball = if ($env:ARRANJAMENTS_TREBALL) { $env:ARRANJAMENTS_TREBALL } else { Join-Path ([Environment]::GetFolderPath('MyDocuments')) "Arranjaments" }
$Bin = if ($env:ARRANJAMENTS_BIN) { $env:ARRANJAMENTS_BIN } else { Join-Path $env:USERPROFILE ".local\bin" }
$Ordre = Join-Path $Bin "partitures.cmd"
$PythonEines = Join-Path $Dades ".venv\Scripts\python.exe"
$script:Falls = 0
# Avisos de progrés per a l'instal·lador visual (només amb ARRANJAMENTS_PROGRES): IniciPas nom ... FiPas
$script:PasId = ""; $script:PasMal = $false
$Visual = [bool]$env:ARRANJAMENTS_PROGRES
if ($Visual) { try { [Console]::OutputEncoding = New-Object Text.UTF8Encoding $false } catch { } }
function Progres($t) { if ($Visual) { Write-Host "@@$t" } }
function IniciPas($id) { $script:PasId = $id; $script:PasMal = $false; Progres "PAS $id inici" }
function FiPas { if ($script:PasMal) { Progres "PAS $($script:PasId) falla" } else { Progres "PAS $($script:PasId) ok" }; $script:PasId = "" }

function Pas($t)   { Write-Host ""; Write-Host "== $t ==" }
function Fet($t)   { Write-Host "  [fet]    $t" }
function Falta($t) { $script:PasMal = $true; Write-Host "  [falta]  $t" }
# fallada: no s'atura, però el resum final no dirà «Tot a punt»
function Fallada($t, $manual) {
    $script:Falls++
    Falta $t
    if ($manual) { Write-Host "           Fes-ho a mà: $manual" }
}
function ActualitzaPath {
    $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User') + ";$env:USERPROFILE\.local\bin"
}
# Vol(x): cal fer el pas x? (sense -Nomes, tots menys Audiveris)
function Vol($x) { if ($Nomes -eq "") { return ($x -ne "audiveris") } else { return ($Nomes -eq $x) } }
function EsAdmin {
    $p = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}
function TrobaOpenCode {
    $r = @(Get-ChildItem "$env:LOCALAPPDATA\Programs\*\OpenCode.exe" -ErrorAction SilentlyContinue)
    if ($r.Count -gt 0) { return $r[0].FullName }
    return $null
}
function TrobaMuseScore {
    @(Get-ChildItem "$env:ProgramFiles\MuseScore*\bin\MuseScore*.exe", "${env:ProgramFiles(x86)}\MuseScore*\bin\MuseScore*.exe", "$env:LOCALAPPDATA\Programs\MuseScore*\bin\MuseScore*.exe" -ErrorAction SilentlyContinue)
}
function TrobaAudiveris {
    @(Get-ChildItem "$env:ProgramFiles\Audiveris*\Audiveris*.exe", "$env:LOCALAPPDATA\Programs\Audiveris*\Audiveris*.exe", "$env:LOCALAPPDATA\Audiveris*\Audiveris*.exe" -ErrorAction SilentlyContinue)
}

# URL d'un fitxer de l'última versió d'un repositori de GitHub: primer l'API (amb clau si n'hi ha),
# i si està limitada, la pàgina pública de la versió.
function UrlGithub($repo, $patro) {
    $h = @{ "User-Agent" = "arranjaments" }
    if ($env:GITHUB_TOKEN) { $h["Authorization"] = "Bearer $env:GITHUB_TOKEN" }
    try {
        $rel = Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/releases/latest" -Headers $h
        $a = @($rel.assets | Where-Object { $_.name -match $patro })
        if ($a.Count -gt 0) { return $a[0].browser_download_url }
    } catch { }
    try {
        $fin = (Invoke-WebRequest -Uri "https://github.com/$repo/releases/latest" -Headers @{ "User-Agent" = "arranjaments" } -UseBasicParsing).BaseResponse.ResponseUri.AbsoluteUri
        $tag = $fin -replace '.*/tag/', ''
        $html = (Invoke-WebRequest -Uri "https://github.com/$repo/releases/expanded_assets/$tag" -Headers @{ "User-Agent" = "arranjaments" } -UseBasicParsing).Content
        $m = [regex]::Matches($html, 'href="([^"]+)"') | ForEach-Object { $_.Groups[1].Value } | Where-Object { $_ -match $patro }
        if ($m) { return "https://github.com" + @($m)[0] }
    } catch { }
    return $null
}

function Baixa($url, $desti) {
    Write-Host "  Baixant $(Split-Path $url -Leaf) (pot tardar uns minuts)..."
    try { Invoke-WebRequest -Uri $url -OutFile $desti -UseBasicParsing; return (Test-Path $desti) } catch { return $false }
}

# Instal·la un MSI oficial per a tots els usuaris. Si no som administrador, Windows demana permís (UAC).
function InstalMsi($url, $nom) {
    $msi = Join-Path $env:TEMP (Split-Path $url -Leaf)
    if (-not (Baixa $url $msi)) { return $false }
    $arg = "/i `"$msi`" /qn /norestart"
    try {
        if (EsAdmin) {
            $p = Start-Process msiexec.exe -ArgumentList $arg -Wait -PassThru
        } else {
            Write-Host "  $nom s'instal·la per a tots els usuaris de l'ordinador, per això Windows et demanarà permís"
            Write-Host "  d'administrador (finestra blava). Prem «Sí». Si no et deixa, consulta qui administra l'ordinador."
            $p = Start-Process msiexec.exe -ArgumentList $arg -Wait -PassThru -Verb RunAs
        }
        Remove-Item $msi -Force -ErrorAction SilentlyContinue
        return ($p.ExitCode -eq 0 -or $p.ExitCode -eq 3010)
    } catch {
        Write-Host "  No s'ha pogut fer la instal·lació ($($_.Exception.Message))."
        return $false
    }
}

# Copia les eines musicals (i el que cal per a reinstal·lar) a la carpeta de dades de l'aplicació.
# Si l'instal·lador ja s'executa des d'allí (ho fa l'ajudant amb «partitures instalar»), no cal copiar res.
function CopiaEines {
    try {
        New-Item -ItemType Directory -Force $Dades, (Join-Path $Dades "instalacio"), (Join-Path $Dades ".opencode") | Out-Null
        if ((Resolve-Path $Dades).Path -eq $Carpeta) { return $true }
        foreach ($vella in @((Join-Path $Dades "scripts"), (Join-Path $Dades ".opencode\skills"))) {
            if (Test-Path $vella) { Remove-Item $vella -Recurse -Force -ErrorAction Stop }
        }
        Copy-Item (Join-Path $Carpeta "scripts") (Join-Path $Dades "scripts") -Recurse -Force -ErrorAction Stop
        foreach ($f in @("pyproject.toml", "uv.lock", ".python-version", "VERSION", "AGENTS.md", "NOVETATS.md", "opencode.json")) {
            Copy-Item (Join-Path $Carpeta $f) (Join-Path $Dades $f) -Force -ErrorAction Stop
        }
        Copy-Item (Join-Path $Carpeta "instalacio\instalar-windows.ps1") (Join-Path $Dades "instalacio\instalar-windows.ps1") -Force -ErrorAction Stop
        Copy-Item (Join-Path $Carpeta ".opencode\skills") (Join-Path $Dades ".opencode\skills") -Recurse -Force -ErrorAction Stop
        Get-ChildItem (Join-Path $Dades "scripts") -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        # Els fitxers venen d'un ZIP baixat d'internet: es trau la marca perquè Windows no avise més endavant
        Get-ChildItem (Join-Path $Dades "scripts"), (Join-Path $Dades "instalacio"), (Join-Path $Dades ".opencode") -Recurse -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue
        return $true
    } catch { Write-Host "  $($_.Exception.Message)"; return $false }
}

# L'ordre «partitures»: un fitxer menut que crida les eines instal·lades, des de la carpeta on s'estiga.
function CreaOrdre {
    try {
        New-Item -ItemType Directory -Force $Bin | Out-Null
        # Amb la carpeta habitual s'escriu amb la variable de Windows, i així el fitxer no porta accents
        $python = if ($env:ARRANJAMENTS_DADES) { $PythonEines } else { '%LOCALAPPDATA%\Arranjaments\.venv\Scripts\python.exe' }
        $text = "@echo off`r`nrem Creat per l'instalador d'Arranjaments. Executa les eines musicals des de la carpeta on estas.`r`n`"$python`" -m partitures.cli %*`r`n"
        $oem = [Text.Encoding]::GetEncoding([Globalization.CultureInfo]::CurrentCulture.TextInfo.OEMCodePage)
        [IO.File]::WriteAllText($Ordre, $text, $oem)
        # Perquè l'ordre «partitures» es trobe sense escriure la ruta: la carpeta ha d'estar al PATH de la usuària
        if (-not $env:ARRANJAMENTS_BIN) {
            $cami = [Environment]::GetEnvironmentVariable('Path', 'User')
            if (-not $cami) { $cami = "" }
            if (($cami -split ';') -notcontains $Bin) {
                [Environment]::SetEnvironmentVariable('Path', ($cami.TrimEnd(';') + ';' + $Bin).TrimStart(';'), 'User')
            }
        }
        return $true
    } catch { Write-Host "  $($_.Exception.Message)"; return $false }
}

# La carpeta de treball. Només es renova la configuració amagada (.opencode): entrada\ i eixida\ no es toquen mai.
function PreparaCarpeta {
    try {
        $cfg = Join-Path $Treball ".opencode"
        New-Item -ItemType Directory -Force (Join-Path $Treball "entrada"), (Join-Path $Treball "eixida"), $cfg | Out-Null
        $skills = Join-Path $cfg "skills"
        if (Test-Path $skills) { Remove-Item $skills -Recurse -Force -ErrorAction Stop }
        Copy-Item (Join-Path $Carpeta ".opencode\skills") $skills -Recurse -Force -ErrorAction Stop
        Copy-Item (Join-Path $Carpeta "AGENTS.md") (Join-Path $cfg "AGENTS.md") -Force -ErrorAction Stop
        Copy-Item (Join-Path $Carpeta "NOVETATS.md") (Join-Path $cfg "NOVETATS.md") -Force -ErrorAction Stop
        # L'actualitzador sap així on és la carpeta de treball (UTF-8 sense BOM: el camí pot portar accents)
        New-Item -ItemType Directory -Force $Dades | Out-Null
        [IO.File]::WriteAllText((Join-Path $Dades "treball.txt"), $Treball + "`n", (New-Object Text.UTF8Encoding $false))
        Copy-Item (Join-Path $Carpeta "opencode.json") (Join-Path $cfg "opencode.json") -Force -ErrorAction Stop
        Get-ChildItem $cfg -Recurse -File -Force -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue
        # Amagada, perquè a la carpeta només es vegen entrada i eixida
        $d = Get-Item $cfg -Force
        $d.Attributes = $d.Attributes -bor [IO.FileAttributes]::Hidden
        return $true
    } catch { Write-Host "  $($_.Exception.Message)"; return $false }
}

if ($Prova) { Write-Host "Mode prova: només es comprova què hi ha instal·lat, no es canvia res." }
ActualitzaPath

# ---------------------------------------------------------------- 1. uv
if (Vol "uv") {
IniciPas "uv"; Pas "1. uv (prepara les eines musicals)"
if (Get-Command uv -ErrorAction SilentlyContinue) { Fet "uv ja està instal·lat" }
elseif ($Prova) { Falta "uv" }
else {
    Write-Host "  Instal·lant uv (instal·lador oficial d'astral.sh)..."
    # (es neteja PSModulePath per si l'instal·lador es llança des de PowerShell 7, que trenca el Windows PowerShell fill)
    powershell -NoProfile -ExecutionPolicy ByPass -c "`$env:PSModulePath = [Environment]::GetEnvironmentVariable('PSModulePath','Machine'); irm https://astral.sh/uv/install.ps1 | iex"
    ActualitzaPath
    if (Get-Command uv -ErrorAction SilentlyContinue) { Fet "uv instal·lat a $env:USERPROFILE\.local\bin\uv.exe" }
    else { Fallada "No s'ha pogut instal·lar uv." "https://docs.astral.sh/uv/getting-started/installation/" }
}
FiPas
}

# ---------------------------------------------------------------- 2. OpenCode
if (Vol "opencode") {
IniciPas "opencode"; Pas "2. OpenCode (l'aplicació amb la qual parles amb l'ajudant)"
if (TrobaOpenCode) { Fet "OpenCode ja està instal·lat" }
elseif ($Prova) { Falta "OpenCode" }
else {
    # Instal·lador NSIS d'un sol clic, per a la usuària actual: /S és silenciós i no demana administrador.
    $exe = Join-Path $env:TEMP "opencode-desktop-win-x64.exe"
    if (Baixa "https://opencode.ai/update/api/latest/desktop/opencode/opencode-desktop-win-x64.exe" $exe) {
        Write-Host "  Instal·lant OpenCode..."
        $p = Start-Process $exe -ArgumentList "/S" -Wait -PassThru
        Remove-Item $exe -Force -ErrorAction SilentlyContinue
        if (TrobaOpenCode) { Fet "OpenCode instal·lat" }
        else { Fallada "No he pogut instal·lar OpenCode automàticament." "https://opencode.ai/download (baixa la versió per a Windows i fes-hi doble clic)" }
    } else { Fallada "No he pogut baixar OpenCode (sense internet?)." "https://opencode.ai/download (baixa la versió per a Windows i fes-hi doble clic)" }
}
FiPas
}

# ---------------------------------------------------------------- 3. MuseScore
if (Vol "musescore") {
IniciPas "musescore"; Pas "3. MuseScore (revisar partitures i fer PDF)"
if ($env:MUSESCORE_PATH -or (TrobaMuseScore).Count -gt 0) { Fet "MuseScore ja està instal·lat" }
elseif ($Prova) { Falta "MuseScore 4" }
else {
    Write-Host "  Buscant l'última versió..."
    $url = UrlGithub "musescore/MuseScore" '-x86_64\.msi$'
    if ($url -and (InstalMsi $url "MuseScore") -and (TrobaMuseScore).Count -gt 0) { Fet "MuseScore instal·lat (sense MuseHub)" }
    else { Fallada "No he pogut instal·lar MuseScore automàticament." "https://musescore.org/ca/download (opció «sense MuseHub»)" }
}
FiPas
}

# ---------------------------------------------------------------- 4. Audiveris (només a demanda)
if (Vol "audiveris") {
IniciPas "audiveris"; Pas "4. Audiveris (convertir PDF en partitura; porta Java inclòs)"
if ($env:AUDIVERIS_PATH -or (TrobaAudiveris).Count -gt 0) { Fet "Audiveris ja està instal·lat" }
elseif ($Prova) { Falta "Audiveris" }
else {
    $url = UrlGithub "Audiveris/audiveris" 'windows-x86_64\.msi$'
    if ($url -and (InstalMsi $url "Audiveris") -and (TrobaAudiveris).Count -gt 0) { Fet "Audiveris instal·lat" }
    else { Fallada "No he pogut instal·lar Audiveris automàticament." "https://github.com/Audiveris/audiveris/releases (fitxer windows-x86_64.msi)" }
}
FiPas
}

# ---------------------------------------------------------------- 5. Eines musicals
if ((Vol "eines") -or (Vol "uv")) {
IniciPas "eines"; Pas "5. Eines musicals (a la carpeta de dades de l'aplicació)"
if ($Prova) { if ((Test-Path $Ordre) -and (Test-Path $PythonEines)) { Fet "eines musicals instal·lades" } else { Falta "eines musicals" } }
elseif (-not (Get-Command uv -ErrorAction SilentlyContinue)) { Fallada "No es poden preparar les eines musicals: falta uv." }
elseif (-not (CopiaEines)) { Fallada "No he pogut copiar les eines musicals a $Dades." }
else {
    Push-Location $Dades
    uv sync --frozen --no-dev
    $codiSync = $LASTEXITCODE
    Pop-Location
    if ($codiSync -ne 0) { Fallada "Ha fallat la preparació de les eines musicals. Comprova internet i torna-ho a provar." }
    elseif (-not (CreaOrdre)) { Fallada "No he pogut crear l'ordre «partitures» a $Bin." }
    else { Fet "eines musicals preparades (ordre: $Ordre)" }
}
FiPas
}

# ---------------------------------------------------------------- 6. Carpeta de treball
if (Vol "carpeta") {
IniciPas "carpeta"; Pas "6. Carpeta de treball: $Treball"
if ($Prova) {
    if ((Test-Path (Join-Path $Treball "entrada")) -and (Test-Path (Join-Path $Treball "eixida")) -and (Test-Path (Join-Path $Treball ".opencode\opencode.json"))) { Fet "la carpeta de treball ja hi és" } else { Falta "carpeta de treball" }
}
elseif (PreparaCarpeta) { Fet "carpeta de treball preparada (les teues partitures no s'han tocat)" }
else { Fallada "No he pogut preparar la carpeta de treball $Treball." }
FiPas
}

# ---------------------------------------------------------------- 7. Icona «Arranjaments» a l'Escriptori
if ((Vol "icona") -or (Vol "opencode")) {
IniciPas "icona"; Pas "7. Icona «Arranjaments» a l'Escriptori"
# GetFolderPath tria l'Escriptori bo encara que OneDrive el moga a una altra carpeta
$escriptori = [Environment]::GetFolderPath('Desktop')
$lnk = Join-Path $escriptori "Arranjaments.lnk"
$oc = TrobaOpenCode
if ($Prova) { if (Test-Path $lnk) { Fet "la icona ja hi és" } else { Falta "icona Arranjaments" } }
elseif (-not $oc) { Fallada "No es pot crear la icona: falta OpenCode." }
else {
    try {
        $sh = New-Object -ComObject WScript.Shell
        $d = $sh.CreateShortcut($lnk)
        # La icona obri un Python sense finestra que busca novetats (sense internet o si falla, no es nota) i després obri OpenCode
        $pyw = Join-Path $Dades ".venv\Scripts\pythonw.exe"
        if (Test-Path $pyw) {
            $d.TargetPath = $pyw
            $d.Arguments = "-I -m partitures.actualitzar --silenci --obri `"$oc`""
        } else { $d.TargetPath = $oc }
        if (Test-Path $Treball) { $d.WorkingDirectory = $Treball }
        $d.IconLocation = "$oc,0"
        $d.Description = "Arranjaments: obri OpenCode"
        $d.Save()
        Fet "icona creada: $lnk"
    } catch { Fallada "No he pogut crear la icona a l'Escriptori ($($_.Exception.Message))." "obri OpenCode des del menú Inici" }
}
FiPas
}

# ---------------------------------------------------------------- Comprovació final
IniciPas "final"; Pas "Comprovació final"
# Amb -Nomes només s'informa (la resta potser encara no toca); sense -Nomes compta per al resum.
# Es fa des de la carpeta de treball i amb l'ordre «partitures», com ho farà l'ajudant.
if ((Test-Path $Ordre) -and (Test-Path $Treball)) {
    Push-Location $Treball
    & $Ordre comprovar
    $codiFinal = $LASTEXITCODE
    Pop-Location
    if ($codiFinal -ne 0 -and $Nomes -eq "") { $script:Falls++; $script:PasMal = $true }
} else { Falta "les eines musicals encara no estan instal·lades"; if ($Nomes -eq "") { $script:Falls++ } }
FiPas
if ($script:Falls -eq 0) { Progres "FI ok" } else { Progres "FI falla $($script:Falls)" }

Write-Host ""
if ($Prova -or $Nomes -ne "") { Write-Host "Fet." }
elseif ($script:Falls -eq 0) {
    Write-Host "=============================================="
    Write-Host " Tot a punt."
    Write-Host " Obri la icona «Arranjaments» de l'Escriptori."
    Write-Host " La teua carpeta de treball: $Treball"
    Write-Host "=============================================="
} else {
    Write-Host "Hi ha $($script:Falls) cosa(es) que no s'han pogut fer (mira els avisos [falta] de dalt)."
    Write-Host "Pots tornar a executar este instal·lador: només fa el que falta."
}
if ($Prova -or $Nomes -ne "") { exit 0 }
if ($script:Falls -gt 0) { exit 1 } else { exit 0 }
