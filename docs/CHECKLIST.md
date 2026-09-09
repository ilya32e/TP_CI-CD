# Check-list — mise en service du pipeline

État actuel : le code est sur GitHub, les jobs 1 (tests unitaires), 2 (tests E2E)
et 3 (build + push Docker Hub) fonctionnent. Il reste à mettre en place la VM Azure
pour que le job 4 passe.

> Ce fichier est une aide au TP, il n'est pas un livrable. Vous pouvez le supprimer
> avant le rendu si vous préférez.

---

## ✅ Déjà fait

- [x] Dépôt poussé sur https://github.com/ilya32e/TP_CI-CD
- [x] Secret `DOCKERHUB_USERNAME`
- [x] Secret `DOCKERHUB_TOKEN` — l'image `tp-cicd-app` est publiée sur Docker Hub

---

## 1. Créer la VM sur le compte Azure for Students

Procédure détaillée : **[`AZURE-VM.md`](AZURE-VM.md)**

En résumé :

| Champ | Valeur |
|---|---|
| Resource group | `rg-tp-cicd` |
| Image | Ubuntu Server 24.04 LTS - x64 Gen2 |
| Size | Standard_B1s |
| Authentication type | **SSH public key** → *Generate new key pair* |
| Username | `azureuser` |
| Inbound ports | cocher **SSH (22)** *et* **HTTP (80)** |

Téléchargez le `.pem` quand le portail le propose — **il n'est proposé qu'une fois**.

Cocher HTTP (80) dès la création évite d'avoir à ajouter la règle NSG après coup.
C'est l'oubli le plus fréquent : sans elle, l'application tourne sur la VM mais
reste injoignable depuis Internet, et le job 4 échoue à l'étape
« Verification via l'IP publique ».

---

## 2. Installer Docker sur la VM

```bash
chmod 600 ~/.ssh/cle-tp-cicd.pem

scp -i ~/.ssh/cle-tp-cicd.pem scripts/setup-vm.sh azureuser@NOUVELLE_IP:~/
ssh -i ~/.ssh/cle-tp-cicd.pem azureuser@NOUVELLE_IP
```

Sur la VM :

```bash
bash setup-vm.sh
exit                 # obligatoire : le groupe docker ne s'applique qu'à la session suivante
```

Vérification depuis votre poste — c'est exactement ce que fera GitHub Actions :

```bash
ssh -i ~/.ssh/cle-tp-cicd.pem azureuser@NOUVELLE_IP "docker ps"
```

Un tableau vide avec ses en-têtes = c'est bon.

---

## 3. Mettre à jour les secrets GitHub

https://github.com/ilya32e/TP_CI-CD/settings/secrets/actions

| Secret | Action | Valeur |
|---|---|---|
| `AZURE_VM_HOST` | créer / modifier | la nouvelle IP publique |
| `AZURE_VM_USER` | créer / modifier | `azureuser` |
| `AZURE_SSH_PRIVATE_KEY` | créer | contenu entier de `cle-tp-cicd.pem` |
| `SSH_PASSWORD` | supprimer | plus utilisé |

```bash
cat ~/.ssh/cle-tp-cicd.pem      # copier TOUT, lignes BEGIN et END comprises
```

Collez le contenu complet, saut de ligne final inclus.

---

## 4. Relancer et vérifier

**Actions** → *CI/CD* → **Run workflow** → branche `main`.

Les 4 jobs doivent passer au vert, puis ouvrez `http://NOUVELLE_IP`.

### Prouver l'idempotence (section 7 du sujet)

Relancez **Run workflow** une seconde fois, puis :

```bash
ssh -i ~/.ssh/cle-tp-cicd.pem azureuser@NOUVELLE_IP "docker ps -a --filter name=myapp"
```

Un **seul** conteneur `myapp` doit apparaître.

---

## 5. Finaliser les livrables

- [ ] Capture d'écran de `http://NOUVELLE_IP` dans le navigateur, **barre d'adresse
      visible** (elle prouve l'accès par l'IP publique) → `docs/capture-vm-azure.png`
- [ ] Dans [`README.md`](../README.md), remplacer :
  - `VOTRE_IP_PUBLIQUE` → la nouvelle IP (2 occurrences)
  - `VOTRE_UTILISATEUR_DOCKERHUB` → votre login Docker Hub
- [ ] Committer et pousser

---

## En cas d'échec du pipeline

| Étape | Message | Cause et solution |
|---|---|---|
| 3 — build-et-push | `unauthorized` | jeton Docker Hub sans droit *Write*, ou `DOCKERHUB_USERNAME` erroné |
| 4 — SSH | `Permission denied (publickey)` | clé mal collée dans le secret (ligne BEGIN/END ou saut de ligne final manquant) |
| 4 — SSH | `ssh: connect ... i/o timeout` | port 22 fermé dans le NSG, ou VM arrêtée |
| 4 — script | `docker est introuvable sur la VM` | `setup-vm.sh` pas encore exécuté |
| 4 — script | `permission denied ... docker daemon socket` | `usermod -aG docker` fait, mais sans reconnexion SSH ensuite |
| 4 — Verification via l'IP publique | timeout | port 80 non ouvert dans le NSG Azure |
| 4 — Verification version | versions différentes | l'ancienne image tourne encore — voir les logs du step SSH |

---

## Préserver le crédit étudiant

Arrêtez la VM depuis le **portail** (bouton *Stop*) quand vous ne l'utilisez pas :
l'état devient *Stopped (deallocated)* et la facturation s'arrête. Un `sudo shutdown`
depuis l'intérieur de la VM continue de facturer.

Si vous arrêtez puis redémarrez la VM, **l'IP publique change** — sauf si vous la
passez en *Static*. Voir la fin de [`AZURE-VM.md`](AZURE-VM.md).
