#!/usr/bin/env bash
# Instal·lació per a Mac. Es pot repetir sense problema: només fa el que falta.
# No cal Homebrew: baixa els instal·ladors oficials directament.
# Ús: bash "instalacio/instalar-mac.sh"                 (tot el que falta)
#     bash "instalacio/instalar-mac.sh" --nomes uv      (només una cosa: uv, musescore, audiveris)
#     bash "instalacio/instalar-mac.sh" --prova         (només comprova, no canvia res)
set -u

CARPETA="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$CARPETA" || exit 1
export PATH="$HOME/.local/bin:$HOME/.opencode/bin:$PATH"

PROVA=0
NOMES=""
while [ $# -gt 0 ]; do
  case "$1" in
    --prova) PROVA=1 ;;
    --nomes) shift; NOMES="${1:-}" ;;
  esac
  shift
done
case "$NOMES" in ""|uv|musescore|audiveris) ;; *) echo "Opció --nomes desconeguda: $NOMES (usa uv, musescore o audiveris)"; exit 1 ;; esac
# vol X: diu si cal fer el pas X (sense --nomes, tots)
vol() { [ -z "$NOMES" ] || [ "$NOMES" = "$1" ]; }

ok()    { printf '  [fet]    %s\n' "$1"; }
falta() { printf '  [falta]  %s\n' "$1"; }
pas()   { printf '\n== %s ==\n' "$1"; }

# Baixa l'últim instal·lador .dmg d'un repositori de GitHub i copia l'aplicació a ~/Applications
# (la carpeta Aplicacions de la teua usuària: no cal contrasenya d'administrador).
# $1 = repositori (propietari/nom)  $2 = patró del nom de fitxer
instal_dmg() {
  local repo="$1" patro="$2" url tmp punt app res
  echo "  Buscant l'última versió..."
  url=$(curl -fsSL "https://api.github.com/repos/$repo/releases/latest" \
        | grep -o '"browser_download_url": *"[^"]*"' | sed 's/.*: *"//; s/"$//' | grep -E "$patro" | head -1)
  if [ -z "$url" ]; then echo "  No he pogut trobar el instal·lador (sense internet?)."; return 1; fi
  tmp="$(mktemp -d)"
  echo "  Baixant $(basename "$url") (pot tardar uns minuts)..."
  curl -fL --progress-bar -o "$tmp/instalador.dmg" "$url" || { rm -rf "$tmp"; return 1; }
  punt="$tmp/volum"; mkdir -p "$punt"
  hdiutil attach -nobrowse -quiet -mountpoint "$punt" "$tmp/instalador.dmg" || { rm -rf "$tmp"; return 1; }
  app=$(ls -d "$punt"/*.app 2>/dev/null | head -1)
  if [ -z "$app" ]; then echo "  No trobe cap aplicació dins de l'instal·lador."; hdiutil detach -quiet "$punt"; rm -rf "$tmp"; return 1; fi
  mkdir -p "$HOME/Applications"
  cp -R "$app" "$HOME/Applications/"; res=$?
  hdiutil detach -quiet "$punt"; rm -rf "$tmp"
  return $res
}

[ "$PROVA" = 1 ] && echo "Mode prova: només es comprova què hi ha instal·lat, no es canvia res."

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
    echo "  Si OpenCode no el troba encara, crida'l amb la ruta completa: ~/.local/bin/uv (no cal reiniciar)."
  else echo "  No s'ha pogut instal·lar uv."; exit 1; fi
fi
fi

if vol musescore; then
pas "2. MuseScore (revisar partitures i fer PDF)"
if ls -d /Applications/MuseScore*.app "$HOME"/Applications/MuseScore*.app >/dev/null 2>&1 || [ -n "${MUSESCORE_PATH:-}" ]; then ok "MuseScore ja està instal·lat"
elif [ "$PROVA" = 1 ]; then falta "MuseScore 4"
elif instal_dmg "musescore/MuseScore" '\.dmg$'; then ok "MuseScore instal·lat (a ~/Applications)"
else
  falta "No he pogut instal·lar MuseScore automàticament."
  echo "  Fes-ho a mà: baixa'l des de https://musescore.org/ca/download (tria l'opció «sense MuseHub») i arrossega la icona a Aplicacions."
fi
fi

if vol audiveris; then
pas "3. Audiveris (convertir PDF en partitura; porta Java inclòs)"
if ls -d /Applications/Audiveris*.app "$HOME"/Applications/Audiveris*.app >/dev/null 2>&1 || [ -n "${AUDIVERIS_PATH:-}" ]; then ok "Audiveris ja està instal·lat"
elif [ "$PROVA" = 1 ]; then falta "Audiveris"
else
  if [ "$(uname -m)" = "arm64" ]; then ARQ="macosx-arm64"; else ARQ="macosx-x86_64"; fi
  if instal_dmg "Audiveris/audiveris" "$ARQ\\.dmg$"; then ok "Audiveris instal·lat"
  else
    falta "No he pogut instal·lar Audiveris automàticament."
    echo "  Fes-ho a mà: baixa el .dmg «$ARQ» de https://github.com/Audiveris/audiveris/releases i arrossega Audiveris a Aplicacions."
  fi
fi
fi

if [ -z "$NOMES" ] || [ "$NOMES" = uv ]; then
pas "4. Eines musicals d'este projecte"
if [ "$PROVA" = 1 ]; then falta "uv sync (no es fa en mode prova)"
elif command -v uv >/dev/null 2>&1; then
  uv sync && ok "eines musicals preparades" || { echo "  Ha fallat «uv sync». Comprova internet i torna-ho a provar."; }
fi
fi

pas "5. Comprovació final"
if command -v uv >/dev/null 2>&1; then uv run partitures comprovar; else falta "uv no disponible (hauria d'estar a ~/.local/bin/uv)"; fi
