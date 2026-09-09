"""Application web Flask : API de taches + endpoint de sante /health."""

import os
import socket

from flask import Flask, jsonify, render_template, request

from app.store import TaskError, TaskStore

VERSION = os.environ.get("APP_VERSION", "dev")
PORT = int(os.environ.get("PORT", 8080))


def create_app(store=None):
    """Fabrique l'application Flask (pratique pour les tests)."""
    application = Flask(__name__)
    application.config["STORE"] = store or TaskStore()

    @application.get("/")
    def accueil():
        """Page web listant les taches."""
        return render_template(
            "index.html",
            taches=application.config["STORE"].lister(),
            hote=socket.gethostname(),
            version=VERSION,
        )

    @application.get("/health")
    def health():
        """Endpoint de verification utilise par la CI et le deploiement."""
        return jsonify(
            status="ok",
            version=VERSION,
            hote=socket.gethostname(),
        )

    @application.get("/api/tasks")
    def lister_taches():
        return jsonify(application.config["STORE"].lister())

    @application.post("/api/tasks")
    def creer_tache():
        donnees = request.get_json(silent=True) or {}
        try:
            tache = application.config["STORE"].ajouter(donnees.get("titre"))
        except TaskError as erreur:
            return jsonify(erreur=str(erreur)), 400
        return jsonify(tache), 201

    @application.get("/api/tasks/<int:identifiant>")
    def recuperer_tache(identifiant):
        tache = application.config["STORE"].recuperer(identifiant)
        if tache is None:
            return jsonify(erreur="tache introuvable"), 404
        return jsonify(tache)

    @application.post("/api/tasks/<int:identifiant>/done")
    def terminer_tache(identifiant):
        tache = application.config["STORE"].terminer(identifiant)
        if tache is None:
            return jsonify(erreur="tache introuvable"), 404
        return jsonify(tache)

    @application.delete("/api/tasks/<int:identifiant>")
    def supprimer_tache(identifiant):
        if not application.config["STORE"].supprimer(identifiant):
            return jsonify(erreur="tache introuvable"), 404
        return "", 204

    return application


app = create_app()


if __name__ == "__main__":
    print(f"[app] demarrage sur le port {PORT}", flush=True)
    app.run(host="0.0.0.0", port=PORT)
