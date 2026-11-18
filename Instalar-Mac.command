#!/bin/bash
# Doble clic en este fitxer per a instal·lar tot el que cal i posar la icona «Arranjaments» a l'Escriptori.
cd "$(dirname "$0")" || exit 1
bash "instalacio/instalar-mac.sh" "$@"
codi=$?
case " $* " in
  *" --sense-preguntes "*) ;;
  *) echo; read -r -p "Prem Retorn per a tancar esta finestra. " _ ;;
esac
exit $codi
