"""Tests unitaires des routes HTTP, via le client de test Flask.

Aucun conteneur ni serveur reel n'est demarre ici : c'est le role
des tests E2E.
"""

import unittest

from app.main import create_app
from app.store import TaskStore


class TestApi(unittest.TestCase):
    def setUp(self):
        # Un stockage neuf par test : les tests restent independants.
        self.app = create_app(store=TaskStore())
        self.client = self.app.test_client()

    def test_health_repond_ok(self):
        reponse = self.client.get("/health")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.get_json()["status"], "ok")

    def test_health_expose_version_et_hote(self):
        corps = self.client.get("/health").get_json()
        self.assertIn("version", corps)
        self.assertIn("hote", corps)

    def test_page_accueil_est_servie(self):
        reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("Gestionnaire de taches", reponse.get_data(as_text=True))

    def test_liste_vide_au_demarrage(self):
        reponse = self.client.get("/api/tasks")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.get_json(), [])

    def test_creation_renvoie_201(self):
        reponse = self.client.post("/api/tasks", json={"titre": "Tache 1"})
        self.assertEqual(reponse.status_code, 201)
        self.assertEqual(reponse.get_json()["titre"], "Tache 1")

    def test_tache_creee_apparait_dans_la_liste(self):
        self.client.post("/api/tasks", json={"titre": "Tache 1"})
        self.assertEqual(len(self.client.get("/api/tasks").get_json()), 1)

    def test_tache_creee_apparait_sur_la_page_web(self):
        self.client.post("/api/tasks", json={"titre": "Tache visible"})
        self.assertIn("Tache visible", self.client.get("/").get_data(as_text=True))

    def test_creation_sans_titre_renvoie_400(self):
        reponse = self.client.post("/api/tasks", json={})
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("erreur", reponse.get_json())

    def test_creation_sans_corps_json_renvoie_400(self):
        self.assertEqual(self.client.post("/api/tasks").status_code, 400)

    def test_recuperation_par_identifiant(self):
        identifiant = self.client.post("/api/tasks", json={"titre": "Tache 1"}).get_json()["id"]
        reponse = self.client.get(f"/api/tasks/{identifiant}")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.get_json()["id"], identifiant)

    def test_tache_inconnue_renvoie_404(self):
        self.assertEqual(self.client.get("/api/tasks/404").status_code, 404)

    def test_terminer_une_tache(self):
        identifiant = self.client.post("/api/tasks", json={"titre": "Tache 1"}).get_json()["id"]
        reponse = self.client.post(f"/api/tasks/{identifiant}/done")
        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(reponse.get_json()["faite"])

    def test_terminer_une_tache_inconnue_renvoie_404(self):
        self.assertEqual(self.client.post("/api/tasks/404/done").status_code, 404)

    def test_suppression_renvoie_204(self):
        identifiant = self.client.post("/api/tasks", json={"titre": "Tache 1"}).get_json()["id"]
        self.assertEqual(self.client.delete(f"/api/tasks/{identifiant}").status_code, 204)
        self.assertEqual(self.client.get("/api/tasks").get_json(), [])

    def test_suppression_dune_tache_inconnue_renvoie_404(self):
        self.assertEqual(self.client.delete("/api/tasks/404").status_code, 404)


if __name__ == "__main__":
    unittest.main()
