"""VetCare: fábrica Flask, CLI e proteção para demonstração local."""

import os
import secrets
from pathlib import Path
import click
from flask import Flask, jsonify, render_template, request, session, send_from_directory
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
    )
    if config:
        app.config.update(config)
    app.teardown_appcontext(close_db)
    from api import api

    app.register_blueprint(api)

    @app.before_request
    def protect_writes():
        # Token por sessão; endpoints mutáveis exigem o cabeçalho da própria interface.
        if request.path.startswith("/api/") and request.method in (
            "POST",
            "PATCH",
            "DELETE",
        ):
            if request.headers.get("X-CSRF-Token") != session.get(
                "csrf"
            ) or not session.get("csrf"):
                return jsonify(error="Sessão expirada. Recarregue a página."), 403

    @app.after_request
    def security_headers(response):
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
        session.setdefault("csrf", secrets.token_hex(32))
        return render_template("index.html", csrf=session["csrf"])

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
            raise click.ClickException("Destino já existe; escolha outro arquivo.")
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
