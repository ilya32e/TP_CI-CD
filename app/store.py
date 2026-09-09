"""Logique metier de l'application : gestion d'une liste de taches.

Ce module ne depend pas de Flask : il est donc directement testable
par les tests unitaires, sans lancer de serveur HTTP.
"""

from itertools import count
from threading import Lock


class TaskError(ValueError):
    """Erreur metier (donnee invalide fournie par le client)."""


class TaskStore:
    """Stockage en memoire des taches, protege par un verrou."""

    def __init__(self):
        self._taches = {}
        self._compteur = count(1)
        self._verrou = Lock()

    def ajouter(self, titre):
        """Cree une tache et renvoie sa representation."""
        if not isinstance(titre, str) or not titre.strip():
            raise TaskError("le titre est obligatoire")

        titre = titre.strip()
        if len(titre) > 200:
            raise TaskError("le titre ne doit pas depasser 200 caracteres")

        with self._verrou:
            identifiant = next(self._compteur)
            tache = {"id": identifiant, "titre": titre, "faite": False}
            self._taches[identifiant] = tache

        return dict(tache)

    def lister(self):
        """Renvoie toutes les taches, triees par identifiant."""
        with self._verrou:
            return [dict(t) for t in sorted(self._taches.values(), key=lambda t: t["id"])]

    def recuperer(self, identifiant):
        """Renvoie une tache, ou None si elle n'existe pas."""
        with self._verrou:
            tache = self._taches.get(identifiant)
            return dict(tache) if tache else None

    def terminer(self, identifiant):
        """Marque une tache comme faite. Renvoie None si elle n'existe pas."""
        with self._verrou:
            tache = self._taches.get(identifiant)
            if tache is None:
                return None
            tache["faite"] = True
            return dict(tache)

    def supprimer(self, identifiant):
        """Supprime une tache. Renvoie True si elle existait."""
        with self._verrou:
            return self._taches.pop(identifiant, None) is not None

    def vider(self):
        """Vide le stockage (utilise par les tests)."""
        with self._verrou:
            self._taches.clear()
