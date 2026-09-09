# TP — CI/CD complet : Tests → Docker Hub → Déploiement sur VM Azure

## 1. Contexte

Une entreprise souhaite industrialiser le déploiement d'une application web.

Chaque **push sur la branche `main`** doit déclencher automatiquement :

- Tests unitaires
- Tests E2E
- Build de l'image Docker
- Push de l'image sur Docker Hub
- Déploiement automatique sur une VM Azure (via SSH)

**Aucune action manuelle n'est autorisée après le push.**

---

## 2. Chaîne CI/CD attendue

```
git push (main)
  ↓
GitHub Actions
  ↓
1) Unit tests
  ↓
2) E2E tests
  ↓ (uniquement si OK)
3) Build Docker image
  ↓
4) Push image Docker Hub
  ↓
5) Deploy on Azure VM (SSH)
  ↓
6) Vérification (healthcheck / requête HTTP)
```

---

## 3. Application à déployer

Votre application (API ou web) doit :

- être fonctionnelle localement
- exposer un port (ex : 3000 ou 8080)
- proposer un endpoint ou une page de vérification, idéalement **GET /health**

---

## 4. Dockerisation

Vous devez fournir :

- un **Dockerfile ou docker compose** fonctionnel et propre
- un conteneur lançable avec docker
- exposition correcte du port

**Attendu :** l'application démarre correctement dans un conteneur Docker.

---

## 5. Tests obligatoires

### Tests unitaires

Vous devez avoir un ensemble de tests unitaires :

- exécutables en CI (commande unique)
- la pipeline doit échouer si un test échoue

### Tests E2E (end-to-end ex: Cypress)

Vous devez avoir un ensemble de tests E2E :

- simulant un parcours réel (HTTP ou navigateur)
- exécutables en CI (commande unique)
- la pipeline doit échouer si un test échoue

Les tests E2E doivent tester au minimum :

- disponibilité de l'application
- au moins une fonctionnalité (ou endpoint) en plus du `/health`

---

## 6. GitHub Actions — Pipeline CI/CD

Vous devez créer un workflow GitHub Actions qui :

- se déclenche sur push sur `main`
- contient **au minimum** les jobs (ou steps) suivants :

### Job 1 — Unit tests

- installe les dépendances
- exécute les tests unitaires

### Job 2 — E2E tests

- installe/démarre ce qui est nécessaire
- exécute les tests E2E

### Job 3 — Build & Push Docker Hub

- construit l'image Docker
- tag l'image (voir section tags)
- push l'image sur Docker Hub
- **uniquement si** Job 1 et Job 2 sont OK

### Job 4 — Deploy sur VM Azure

- se connecte à la VM via SSH
- récupère l'image depuis Docker Hub
- redémarre l'application (idempotent)
- vérifie que l'application répond

---

## 7. Déploiement sur VM Azure (via SSH)

La pipeline doit déployer sur une VM Azure.

### Contraintes

- **le déploiement se fait dans GitHub Actions**, pas à la main
- l'application doit être accessible via l'IP publique de la VM
- le déploiement doit être **idempotent**

### Définition d'*idempotent*

Relancer le workflow (ou pousser à nouveau le même commit) doit :

- ne pas créer plusieurs conteneurs
- ne pas casser le service
- simplement confirmer l'état ou redéployer proprement

### Recommandation

Utiliser un déploiement stable avec :

- un nom de conteneur fixe (`myapp`)
- ou `docker compose up -d` (si vous choisissez compose)

---

## 8. Gestion des secrets (obligatoire)

Aucun identifiant ne doit apparaître en clair dans le dépôt.

Vous devez utiliser **GitHub Secrets** pour :

- identifiants Docker Hub (username + token)
- accès SSH à la VM (clé privée)
- IP/host de la VM + user

---

## 9. Livrables attendus

### Un dépôt GitHub contenant

- le code de l'application
- le Dockerfile
- le workflow GitHub Actions

### Une application fonctionnelle

- Une capture d'écran de la VM Azure accessible sur l'IP publique

### Un court README expliquant

- le fonctionnement du pipeline
- comment le déploiement est déclenché
- les choix techniques réalisés
