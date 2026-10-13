"""VetCare: fábrica Flask, CLI e proteção para demonstração local."""

import os
import secrets
from pathlib import Path
import click
from flask import (
    Flask,
    g,
    jsonify,
    render_template,
    request,
    session,
    send_from_directory,
)
from cloud_db import StorageConflict, StorageUnavailable, persist_cloud_database
from db import ROOT, close_db, initialize


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        DATABASE=os.environ.get(
            "VETCARE_DATABASE", str(ROOT / "instance/vetcare.sqlite3")
        ),
        SECRET_KEY=os.environ.get("VETCARE_SECRET", secrets.token_hex(32)),
        MAX_CONTENT_LENGTH=64 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        CLOUD_DATABASE=os.environ.get("VERCEL") == "1",
    )
    if config:
        app.config.update(config)
    app.teardown_appcontext(close_db)
    from api import api

    app.register_blueprint(api)

    @app.before_request
    def protect_writes():
        # Token por sessão, endpoints mutáveis exigem o cabeçalho da própria interface.
        if request.path.startswith("/api/") and request.method in (
            "POST",
            "PATCH",
            "DELETE",
        ):
            csrf = (
                request.cookies.get("__Host-vetcare-csrf")
                if app.config["CLOUD_DATABASE"]
                else session.get("csrf")
            )
            if not csrf or not secrets.compare_digest(
                request.headers.get("X-CSRF-Token", ""), csrf
            ):
                return jsonify(error="Sessão expirada. Recarregue a página."), 403

    @app.after_request
    def security_headers(response):
        if app.config["CLOUD_DATABASE"]:
            try:
                response = persist_cloud_database(response)
            except StorageConflict:
                response = jsonify(
                    error="Outro acesso alterou os dados. Recarregue e tente novamente."
                )
                response.status_code = 409
            except StorageUnavailable:
                response = jsonify(
                    error="Não foi possível confirmar a gravação. Recarregue antes de tentar novamente."
                )
                response.status_code = 503
            if g.get("cloud_csrf"):
                response.set_cookie(
                    "__Host-vetcare-csrf",
                    g.cloud_csrf,
                    secure=True,
                    httponly=True,
                    samesite="Strict",
                    path="/",
                )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    def index():
        if app.config["CLOUD_DATABASE"]:
            csrf = request.cookies.get("__Host-vetcare-csrf") or secrets.token_hex(32)
            g.cloud_csrf = csrf
            return render_template("index.html", csrf=csrf, cloud=True)
        session.setdefault("csrf", secrets.token_hex(32))
        return render_template("index.html", csrf=session["csrf"])

    @app.errorhandler(StorageUnavailable)
    def storage_unavailable(_error):
        return jsonify(error="Armazenamento indisponível. Tente novamente."), 503

    @app.errorhandler(StorageConflict)
    def storage_conflict(_error):
        return (
            jsonify(
                error="Outro acesso alterou os dados. Recarregue e tente novamente."
            ),
            409,
        )

    @app.get("/docs/<path:filename>")
    def documentation(filename):
        return send_from_directory(ROOT / "docs", filename)

    @app.cli.command("init-db")
    @click.option(
        "--demo", is_flag=True, help="Carrega dados fictícios em banco vazio."
    )
    def init_db(demo):
        try:
            initialize(app.config["DATABASE"], demo=demo)
        except ValueError as exc:
            raise click.ClickException(str(exc))
        click.echo("Banco pronto: " + app.config["DATABASE"])

    @app.cli.command("backup-db")
    @click.argument("destination", type=click.Path())
    def backup_db(destination):
        """Backup consistente, incluindo dados ainda no WAL."""
        import sqlite3

        if Path(destination).exists():
            raise click.ClickException("Destino já existe, escolha outro arquivo.")
        with sqlite3.connect(app.config["DATABASE"]) as source, sqlite3.connect(
            destination
        ) as target:
            source.backup(target)
        click.echo("Backup criado: " + destination)

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify(error="Conteúdo excede o limite de 64 KB."), 413

    return app


app = create_app()
if __name__ == "__main__":
    # Sem debug e limitado ao próprio computador. Inicialização é um comando separado.
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))
