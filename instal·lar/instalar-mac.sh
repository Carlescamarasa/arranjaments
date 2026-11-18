#!/usr/bin/env bash
# Instal·lació per a Mac. Es pot repetir sense problema: només fa el que falta.
# Ús: obri el Terminal, escriu "bash " i arrossega este fitxer, i prem Retorn.
set -u

CARPETA="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$CARPETA" || exit 1

ok()   { printf '  [fet]  %s\n' "$1"; }
falta() { printf '  [falta] %s\n' "$1"; }
pas()  { printf '\n== %s ==\n' "$1"; }

if [ "${1:-}" = "--prova" ]; then
  echo "Mode prova: només es comprova què hi ha instal·lat, no es canvia res."
  PROVA=1
else
  PROVA=0
fi

pas "1. uv (el gestor que prepara les eines musicals)"
if command -v uv >/dev/null 2>&1; then
  ok "uv ja està instal·lat"
elif [ "$PROVA" = 1 ]; then
  falta "uv no està instal·lat (s'instal·laria des d'astral.sh/uv)"
else
  echo "  Instal·lant uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  command -v uv >/dev/null 2>&1 && ok "uv instal·lat" || { echo "  No s'ha pogut instal·lar uv. Pregunta a algú de suport."; exit 1; }
fi

pas "2. MuseScore 4 (per a revisar partitures i fer PDF)"
if [ -d "/Applications/MuseScore 4.app" ] || [ -n "${MUSESCORE_PATH:-}" ]; then
  ok "MuseScore 4 trobat"
else
  falta "MuseScore 4 no està instal·lat."
  echo "  Baixa'l i instal·la'l (és gratuït) des de: https://musescore.org/ca/download"
  echo "  Arrossega la icona a la carpeta Aplicacions."
fi

pas "3. Audiveris (per a convertir PDF en partitura editable)"
if [ -d "/Applications/Audiveris.app" ] || [ -n "${AUDIVERIS_PATH:-}" ]; then
  ok "Audiveris trobat"
else
  falta "Audiveris no està instal·lat (només cal si has de treballar amb PDF)."
  echo "  Baixa l'instal·lador per a Mac (.dmg) des de: https://github.com/Audiveris/audiveris/releases"
  echo "  Si el teu Mac és recent (M1, M2, M3...) tria «macosx-arm64»; si és antic, «macosx-x86_64»."
  echo "  Obri el .dmg i arrossega Audiveris a Aplicacions."
fi

pas "4. OpenCode (l'ajudant)"
if command -v opencode >/dev/null 2>&1 || [ -x "$HOME/.opencode/bin/opencode" ]; then
  ok "OpenCode ja està instal·lat"
else
  falta "OpenCode no està instal·lat."
  echo "  Instal·la'l amb esta ordre al Terminal: curl -fsSL https://opencode.ai/install | bash"
  echo "  (més informació a https://opencode.ai)"
fi

pas "5. Eines musicals del projecte"
if [ "$PROVA" = 1 ]; then
  falta "no s'ha executat «uv sync» (mode prova)"
elif command -v uv >/dev/null 2>&1; then
  if uv sync; then ok "eines musicals preparades"; else echo "  Ha fallat «uv sync». Torna-ho a provar amb internet."; exit 1; fi
fi

printf '\nFet. Per a començar: obri el Terminal, escriu «cd » i arrossega esta carpeta (%s), prem Retorn i escriu «opencode».\n' "$CARPETA"
