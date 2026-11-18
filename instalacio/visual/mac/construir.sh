#!/usr/bin/env bash
# Construeix «Instal·lar Arranjaments.app» (universal: Apple Silicon i Intel) amb swiftc, sense Xcode.
# Ús: bash "instalacio/visual/mac/construir.sh" [carpeta d'eixida]   (per defecte, una carpeta temporal que s'escriu al final)
# L'aplicació no va signada per cap empresa (signatura «ad hoc»): a GitHub es construeix sola i es publica dins del ZIP.
set -euo pipefail
ACI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EIXIDA="${1:-$(mktemp -d)}"
mkdir -p "$EIXIDA"
APP="$EIXIDA/Instal·lar Arranjaments.app"
TMP="$(mktemp -d)"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
for arq in arm64 x86_64; do
  swiftc -O -swift-version 5 -target "$arq-apple-macos12.0" -o "$TMP/instalar-$arq" "$ACI/InstalarArranjaments.swift"
done
lipo -create -output "$APP/Contents/MacOS/InstalarArranjaments" "$TMP/instalar-arm64" "$TMP/instalar-x86_64"
cp "$ACI/Info.plist" "$APP/Contents/Info.plist"
cp "$ACI/../icona/Arranjaments.icns" "$APP/Contents/Resources/Arranjaments.icns"
printf 'APPL????' > "$APP/Contents/PkgInfo"
codesign --force --sign - "$APP"
codesign --verify --strict "$APP"
rm -rf "$TMP"
lipo -archs "$APP/Contents/MacOS/InstalarArranjaments"
echo "$APP"
