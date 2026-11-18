#!/usr/bin/env bash
# Instal·lació per a Mac. Es pot repetir sense problema: només fa el que falta.
# No cal Homebrew ni contrasenya: baixa els instal·ladors oficials amb curl (sense quarantena)
# i copia les aplicacions a ~/Applications (la carpeta Aplicacions de la teua usuària).
# Ús: bash "instalacio/instalar-mac.sh"                 (tot el que falta, i la icona «Arranjaments» a l'Escriptori)
#     bash "instalacio/instalar-mac.sh" --nomes uv      (només una cosa: uv, opencode, musescore, audiveris, icona)
#     bash "instalacio/instalar-mac.sh" --prova         (només comprova, no canvia res)
#     bash "instalacio/instalar-mac.sh" --sense-preguntes   (no s'atura mai a esperar una tecla; per a proves)
# Audiveris NO s'instal·la si no el demanes amb --nomes audiveris (només cal per a convertir PDF).
set -u

CARPETA="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$CARPETA" || exit 1
export PATH="$HOME/.local/bin:$PATH"

PROVA=0
NOMES=""
while [ $# -gt 0 ]; do
  case "$1" in
    --prova) PROVA=1 ;;
    --sense-preguntes) ;;
    --nomes) shift; NOMES="${1:-}" ;;
  esac
  shift
done
case "$NOMES" in ""|uv|opencode|musescore|audiveris|icona) ;; *) echo "Opció --nomes desconeguda: $NOMES (usa uv, opencode, musescore, audiveris o icona)"; exit 1 ;; esac
# vol X: diu si cal fer el pas X (sense --nomes, tots menys Audiveris)
vol() { if [ -z "$NOMES" ]; then [ "$1" != audiveris ]; else [ "$NOMES" = "$1" ]; fi; }

# Resum final: llista del que ha anat bé i del que cal fer a mà
FALLS=0
ok()    { printf '  [fet]    %s\n' "$1"; }
falta() { printf '  [falta]  %s\n' "$1"; }
pas()   { printf '\n== %s ==\n' "$1"; }
# fallada: no s'atura, però el resum final no dirà «Tot a punt»
fallada() { FALLS=$((FALLS + 1)); falta "$1"; [ -n "${2:-}" ] && printf '           Fes-ho a mà: %s\n' "$2"; return 0; }

if [ "$(sysctl -n hw.optional.arm64 2>/dev/null)" = 1 ]; then APPLE_SILICI=1; else APPLE_SILICI=0; fi

# Troba una aplicació ja instal·lada: $1 = patró del nom (p. ex. OpenCode.app). Escriu la ruta.
troba_app() {
  local d
  for d in "$HOME/Applications" /Applications; do
    ls -d "$d"/$1 2>/dev/null | sort -r | head -1 | grep . && return 0
  done
  return 1
}

# URL d'un fitxer de l'última versió d'un repositori de GitHub. $1 = propietari/nom, $2 = patró (grep -E)
# Primer l'API (amb clau si n'hi ha); si està limitada, la pàgina pública de la versió.
url_github() {
  local repo="$1" patro="$2" url tag auth=()
  [ -n "${GITHUB_TOKEN:-}" ] && auth=(-H "Authorization: Bearer $GITHUB_TOKEN")
  url=$(curl -fsSL "${auth[@]}" "https://api.github.com/repos/$repo/releases/latest" 2>/dev/null \
        | grep -o '"browser_download_url": *"[^"]*"' | sed 's/.*: *"//; s/"$//' | grep -E "$patro" | head -1)
  if [ -z "$url" ]; then
    tag=$(curl -fsSLI -o /dev/null -w '%{url_effective}' "https://github.com/$repo/releases/latest" 2>/dev/null | sed 's#.*/tag/##')
    [ -n "$tag" ] && url=$(curl -fsSL "https://github.com/$repo/releases/expanded_assets/$tag" 2>/dev/null \
        | grep -o 'href="[^"]*"' | sed 's/href="//; s/"$//' | grep -E "$patro" | head -1 | sed 's#^/#https://github.com/#')
  fi
  printf '%s' "$url"
}

# Baixa un .dmg i copia l'aplicació a ~/Applications. $1 = URL  $2 = nom de l'aplicació dins del dmg (patró)
# curl no marca el fitxer amb quarantena, així que Mac no mostra cap avís en obrir l'aplicació.
instal_dmg() {
  local url="$1" tmp punt app dest res
  tmp="$(mktemp -d)"
  echo "  Baixant $(basename "$url") (pot tardar uns minuts)..."
  curl -fL --progress-bar -o "$tmp/instalador.dmg" "$url" || { rm -rf "$tmp"; return 1; }
  punt="$tmp/volum"; mkdir -p "$punt"
  hdiutil attach -nobrowse -readonly -quiet -mountpoint "$punt" "$tmp/instalador.dmg" </dev/null || { rm -rf "$tmp"; return 1; }
  app=$(ls -d "$punt"/*.app 2>/dev/null | head -1)
  if [ -z "$app" ]; then echo "  No trobe cap aplicació dins de l'instal·lador."; hdiutil detach -quiet "$punt"; rm -rf "$tmp"; return 1; fi
  mkdir -p "$HOME/Applications"
  dest="$HOME/Applications/$(basename "$app")"
  rm -rf "$dest.nou"
  cp -R "$app" "$dest.nou" && mv "$dest.nou" "$dest"; res=$?
  hdiutil detach -quiet "$punt"; rm -rf "$tmp"
  return $res
}

[ "$PROVA" = 1 ] && echo "Mode prova: només es comprova què hi ha instal·lat, no es canvia res."

# ---------------------------------------------------------------- 1. uv
if vol uv; then
pas "1. uv (prepara les eines musicals)"
if command -v uv >/dev/null 2>&1; then ok "uv ja està instal·lat"
elif [ "$PROVA" = 1 ]; then falta "uv"
else
  echo "  Instal·lant uv (instal·lador oficial d'astral.sh)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  if command -v uv >/dev/null 2>&1; then
    ok "uv instal·lat a $HOME/.local/bin/uv"
  else fallada "No s'ha pogut instal·lar uv." "https://docs.astral.sh/uv/getting-started/installation/"; fi
fi
fi

# ---------------------------------------------------------------- 2. OpenCode
if vol opencode; then
pas "2. OpenCode (l'aplicació amb la qual parles amb l'ajudant)"
if troba_app "OpenCode.app" >/dev/null; then ok "OpenCode ja està instal·lat"
elif [ "$PROVA" = 1 ]; then falta "OpenCode"
else
  if [ "$APPLE_SILICI" = 1 ]; then ARQ=arm64; else ARQ=x64; fi
  if instal_dmg "https://opencode.ai/update/api/latest/desktop/opencode/opencode-desktop-mac-$ARQ.dmg"; then
    ok "OpenCode instal·lat (a ~/Applications)"
  else fallada "No he pogut instal·lar OpenCode automàticament." "https://opencode.ai/download (baixa la versió per a Mac $ARQ i arrossega OpenCode a Aplicacions)"; fi
fi
fi

# ---------------------------------------------------------------- 3. MuseScore
if vol musescore; then
pas "3. MuseScore (revisar partitures i fer PDF)"
if troba_app "MuseScore*.app" >/dev/null || [ -n "${MUSESCORE_PATH:-}" ]; then ok "MuseScore ja està instal·lat"
elif [ "$PROVA" = 1 ]; then falta "MuseScore 4"
else
  echo "  Buscant l'última versió..."
  URL=$(url_github "musescore/MuseScore" '\.dmg$')
  if [ -n "$URL" ] && instal_dmg "$URL"; then ok "MuseScore instal·lat (a ~/Applications, sense MuseHub)"
  else fallada "No he pogut instal·lar MuseScore automàticament." "https://musescore.org/ca/download (opció «sense MuseHub»; arrossega la icona a Aplicacions)"; fi
fi
fi

# ---------------------------------------------------------------- 4. Audiveris (només a demanda)
if vol audiveris; then
pas "4. Audiveris (convertir PDF en partitura; porta Java inclòs)"
if troba_app "Audiveris*.app" >/dev/null || [ -n "${AUDIVERIS_PATH:-}" ]; then ok "Audiveris ja està instal·lat"
elif [ "$PROVA" = 1 ]; then falta "Audiveris"
else
  if [ "$APPLE_SILICI" = 1 ]; then ARQ="macosx-arm64"; else ARQ="macosx-x86_64"; fi
  URL=$(url_github "Audiveris/audiveris" "$ARQ\\.dmg$")
  if [ -n "$URL" ] && instal_dmg "$URL"; then ok "Audiveris instal·lat"
  else fallada "No he pogut instal·lar Audiveris automàticament." "https://github.com/Audiveris/audiveris/releases (baixa el .dmg «$ARQ» i arrossega Audiveris a Aplicacions)"; fi
fi
fi

# ---------------------------------------------------------------- 5. Eines musicals
if vol uv; then
pas "5. Eines musicals d'este projecte"
if [ "$PROVA" = 1 ]; then falta "uv sync (no es fa en mode prova)"
elif command -v uv >/dev/null 2>&1; then
  if uv sync; then ok "eines musicals preparades"; else fallada "Ha fallat «uv sync». Comprova internet i torna-ho a provar."; fi
fi
fi

# ---------------------------------------------------------------- 6. Icona «Arranjaments» a l'Escriptori
if vol icona || vol opencode; then
pas "6. Icona «Arranjaments» a l'Escriptori"
ESCRIPTORI="$HOME/Desktop"
ICONA="$ESCRIPTORI/Arranjaments.app"
if [ "$PROVA" = 1 ]; then
  [ -d "$ICONA" ] && ok "la icona ja hi és" || falta "icona Arranjaments"
elif ! troba_app "OpenCode.app" >/dev/null; then
  fallada "No es pot crear la icona: falta OpenCode."
else
  # Es crea ací mateix, no es baixa: així Mac no la tracta com un programa baixat d'internet i no mostra avisos.
  # La ruta d'esta carpeta es guarda dins de la icona; si mous la carpeta, torna a executar l'instal·lador.
  TMP="$(mktemp -d)"
  CARPETA_AS="${CARPETA//\\/\\\\}"; CARPETA_AS="${CARPETA_AS//\"/\\\"}"
  cat > "$TMP/arranjaments.applescript" <<APPLESCRIPT
set carpeta to "$CARPETA_AS"
set rutes to {(POSIX path of (path to home folder)) & "Applications/OpenCode.app", "/Applications/OpenCode.app"}
set trobada to ""
repeat with r in rutes
	try
		do shell script "test -d " & quoted form of (r as text)
		set trobada to r as text
		exit repeat
	end try
end repeat
if trobada is "" then
	display dialog "No trobe OpenCode. Torna a executar Instalar-Mac.command (la carpeta d'Arranjaments)." buttons {"D'acord"} default button 1 with icon caution
else
	try
		do shell script "test -d " & quoted form of carpeta
	on error
		display dialog "La carpeta d'Arranjaments s'ha mogut. Torna a executar Instalar-Mac.command des de la nova ubicació i esta icona s'arreglarà." buttons {"D'acord"} default button 1 with icon caution
	end try
	do shell script "open " & quoted form of trobada
end if
APPLESCRIPT
  if osacompile -o "$TMP/Arranjaments.app" "$TMP/arranjaments.applescript" 2>/dev/null; then
    # La icona d'OpenCode, perquè es reconega a l'Escriptori
    APP="$(troba_app "OpenCode.app")"
    if [ -f "$APP/Contents/Resources/icon.icns" ]; then
      cp "$APP/Contents/Resources/icon.icns" "$TMP/Arranjaments.app/Contents/Resources/applet.icns"
      # macOS recent prefereix la icona genèrica del catàleg; la traiem perquè use la d'OpenCode
      /usr/libexec/PlistBuddy -c "Delete :CFBundleIconName" "$TMP/Arranjaments.app/Contents/Info.plist" >/dev/null 2>&1
      rm -f "$TMP/Arranjaments.app/Contents/Resources/Assets.car"
    fi
    codesign --force --sign - "$TMP/Arranjaments.app" >/dev/null 2>&1
    mkdir -p "$ESCRIPTORI"
    rm -rf "$ICONA"
    mv "$TMP/Arranjaments.app" "$ICONA" && ok "icona creada: $ICONA" || fallada "No he pogut crear la icona a l'Escriptori."
  else
    fallada "No he pogut crear la icona a l'Escriptori." "obri OpenCode des de la carpeta Aplicacions"
  fi
  rm -rf "$TMP"
fi
fi

# ---------------------------------------------------------------- Comprovació final
pas "Comprovació final"
# Amb --nomes només s'informa (la resta potser encara no toca); sense --nomes compta per al resum.
if command -v uv >/dev/null 2>&1; then
  if ! uv run partitures comprovar && [ -z "$NOMES" ]; then FALLS=$((FALLS + 1)); fi
else
  falta "uv no disponible (hauria d'estar a ~/.local/bin/uv)"; [ -z "$NOMES" ] && FALLS=$((FALLS + 1))
fi

echo
if [ "$PROVA" = 1 ] || [ -n "$NOMES" ]; then echo "Fet."
elif [ "$FALLS" = 0 ]; then
  echo "=============================================="
  echo " Tot a punt."
  echo " Obri la icona «Arranjaments» de l'Escriptori."
  echo "=============================================="
else
  echo "Hi ha $FALLS cosa(es) que no s'han pogut fer (mira els avisos [falta] de dalt)."
  echo "Pots tornar a executar este instal·lador: només fa el que falta."
fi
exit $(( FALLS > 0 ? 1 : 0 ))
