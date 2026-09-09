#!/usr/bin/env bash
# Tests E2E en une seule commande : build de l'image, demarrage du
# conteneur, execution des tests, puis nettoyage systematique.
#
# Usage : ./scripts/run-e2e.sh [port_hote]

set -euo pipefail

PORT_HOTE="${1:-8080}"
CONTENEUR="myapp-e2e"
IMAGE="tp-cicd-app:e2e"

nettoyer() {
  echo "[e2e] nettoyage du conteneur ${CONTENEUR}"
  docker logs "$CONTENEUR" 2>&1 | tail -30 || true
  docker rm -f "$CONTENEUR" >/dev/null 2>&1 || true
}
# Le nettoyage a lieu meme si les tests echouent : pas de conteneur
# orphelin qui bloquerait la prochaine execution.
trap nettoyer EXIT

echo "[e2e] construction de l'image"
docker build --build-arg APP_VERSION=e2e -t "$IMAGE" .

echo "[e2e] demarrage du conteneur sur le port ${PORT_HOTE}"
docker rm -f "$CONTENEUR" >/dev/null 2>&1 || true
docker run -d --name "$CONTENEUR" -p "${PORT_HOTE}:8080" "$IMAGE" >/dev/null

echo "[e2e] attente de la disponibilite"
./scripts/healthcheck.sh "http://localhost:${PORT_HOTE}" 30 2

echo "[e2e] execution des tests"
E2E_BASE_URL="http://localhost:${PORT_HOTE}" python -m pytest tests/e2e -v
