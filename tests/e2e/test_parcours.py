"""Tests E2E : parcours reel en HTTP contre l'application deployee.

Ces tests ne connaissent RIEN du code Python : ils ne font que des
requetes HTTP, exactement comme un vrai utilisateur ou un client de l'API.
Ils nettoient les taches qu'ils creent pour rester rejouables a l'infini
(la CI comme la VM peuvent les relancer sans les faire echouer).
"""

import uuid

import pytest


@pytest.fixture
def titre_unique():
    """Un titre different a chaque execution, pour ne pas confondre
    les taches d'un test avec celles d'un autre."""
    return f"tache-e2e-{uuid.uuid4().hex[:8]}"


# --------------------------------------------------------------------
# 1. Disponibilite de l'application (exige par le TP)
# --------------------------------------------------------------------

class TestDisponibilite:
    def test_health_repond_200(self, session, base_url):
        reponse = session.get(f"{base_url}/health")
        assert reponse.status_code == 200

    def test_health_renvoie_un_statut_ok(self, session, base_url):
        corps = session.get(f"{base_url}/health").json()
        assert corps["status"] == "ok"

    def test_health_expose_la_version_deployee(self, session, base_url):
        """La version vient du ARG APP_VERSION du Dockerfile : elle prouve
        quelle image tourne reellement."""
        corps = session.get(f"{base_url}/health").json()
        assert corps["version"], "la version ne doit pas etre vide"
        print(f"\n[e2e] version deployee : {corps['version']} (hote {corps['hote']})")

    def test_la_page_web_est_accessible(self, session, base_url):
        reponse = session.get(f"{base_url}/")
        assert reponse.status_code == 200
        assert "Gestionnaire de taches" in reponse.text


# --------------------------------------------------------------------
# 2. Parcours fonctionnel complet (la fonctionnalite en plus de /health)
# --------------------------------------------------------------------

class TestParcoursTaches:
    def test_parcours_complet_creer_lire_terminer_supprimer(
        self, session, base_url, titre_unique
    ):
        """Le parcours reel d'un utilisateur, de bout en bout."""

        # 1) Creation d'une tache
        creation = session.post(f"{base_url}/api/tasks", json={"titre": titre_unique})
        assert creation.status_code == 201, creation.text
        tache = creation.json()
        identifiant = tache["id"]
        assert tache["titre"] == titre_unique
        assert tache["faite"] is False

        try:
            # 2) La tache est bien relisible par son identifiant
            lecture = session.get(f"{base_url}/api/tasks/{identifiant}")
            assert lecture.status_code == 200
            assert lecture.json()["titre"] == titre_unique

            # 3) Elle apparait dans la liste
            liste = session.get(f"{base_url}/api/tasks")
            assert liste.status_code == 200
            assert titre_unique in [t["titre"] for t in liste.json()]

            # 4) Elle est visible sur la page web (rendu HTML)
            page = session.get(f"{base_url}/")
            assert titre_unique in page.text

            # 5) On la marque comme faite
            fin = session.post(f"{base_url}/api/tasks/{identifiant}/done")
            assert fin.status_code == 200
            assert fin.json()["faite"] is True

            # 6) Le changement est bien persiste cote serveur
            relecture = session.get(f"{base_url}/api/tasks/{identifiant}")
            assert relecture.json()["faite"] is True

        finally:
            # 7) Nettoyage : le test est rejouable
            suppression = session.delete(f"{base_url}/api/tasks/{identifiant}")
            assert suppression.status_code == 204

        # 8) Apres suppression, la tache n'existe plus
        assert session.get(f"{base_url}/api/tasks/{identifiant}").status_code == 404

    def test_creation_refusee_sans_titre(self, session, base_url):
        """L'application doit rejeter une entree invalide, pas planter."""
        reponse = session.post(f"{base_url}/api/tasks", json={})
        assert reponse.status_code == 400
        assert "erreur" in reponse.json()

    def test_tache_inexistante_renvoie_404(self, session, base_url):
        reponse = session.get(f"{base_url}/api/tasks/999999")
        assert reponse.status_code == 404

    def test_la_liste_est_toujours_un_tableau_json(self, session, base_url):
        reponse = session.get(f"{base_url}/api/tasks")
        assert reponse.headers["Content-Type"].startswith("application/json")
        assert isinstance(reponse.json(), list)
