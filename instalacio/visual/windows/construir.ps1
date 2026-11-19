# Construeix «Instal·lar Arranjaments.exe» amb el compilador de C# que ja porta Windows (.NET Framework 4.8).
# No cal instal·lar res. Ús: powershell -ExecutionPolicy Bypass -File "instalacio\visual\windows\construir.ps1" [carpeta d'eixida]
# El resultat és un .exe menut (unes desenes de KB) que funciona a Windows 10 i 11 (també a Windows 11 ARM, on corre
# de forma nativa amb .NET Framework 4.8.1) sense cap instal·lació prèvia. «Arranjaments-Windows.exe» és este mateix .exe amb el
# projecte enganxat al final (vegeu ../paquets.py).
param([string]$Eixida = (Join-Path $env:TEMP "arranjaments-visual"))
$ErrorActionPreference = "Stop"
$aci = $PSScriptRoot
New-Item -ItemType Directory -Force $Eixida | Out-Null
$csc = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path $csc)) { $csc = Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319\csc.exe" }
if (-not (Test-Path $csc)) { throw "No trobe el compilador de C# de .NET Framework (csc.exe)." }
$provisional = Join-Path $Eixida "InstalarArranjaments.exe"
$icona = Join-Path $aci "..\icona\Arranjaments.ico"
& $csc /nologo /target:winexe /platform:anycpu /optimize+ /codepage:65001 /utf8output `
    "/out:$provisional" "/win32icon:$icona" "/win32manifest:$(Join-Path $aci 'app.manifest')" `
    "/resource:$icona,Arranjaments.ico" /reference:System.dll /reference:System.Drawing.dll /reference:System.Windows.Forms.dll /reference:System.IO.Compression.dll `
    (Join-Path $aci "InstalarArranjaments.cs")
if ($LASTEXITCODE -ne 0) { throw "La compilació ha fallat." }
# El nom definitiu porta un punt volat (U+00B7): s'escriu amb el seu codi perquè no depenga de la codificació d'este fitxer.
$final = Join-Path $Eixida ("Instal" + [char]0xB7 + "lar Arranjaments.exe")
Move-Item -Force $provisional $final
Write-Host $final
