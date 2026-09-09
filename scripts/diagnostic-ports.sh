#!/usr/bin/env bash
# Depuis quel port la VM est-elle joignable depuis Internet ?
#
# A lancer depuis un runner GitHub : contrairement au reseau de l'ecole, qui
# intercepte les connexions sortantes et fausse toute mesure, le runner a un
# acces direct. Le resultat fait donc autorite sur la configuration du NSG.
#
# Usage : ./scripts/diagnostic-ports.sh <ip>

set -uo pipefail

HOTE="${1:?usage: diagnostic-ports.sh <ip>}"
PORTS="${2:-80 443 8080 8081 8082 8083 8084 8085 8086 8087 8088 8089 8090}"

echo "Test de joignabilite de ${HOTE} depuis le runner GitHub"
echo "--------------------------------------------------------"

joignables=""
for port in $PORTS; do
  code=$(curl -s -o /dev/null -m 6 -w '%{http_code}' "http://${HOTE}:${port}/health" 2>/dev/null)
  if [ "$code" = "000" ]; then
    printf '  port %-5s  injoignable\n' "$port"
  else
    printf '  port %-5s  JOIGNABLE (HTTP %s)\n' "$port" "$code"
    joignables="${joignables}${port} "
  fi
done

echo "--------------------------------------------------------"
if [ -z "$joignables" ]; then
  echo "Aucun port HTTP joignable : le NSG Azure ne publie que SSH (22)."
  echo "Une regle entrante est necessaire pour rendre l'application accessible."
else
  echo "Ports ouverts dans le NSG : ${joignables}"
fi

# Ce script est un diagnostic : il ne doit jamais faire echouer le pipeline.
exit 0
