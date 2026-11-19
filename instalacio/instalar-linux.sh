#!/usr/bin/env bash
# Instal·lació per a Linux (LliureX i altres Ubuntu). Es pot repetir sense problema: només fa el que falta.
# No cal sudo ni contrasenya: tot va a la carpeta de la usuària.
# Les aplicacions (OpenCode i MuseScore) es baixen com a AppImage i es DESCOMPRIMEIXEN una vegada a la carpeta
# de dades: així no cal FUSE ni el paquet libfuse2 (que a Ubuntu 22.04 i 24.04 no ve instal·lat).
# Què deixa a l'ordinador:
#   - les eines musicals i les aplicacions: ~/.local/share/Arranjaments (o $XDG_DATA_HOME/Arranjaments)
#   - la carpeta de treball que veu la professora: Documents/Arranjaments (la carpeta Documents del sistema)
#   - l'ordre «partitures» a ~/.local/bin
#   - la icona «Arranjaments» al menú d'aplicacions i a l'Escriptori
# Ús: bash "instalacio/instalar-linux.sh"                 (tot el que falta)
#     bash "instalacio/instalar-linux.sh" --nomes uv      (només una cosa: uv, opencode, musescore, audiveris, eines, carpeta, icona)
#     bash "instalacio/instalar-linux.sh" --prova         (només comprova, no canvia res)
#     bash "instalacio/instalar-linux.sh" --sense-preguntes   (no s'atura mai a esperar una tecla; per a proves)
# Amb la variable d'entorn ARRANJAMENTS_PROGRES=1 s'escriuen també línies «@@PAS nom inici|ok|falla» i «@@FI ok|falla».
# Audiveris NO s'instal·la si no el demanes amb --nomes audiveris (només cal per a convertir PDF).
set -u

CARPETA="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$CARPETA" || exit 1
export PATH="$HOME/.local/bin:$PATH"

# Carpeta Documents i Escriptori del sistema (poden dir-se Documentos, Escritorio...). Si no n'hi ha cap, les de sempre.
carpeta_usuaria() {  # $1 = DOCUMENTS|DESKTOP, $2 = nom per defecte
  local r=""
  command -v xdg-user-dir >/dev/null 2>&1 && r="$(xdg-user-dir "$1" 2>/dev/null)"
  if [ -z "$r" ] || [ "$r" = "$HOME" ] || [ "$r" = "$HOME/" ]; then r="$HOME/$2"; fi
  printf '%s' "$r"
}
# On va cada cosa (les variables ARRANJAMENTS_* només són per a proves)
DADES="${ARRANJAMENTS_DADES:-${XDG_DATA_HOME:-$HOME/.local/share}/Arranjaments}"
TREBALL="${ARRANJAMENTS_TREBALL:-$(carpeta_usuaria DOCUMENTS Documents)/Arranjaments}"
ESCRIPTORI="${ARRANJAMENTS_ESCRIPTORI:-$(carpeta_usuaria DESKTOP Desktop)}"
MENU="${ARRANJAMENTS_MENU:-${XDG_DATA_HOME:-$HOME/.local/share}/applications}"
BIN="${ARRANJAMENTS_BIN:-$HOME/.local/bin}"
ORDRE="$BIN/partitures"

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
case "$NOMES" in ""|uv|opencode|musescore|audiveris|eines|carpeta|icona) ;; *) echo "Opció --nomes desconeguda: $NOMES (usa uv, opencode, musescore, audiveris, eines, carpeta o icona)"; exit 1 ;; esac
vol() { if [ -z "$NOMES" ]; then [ "$1" != audiveris ]; else [ "$NOMES" = "$1" ]; fi; }

FALLS=0
ok()    { printf '  [fet]    %s\n' "$1"; }
falta() { PAS_MAL=1; printf '  [falta]  %s\n' "$1"; }
pas()   { printf '\n== %s ==\n' "$1"; }
PAS_ID=""; PAS_MAL=0
progres()   { [ -n "${ARRANJAMENTS_PROGRES:-}" ] && printf '@@%s\n' "$1"; return 0; }
inici_pas() { PAS_ID="$1"; PAS_MAL=0; progres "PAS $1 inici"; }
fi_pas()    { if [ "$PAS_MAL" = 0 ]; then progres "PAS $PAS_ID ok"; else progres "PAS $PAS_ID falla"; fi; PAS_ID=""; }
fallada() { FALLS=$((FALLS + 1)); falta "$1"; [ -n "${2:-}" ] && printf '           Fes-ho a mà: %s\n' "$2"; return 0; }

case "$(uname -m)" in
  x86_64|amd64) ARQ=x86_64; ARQ_OC=x86_64 ;;
  aarch64|arm64) ARQ=aarch64; ARQ_OC=arm64 ;;
  *) ARQ=""; ARQ_OC="" ;;
esac

# Aplicacions ja instal·lades (la nostra, o una de la distribució)
troba_opencode() {
  if [ -x "$DADES/OpenCode/AppRun" ]; then printf '%s' "$DADES/OpenCode/AppRun"; return 0; fi
  command -v opencode-desktop 2>/dev/null
}
troba_musescore() {
  if [ -n "${MUSESCORE_PATH:-}" ]; then printf '%s' "$MUSESCORE_PATH"; return 0; fi
  if [ -x "$DADES/MuseScore/AppRun" ]; then printf '%s' "$DADES/MuseScore/AppRun"; return 0; fi
  local c
  for c in mscore musescore mscore4portable org.musescore.MuseScore; do command -v "$c" 2>/dev/null && return 0; done
  for c in "$HOME/.local/share/flatpak/exports/bin/org.musescore.MuseScore" /var/lib/flatpak/exports/bin/org.musescore.MuseScore; do
    [ -x "$c" ] && { printf '%s' "$c"; return 0; }
  done
  return 1
}

# URL d'un fitxer de l'última versió d'un repositori de GitHub. $1 = propietari/nom, $2 = patró (grep -E)
url_github() {
  local repo="$1" patro="$2" url tag auth=()
  [ -n "${GITHUB_TOKEN:-}" ] && auth=(-H "Authorization: Bearer $GITHUB_TOKEN")
  url=$(curl -fsSL "${auth[@]}" "https://api.github.com/repos/$repo/releases/latest" 2>/dev/null \
        | grep -o '"browser_download_url": *"[^"]*"' | sed 's/.*: *"//; s/"$//' | grep -E -e "$patro" | head -1)
  if [ -z "$url" ]; then
    tag=$(curl -fsSLI -o /dev/null -w '%{url_effective}' "https://github.com/$repo/releases/latest" 2>/dev/null | sed 's#.*/tag/##')
    [ -n "$tag" ] && url=$(curl -fsSL "https://github.com/$repo/releases/expanded_assets/$tag" 2>/dev/null \
        | grep -o 'href="[^"]*"' | sed 's/href="//; s/"$//' | grep -E -e "$patro" | head -1 | sed 's#^/#https://github.com/#')
  fi
  printf '%s' "$url"
}

# Baixa una AppImage i la descomprimeix a la carpeta $2 (sense FUSE). $1 = URL
# Es treballa dins de la carpeta de dades i no a /tmp, que de vegades no deixa executar programes.
instal_appimage() {
  local url="$1" dest="$2" tmp res
  mkdir -p "$DADES" || return 1
  tmp="$(mktemp -d "$DADES/.baixada.XXXXXX")" || return 1
  echo "  Baixant $(basename "$url") (pot tardar uns minuts)..."
  local barra=(-sS); [ -t 2 ] && barra=(--progress-bar)
  curl -fL "${barra[@]}" -o "$tmp/app.AppImage" "$url" || { rm -rf "$tmp"; return 1; }
  chmod +x "$tmp/app.AppImage"
  echo "  Preparant l'aplicació (es descomprimeix una sola vegada)..."
  (cd "$tmp" && ./app.AppImage --appimage-extract >/dev/null 2>"$tmp/error.txt") || { tail -3 "$tmp/error.txt"; rm -rf "$tmp"; return 1; }
  if [ ! -x "$tmp/squashfs-root/AppRun" ]; then echo "  L'AppImage no té el format esperat."; rm -rf "$tmp"; return 1; fi
  chmod -R u+rwX "$tmp/squashfs-root"
  rm -rf "$dest.nou"
  mv "$tmp/squashfs-root" "$dest.nou" && rm -rf "$dest" && mv "$dest.nou" "$dest"; res=$?
  rm -rf "$tmp"
  return $res
}

copia_eines() {
  [ "$CARPETA" -ef "$DADES" ] && return 0
  mkdir -p "$DADES/instalacio" "$DADES/.opencode" || return 1
  rm -rf "$DADES/scripts" "$DADES/.opencode/skills"
  cp -R "$CARPETA/scripts" "$DADES/scripts" \
    && cp "$CARPETA/pyproject.toml" "$CARPETA/uv.lock" "$CARPETA/.python-version" "$CARPETA/VERSION" "$CARPETA/AGENTS.md" "$CARPETA/NOVETATS.md" "$CARPETA/opencode.json" "$DADES/" \
    && cp "$CARPETA/instalacio/instalar-linux.sh" "$DADES/instalacio/" \
    && cp -R "$CARPETA/.opencode/skills" "$DADES/.opencode/skills" || return 1
  find "$DADES/scripts" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
  # L'actualitzador sap així on és la carpeta de treball
  printf '%s\n' "$TREBALL" > "$DADES/treball.txt"
  return 0
}

crea_ordre() {
  mkdir -p "$BIN" || return 1
  cat > "$ORDRE" <<ORDRE_FI
#!/bin/sh
# Creat per l'instal·lador d'Arranjaments. Executa les eines musicals des de la carpeta on estàs.
exec "$DADES/.venv/bin/python" -m partitures.cli "\$@"
ORDRE_FI
  chmod +x "$ORDRE"
}

[ "$PROVA" = 1 ] && echo "Mode prova: només es comprova què hi ha instal·lat, no es canvia res."
if [ "$(uname -s)" != Linux ]; then echo "Este instal·lador és només per a Linux."; exit 1; fi
if [ -z "$ARQ" ] && [ "$PROVA" = 0 ]; then echo "Arquitectura no suportada: $(uname -m)."; exit 1; fi
if [ "$PROVA" = 0 ] && ! command -v curl >/dev/null 2>&1; then
  echo "Falta el programa «curl». Una administradora ha d'executar: sudo apt install curl"; exit 1
fi

# ---------------------------------------------------------------- 1. uv
if vol uv; then
inici_pas uv; pas "1. Preparació (uv, el programa que prepara les eines musicals)"
if command -v uv >/dev/null 2>&1; then ok "uv ja està instal·lat"
elif [ "$PROVA" = 1 ]; then falta "uv"
else
  echo "  Instal·lant uv (instal·lador oficial d'astral.sh)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  if command -v uv >/dev/null 2>&1; then ok "uv instal·lat a $HOME/.local/bin/uv"
  else fallada "No s'ha pogut instal·lar uv." "https://docs.astral.sh/uv/getting-started/installation/"; fi
fi
fi_pas
fi

# ---------------------------------------------------------------- 2. OpenCode
if vol opencode; then
inici_pas opencode; pas "2. OpenCode (l'aplicació amb la qual parles amb l'ajudant)"
if troba_opencode >/dev/null; then ok "OpenCode ja està instal·lat"
elif [ "$PROVA" = 1 ]; then falta "OpenCode"
elif instal_appimage "https://opencode.ai/update/api/latest/desktop/opencode/opencode-desktop-linux-$ARQ_OC.AppImage" "$DADES/OpenCode"; then
  ok "OpenCode instal·lat (a $DADES/OpenCode)"
else fallada "No he pogut instal·lar OpenCode automàticament." "https://opencode.ai/download (baixa «Linux AppImage»)"; fi
fi_pas
fi

# ---------------------------------------------------------------- 3. MuseScore
if vol musescore; then
inici_pas musescore; pas "3. MuseScore (revisar partitures i fer PDF)"
if troba_musescore >/dev/null; then ok "MuseScore ja està instal·lat"
elif [ "$PROVA" = 1 ]; then falta "MuseScore 4"
else
  echo "  Buscant l'última versió..."
  URL=$(url_github "musescore/MuseScore" "-$ARQ\\.AppImage\$")
  if [ -n "$URL" ] && instal_appimage "$URL" "$DADES/MuseScore"; then ok "MuseScore instal·lat (a $DADES/MuseScore)"
  else fallada "No he pogut instal·lar MuseScore automàticament." "https://musescore.org/ca/download (baixa l'AppImage)"; fi
fi
fi_pas
fi

# ---------------------------------------------------------------- 4. Audiveris (només a demanda)
if vol audiveris; then
inici_pas audiveris; pas "4. Audiveris (convertir PDF en partitura)"
if command -v audiveris >/dev/null 2>&1 || [ -x /opt/audiveris/bin/Audiveris ] || [ -n "${AUDIVERIS_PATH:-}" ]; then ok "Audiveris ja està instal·lat"
elif [ "$PROVA" = 1 ]; then falta "Audiveris"
else fallada "A Linux, Audiveris no s'instal·la sol (el seu paquet necessita permisos d'administradora)." "https://github.com/Audiveris/audiveris/releases (paquet .deb per a Ubuntu)"; fi
fi_pas
fi

# ---------------------------------------------------------------- 5. Eines musicals
if vol eines || vol uv; then
inici_pas eines; pas "5. Eines musicals (a la carpeta de dades de l'aplicació)"
if [ "$PROVA" = 1 ]; then
  if [ -x "$ORDRE" ] && [ -x "$DADES/.venv/bin/python" ]; then ok "eines musicals instal·lades"; else falta "eines musicals"; fi
elif ! command -v uv >/dev/null 2>&1; then fallada "No es poden preparar les eines musicals: falta uv."
elif ! copia_eines; then fallada "No he pogut copiar les eines musicals a $DADES."
elif ! (cd "$DADES" && uv sync --frozen --no-dev); then fallada "Ha fallat la preparació de les eines musicals. Comprova internet i torna-ho a provar."
elif ! crea_ordre; then fallada "No he pogut crear l'ordre «partitures» a $BIN."
else ok "eines musicals preparades (ordre: $ORDRE)"
fi
fi_pas
fi

# ---------------------------------------------------------------- 6. Carpeta de treball
if vol carpeta; then
inici_pas carpeta; pas "6. Carpeta de treball: $TREBALL"
if [ "$PROVA" = 1 ]; then
  if [ -d "$TREBALL/entrada" ] && [ -d "$TREBALL/eixida" ] && [ -f "$TREBALL/.opencode/opencode.json" ]; then ok "la carpeta de treball ja hi és"; else falta "carpeta de treball"; fi
else
  # Només es renova la configuració amagada (.opencode). El que hi ha a entrada/ i eixida/ no es toca mai.
  if mkdir -p "$TREBALL/entrada" "$TREBALL/eixida" "$TREBALL/.opencode" \
     && rm -rf "$TREBALL/.opencode/skills" \
     && cp -R "$CARPETA/.opencode/skills" "$TREBALL/.opencode/skills" \
     && cp "$CARPETA/AGENTS.md" "$TREBALL/.opencode/AGENTS.md" \
     && cp "$CARPETA/NOVETATS.md" "$TREBALL/.opencode/NOVETATS.md" \
     && cp "$CARPETA/opencode.json" "$TREBALL/.opencode/opencode.json"; then
    ok "carpeta de treball preparada (les teues partitures no s'han tocat)"
  else fallada "No he pogut preparar la carpeta de treball $TREBALL."; fi
fi
fi_pas
fi

# ---------------------------------------------------------------- 7. Icona «Arranjaments» (menú i Escriptori)
if vol icona || vol opencode; then
inici_pas icona; pas "7. Icona «Arranjaments» (menú d'aplicacions i Escriptori)"
if [ "$PROVA" = 1 ]; then
  [ -f "$MENU/arranjaments.desktop" ] && ok "la icona ja hi és" || falta "icona Arranjaments"
elif ! OC="$(troba_opencode)" || [ -z "$OC" ]; then
  fallada "No es pot crear la icona: falta OpenCode."
else
  # Icona: la d'OpenCode, si l'AppImage en porta una
  ICONA_IMG=""
  for c in "$DADES"/OpenCode/*.png "$DADES"/OpenCode/usr/share/icons/hicolor/512x512/apps/*.png "$DADES"/OpenCode/usr/share/icons/hicolor/256x256/apps/*.png; do
    [ -f "$c" ] && { ICONA_IMG="$c"; break; }
  done
  [ -z "$ICONA_IMG" ] && ICONA_IMG="audio-x-generic"
  # Electron no pot usar el seu aïllament en algunes configuracions (Ubuntu 24.04): llavors cal --no-sandbox.
  # El llançador ho decideix cada vegada, sense preguntar res.
  LLANCADOR="$DADES/arranjaments-obrir.sh"
  cat > "$LLANCADOR" <<LLANCADOR_FI
#!/bin/sh
# Creat per l'instal·lador d'Arranjaments. Obri OpenCode des de la carpeta de treball.
cd "$TREBALL" 2>/dev/null || cd "\$HOME"
# Actualització silenciosa: si falla o no hi ha internet, no es nota res i s'obri OpenCode igualment
"$DADES/.venv/bin/python" -I -m partitures.actualitzar --silenci >/dev/null 2>&1 </dev/null || true
EXTRA=""
if [ "\$(cat /proc/sys/kernel/apparmor_restrict_unprivileged_userns 2>/dev/null)" = 1 ] \\
   || [ "\$(cat /proc/sys/kernel/unprivileged_userns_clone 2>/dev/null)" = 0 ]; then EXTRA="--no-sandbox"; fi
exec "$OC" \$EXTRA "\$@"
LLANCADOR_FI
  chmod +x "$LLANCADOR"
  ESCRIT="[Desktop Entry]
Type=Application
Version=1.0
Name=Arranjaments
Comment=Ajudant per a fer arranjaments de cambra
Exec=\"$LLANCADOR\"
Path=$TREBALL
Icon=$ICONA_IMG
Terminal=false
Categories=AudioVideo;Audio;Music;"
  if mkdir -p "$MENU" && printf '%s\n' "$ESCRIT" > "$MENU/arranjaments.desktop" && chmod +x "$MENU/arranjaments.desktop"; then
    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$MENU" >/dev/null 2>&1
    ok "icona al menú d'aplicacions: $MENU/arranjaments.desktop"
    if mkdir -p "$ESCRIPTORI" && printf '%s\n' "$ESCRIT" > "$ESCRIPTORI/Arranjaments.desktop" && chmod +x "$ESCRIPTORI/Arranjaments.desktop"; then
      # Marcada com a fiable perquè s'òbriga amb doble clic sense avisos (Ubuntu/GNOME; a KDE basta el permís d'execució)
      command -v gio >/dev/null 2>&1 && gio set "$ESCRIPTORI/Arranjaments.desktop" metadata::trusted true >/dev/null 2>&1
      ok "icona a l'Escriptori: $ESCRIPTORI/Arranjaments.desktop"
    else fallada "No he pogut crear la icona a l'Escriptori." "obri «Arranjaments» des del menú d'aplicacions"; fi
  else fallada "No he pogut crear la icona del menú d'aplicacions."; fi
fi
fi_pas
fi

# ---------------------------------------------------------------- Comprovació final
inici_pas final; pas "Comprovació final"
if [ -x "$ORDRE" ] && [ -d "$TREBALL" ]; then
  if ! (cd "$TREBALL" && "$ORDRE" comprovar) && [ -z "$NOMES" ]; then FALLS=$((FALLS + 1)); PAS_MAL=1; fi
else
  falta "les eines musicals encara no estan instal·lades"; [ -z "$NOMES" ] && FALLS=$((FALLS + 1))
fi
fi_pas
if [ "$FALLS" = 0 ]; then progres "FI ok"; else progres "FI falla $FALLS"; fi

echo
if [ "$PROVA" = 1 ] || [ -n "$NOMES" ]; then echo "Fet."
elif [ "$FALLS" = 0 ]; then
  echo "=============================================="
  echo " Tot a punt."
  echo " Obri la icona «Arranjaments» de l'Escriptori"
  echo " (o del menú d'aplicacions)."
  echo " La teua carpeta de treball: $TREBALL"
  echo "=============================================="
else
  echo "Hi ha $FALLS cosa(es) que no s'han pogut fer (mira els avisos [falta] de dalt)."
  echo "Pots tornar a executar este instal·lador: només fa el que falta."
fi
exit $(( FALLS > 0 ? 1 : 0 ))
