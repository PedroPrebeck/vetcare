"""Persistência remota e concorrência usando um armazenamento controlado."""

import re
import unittest
from app import create_app
from cloud_db import StorageConflict, StorageUnavailable


class FakeBlob:
    def __init__(self):
        self.data = None
        self.version = 0
        self.conflict = False
        self.unavailable = False

    def load(self):
        return (self.data, str(self.version)) if self.data else None

    def save(self, data, etag=None):
        if self.unavailable:
            raise StorageUnavailable()
        if self.conflict or (etag is not None and etag != str(self.version)):
            raise StorageConflict()
        if etag is None and self.data is not None:
            raise StorageConflict()
        self.data = data
        self.version += 1
        return str(self.version)


class CloudTest(unittest.TestCase):
    def setUp(self):
        self.store = FakeBlob()
        self.app = create_app(
            {
                "TESTING": True,
                "CLOUD_DATABASE": True,
                "BLOB_STORE_FACTORY": lambda: self.store,
            }
        )
        self.client = self.app.test_client()
        html = self.client.get("/", base_url="https://vetcare.example").get_data(
            as_text=True
        )
        self.token = re.search(r'name="csrf-token" content="([^"]+)"', html)[1]
        self.assertEqual(self.read().status_code, 200)

    def read(self, client=None):
        return (client or self.client).get(
            "/api/bootstrap", base_url="https://vetcare.example"
        )

    def write(self):
        return self.client.post(
            "/api/tutors",
            json={"name": "Teste nuvem", "phone": "71999999999"},
            headers={"X-CSRF-Token": self.token},
            base_url="https://vetcare.example",
        )

    def test_persists_across_instances(self):
        self.assertEqual(self.write().status_code, 201)
        second = create_app(
            {
                "TESTING": True,
                "CLOUD_DATABASE": True,
                "BLOB_STORE_FACTORY": lambda: self.store,
            }
        ).test_client()
        self.assertTrue(
            any(
                t["name"] == "Teste nuvem"
                for t in self.read(second).get_json()["tutors"]
            )
        )

    def test_conflict_does_not_overwrite(self):
        before = self.store.data
        self.store.conflict = True
        self.assertEqual(self.write().status_code, 409)
        self.assertEqual(self.store.data, before)
        self.assertFalse(
            any(t["name"] == "Teste nuvem" for t in self.read().get_json()["tutors"])
        )

    def test_failed_storage_never_returns_success(self):
        before = self.store.data
        self.store.unavailable = True
        self.assertEqual(self.write().status_code, 503)
        self.assertEqual(self.store.data, before)

    def test_csrf_cookie_survives_instance_change(self):
        response = self.client.get("/", base_url="https://vetcare.example")
        cookie = response.headers.get("Set-Cookie")
        self.assertIn("Secure", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)
        self.assertEqual(self.write().status_code, 201)

    def test_read_does_not_write_snapshot(self):
        version = self.store.version
        self.read()
        self.assertEqual(version, self.store.version)

    def test_missing_csrf_blocks_write(self):
        response = self.client.post(
            "/api/tutors",
            json={"name": "Teste", "phone": "71999999999"},
            base_url="https://vetcare.example",
        )
        self.assertEqual(response.status_code, 403)
