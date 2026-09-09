"""Tests unitaires de la logique metier (aucun serveur HTTP requis)."""

import unittest

from app.store import TaskError, TaskStore


class TestTaskStore(unittest.TestCase):
    def setUp(self):
        self.store = TaskStore()

    def test_ajouter_renvoie_une_tache_non_faite(self):
        tache = self.store.ajouter("Ecrire le Dockerfile")
        self.assertEqual(tache["id"], 1)
        self.assertEqual(tache["titre"], "Ecrire le Dockerfile")
        self.assertFalse(tache["faite"])

    def test_les_identifiants_sont_incrementes(self):
        premiere = self.store.ajouter("Tache 1")
        seconde = self.store.ajouter("Tache 2")
        self.assertEqual([premiere["id"], seconde["id"]], [1, 2])

    def test_le_titre_est_nettoye(self):
        tache = self.store.ajouter("   Deployer sur Azure   ")
        self.assertEqual(tache["titre"], "Deployer sur Azure")

    def test_titre_vide_refuse(self):
        with self.assertRaises(TaskError):
            self.store.ajouter("   ")

    def test_titre_absent_refuse(self):
        with self.assertRaises(TaskError):
            self.store.ajouter(None)

    def test_titre_trop_long_refuse(self):
        with self.assertRaises(TaskError):
            self.store.ajouter("x" * 201)

    def test_lister_est_trie_par_identifiant(self):
        self.store.ajouter("Tache 1")
        self.store.ajouter("Tache 2")
        self.assertEqual([t["id"] for t in self.store.lister()], [1, 2])

    def test_lister_est_vide_au_depart(self):
        self.assertEqual(self.store.lister(), [])

    def test_recuperer_une_tache_existante(self):
        cree = self.store.ajouter("Tache 1")
        self.assertEqual(self.store.recuperer(cree["id"]), cree)

    def test_recuperer_une_tache_inconnue_renvoie_none(self):
        self.assertIsNone(self.store.recuperer(404))

    def test_terminer_bascule_le_drapeau(self):
        cree = self.store.ajouter("Tache 1")
        termine = self.store.terminer(cree["id"])
        self.assertTrue(termine["faite"])
        self.assertTrue(self.store.recuperer(cree["id"])["faite"])

    def test_terminer_une_tache_inconnue_renvoie_none(self):
        self.assertIsNone(self.store.terminer(404))

    def test_supprimer_une_tache_existante(self):
        cree = self.store.ajouter("Tache 1")
        self.assertTrue(self.store.supprimer(cree["id"]))
        self.assertEqual(self.store.lister(), [])

    def test_supprimer_une_tache_inconnue_renvoie_false(self):
        self.assertFalse(self.store.supprimer(404))

    def test_lister_renvoie_des_copies(self):
        """Modifier le resultat de lister() ne doit pas alterer le stockage."""
        self.store.ajouter("Tache 1")
        self.store.lister()[0]["titre"] = "pirate"
        self.assertEqual(self.store.lister()[0]["titre"], "Tache 1")


if __name__ == "__main__":
    unittest.main()
