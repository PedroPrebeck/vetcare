"""Conexões SQLite por requisição e inicialização explícita, sem apagar dados."""

import sqlite3
from pathlib import Path
from flask import current_app, g

ROOT = Path(__file__).resolve().parent


def get_db():
    if "db" not in g:
        if current_app.config.get("CLOUD_DATABASE"):
            from cloud_db import open_cloud_database

            g.db = open_cloud_database()
            return g.db
        g.db = sqlite3.connect(current_app.config["DATABASE"], timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA busy_timeout = 10000")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def initialize(path, demo=False):
    """Cria esquema idempotente; seed somente quando todas as tabelas estão vazias."""
    if sqlite3.sqlite_version_info < (3, 37, 0):
        raise ValueError("SQLite 3.37+ é necessário para tabelas STRICT.")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        if conn.execute("PRAGMA user_version").fetchone()[0] > 1:
            raise ValueError(
                "Banco de versão mais recente. Use uma aplicação compatível."
            )
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(
            (ROOT / "database/01_schema.sql").read_text(encoding="utf-8")
        )
        tables = (
            "tutors",
            "pets",
            "veterinarians",
            "services",
            "appointments",
            "medical_records",
            "payments",
        )
        if demo:
            if any(
                conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables
            ):
                raise ValueError(
                    "O seed exige um banco vazio. Os dados existentes foram preservados."
                )
            conn.executescript(
                (ROOT / "database/02_seed.sql").read_text(encoding="utf-8")
            )
