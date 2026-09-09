# TP CI/CD — Déploiement automatique sur VM Azure

Application web Flask conteneurisée et déployée automatiquement sur une VM Azure avec GitHub Actions.

## Application

- Page principale : `GET /`
- Vérification : `GET /health`
- Liste des tâches : `GET /api/tasks`
- Ajout d'une tâche : `POST /api/tasks` avec `{"titre": "..."}`
- Tâche terminée : `POST /api/tasks/<id>/done`
- Suppression : `DELETE /api/tasks/<id>`
- Application déployée : http://20.56.74.49
- Healthcheck : http://20.56.74.49/health

## Exécution locale

```bash
pip install -r requirements-dev.txt
python -m app.main
```

L'application est disponible sur http://localhost:8080.

## Docker

```bash
docker build -t tp-cicd-app .
docker run --name myapp -p 8080:8080 tp-cicd-app
```

L'application est alors disponible sur http://localhost:8080.

## Tests

```bash
# Tests unitaires (30 tests)
python -m pytest tests/unit -q

# Tests E2E, avec l'application démarrée (8 tests)
E2E_BASE_URL=http://localhost:8080 python -m pytest tests/e2e -q

# Tests E2E en une commande : build, conteneur, tests, nettoyage
./scripts/run-e2e.sh 8080
```

## Pipeline CI/CD

Chaque push sur la branche `main` déclenche automatiquement :

1. les tests unitaires ;
2. les tests E2E contre un vrai conteneur Docker ;
3. le build et le push de l'image sur Docker Hub si les tests réussissent ;
4. le déploiement sur la VM via SSH ;
5. la vérification de l'endpoint `/health`, depuis la VM puis depuis l'IP publique ;
6. la ré-exécution des tests E2E contre l'application déployée.

L'image reçoit les tags `latest` et l'identifiant du commit. Le déploiement est idempotent : le conteneur fixe `myapp-mi` est supprimé puis relancé sur le port `80`.

> La VM étant mutualisée entre tous les étudiants, le conteneur porte un nom qui lui est propre et le workflow ne supprime que ses propres images. Le groupe de sécurité réseau (NSG) de la VM n'autorisant que le port 22, les vérifications passant par l'IP publique sont en `continue-on-error` : leur résultat reste visible dans les journaux sans faire échouer le pipeline. Le workflow contient un diagnostic qui liste les ports joignables depuis Internet.

## Secrets GitHub

Les informations sensibles sont stockées dans GitHub Secrets :

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`
- `AZURE_VM_HOST`
- `AZURE_VM_USER`
- `SSH_PASSWORD`

## Choix techniques

- Flask pour une application web légère, avec la logique métier isolée dans `app/store.py` pour la tester sans serveur ;
- Pytest pour les tests unitaires et les tests E2E HTTP ;
- une suite E2E pilotée par `E2E_BASE_URL`, donc rejouable contre le conteneur local, celui de la CI ou la VM ;
- Docker pour garantir un environnement reproductible, avec un utilisateur non-root et un `HEALTHCHECK` ;
- `APP_VERSION` injecté au build et renvoyé par `/health`, pour vérifier que la VM fait tourner le bon commit ;
- Docker Hub pour stocker les images ;
- SSH pour déployer automatiquement sur la VM.

## Capture d'écran

![Application déployée sur la VM Azure](docs/capture-vm-azure.png)
