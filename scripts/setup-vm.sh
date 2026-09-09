#!/usr/bin/env bash
# Preparation de la VM Azure - A EXECUTER UNE SEULE FOIS, sur la VM.
#
#   ssh azureuser@<IP_PUBLIQUE>
#   curl -fsSL <url_brute_de_ce_fichier> -o setup-vm.sh
#   bash setup-vm.sh
#
# Ensuite, tout passe par GitHub Actions : plus aucune action manuelle.

set -euo pipefail

# $USER n'est pas toujours defini dans un shell SSH non interactif :
# on determine l'utilisateur courant de facon fiable.
UTILISATEUR="$(id -un)"

echo "=========================================="
echo " Preparation de la VM pour le TP CI/CD"
echo "=========================================="

# --- 1. Installation de Docker -------------------------------------
if command -v docker >/dev/null 2>&1; then
  echo "[1/4] Docker est deja installe : $(docker --version)"
else
  echo "[1/4] Installation de Docker..."
  sudo apt-get update -y
  sudo apt-get install -y ca-certificates curl gnupg
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  sudo apt-get update -y
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

# --- 2. Docker utilisable sans sudo --------------------------------
# Indispensable : GitHub Actions se connecte en SSH sans mot de passe
# et ne pourra donc pas repondre a une demande de mot de passe sudo.
echo "[2/4] Ajout de ${UTILISATEUR} au groupe docker"
sudo usermod -aG docker "$UTILISATEUR"

# --- 3. Demarrage automatique au boot ------------------------------
echo "[3/4] Activation du service Docker au demarrage"
sudo systemctl enable --now docker

# --- 4. Verification -----------------------------------------------
echo "[4/4] Verification"
sudo docker run --rm hello-world >/dev/null && echo "      Docker fonctionne."

echo ""
echo "=========================================="
echo " Termine."
echo ""
echo " IMPORTANT : deconnectez-vous puis reconnectez-vous"
echo " (exit puis ssh) pour que le groupe docker prenne effet,"
echo " puis verifiez que ceci marche SANS sudo :"
echo ""
echo "     docker ps"
echo ""
echo " Pensez aussi a ouvrir le port 80 dans le groupe de"
echo " securite reseau (NSG) de la VM sur le portail Azure."
echo "=========================================="
