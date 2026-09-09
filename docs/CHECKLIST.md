# Check-list — mise en service du pipeline

Le code est poussé sur GitHub. Il reste à créer les secrets Docker Hub et à
vérifier la VM, puis à relancer le pipeline.

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

## 2. Authentification SSH

Le déploiement se connecte à la VM **par mot de passe**, stocké dans le secret
`SSH_PASSWORD` (déjà créé). Rien à faire ici, à part vérifier que la connexion
fonctionne depuis votre poste :

```bash
ssh ubuntu@20.56.74.49 "echo connexion OK && docker --version"
```

Si la commande demande le mot de passe et l'accepte, le job 4 pourra faire pareil.

---

## 3. Préparer la VM Azure

Sur la VM :

```bash
ssh ubuntu@20.56.74.49

# Docker doit être utilisable SANS sudo (GitHub Actions ne peut pas saisir
# de mot de passe sudo). Si "docker ps" échoue, lancez :
sudo usermod -aG docker $USER
sudo systemctl enable --now docker
exit                                        # reconnexion obligatoire

ssh ubuntu@20.56.74.49 "docker ps"   # doit marcher sans sudo
```

Si Docker n'est pas installé du tout, copiez et lancez le script fourni :

```bash
scp scripts/setup-vm.sh ubuntu@20.56.74.49:~/
ssh ubuntu@20.56.74.49 "bash setup-vm.sh"
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

✅ **Déjà fait.** Le code est poussé sur https://github.com/ilya32e/TP_CI-CD
(commit `initial`, branche `main`).

Une fois les secrets créés (étape 5), relancez le pipeline sans créer de commit :
Actions → *CI/CD* → **Run workflow**.

---

## 5. Enregistrer les 5 secrets GitHub

Dépôt → **Settings → Secrets and variables → Actions → New repository secret**

| Nom du secret | Valeur |
|---|---|
| `DOCKERHUB_USERNAME` | votre login Docker Hub |
| `DOCKERHUB_TOKEN` | le jeton de l'étape 1 |
| `AZURE_VM_HOST` | `20.56.74.49` |
| `AZURE_VM_USER` | `ubuntu` |
| `SSH_PASSWORD` | mot de passe SSH de `ubuntu` — ✅ déjà créé |

`SSH_PASSWORD` est déjà en place : il ne reste que les quatre premiers à créer.

---

## 6. Déclencher et vérifier

Actions → *CI/CD* → **Run workflow** → branche `main`.

Onglet **Actions** du dépôt : les 4 jobs doivent s'enchaîner en vert.

Puis ouvrez http://20.56.74.49 dans le navigateur.

### Prouver l'idempotence (demandé en section 7 du sujet)

Actions → *CI/CD* → **Run workflow** → relancez sur `main`. Ensuite :

```bash
ssh ubuntu@20.56.74.49 "docker ps -a --filter name=myapp"
```

Un **seul** conteneur `myapp` doit apparaître.

---

## 7. Finaliser les livrables

- [ ] Capture d'écran de http://20.56.74.49 dans le navigateur, **barre d'adresse
      visible** (elle prouve l'accès par l'IP publique) → enregistrer dans
      `docs/capture-vm-azure.png`
- [ ] Dans [`README.md`](../README.md), remplacer `VOTRE_UTILISATEUR_DOCKERHUB`
      par votre login Docker Hub (l'IP est déjà renseignée)
- [ ] Committer et pousser ces derniers changements

---

## En cas d'échec du pipeline

| Job en échec | Cause probable | Solution |
|---|---|---|
| 3 — build-et-push | `unauthorized` | jeton Docker Hub sans droit *Write*, ou `DOCKERHUB_USERNAME` erroné |
| 4 — SSH | `Permission denied` | mot de passe erroné dans `SSH_PASSWORD`, ou `AZURE_VM_USER` different de `ubuntu` |
| 4 — script SSH | `permission denied while trying to connect to the Docker daemon` | `usermod -aG docker` non fait, ou reconnexion SSH non effectuée depuis |
| 4 — Verification via l'IP publique | timeout | port 80 non ouvert dans le NSG Azure |
| 4 — Verification version | versions différentes | l'ancienne image tourne encore — regardez les logs du step SSH |
