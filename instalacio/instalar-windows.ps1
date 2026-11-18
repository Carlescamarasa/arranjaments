# Instal·lació per a Windows. Es pot repetir sense problema: només fa el que falta.
# - uv i OpenCode s'instal·len a la teua carpeta d'usuària: NO demanen permís d'administrador.
# - MuseScore (i Audiveris, si el demanes) s'instal·len per a tots els usuaris amb el seu instal·lador MSI:
#   Windows et demana permís d'administrador (finestra blava, UAC). Si l'ordinador no et deixa, consulta qui l'administra.
# Ús: powershell -ExecutionPolicy Bypass -File "instalacio\instalar-windows.ps1"             (tot el que falta, i la icona «Arranjaments» a l'Escriptori)
#     powershell -ExecutionPolicy Bypass -File "instalacio\instalar-windows.ps1" -Nomes uv    (només una cosa: uv, opencode, musescore, audiveris, icona)
#     powershell -ExecutionPolicy Bypass -File "instalacio\instalar-windows.ps1" -Prova      (només comprova)
#     ... -SensePreguntes   (no s'atura mai a esperar una tecla; per a proves)
# Audiveris NO s'instal·la si no el demanes amb -Nomes audiveris (només cal per a convertir PDF).
param([switch]$Prova, [switch]$SensePreguntes, [ValidateSet("", "uv", "opencode", "musescore", "audiveris", "icona")][string]$Nomes = "")

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$Carpeta = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Carpeta
$script:Falls = 0

function Pas($t)   { Write-Host ""; Write-Host "== $t ==" }
function Fet($t)   { Write-Host "  [fet]    $t" }
function Falta($t) { Write-Host "  [falta]  $t" }
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

if ($Prova) { Write-Host "Mode prova: només es comprova què hi ha instal·lat, no es canvia res." }
ActualitzaPath

# ---------------------------------------------------------------- 1. uv
if (Vol "uv") {
Pas "1. uv (prepara les eines musicals)"
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
}

# ---------------------------------------------------------------- 2. OpenCode
if (Vol "opencode") {
Pas "2. OpenCode (l'aplicació amb la qual parles amb l'ajudant)"
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
}

# ---------------------------------------------------------------- 3. MuseScore
if (Vol "musescore") {
Pas "3. MuseScore (revisar partitures i fer PDF)"
if ($env:MUSESCORE_PATH -or (TrobaMuseScore).Count -gt 0) { Fet "MuseScore ja està instal·lat" }
elseif ($Prova) { Falta "MuseScore 4" }
else {
    Write-Host "  Buscant l'última versió..."
    $url = UrlGithub "musescore/MuseScore" '-x86_64\.msi$'
    if ($url -and (InstalMsi $url "MuseScore") -and (TrobaMuseScore).Count -gt 0) { Fet "MuseScore instal·lat (sense MuseHub)" }
    else { Fallada "No he pogut instal·lar MuseScore automàticament." "https://musescore.org/ca/download (opció «sense MuseHub»)" }
}
}

# ---------------------------------------------------------------- 4. Audiveris (només a demanda)
if (Vol "audiveris") {
Pas "4. Audiveris (convertir PDF en partitura; porta Java inclòs)"
if ($env:AUDIVERIS_PATH -or (TrobaAudiveris).Count -gt 0) { Fet "Audiveris ja està instal·lat" }
elseif ($Prova) { Falta "Audiveris" }
else {
    $url = UrlGithub "Audiveris/audiveris" 'windows-x86_64\.msi$'
    if ($url -and (InstalMsi $url "Audiveris") -and (TrobaAudiveris).Count -gt 0) { Fet "Audiveris instal·lat" }
    else { Fallada "No he pogut instal·lar Audiveris automàticament." "https://github.com/Audiveris/audiveris/releases (fitxer windows-x86_64.msi)" }
}
}

# ---------------------------------------------------------------- 5. Eines musicals
if (Vol "uv") {
Pas "5. Eines musicals d'este projecte"
if ($Prova) { Falta "uv sync (no es fa en mode prova)" }
elseif (Get-Command uv -ErrorAction SilentlyContinue) {
    uv sync
    if ($LASTEXITCODE -eq 0) { Fet "eines musicals preparades" } else { Fallada "Ha fallat «uv sync». Comprova internet i torna-ho a provar." }
}
}

# ---------------------------------------------------------------- 6. Icona «Arranjaments» a l'Escriptori
if ((Vol "icona") -or (Vol "opencode")) {
Pas "6. Icona «Arranjaments» a l'Escriptori"
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
        $d.TargetPath = $oc
        $d.WorkingDirectory = $Carpeta
        $d.IconLocation = "$oc,0"
        $d.Description = "Arranjaments: obri OpenCode"
        $d.Save()
        Fet "icona creada: $lnk"
    } catch { Fallada "No he pogut crear la icona a l'Escriptori ($($_.Exception.Message))." "obri OpenCode des del menú Inici" }
}
}

# ---------------------------------------------------------------- Comprovació final
Pas "Comprovació final"
# Amb -Nomes només s'informa (la resta potser encara no toca); sense -Nomes compta per al resum.
if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv run partitures comprovar
    if ($LASTEXITCODE -ne 0 -and $Nomes -eq "") { $script:Falls++ }
} else { Falta "uv no disponible (hauria d'estar a $env:USERPROFILE\.local\bin\uv.exe)"; if ($Nomes -eq "") { $script:Falls++ } }

Write-Host ""
if ($Prova -or $Nomes -ne "") { Write-Host "Fet." }
elseif ($script:Falls -eq 0) {
    Write-Host "=============================================="
    Write-Host " Tot a punt."
    Write-Host " Obri la icona «Arranjaments» de l'Escriptori."
    Write-Host "=============================================="
} else {
    Write-Host "Hi ha $($script:Falls) cosa(es) que no s'han pogut fer (mira els avisos [falta] de dalt)."
    Write-Host "Pots tornar a executar este instal·lador: només fa el que falta."
}
if ($Prova -or $Nomes -ne "") { exit 0 }
if ($script:Falls -gt 0) { exit 1 } else { exit 0 }
