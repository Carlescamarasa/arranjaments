#!/bin/sh
# Arranjaments-LliureX.run: instal·lador d'un sol fitxer per a LliureX i altres Linux (Ubuntu).
# És este guió amb el projecte (un tar.gz) enganxat darrere de la línia __ARXIU__ (vegeu ../paquets.py).
# Què fa: si l'han obert amb doble clic (sense terminal), es torna a obrir dins d'una finestra de Terminal; descomprimeix el
# projecte a ~/.local/share/Arranjaments/staging, executa l'instal·lador de Linux (sense sudo) i esborra la còpia temporal.
# Si el navegador l'ha baixat sense permís d'execució (és el normal), es pot obrir igualment amb:  sh Arranjaments-LliureX.run
# Opcions: --sense-terminal (no obrir cap Terminal), --sense-preguntes (no esperar cap tecla al final) i les de
# instalacio/instalar-linux.sh (--prova, --nomes ...).
set -u

AQUEST="$0"
case "$AQUEST" in /*) ;; *) AQUEST="$(pwd)/$AQUEST" ;; esac
SENSE_TERMINAL=0
for a in "$@"; do [ "$a" = "--sense-terminal" ] && SENSE_TERMINAL=1; done
if [ "$SENSE_TERMINAL" = 1 ]; then
  # es trau l'opció --sense-terminal de la llista d'arguments
  n=$#; while [ "$n" -gt 0 ]; do a="$1"; shift; [ "$a" = "--sense-terminal" ] || set -- "$@" "$a"; n=$((n - 1)); done
fi

avis() {  # missatge per a qui no veu cap terminal (doble clic sense Terminal disponible)
  printf '%s\n' "$1" >&2
  if [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
    if command -v kdialog >/dev/null 2>&1; then kdialog --title "Arranjaments" --msgbox "$1" >/dev/null 2>&1 && return 0; fi
    if command -v zenity >/dev/null 2>&1; then zenity --info --title "Arranjaments" --text "$1" >/dev/null 2>&1 && return 0; fi
  fi
  return 0
}

# 1. Sense terminal (doble clic des del gestor de fitxers): tornar-se a obrir dins d'un Terminal
if [ ! -t 1 ] && [ "$SENSE_TERMINAL" = 0 ] && [ -z "${ARRANJAMENTS_EN_TERMINAL:-}" ] && [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
  export ARRANJAMENTS_EN_TERMINAL=1
  for t in konsole gnome-terminal xfce4-terminal mate-terminal lxterminal x-terminal-emulator xterm; do
    command -v "$t" >/dev/null 2>&1 || continue
    printf 'Obrint en un terminal: %s\n' "$t" >&2
    case "$t" in
      gnome-terminal) "$t" -- sh "$AQUEST" "$@" ;;
      xfce4-terminal|mate-terminal) "$t" -x sh "$AQUEST" "$@" ;;
      *) "$t" -e sh "$AQUEST" "$@" ;;
    esac
    exit $?
  done
  avis "No he trobat cap programa de Terminal. Obri un Terminal i escriu: sh \"$AQUEST\""
fi

# 2. Descomprimir el projecte a una carpeta temporal
DADES="${ARRANJAMENTS_DADES:-${XDG_DATA_HOME:-$HOME/.local/share}/Arranjaments}"
STAGING="$DADES/staging"
echo "Preparant els fitxers..."
rm -rf "$STAGING"
mkdir -p "$STAGING" || { avis "No puc crear la carpeta $STAGING."; exit 1; }
INICI="$(LC_ALL=C awk '/^__ARXIU__$/ { print NR + 1; exit }' "$AQUEST")"
if [ -z "$INICI" ] || ! tail -n +"$INICI" "$AQUEST" | tar -xzf - -C "$STAGING" 2>/dev/null || [ ! -f "$STAGING/instalacio/instalar-linux.sh" ]; then
  rm -rf "$STAGING"
  avis "El fitxer està trencat o incomplet. Torna a baixar-lo."
  exit 1
fi

# 3. Instal·lar (el mateix de sempre: sense sudo) i netejar
bash "$STAGING/instalacio/Instalar-Linux-Terminal.sh" "$@"
CODI=$?
rm -rf "$STAGING"
exit $CODI
__ARXIU__
