"""Testes de integração em banco temporário. Nenhum dado real é alterado."""

import re
import sqlite3
import tempfile
import unittest
from pathlib import Path
from clock import today
from app import create_app
from db import initialize


class VetCareTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / "test.sqlite3")
        initialize(self.path, demo=True)
        self.app = create_app(
            {"TESTING": True, "DATABASE": self.path, "SECRET_KEY": "test-secret"}
        )
        self.client = self.app.test_client()
        html = self.client.get("/").get_data(as_text=True)
        token = re.search(r'name="csrf-token" content="([^"]+)"', html)[1]
        self.headers = {"X-CSRF-Token": token}
        self.today = today().isoformat()

    def tearDown(self):
        self.tmp.cleanup()

    def post(self, path, data):
        return self.client.post("/api" + path, json=data, headers=self.headers)

    def patch(self, path, data):
        return self.client.patch("/api" + path, json=data, headers=self.headers)

    def read(self):
        return self.client.get("/api/bootstrap").get_json()

    def appointment(self, **changes):
        data = dict(
            pet_id=6,
            veterinarian_id=1,
            service_id=1,
            starts_at=self.today + "T17:00",
            notes="",
        )
        data.update(changes)
        return self.post("/appointments", data)

    def test_bootstrap(self):
        data = self.read()
        self.assertEqual(len(data["pets"]), 8)
        self.assertEqual(len(data["appointments"]), 9)
        self.assertEqual(data["dashboard"]["patients"], 8)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_csrf_required(self):
        self.assertEqual(self.client.post("/api/tutors", json={}).status_code, 403)

    def test_json_required(self):
        self.assertEqual(
            self.client.post(
                "/api/tutors", data="broken", headers=self.headers
            ).status_code,
            400,
        )

    def test_full_workflow(self):
        t = self.post(
            "/tutors",
            dict(name="Tutor teste", phone="71999999999", email="", address=""),
        ).get_json()["id"]
        p = self.post(
            "/pets",
            dict(
                tutor_id=t,
                name="Animal teste",
                species="Cão",
                breed="",
                sex="Macho",
                birth_date="",
                weight_kg="2.5",
                notes="",
            ),
        ).get_json()["id"]
        a = self.appointment(pet_id=p).get_json()["id"]
        self.assertEqual(
            self.patch(f"/appointments/{a}", dict(status="Confirmado")).status_code, 200
        )
        result = self.post(
            f"/appointments/{a}/record",
            dict(
                complaint="Rotina",
                diagnosis="Exemplo fictício",
                treatment="Acompanhamento",
                weight_kg="2.6",
            ),
        )
        self.assertEqual(result.status_code, 201, result.get_json())
        self.assertEqual(
            self.post(
                "/payments",
                dict(
                    appointment_id=a, amount="50.00", method="Pix", paid_at=self.today
                ),
            ).status_code,
            201,
        )
        balance = next(x for x in self.read()["appointments"] if x["id"] == a)
        self.assertEqual(balance["balance_cents"], 13000)
        history = self.client.get(f"/api/pets/{p}/history").get_json()
        self.assertEqual(len(history["records"]), 1)

    def test_vet_overlap(self):
        self.assertEqual(
            self.appointment(pet_id=8, starts_at=self.today + "T09:35").status_code, 409
        )

    def test_pet_overlap_other_vet(self):
        self.assertEqual(
            self.appointment(
                pet_id=2, veterinarian_id=2, starts_at=self.today + "T09:35"
            ).status_code,
            409,
        )

    def test_adjacent_allowed(self):
        self.assertEqual(
            self.appointment(pet_id=8, starts_at=self.today + "T09:50").status_code, 201
        )

    def test_update_overlap(self):
        a = self.appointment().get_json()["id"]
        self.assertEqual(
            self.patch(
                f"/appointments/{a}",
                dict(
                    pet_id=6,
                    veterinarian_id=1,
                    service_id=1,
                    starts_at=self.today + "T09:35",
                    notes="",
                ),
            ).status_code,
            409,
        )

    def test_cancel_releases_slot(self):
        self.assertEqual(
            self.patch("/appointments/2", dict(status="Cancelado")).status_code, 200
        )
        self.assertEqual(
            self.appointment(pet_id=8, starts_at=self.today + "T09:30").status_code, 201
        )

    def test_overpayment_blocked(self):
        result = self.post(
            "/payments",
            dict(appointment_id=2, amount="90.01", method="Pix", paid_at=self.today),
        )
        self.assertEqual(result.status_code, 409)
        self.assertEqual(
            next(a for a in self.read()["appointments"] if a["id"] == 2)[
                "received_cents"
            ],
            0,
        )

    def test_paid_cannot_cancel(self):
        self.post(
            "/payments",
            dict(appointment_id=2, amount="10.00", method="Pix", paid_at=self.today),
        )
        self.assertEqual(
            self.patch("/appointments/2", dict(status="Cancelado")).status_code, 409
        )

    def test_snapshot(self):
        self.patch(
            "/services/1",
            dict(name="Consulta clínica", price="200.00", duration_minutes=40),
        )
        a = self.appointment().get_json()["id"]
        data = self.read()["appointments"]
        self.assertEqual(next(x for x in data if x["id"] == 6)["fee_cents"], 18000)
        self.assertEqual(next(x for x in data if x["id"] == a)["fee_cents"], 20000)

    def test_history_protected(self):
        self.assertEqual(
            self.patch("/appointments/1", dict(status="Cancelado")).status_code, 400
        )
        with sqlite3.connect(self.path) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM medical_records WHERE appointment_id=1")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE payments SET amount_cents=1 WHERE id=1")

    def test_invalid_record_does_not_finish(self):
        self.assertEqual(
            self.post(
                "/appointments/2/record", dict(complaint="a", diagnosis="")
            ).status_code,
            400,
        )
        self.assertEqual(
            next(a for a in self.read()["appointments"] if a["id"] == 2)["status"],
            "Confirmado",
        )

    def test_transaction_rolls_back_on_record_failure(self):
        with sqlite3.connect(self.path) as db:
            db.execute(
                "CREATE TRIGGER force_record_failure BEFORE INSERT ON medical_records BEGIN SELECT RAISE(ABORT,'Falha simulada'); END"
            )
        result = self.post(
            "/appointments/2/record",
            dict(
                complaint="Rotina",
                diagnosis="Exemplo fictício",
                treatment="",
                weight_kg="",
            ),
        )
        self.assertEqual(result.status_code, 409)
        self.assertEqual(
            next(a for a in self.read()["appointments"] if a["id"] == 2)["status"],
            "Confirmado",
        )

    def test_payment_protects_links(self):
        self.post(
            "/payments",
            dict(appointment_id=2, amount="10.00", method="Pix", paid_at=self.today),
        )
        result = self.patch(
            "/appointments/2",
            dict(
                pet_id=8,
                veterinarian_id=1,
                service_id=2,
                starts_at=self.today + "T09:30",
                notes="",
            ),
        )
        self.assertEqual(result.status_code, 409)

    def test_fk_direct(self):
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO pets(tutor_id,name,species) VALUES (999,'Teste','Cão')"
                )

    def test_archive_guard(self):
        self.assertEqual(self.patch("/tutors/1", dict(active=0)).status_code, 400)
        self.assertEqual(self.patch("/pets/2", dict(active=0)).status_code, 400)
        self.assertEqual(self.patch("/pets/7", dict(active=2)).status_code, 400)

    def test_crmv_unique(self):
        self.assertEqual(
            self.post(
                "/veterinarians",
                dict(
                    name="Novo Vet",
                    crmv="BA-DEMO-001",
                    specialty="Clínica geral",
                    phone="",
                ),
            ).status_code,
            409,
        )

    def test_precision(self):
        self.assertEqual(
            self.post(
                "/payments",
                dict(
                    appointment_id=2, amount="1.001", method="Pix", paid_at=self.today
                ),
            ).status_code,
            400,
        )

    def test_seed_preserves_existing(self):
        with self.assertRaises(ValueError):
            initialize(self.path, demo=True)
        self.assertEqual(len(self.read()["pets"]), 8)

    def test_database_date_constraint(self):
        with sqlite3.connect(self.path) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO pets(tutor_id,name,species,birth_date) VALUES (1,'Teste','Cão','2026-02-30')"
                )


if __name__ == "__main__":
    unittest.main()
