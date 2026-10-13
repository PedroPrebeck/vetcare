"""Vínculos compartilhados, acompanhante e preservação do histórico."""

import re, sqlite3, tempfile, unittest
from pathlib import Path
from app import create_app
from db import initialize
from clock import today


class TutorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / "db.sqlite3")
        initialize(self.path, True)
        self.client = create_app({"TESTING": True, "DATABASE": self.path}).test_client()
        html = self.client.get("/").get_data(as_text=True)
        self.headers = {
            "X-CSRF-Token": re.search(r'name="csrf-token" content="([^"]+)"', html)[1]
        }

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, path, data, method="POST"):
        return self.client.open(
            "/api" + path, method=method, json=data, headers=self.headers
        )

    def appointment(self, tutor=2, **changes):
        data = dict(
            pet_id=1,
            accompanying_tutor_id=tutor,
            veterinarian_id=1,
            service_id=1,
            starts_at=today().isoformat() + "T17:00",
        )
        data.update(changes)
        return self.call("/appointments", data)

    def test_second_tutor_is_recorded_without_duplicate_patient(self):
        response = self.appointment()
        self.assertEqual(response.status_code, 201)
        data = self.client.get("/api/bootstrap").get_json()
        self.assertEqual(len(data["pets"]), 8)
        a = next(
            a for a in data["appointments"] if a["id"] == response.get_json()["id"]
        )
        self.assertEqual(a["tutor_name"], "Rafael Santos")
        self.assertEqual(
            next(p for p in data["pets"] if p["id"] == 1)["tutor_ids"], [1, 2]
        )

    def test_missing_or_unlinked_companion_rejected(self):
        self.assertEqual(self.appointment(None).status_code, 400)
        self.assertEqual(self.appointment(3).status_code, 400)

    def test_database_rejects_unlinked_companion(self):
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO appointments(pet_id,accompanying_tutor_id,veterinarian_id,service_id,starts_at,duration_minutes,fee_cents) VALUES(1,3,1,1,'2026-01-01T10:00',30,100)"
                )

    def test_empty_and_duplicate_tutors_rejected(self):
        base = dict(name="Novo pet", species="Cão", sex="Macho")
        for ids in ([], [1, 1], [999]):
            self.assertEqual(
                self.call("/pets", dict(base, tutor_ids=ids)).status_code, 400
            )

    def test_remove_link_preserves_completed_consultation(self):
        pet = next(
            p
            for p in self.client.get("/api/bootstrap").get_json()["pets"]
            if p["id"] == 1
        )
        pet["tutor_ids"] = [2]
        self.assertEqual(self.call("/pets/1", pet, "PATCH").status_code, 200)
        data = self.client.get("/api/pets/1/history").get_json()
        self.assertEqual(data["appointments"][0]["tutor_name"], "Marina Oliveira")
        with sqlite3.connect(self.path) as db:
            self.assertEqual(
                db.execute(
                    "SELECT active FROM pet_tutors WHERE pet_id=1 AND tutor_id=1"
                ).fetchone()[0],
                0,
            )

    def test_open_appointment_blocks_unlink_and_rolls_back_pet_edit(self):
        self.assertEqual(self.appointment().status_code, 201)
        pet = next(
            p
            for p in self.client.get("/api/bootstrap").get_json()["pets"]
            if p["id"] == 1
        )
        pet.update(tutor_ids=[1], name="Não deve salvar")
        self.assertEqual(self.call("/pets/1", pet, "PATCH").status_code, 400)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(
                db.execute("SELECT name FROM pets WHERE id=1").fetchone()[0], "Luna"
            )

    def test_archived_companion_rejected(self):
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE tutors SET active=0 WHERE id=2")
        self.assertEqual(self.appointment().status_code, 400)

    def test_reactivation_and_historical_companion(self):
        pet = next(
            p
            for p in self.client.get("/api/bootstrap").get_json()["pets"]
            if p["id"] == 1
        )
        pet["tutor_ids"] = [2]
        self.assertEqual(self.call("/pets/1", pet, "PATCH").status_code, 200)
        pet["tutor_ids"] = [1, 2]
        self.assertEqual(self.call("/pets/1", pet, "PATCH").status_code, 200)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM pet_tutors WHERE pet_id=1").fetchone()[
                    0
                ],
                2,
            )
