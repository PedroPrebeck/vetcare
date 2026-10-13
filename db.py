"""Conexões SQLite por requisição e inicialização explícita, sem apagar dados."""

import sqlite3
from pathlib import Path
from flask import current_app, g

ROOT = Path(__file__).resolve().parent
SCHEMA_VERSION = 2


def statements(script):
    buffer = ""
    for line in script.splitlines(True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            yield buffer
            buffer = ""


def migrate(conn):
    """Migração transacional. O chamador preserva um backup antes de executar."""
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version > SCHEMA_VERSION:
        raise ValueError("Banco de versão mais recente. Use uma aplicação compatível.")
    if version == SCHEMA_VERSION:
        return False
    schema = (ROOT / "database/01_schema.sql").read_text(encoding="utf-8")
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN IMMEDIATE")
        if version == 1:
            migration = (ROOT / "database/05_migrate_tutors.sql").read_text(
                encoding="utf-8"
            )
            for sql in statements(migration):
                conn.execute(sql)
        for sql in statements(schema):
            clean = "\n".join(
                line for line in sql.splitlines() if not line.lstrip().startswith("--")
            ).strip()
            if clean in ("BEGIN;", "COMMIT;", "PRAGMA foreign_keys = ON;"):
                continue
            conn.execute(sql)
        if conn.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("Migração interrompida por vínculos inconsistentes.")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
    return True


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
    """Cria esquema idempotente, seed somente quando todas as tabelas estão vazias."""
    if sqlite3.sqlite_version_info < (3, 37, 0):
        raise ValueError("SQLite 3.37+ é necessário para tabelas STRICT.")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version == 1:
            backup = Path(str(path) + ".v1-backup.sqlite3")
            if not backup.exists():
                with sqlite3.connect(backup) as target:
                    conn.backup(target)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        migrate(conn)
        tables = (
            "tutors",
            "pets",
            "pet_tutors",
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
