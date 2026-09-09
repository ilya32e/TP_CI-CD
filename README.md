# TP CI/CD — Déploiement automatique sur une VM Azure

Petite application web en Flask (une liste de tâches) qui se déploie toute seule
sur une VM Azure à chaque push sur `main`. Une fois le push fait, il n'y a plus
rien à toucher à la main.

- Application : http://20.56.74.49:8090
- Healthcheck : http://20.56.74.49:8090/health
- Image Docker Hub : `ilya32e/tp-cicd-app`

## L'application

C'est volontairement simple, le sujet porte sur la chaîne CI/CD et pas sur
l'application elle-même.

| Route | Ce que ça fait |
|---|---|
| `GET /` | une page web qui liste les tâches |
| `GET /health` | répond `{"status":"ok","version":"...","hote":"..."}` |
| `GET /api/tasks` | la liste des tâches en JSON |
| `POST /api/tasks` | ajoute une tâche, corps `{"titre":"..."}` |
| `POST /api/tasks/<id>/done` | marque la tâche comme faite |
| `DELETE /api/tasks/<id>` | supprime la tâche |

Le code est séparé en deux : `app/store.py` contient la logique (ajouter,
lister, terminer une tâche) sans rien connaître de Flask, et `app/main.py`
contient les routes HTTP. Ça permet de tester la logique sans lancer de serveur.

## Le pipeline

Tout est dans `.github/workflows/ci-cd.yml`. Il y a 4 jobs, chacun ne démarre
que si le précédent a réussi :

```
push sur main
   → 1. tests unitaires   (pytest, 30 tests)
   → 2. tests E2E         (on lance le conteneur et on tape dessus en HTTP, 8 tests)
   → 3. build + push sur Docker Hub
   → 4. déploiement SSH sur la VM Azure
```

Le job 3 déclare `needs: [tests-unitaires, tests-e2e]`, donc si un seul test
échoue, aucune image n'est publiée et le déploiement n'a jamais lieu.

Sur la VM, le job 4 fait ça :

```bash
docker pull ilya32e/tp-cicd-app:<sha>
docker rm -f myapp-mi || true
docker run -d --name myapp-mi --restart unless-stopped -p 8090:8080 ilya32e/tp-cicd-app:<sha>
```

Ensuite il vérifie trois choses : que l'appli répond en local sur la VM, qu'elle
répond depuis l'extérieur sur l'IP publique, et que la version renvoyée par
`/health` correspond bien au commit qu'on vient de pousser. Pour finir, il rejoue
les 8 tests E2E contre la VM. Si une seule de ces vérifications échoue, le job
passe au rouge.

## Comment le déploiement se déclenche

Automatiquement, à chaque push sur `main`. J'ai aussi ajouté
`workflow_dispatch`, qui ajoute un bouton « Run workflow » dans l'onglet
Actions : ça permet de relancer le pipeline sans faire de commit, pratique pour
montrer que le déploiement est idempotent.

### Idempotence

Le conteneur a un nom fixe (`myapp-mi`), et on fait `docker rm -f` avant de le
recréer. Relancer le workflow ne crée donc jamais un deuxième conteneur, ça
remplace juste l'ancien. Le `|| true` évite que ça plante au tout premier
déploiement, quand le conteneur n'existe pas encore.

Vérifié en local en lançant la séquence trois fois de suite : il reste bien un
seul conteneur.

## Les secrets

Rien n'est écrit en clair dans le dépôt, tout passe par les GitHub Secrets
(Settings → Secrets and variables → Actions) :

| Secret | Contenu |
|---|---|
| `DOCKERHUB_USERNAME` | mon login Docker Hub |
| `DOCKERHUB_TOKEN` | un token Docker Hub (pas le mot de passe) |
| `AZURE_VM_HOST` | l'IP publique de la VM |
| `AZURE_VM_USER` | l'utilisateur SSH |
| `SSH_PASSWORD` | le mot de passe SSH |

## Choix techniques

**Flask + pytest.** Je suis resté sur la même stack que les TP précédents. Les
tests unitaires utilisent le `test_client()` de Flask : instantanés, et sans
aucun accès réseau.

**Tests E2E en HTTP plutôt que Cypress.** Le sujet laisse le choix entre HTTP et
navigateur. En HTTP c'est plus rapide (pas besoin d'installer Node et Chrome sur
le runner), et surtout les mêmes tests peuvent viser n'importe quelle URL grâce
à la variable `E2E_BASE_URL`. C'est ce qui me permet de rejouer exactement la
même suite contre le conteneur local, contre celui de la CI, puis contre la VM
après le déploiement.

**Les tests E2E m'ont trouvé un vrai bug.** Au départ le conteneur tournait avec
gunicorn en `--workers 2`. Les tests E2E échouaient de façon aléatoire avec des
404 : deux workers, c'est deux processus, donc deux stockages en mémoire
différents — une tâche créée par l'un était invisible pour l'autre. Les 30 tests
unitaires ne pouvaient pas voir ça, ils ne lancent pas de vrai serveur. C'est
pour moi le meilleur argument en faveur des tests E2E.

**Un nom de conteneur et un port qui me sont propres.** La VM est partagée avec
toute la promo, sous un seul compte `ubuntu`. Si j'appelle mon conteneur `myapp`
comme le suggère le sujet, je casse celui du voisin et il casse le mien — c'est
arrivé plusieurs fois entre camarades. J'utilise donc `myapp-mi` sur le port
8090. Pour la même raison je n'ai pas mis de `docker image prune`, qui aurait
supprimé les images des autres, et je ne fais pas de `docker login` sur la VM,
qui laisserait mon token Docker Hub dans un fichier lisible par tout le monde.
Mon image étant publique, le `docker pull` fonctionne sans authentification.

**Deux tags par image : `latest` et le SHA du commit.** Le tag SHA permet de
savoir exactement quel commit tourne sur la VM, et de revenir en arrière si
besoin. Ce SHA est aussi injecté dans l'image au build (`ARG APP_VERSION`) puis
renvoyé par `/health`, ce qui me sert à vérifier automatiquement après le
déploiement que la VM fait bien tourner la nouvelle version et pas l'ancienne.

**Le Dockerfile.** Image `python:3.12-slim`, l'application tourne sous un
utilisateur non-root, et les dépendances sont installées avant la copie du code
pour profiter du cache Docker. Le conteneur démarre avec `python -m app.main`
(la forme `-m` est nécessaire parce que `main.py` importe `app.store`).

## Lancer en local

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt

pytest                      # les 30 tests unitaires
./scripts/run-e2e.sh 8080   # build + conteneur + tests E2E + nettoyage

docker build -t tp-cicd-app .
docker run -d --name myapp -p 8080:8080 tp-cicd-app
curl http://localhost:8080/health
```

## Structure du dépôt

```
app/            l'application (store.py = logique, main.py = routes)
tests/unit/     30 tests unitaires
tests/e2e/      8 tests E2E
scripts/        healthcheck, lancement des E2E, préparation de la VM
.github/workflows/ci-cd.yml
Dockerfile
```

## Capture d'écran

![Application sur l'IP publique de la VM Azure](docs/capture-vm-azure.png)
