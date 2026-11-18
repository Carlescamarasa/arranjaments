#!/bin/bash
# Instal·lador per a Linux (LliureX) amb finestra de Terminal. S'obri amb el doble clic al fitxer
# «Instal·lar Arranjaments (Linux).desktop» de la carpeta principal, o amb: bash instalacio/Instalar-Linux-Terminal.sh
cd "$(dirname "$0")/.." || exit 1
bash "instalacio/instalar-linux.sh" "$@"
codi=$?
case " $* " in
  *" --sense-preguntes "*) ;;
  *) echo; read -r -p "Prem Retorn per a tancar esta finestra. " _ ;;
esac
exit $codi
