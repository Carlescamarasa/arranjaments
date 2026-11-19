#!/usr/bin/env bash
# Fa «Arranjaments-Mac.dmg»: el DMG que baixa la professora. Dins hi ha només «Instal·lar Arranjaments.app», amb el projecte
# complet a dins de l'aplicació (Contents/Resources/projecte.tar.gz), de manera que no cal baixar ni descomprimir res més.
# Ús: bash instalacio/visual/mac/fes-dmg.sh "Instal·lar Arranjaments.app" projecte.tar.gz Arranjaments-Mac.dmg
# Cal macOS (hdiutil i codesign). L'aplicació de partida no s'ha de tocar: es treballa amb una còpia.
set -euo pipefail
APP_ORIGEN="$1"; PROJECTE="$2"; DMG="$3"
test -d "$APP_ORIGEN" && test -s "$PROJECTE"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
VOLUM="$TMP/volum"
mkdir -p "$VOLUM"
APP="$VOLUM/Instal·lar Arranjaments.app"
ditto "$APP_ORIGEN" "$APP"
cp "$PROJECTE" "$APP/Contents/Resources/projecte.tar.gz"
# Afegir un fitxer trenca la signatura de l'aplicació: se signa de nou (signatura «ad hoc», sense cap empresa)
codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict "$APP"
rm -f "$DMG"
hdiutil create -quiet -volname "Arranjaments" -srcfolder "$VOLUM" -fs HFS+ -format UDZO -imagekey zlib-level=9 -ov "$DMG"
hdiutil verify -quiet "$DMG"
echo "$DMG"
