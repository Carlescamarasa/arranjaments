# Instal·lació per a Windows. Es pot repetir sense problema: només fa el que falta.
# Fa servir winget (ve amb Windows 10/11). Windows et demanarà permís (finestra blava): accepta.
# Ús: powershell -ExecutionPolicy Bypass -File "instal·lar\instalar-windows.ps1"   (o amb -Prova)
param([switch]$Prova)

$ErrorActionPreference = "Continue"
$Carpeta = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Carpeta

function Pas($t)   { Write-Host ""; Write-Host "== $t ==" }
function Fet($t)   { Write-Host "  [fet]    $t" }
function Falta($t) { Write-Host "  [falta]  $t" }
function ActualitzaPath {
    $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User') + ";$env:USERPROFILE\.local\bin"
}
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
}

Pas "1. uv (prepara les eines musicals)"
if (Get-Command uv -ErrorAction SilentlyContinue) { Fet "uv ja està instal·lat" }
elseif ($Prova) { Falta "uv" }
else {
    Write-Host "  Instal·lant uv (instal·lador oficial d'astral.sh)..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ActualitzaPath
    if (Get-Command uv -ErrorAction SilentlyContinue) { Fet "uv instal·lat" }
    else { Write-Host "  No s'ha pogut instal·lar uv. Tanca esta finestra, obri-la de nou i repeteix."; exit 1 }
}

Pas "2. MuseScore 4 (revisar partitures i fer PDF)"
$ms = @("$env:ProgramFiles\MuseScore 4\bin\MuseScore4.exe", "${env:ProgramFiles(x86)}\MuseScore 4\bin\MuseScore4.exe")
if ($env:MUSESCORE_PATH -or ($ms | Where-Object { Test-Path $_ })) { Fet "MuseScore 4 ja està instal·lat" }
elseif ($Prova) { Falta "MuseScore 4" }
else { InstalWinget "Musescore.Musescore" "MuseScore 4" "https://musescore.org/ca/download" }

Pas "3. Audiveris (convertir PDF en partitura; porta Java inclòs)"
$av = @(Get-ChildItem "$env:ProgramFiles\Audiveris*\Audiveris*.exe" -ErrorAction SilentlyContinue)
if ($env:AUDIVERIS_PATH -or $av.Count -gt 0) { Fet "Audiveris ja està instal·lat" }
elseif ($Prova) { Falta "Audiveris" }
else { InstalWinget "audiveris.org.Audiveris" "Audiveris" "https://github.com/Audiveris/audiveris/releases (fitxer windows-x86_64.msi)" }

Pas "4. Eines musicals d'este projecte"
if ($Prova) { Falta "uv sync (no es fa en mode prova)" }
elseif (Get-Command uv -ErrorAction SilentlyContinue) {
    uv sync
    if ($LASTEXITCODE -eq 0) { Fet "eines musicals preparades" } else { Write-Host "  Ha fallat «uv sync». Comprova internet i torna-ho a provar." }
}

Pas "5. Comprovació final"
if (Get-Command uv -ErrorAction SilentlyContinue) { uv run partitures comprovar } else { Falta "uv no disponible: tanca esta finestra, obri-la de nou i repeteix" }
