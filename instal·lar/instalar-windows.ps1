# Instal·lació per a Windows. Es pot repetir sense problema: només fa el que falta.
# Ús: clic dret sobre el fitxer, "Executa amb PowerShell".
# Si Windows ho bloqueja: obri PowerShell i escriu
#   powershell -ExecutionPolicy Bypass -File .\instalar-windows.ps1
param([switch]$Prova)

$ErrorActionPreference = "Continue"
$Carpeta = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Carpeta

function Pas($t)   { Write-Host ""; Write-Host "== $t ==" }
function Fet($t)   { Write-Host "  [fet]    $t" }
function Falta($t) { Write-Host "  [falta]  $t" }

if ($Prova) { Write-Host "Mode prova: només es comprova què hi ha instal·lat, no es canvia res." }

Pas "1. uv (el gestor que prepara les eines musicals)"
if (Get-Command uv -ErrorAction SilentlyContinue) {
    Fet "uv ja està instal·lat"
} elseif ($Prova) {
    Falta "uv no està instal·lat (s'instal·laria des d'astral.sh/uv)"
} else {
    Write-Host "  Instal·lant uv..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
    if (Get-Command uv -ErrorAction SilentlyContinue) { Fet "uv instal·lat" }
    else { Write-Host "  No s'ha pogut instal·lar uv. Tanca i torna a obrir esta finestra, o pregunta a algú de suport." ; exit 1 }
}

Pas "2. MuseScore 4 (per a revisar partitures i fer PDF)"
$ms = @("$env:ProgramFiles\MuseScore 4\bin\MuseScore4.exe", "${env:ProgramFiles(x86)}\MuseScore 4\bin\MuseScore4.exe")
if ($env:MUSESCORE_PATH -or ($ms | Where-Object { Test-Path $_ })) { Fet "MuseScore 4 trobat" }
else {
    Falta "MuseScore 4 no està instal·lat."
    Write-Host "  Baixa'l i instal·la'l (és gratuït) des de: https://musescore.org/ca/download"
}

Pas "3. Audiveris (per a convertir PDF en partitura editable)"
$av = @(Get-ChildItem "$env:ProgramFiles\Audiveris*\Audiveris*.exe" -ErrorAction SilentlyContinue)
if ($env:AUDIVERIS_PATH -or $av.Count -gt 0) { Fet "Audiveris trobat" }
else {
    Falta "Audiveris no està instal·lat (només cal si has de treballar amb PDF)."
    Write-Host "  Baixa l'instal·lador des de: https://github.com/Audiveris/audiveris/releases"
    Write-Host "  Tria el fitxer que acaba en «windows-x86_64.msi» (o el «windowsConsole», que mostra missatges a la finestra)."
}

Pas "4. OpenCode (l'ajudant)"
if (Get-Command opencode -ErrorAction SilentlyContinue) { Fet "OpenCode ja està instal·lat" }
else {
    Falta "OpenCode no està instal·lat."
    Write-Host "  Mira les instruccions per a Windows a https://opencode.ai (hi ha una ordre d'instal·lació d'una línia)."
}

Pas "5. Eines musicals del projecte"
if ($Prova) { Falta "no s'ha executat «uv sync» (mode prova)" }
elseif (Get-Command uv -ErrorAction SilentlyContinue) {
    uv sync
    if ($LASTEXITCODE -eq 0) { Fet "eines musicals preparades" } else { Write-Host "  Ha fallat «uv sync». Torna-ho a provar amb internet."; exit 1 }
}

Write-Host ""
Write-Host "Fet. Per a començar: obri PowerShell dins d'esta carpeta ($Carpeta) i escriu «opencode»."
