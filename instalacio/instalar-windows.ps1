# Instal·lació per a Windows. Es pot repetir sense problema: només fa el que falta.
# Fa servir winget (ve amb Windows 10/11). MuseScore i Audiveris es desen per a tots els usuaris:
# Windows demana permís d'administrador (finestra blava, UAC). Si l'ordinador no et deixa, consulta qui l'administra.
# uv s'instal·la a la teua carpeta d'usuària i no demana permís.
# Ús: powershell -ExecutionPolicy Bypass -File "instalacio\instalar-windows.ps1"             (tot el que falta)
#     powershell -ExecutionPolicy Bypass -File "instalacio\instalar-windows.ps1" -Nomes uv    (només una cosa: uv, musescore, audiveris)
#     powershell -ExecutionPolicy Bypass -File "instalacio\instalar-windows.ps1" -Prova      (només comprova)
param([switch]$Prova, [ValidateSet("", "uv", "musescore", "audiveris")][string]$Nomes = "")

$ErrorActionPreference = "Continue"
$Carpeta = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Carpeta

function Pas($t)   { Write-Host ""; Write-Host "== $t ==" }
function Fet($t)   { Write-Host "  [fet]    $t" }
function Falta($t) { Write-Host "  [falta]  $t" }
function ActualitzaPath {
    $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User') + ";$env:USERPROFILE\.local\bin"
}
function Vol($x) { return ($Nomes -eq "" -or $Nomes -eq $x) }
$TeWinget = [bool](Get-Command winget -ErrorAction SilentlyContinue)
ActualitzaPath

if ($Prova) { Write-Host "Mode prova: només es comprova què hi ha instal·lat, no es canvia res." }

function InstalWinget($id, $nom, $urlManual) {
    if (-not $TeWinget) {
        Falta "No tens winget. Instal·la $nom a mà: $urlManual"
        return
    }
    Write-Host "  Instal·lant $nom (pot tardar uns minuts; accepta la finestra de permís de Windows)..."
    winget install --id $id -e --accept-package-agreements --accept-source-agreements
    ActualitzaPath
    if ($LASTEXITCODE -ne 0) { Falta "No he pogut instal·lar $nom automàticament. Fes-ho a mà: $urlManual" }
    else { Fet "$nom instal·lat" }
}

if (Vol "uv") {
Pas "1. uv (prepara les eines musicals)"
if (Get-Command uv -ErrorAction SilentlyContinue) { Fet "uv ja està instal·lat" }
elseif ($Prova) { Falta "uv" }
else {
    Write-Host "  Instal·lant uv (instal·lador oficial d'astral.sh)..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ActualitzaPath
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Fet "uv instal·lat a $env:USERPROFILE\.local\bin\uv.exe"
        Write-Host "  Si OpenCode no el troba encara, crida'l amb la ruta completa (no cal reiniciar): & `"$env:USERPROFILE\.local\bin\uv.exe`" run partitures comprovar"
    }
    else { Write-Host "  No s'ha pogut instal·lar uv. Tanca esta finestra, obri-la de nou i repeteix."; exit 1 }
}
}

if (Vol "musescore") {
Pas "2. MuseScore (revisar partitures i fer PDF)"
$ms = @(Get-ChildItem "$env:ProgramFiles\MuseScore*\bin\MuseScore*.exe", "${env:ProgramFiles(x86)}\MuseScore*\bin\MuseScore*.exe", "$env:LOCALAPPDATA\Programs\MuseScore*\bin\MuseScore*.exe" -ErrorAction SilentlyContinue)
if ($env:MUSESCORE_PATH -or $ms.Count -gt 0) { Fet "MuseScore ja està instal·lat" }
elseif ($Prova) { Falta "MuseScore 4" }
else { InstalWinget "Musescore.Musescore" "MuseScore" "https://musescore.org/ca/download (tria l'opció «sense MuseHub»)" }
}

if (Vol "audiveris") {
Pas "3. Audiveris (convertir PDF en partitura; porta Java inclòs)"
$av = @(Get-ChildItem "$env:ProgramFiles\Audiveris*\Audiveris*.exe", "$env:LOCALAPPDATA\Programs\Audiveris*\Audiveris*.exe", "$env:LOCALAPPDATA\Audiveris*\Audiveris*.exe" -ErrorAction SilentlyContinue)
if ($env:AUDIVERIS_PATH -or $av.Count -gt 0) { Fet "Audiveris ja està instal·lat" }
elseif ($Prova) { Falta "Audiveris" }
else { InstalWinget "audiveris.org.Audiveris" "Audiveris" "https://github.com/Audiveris/audiveris/releases (fitxer windows-x86_64.msi)" }
}

if ((Vol "uv")) {
Pas "4. Eines musicals d'este projecte"
if ($Prova) { Falta "uv sync (no es fa en mode prova)" }
elseif (Get-Command uv -ErrorAction SilentlyContinue) {
    uv sync
    if ($LASTEXITCODE -eq 0) { Fet "eines musicals preparades" } else { Write-Host "  Ha fallat «uv sync». Comprova internet i torna-ho a provar." }
}
}

Pas "5. Comprovació final"
if (Get-Command uv -ErrorAction SilentlyContinue) { uv run partitures comprovar; if ($LASTEXITCODE -eq 0) { Write-Host "Instal·lació acabada: tot a punt." } } else { Falta "uv no disponible (hauria d'estar a $env:USERPROFILE\.local\bin\uv.exe)" }
