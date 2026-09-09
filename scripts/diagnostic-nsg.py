"""Cartographie les ports que le NSG Azure laisse passer.

A executer depuis un runner GitHub : contrairement au reseau de l'ecole,
qui intercepte les connexions sortantes et repond a la place de la VM,
le runner a un acces direct. Son verdict fait donc autorite.

La methode repose sur la difference de comportement entre les deux refus :

  - connexion acceptee   -> le NSG laisse passer ET un service ecoute
  - connexion refusee    -> le NSG laisse passer, mais rien n'ecoute
                            (la VM repond elle-meme par un RST)
  - delai depasse        -> le NSG jette le paquet en silence

Seuls les deux premiers cas prouvent qu'un port est ouvert dans le NSG.

Usage : python scripts/diagnostic-nsg.py <ip>
"""

import socket
import sys
from concurrent.futures import ThreadPoolExecutor

DELAI = 4
PARALLELISME = 150


def ports_a_tester():
    """Ports bien connus, plus les plages habituelles des serveurs web."""
    ports = set(range(1, 1025))            # tous les ports reserves
    ports |= set(range(3000, 3011))        # Node, React
    ports |= set(range(4000, 4011))
    ports |= set(range(5000, 5011))        # Flask
    ports |= set(range(7000, 7011))
    ports |= set(range(8000, 9001))        # la zone ou toute la promo deploie
    ports |= {9090, 9200, 9300, 27017, 50000}
    return sorted(ports)


def tester(hote, port):
    """Renvoie (port, etat) ou etat vaut None si le port est bloque."""
    prise = socket.socket()
    prise.settimeout(DELAI)
    try:
        prise.connect((hote, port))
        return port, "OUVERT (un service ecoute)"
    except ConnectionRefusedError:
        return port, "ouvert dans le NSG (rien n'ecoute derriere)"
    except (socket.timeout, TimeoutError):
        return port, None
    except OSError:
        return port, None
    finally:
        prise.close()


def main():
    if len(sys.argv) < 2:
        print("usage : diagnostic-nsg.py <ip>", file=sys.stderr)
        return 0

    hote = sys.argv[1]
    ports = ports_a_tester()

    print(f"Cartographie du NSG de {hote} depuis le runner GitHub")
    print(f"{len(ports)} ports testes, delai de {DELAI}s par port")
    print("-" * 60)

    with ThreadPoolExecutor(max_workers=PARALLELISME) as executeur:
        resultats = list(executeur.map(lambda p: tester(hote, p), ports))

    joignables = [(p, e) for p, e in resultats if e]

    for port, etat in joignables:
        print(f"  port {port:<6} {etat}")

    print("-" * 60)
    if joignables:
        liste = " ".join(str(p) for p, _ in joignables)
        print(f"Ports que le NSG laisse passer : {liste}")
    else:
        print("Aucun port joignable parmi ceux testes.")
    print(f"{len(resultats) - len(joignables)} ports bloques par le NSG.")

    # Diagnostic pur : ne doit jamais faire echouer le pipeline.
    return 0


if __name__ == "__main__":
    sys.exit(main())
