#!/bin/bash
# Alternativa a «Instal·lar Arranjaments» (l'instal·lador amb finestra de la carpeta principal), per si no s'obri.
# Doble clic en este fitxer: instal·la tot el que cal en una finestra de Terminal i posa la icona «Arranjaments» a l'Escriptori.
cd "$(dirname "$0")/.." || exit 1
bash "instalacio/instalar-mac.sh" "$@"
codi=$?
case " $* " in
  *" --sense-preguntes "*) ;;
  *) echo; read -r -p "Prem Retorn per a tancar esta finestra. " _ ;;
esac
exit $codi
