"""SQLite por requisição, persistido no Blob privado com controle por ETag.

Protocolo do SDK oficial @vercel/blob 2.8.1. OIDC dispensa token permanente.
Cada alteração envia uma imagem completa; adequado à demonstração acadêmica.
"""

import json
import os
import sqlite3
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from flask import current_app, g, request
from db import ROOT

MAX_DATABASE_BYTES = 4 * 1024 * 1024


class StorageUnavailable(Exception):
    pass


class StorageConflict(Exception):
    pass


class BlobStore:
    def __init__(self):
        self.store_id = os.environ.get("BLOB_STORE_ID", "").removeprefix("store_")
        self.token = request.headers.get("x-vercel-oidc-token") or os.environ.get(
            "VERCEL_OIDC_TOKEN"
        )
        if not self.store_id or not self.token:
            raise StorageUnavailable("Conexão OIDC do armazenamento ausente.")
        # Previews nunca alteram o banco usado na apresentação em produção.
        self.pathname = (
            "vetcare/production.sqlite3"
            if os.environ.get("VERCEL_ENV") == "production"
            else "vetcare/preview.sqlite3"
        )

    def load(self):
        url = f"https://{self.store_id}.private.blob.vercel-storage.com/{self.pathname}?cache=0"
        req = Request(url, headers={"Authorization": "Bearer " + self.token})
        try:
            with urlopen(req, timeout=20) as response:
                data = response.read(MAX_DATABASE_BYTES + 1)
                etag = response.headers.get("ETag")
                if len(data) > MAX_DATABASE_BYTES or not etag:
                    raise StorageUnavailable("Imagem inválida ou acima do limite.")
                return data, etag
        except HTTPError as error:
            if error.code == 404:
                return None
            raise StorageUnavailable("Falha na leitura do armazenamento.") from error
        except (URLError, TimeoutError) as error:
            raise StorageUnavailable("Armazenamento indisponível.") from error

    def save(self, data, etag=None):
        if len(data) > MAX_DATABASE_BYTES:
            raise StorageUnavailable("Banco excede o limite da demonstração.")
        headers = {
            "Authorization": "Bearer " + self.token,
            "x-vercel-blob-store-id": self.store_id,
            "x-api-version": "12",
            "x-api-blob-request-id": str(uuid.uuid4()),
            "x-vercel-blob-access": "private",
            "x-add-random-suffix": "0",
            "x-allow-overwrite": "1" if etag else "0",
            "x-content-type": "application/vnd.sqlite3",
            "Content-Type": "application/octet-stream",
        }
        if etag:
            headers["x-if-match"] = etag
        req = Request(
            "https://vercel.com/api/blob/?pathname=" + self.pathname,
            data=data,
            headers=headers,
            method="PUT",
        )
        try:
            with urlopen(req, timeout=20) as response:
                result = json.load(response)
                if not result.get("etag"):
                    raise StorageUnavailable("Gravação sem versão confirmada.")
                return result["etag"]
        except HTTPError as error:
            try:
                code = json.loads(error.read()).get("error", {}).get("code", "")
            except (ValueError, AttributeError):
                code = ""
            if error.code in (409, 412) or code in (
                "blob_already_exists",
                "precondition_failed",
            ):
                raise StorageConflict() from error
            raise StorageUnavailable("Falha na gravação do armazenamento.") from error
        except (URLError, TimeoutError, ValueError) as error:
            raise StorageUnavailable("Gravação não confirmada.") from error


def open_cloud_database():
    store = current_app.config.get("BLOB_STORE_FACTORY", BlobStore)()
    stored = store.load()
    conn = sqlite3.connect(":memory:")
    try:
        if stored is None:
            conn.executescript(
                (ROOT / "database/01_schema.sql").read_text(encoding="utf-8")
            )
            conn.executescript(
                (ROOT / "database/02_seed.sql").read_text(encoding="utf-8")
            )
            try:
                etag = store.save(conn.serialize())
            except StorageConflict:
                stored = store.load()
                if stored is None:
                    raise StorageUnavailable("Inicialização não confirmada.")
                conn.deserialize(stored[0])
                etag = stored[1]
        else:
            conn.deserialize(stored[0])
            etag = stored[1]
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.blob_store, g.blob_etag = store, etag
        g.db_baseline = conn.total_changes
        return conn
    except Exception:
        conn.close()
        raise


def persist_cloud_database(response):
    conn = g.get("db")
    if (
        conn is not None
        and "blob_store" in g
        and response.status_code < 400
        and conn.total_changes > g.db_baseline
    ):
        conn.commit()
        g.blob_store.save(conn.serialize(), g.blob_etag)
    return response
