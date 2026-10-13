"""Migração do banco anterior sem perder os fatos do atendimento."""

import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch
from db import migrate, ROOT


class MigrationTest(unittest.TestCase):
    def old_database(self):
        db = sqlite3.connect(":memory:")
        db.executescript((ROOT / "tests/fixtures/schema_v1.sql").read_text())
        db.executescript(
            """INSERT INTO tutors(id,name,phone) VALUES(1,'Tutor antigo','71999999999');
        INSERT INTO pets(id,tutor_id,name,species) VALUES(1,1,'Pet antigo','Cão');
        INSERT INTO veterinarians(id,name,crmv) VALUES(1,'Vet antigo','DEMO');
        INSERT INTO services(id,name,price_cents) VALUES(1,'Consulta',10000);
        INSERT INTO appointments(id,pet_id,veterinarian_id,service_id,starts_at,duration_minutes,fee_cents,status) VALUES(1,1,1,1,'2026-01-01T10:00',30,10000,'Concluído');
        INSERT INTO medical_records(appointment_id,complaint,diagnosis) VALUES(1,'Queixa antiga','Avaliação antiga');
        INSERT INTO payments(appointment_id,amount_cents,method,paid_at) VALUES(1,5000,'Pix','2026-01-01');"""
        )
        return db

    def test_preserves_history_without_inventing_companion(self):
        db = self.old_database()
        migrate(db)
        self.assertEqual(
            db.execute("SELECT pet_id,tutor_id FROM pet_tutors").fetchall(), [(1, 1)]
        )
        self.assertIsNone(
            db.execute("SELECT accompanying_tutor_id FROM appointments").fetchone()[0]
        )
        self.assertEqual(
            db.execute("SELECT balance_cents FROM appointment_balances").fetchone()[0],
            5000,
        )
        self.assertEqual(
            db.execute("SELECT complaint FROM medical_records").fetchone()[0],
            "Queixa antiga",
        )
        self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
        self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertFalse(migrate(db))

    def test_failure_rolls_back_entire_migration(self):
        db = self.old_database()
        original = Path.read_text

        def broken(path, *args, **kwargs):
            value = original(path, *args, **kwargs)
            return (
                value + "\nSELECT * FROM nonexistent_table;\n"
                if path.name == "05_migrate_tutors.sql"
                else value
            )

        with patch.object(Path, "read_text", broken):
            with self.assertRaises(sqlite3.OperationalError):
                migrate(db)
        self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 1)
        self.assertEqual(db.execute("SELECT tutor_id FROM pets").fetchone()[0], 1)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM payments").fetchone()[0], 1)
        self.assertEqual(db.execute("PRAGMA foreign_keys").fetchone()[0], 1)
