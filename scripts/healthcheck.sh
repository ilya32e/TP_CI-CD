#!/usr/bin/env bash
# Attend que l'application reponde sur /health.
# Utilise en local, dans la CI et sur la VM Azure apres deploiement.
#
# Usage : ./scripts/healthcheck.sh <url_de_base> [tentatives] [delai_secondes]

set -euo pipefail

BASE_URL="${1:-http://localhost:8080}"
TENTATIVES="${2:-30}"
DELAI="${3:-2}"

echo "[healthcheck] cible : ${BASE_URL}/health"

for i in $(seq 1 "$TENTATIVES"); do
  if reponse=$(curl -fsS --max-time 5 "${BASE_URL}/health" 2>/dev/null); then
    echo "[healthcheck] OK apres ${i} tentative(s) : ${reponse}"
    exit 0
  fi
  echo "[healthcheck] tentative ${i}/${TENTATIVES} en echec, nouvelle tentative dans ${DELAI}s..."
  sleep "$DELAI"
done

echo "[healthcheck] ECHEC : l'application n'a pas repondu apres ${TENTATIVES} tentatives" >&2
exit 1
