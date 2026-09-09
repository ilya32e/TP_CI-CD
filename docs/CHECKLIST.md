# Check-list — mise en service du pipeline

Tout le code est prêt et committé en local. Il reste 6 étapes à faire de votre côté.
Suivez-les dans l'ordre : la dernière déclenche le pipeline complet.

> Ce fichier est une aide au TP, il n'est pas un livrable. Vous pouvez le supprimer
> avant le rendu si vous préférez.

---

## 1. Docker Hub — créer le jeton d'accès

1. https://hub.docker.com → se connecter (ou créer un compte).
2. **Account Settings → Personal access tokens → Generate new token**
3. Nom : `github-actions-tp-cicd` — Permissions : **Read & Write**
4. **Copiez le jeton immédiatement**, il ne sera plus jamais affiché.

Il n'y a pas besoin de créer le dépôt d'image à la main : le premier `push`
du pipeline crée automatiquement `<votre_user>/tp-cicd-app`.

---

## 2. Clé SSH pour GitHub Actions

⚠️ **Point d'attention.** Votre ancien TP (`pipeline-CI`) se connectait à la VM
par **mot de passe** (`sshpass -p "$SSH_PASSWORD" ... ubuntu@20.56.74.49`).
Le sujet exige cette fois une **clé privée** en secret (section 8). Il faut donc
installer une clé sur la VM.

Dans Git Bash :

```bash
# a) Générer une paire de clés dédiée au pipeline (sans passphrase :
#    GitHub Actions ne pourrait pas la saisir)
ssh-keygen -t ed25519 -f ~/.ssh/tp-cicd -N "" -C "github-actions-tp-cicd"

# b) Installer la clé publique sur la VM (mot de passe demandé une dernière fois)
ssh-copy-id -i ~/.ssh/tp-cicd.pub ubuntu@20.56.74.49

# c) Vérifier que la connexion par clé fonctionne, SANS mot de passe
ssh -i ~/.ssh/tp-cicd ubuntu@20.56.74.49 "echo connexion OK && docker --version"
```

Si `ssh-copy-id` échoue, équivalent manuel :

```bash
cat ~/.ssh/tp-cicd.pub | ssh ubuntu@20.56.74.49 \
  "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

La **clé privée** à mettre dans les secrets est le contenu de `~/.ssh/tp-cicd`
(le fichier **sans** `.pub`) :

```bash
cat ~/.ssh/tp-cicd        # à copier en entier, lignes BEGIN et END comprises
```

---

## 3. Préparer la VM Azure

Sur la VM :

```bash
ssh -i ~/.ssh/tp-cicd ubuntu@20.56.74.49

# Docker doit être utilisable SANS sudo (GitHub Actions ne peut pas saisir
# de mot de passe sudo). Si "docker ps" échoue, lancez :
sudo usermod -aG docker $USER
sudo systemctl enable --now docker
exit                                        # reconnexion obligatoire

ssh -i ~/.ssh/tp-cicd ubuntu@20.56.74.49 "docker ps"   # doit marcher sans sudo
```

Si Docker n'est pas installé du tout, copiez et lancez le script fourni :

```bash
scp -i ~/.ssh/tp-cicd scripts/setup-vm.sh ubuntu@20.56.74.49:~/
ssh -i ~/.ssh/tp-cicd ubuntu@20.56.74.49 "bash setup-vm.sh"
```

### Ouvrir le port 80

Portail Azure → votre VM → **Networking** → **Add inbound port rule** :

| Champ | Valeur |
|---|---|
| Source | `Any` |
| Destination port ranges | `80` |
| Protocol | `TCP` |
| Action | `Allow` |
| Priority | `310` (ou tout numéro libre) |
| Name | `AllowHTTP` |

Vérification : rien ne répond actuellement en HTTP sur cette VM (testé), donc
cette règle est probablement à créer. Sans elle, le job 4 échouera à l'étape
« Verification via l'IP publique ».

---

## 4. Créer le dépôt GitHub et pousser

Créez un dépôt **vide** sur https://github.com/new (sans README ni .gitignore),
nommé par exemple `tp-cicd-azure`, puis :

```bash
cd ~/Desktop/TP_CI-CD
git remote add origin https://github.com/ilya32e/tp-cicd-azure.git
git push -u origin main
```

⚠️ **Ne poussez pas encore si les secrets ne sont pas créés** : le pipeline se
déclencherait aussitôt et échouerait au job 3. Faites l'étape 5 d'abord.

---

## 5. Enregistrer les 5 secrets GitHub

Dépôt → **Settings → Secrets and variables → Actions → New repository secret**

| Nom du secret | Valeur |
|---|---|
| `DOCKERHUB_USERNAME` | votre login Docker Hub |
| `DOCKERHUB_TOKEN` | le jeton de l'étape 1 |
| `AZURE_VM_HOST` | `20.56.74.49` |
| `AZURE_VM_USER` | `ubuntu` |
| `AZURE_SSH_PRIVATE_KEY` | contenu **entier** de `~/.ssh/tp-cicd` |

Pour la clé privée : incluez bien la première ligne `-----BEGIN OPENSSH PRIVATE KEY-----`,
la dernière `-----END OPENSSH PRIVATE KEY-----` **et le saut de ligne final**.

---

## 6. Déclencher et vérifier

```bash
git push -u origin main      # si pas encore fait
```

Onglet **Actions** du dépôt : les 4 jobs doivent s'enchaîner en vert.

Puis ouvrez http://20.56.74.49 dans le navigateur.

### Prouver l'idempotence (demandé en section 7 du sujet)

Actions → *CI/CD* → **Run workflow** → relancez sur `main`. Ensuite :

```bash
ssh -i ~/.ssh/tp-cicd ubuntu@20.56.74.49 "docker ps -a --filter name=myapp"
```

Un **seul** conteneur `myapp` doit apparaître.

---

## 7. Finaliser les livrables

- [ ] Capture d'écran de http://20.56.74.49 dans le navigateur, **barre d'adresse
      visible** (elle prouve l'accès par l'IP publique) → enregistrer dans
      `docs/capture-vm-azure.png`
- [ ] Dans [`README.md`](../README.md), remplacer :
  - `VOTRE_IP_PUBLIQUE` → `20.56.74.49` (3 occurrences)
  - `VOTRE_UTILISATEUR_DOCKERHUB` → votre login Docker Hub
- [ ] Committer et pousser ces derniers changements

---

## En cas d'échec du pipeline

| Job en échec | Cause probable | Solution |
|---|---|---|
| 3 — build-et-push | `unauthorized` | jeton Docker Hub sans droit *Write*, ou `DOCKERHUB_USERNAME` erroné |
| 4 — SSH | `Permission denied (publickey)` | clé privée mal collée (ligne BEGIN/END ou saut de ligne final manquant), ou clé publique pas installée sur la VM |
| 4 — script SSH | `permission denied while trying to connect to the Docker daemon` | `usermod -aG docker` non fait, ou reconnexion SSH non effectuée depuis |
| 4 — Verification via l'IP publique | timeout | port 80 non ouvert dans le NSG Azure |
| 4 — Verification version | versions différentes | l'ancienne image tourne encore — regardez les logs du step SSH |
