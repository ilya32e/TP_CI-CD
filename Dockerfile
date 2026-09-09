# Image de base legere et versionnee (pas de tag "latest" flottant).
FROM python:3.12-slim

LABEL description="TP CI/CD - API de taches Flask deployee sur VM Azure"

# Sorties Python non bufferisees : les logs remontent immediatement
# dans "docker logs", ce qui est indispensable pour diagnostiquer
# le conteneur sur la VM Azure.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /srv

# Les dependances sont copiees et installees AVANT le code applicatif :
# tant que requirements.txt ne change pas, Docker reutilise le cache
# de cette couche et le build reste rapide.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# L'application ne tourne pas en root (bonne pratique de securite).
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /srv
USER appuser

# Version de l'image, injectee au build par GitHub Actions (SHA du commit).
# Elle est renvoyee par /health : c'est ce qui permet de prouver que la VM
# fait bien tourner la nouvelle image apres un deploiement.
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

EXPOSE 8080

# Healthcheck Docker : "docker ps" affiche healthy/unhealthy.
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,os,sys; sys.exit(0) if urllib.request.urlopen(f\"http://127.0.0.1:{os.environ['PORT']}/health\", timeout=2).status == 200 else sys.exit(1)"

# Serveur de production (gunicorn), pas le serveur de developpement Flask.
#
# UN SEUL processus, mais 4 threads (--threads 4) : les taches sont stockees
# en memoire, donc plusieurs workers = plusieurs memoires separees et une
# tache creee par l'un serait invisible pour l'autre. TaskStore est protege
# par un verrou : il est concu pour etre partage entre threads.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --access-logfile - app.main:app"]
