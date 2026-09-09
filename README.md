# TP CI/CD — Tests → Docker Hub → Déploiement sur VM Azure

Application web (API de tâches en Flask) déployée automatiquement sur une VM Azure
à chaque push sur `main`. **Aucune action manuelle n'est nécessaire après le push.**

- Application en production : http://VOTRE_IP_PUBLIQUE
- Healthcheck : http://VOTRE_IP_PUBLIQUE/health
- Image Docker Hub : `VOTRE_UTILISATEUR_DOCKERHUB/tp-cicd-app`

---

## 1. Fonctionnement du pipeline

Le workflow [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml) enchaîne
quatre jobs. Chacun ne démarre que si le précédent est vert (mot-clé `needs`) :

```
git push (main)
      │
      ▼
┌─────────────────────────┐
│ 1. tests-unitaires      │  pytest tests/unit  — 30 tests
└─────────────────────────┘
      │ vert
      ▼
┌─────────────────────────┐
│ 2. tests-e2e            │  build image → run conteneur → pytest tests/e2e — 8 tests
└─────────────────────────┘
      │ vert  (needs: [1, 2])
      ▼
┌─────────────────────────┐
│ 3. build-et-push        │  docker build → push Docker Hub (tags :latest et :<sha>)
└─────────────────────────┘
      │ vert
      ▼
┌─────────────────────────┐
│ 4. deploiement-azure    │  SSH → docker pull → docker run → vérifications
└─────────────────────────┘
      │
      ▼
  Application en ligne sur l'IP publique de la VM
```

### Détail des jobs

| # | Job | Ce qu'il fait | Échoue si… |
|---|---|---|---|
| 1 | `tests-unitaires` | installe les dépendances, lance `pytest tests/unit` | un test unitaire échoue |
| 2 | `tests-e2e` | construit l'image, démarre le conteneur, lance `pytest tests/e2e` contre lui | l'app ne démarre pas ou un parcours échoue |
| 3 | `build-et-push` | build puis push sur Docker Hub avec deux tags | identifiants Docker Hub invalides |
| 4 | `deploiement-azure` | SSH sur la VM, pull, redémarrage du conteneur, vérifications | l'app ne répond pas ou la mauvaise version tourne |

Le job 3 déclare `needs: [tests-unitaires, tests-e2e]` : **aucune image n'est publiée
si un seul test échoue**, et le déploiement n'a donc jamais lieu.

### Les vérifications du job 4

Le déploiement n'est pas considéré comme réussi tant que ces trois contrôles ne passent pas :

1. **Depuis la VM** — boucle `curl http://localhost/health` (30 tentatives, 2 s d'intervalle).
   En cas d'échec, les logs du conteneur sont affichés dans GitHub Actions.
2. **Depuis l'extérieur** — le runner GitHub interroge `http://<IP_PUBLIQUE>/health`,
   ce qui prouve que l'application est bien joignable depuis Internet et pas seulement
   en local sur la VM.
3. **Bonne version déployée** — `/health` renvoie le champ `version`, qui contient le SHA
   du commit injecté au build. Le workflow le compare au commit en cours : si la VM
   faisait encore tourner l'ancienne image, le job devient rouge.

Enfin, **les 8 tests E2E sont rejoués contre la production**. Ce n'est pas seulement
« le serveur répond », c'est « le parcours métier fonctionne réellement sur la VM ».

---

## 2. Comment le déploiement est déclenché

```yaml
on:
  push:
    branches: [main]
  workflow_dispatch:
```

- **Automatique** : tout `git push` sur `main` lance la chaîne complète.
- **Manuel** : le bouton *Run workflow* de l'onglet Actions rejoue le pipeline à
  l'identique. C'est utile pour démontrer l'idempotence sans créer de commit.

Un `concurrency group` empêche deux déploiements simultanés sur la VM : si un second
push arrive pendant un déploiement, il attend la fin du premier.

### Idempotence

Rejouer le workflow (ou repousser le même commit) ne crée jamais de second conteneur :

```bash
docker rm -f myapp || true     # supprime l'ancien s'il existe
docker run -d --name myapp ... # recrée toujours le même nom
```

Le nom de conteneur est **fixe** (`myapp`). Le `|| true` évite l'échec au tout premier
déploiement, quand `myapp` n'existe pas encore. Vérifié en local : trois déploiements
consécutifs laissent bien **un seul** conteneur.

`--restart unless-stopped` garantit en plus que l'application redémarre toute seule
si la VM Azure reboote.

---

## 3. Application

| Route | Méthode | Rôle |
|---|---|---|
| `/` | GET | page web listant les tâches |
| `/health` | GET | healthcheck : `{"status":"ok","version":"<sha>","hote":"<conteneur>"}` |
| `/api/tasks` | GET | liste des tâches |
| `/api/tasks` | POST | création — corps `{"titre":"..."}` |
| `/api/tasks/<id>` | GET | détail d'une tâche |
| `/api/tasks/<id>/done` | POST | marque la tâche comme faite |
| `/api/tasks/<id>` | DELETE | suppression |

---

## 4. Utilisation en local

```bash
# Installation
python -m venv .venv
.venv\Scripts\activate            # Windows  (source .venv/bin/activate sous Linux)
pip install -r requirements-dev.txt

# Tests unitaires (30 tests, aucun conteneur requis)
pytest

# Tests E2E en une commande : build + run + tests + nettoyage
./scripts/run-e2e.sh 8080

# Lancer l'application dans Docker
docker build -t tp-cicd-app:local .
docker run -d --name myapp -p 8080:8080 tp-cicd-app:local
curl http://localhost:8080/health
```

---

## 5. Secrets GitHub (obligatoires)

Aucun identifiant n'apparaît en clair dans le dépôt. À créer dans
**Settings → Secrets and variables → Actions → New repository secret** :

| Secret | Contenu | Où l'obtenir |
|---|---|---|
| `DOCKERHUB_USERNAME` | votre login Docker Hub | hub.docker.com |
| `DOCKERHUB_TOKEN` | jeton d'accès (**pas** le mot de passe) | Docker Hub → Account Settings → Personal access tokens → *Read & Write* |
| `AZURE_VM_HOST` | IP publique de la VM, ex. `20.56.74.49` | portail Azure → VM → Overview |
| `AZURE_VM_USER` | utilisateur SSH, ex. `azureuser` | choisi à la création de la VM |
| `AZURE_SSH_PRIVATE_KEY` | clé privée SSH **complète** | fichier `.pem` téléchargé à la création de la VM |

> Pour `AZURE_SSH_PRIVATE_KEY`, collez le contenu entier du fichier, en incluant
> les lignes `-----BEGIN ... PRIVATE KEY-----` et `-----END ... PRIVATE KEY-----`,
> ainsi que le saut de ligne final.

Dans le script SSH, les secrets sont transmis par `envs:` plutôt qu'interpolés dans
le corps du script : ils ne peuvent donc pas se retrouver écrits en clair dans les
journaux d'exécution.

---

## 6. Préparation de la VM Azure (une seule fois)

```bash
ssh -i cle.pem azureuser@<IP_PUBLIQUE>
bash scripts/setup-vm.sh   # installe Docker et ajoute l'utilisateur au groupe docker
exit                       # obligatoire : reconnexion pour appliquer le groupe
```

Puis, sur le **portail Azure** → VM → *Networking* → *Add inbound port rule* :
autoriser le **port 80 (TCP)** depuis `Any`. Sans cette règle, la VM répond en local
mais reste injoignable depuis Internet.

Le script est idempotent : le relancer sur une VM déjà configurée ne casse rien.

---

## 7. Choix techniques

**Python / Flask.** Application volontairement simple : le sujet porte sur la chaîne
CI/CD, pas sur la complexité applicative. La logique métier est isolée dans
[`app/store.py`](app/store.py), sans dépendance à Flask, ce qui la rend testable
unitairement sans démarrer de serveur.

**Tests E2E en HTTP (pytest + requests) plutôt que Cypress.** Le sujet autorise
« HTTP ou navigateur ». L'approche HTTP évite d'installer Node et Chrome sur le runner
(pipeline plus rapide), et surtout **la même suite de tests peut cibler n'importe quelle
URL** via la variable `E2E_BASE_URL` : le conteneur local, celui de la CI, ou la VM Azure
en production. C'est ce qui permet de rejouer les E2E contre la production après le
déploiement.

**gunicorn avec 1 worker et 4 threads.** Le Dockerfile utilisait initialement
`--workers 2`, et **les tests E2E ont révélé un bug que les 30 tests unitaires ne
pouvaient pas voir** : deux workers gunicorn sont deux processus séparés, donc deux
`TaskStore` en mémoire distincts. Une tâche créée par le worker A renvoyait un 404
quand la requête suivante tombait sur le worker B. Corrigé en passant à un seul
processus multi-threadé — le `Lock` de `TaskStore` rend le stockage sûr entre threads.
*C'est l'illustration concrète de l'intérêt des tests E2E en plus des tests unitaires.*

**Double tag d'image (`latest` + `<sha-court>`).** Le tag SHA rend chaque image
traçable jusqu'au commit exact qui l'a produite, et permet de revenir à une version
antérieure en cas de problème. `latest` reste pratique à lire.

**`APP_VERSION` injecté au build et exposé par `/health`.** C'est ce qui permet de
vérifier automatiquement, après le déploiement, que la VM fait bien tourner la nouvelle
image — un déploiement « silencieusement raté » est ainsi détecté.

**Conteneur non-root, `HEALTHCHECK` Docker, `.dockerignore`.** L'application tourne
sous l'utilisateur `appuser` ; `docker ps` affiche `healthy` ou `unhealthy`, ce qui aide
au diagnostic sur la VM ; le `.dockerignore` exclut `.venv/`, `tests/` et `.git/` pour
une image plus légère (198 Mo) et un build plus rapide.

**`.gitattributes` avec `eol=lf`.** Le développement se fait sous Windows, la CI et la
VM sous Linux. Sans cette règle, Git convertirait les scripts `.sh` en CRLF et Linux
répondrait `bad interpreter: /usr/bin/env bash^M`.

---

## 8. Structure du dépôt

```
.
├── app/
│   ├── store.py              logique métier (testable sans Flask)
│   ├── main.py               application Flask et routes
│   └── templates/index.html  page web
├── tests/
│   ├── unit/                 30 tests unitaires
│   └── e2e/                  8 tests E2E (HTTP)
├── scripts/
│   ├── healthcheck.sh        attente + vérification de /health
│   ├── run-e2e.sh            tests E2E en une seule commande
│   └── setup-vm.sh           préparation de la VM Azure (une fois)
├── .github/workflows/ci-cd.yml
├── Dockerfile
├── docker-compose.yml
└── requirements.txt / requirements-dev.txt
```

---

## 9. Capture d'écran

![Application accessible sur l'IP publique de la VM Azure](docs/capture-vm-azure.png)
