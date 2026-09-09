"""Configuration des tests E2E.

Contrairement aux tests unitaires, ces tests tapent sur une VRAIE
application qui tourne (conteneur Docker en local ou en CI, ou VM Azure).
L'adresse cible est donnee par la variable d'environnement E2E_BASE_URL.
"""

import os

import pytest
import requests

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8080").rstrip("/")
DELAI = float(os.environ.get("E2E_TIMEOUT", "10"))
# Nombre de tentatives avant de declarer l'application injoignable.
TENTATIVES = int(os.environ.get("E2E_RETRIES", "30"))


@pytest.fixture(scope="session")
def base_url():
    """Adresse de l'application ciblee par les tests E2E."""
    return BASE_URL


@pytest.fixture(scope="session", autouse=True)
def attendre_application():
    """Verifie que l'application repond avant de lancer la suite.

    Sans cela, un demarrage un peu lent ferait echouer le premier test
    pour une mauvaise raison.
    """
    derniere_erreur = None
    for _ in range(TENTATIVES):
        try:
            reponse = requests.get(f"{BASE_URL}/health", timeout=DELAI)
            if reponse.status_code == 200:
                print(f"\n[e2e] application joignable sur {BASE_URL}")
                return
            derniere_erreur = f"statut HTTP {reponse.status_code}"
        except requests.RequestException as erreur:
            derniere_erreur = erreur
        import time

        time.sleep(2)

    pytest.fail(f"application injoignable sur {BASE_URL} : {derniere_erreur}")


@pytest.fixture
def session():
    """Session HTTP reutilisee, avec un timeout par defaut."""
    with requests.Session() as s:
        s.request = _avec_timeout(s.request, DELAI)
        yield s


def _avec_timeout(methode, delai):
    def appel(*args, **kwargs):
        kwargs.setdefault("timeout", delai)
        return methode(*args, **kwargs)

    return appel
