-- Migração 1 -> 2, executada por db.migrate dentro de uma única transação.
-- foreign_keys é desabilitado antes do BEGIN e verificado antes do COMMIT.
-- Faça backup antes. Os dados originais não registravam quem acompanhou o pet.
DROP VIEW IF EXISTS appointment_balances;
DROP TRIGGER IF EXISTS appointment_no_overlap_insert;
DROP TRIGGER IF EXISTS appointment_no_overlap_update;
DROP TRIGGER IF EXISTS appointment_history_guard;
DROP TRIGGER IF EXISTS appointment_finance_guard;
DROP TRIGGER IF EXISTS record_completed_only;
DROP TRIGGER IF EXISTS payment_limit;
DROP TRIGGER IF EXISTS payment_no_update;
DROP TRIGGER IF EXISTS payment_no_delete;
DROP TRIGGER IF EXISTS record_no_update;
DROP TRIGGER IF EXISTS record_no_delete;
CREATE TABLE IF NOT EXISTS pet_tutors (
 pet_id INTEGER NOT NULL REFERENCES pets(id) ON DELETE RESTRICT,
 tutor_id INTEGER NOT NULL REFERENCES tutors(id) ON DELETE RESTRICT,
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 PRIMARY KEY(pet_id,tutor_id)
) STRICT;
INSERT INTO pet_tutors(pet_id,tutor_id) SELECT id,tutor_id FROM pets;
CREATE TABLE pets_v2 (
 id INTEGER PRIMARY KEY,
 name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 80),
 species TEXT NOT NULL CHECK(species IN ('Cão','Gato','Ave','Outro')),
 breed TEXT NOT NULL DEFAULT '' CHECK(length(breed) <= 80),
 sex TEXT NOT NULL DEFAULT 'Não informado' CHECK(sex IN ('Macho','Fêmea','Não informado')),
 birth_date TEXT CHECK(birth_date IS NULL OR (date(birth_date,'+0 days') IS NOT NULL AND date(birth_date,'+0 days') = birth_date)),
 weight_kg REAL CHECK(weight_kg IS NULL OR weight_kg > 0),
 notes TEXT NOT NULL DEFAULT '' CHECK(length(notes) <= 4000),
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
) STRICT;
INSERT INTO pets_v2(id,name,species,breed,sex,birth_date,weight_kg,notes,active,created_at) SELECT id,name,species,breed,sex,birth_date,weight_kg,notes,active,created_at FROM pets;
DROP TABLE pets;
ALTER TABLE pets_v2 RENAME TO pets;
CREATE TABLE appointments_v2 (
 id INTEGER PRIMARY KEY,
 pet_id INTEGER NOT NULL REFERENCES pets(id) ON DELETE RESTRICT,
 accompanying_tutor_id INTEGER,
 veterinarian_id INTEGER NOT NULL REFERENCES veterinarians(id) ON DELETE RESTRICT,
 service_id INTEGER NOT NULL REFERENCES services(id) ON DELETE RESTRICT,
 starts_at TEXT NOT NULL CHECK(length(starts_at)=16 AND strftime('%Y-%m-%dT%H:%M',starts_at,'+0 days') IS NOT NULL AND strftime('%Y-%m-%dT%H:%M',starts_at,'+0 days')=starts_at),
 duration_minutes INTEGER NOT NULL CHECK(duration_minutes BETWEEN 10 AND 240),
 fee_cents INTEGER NOT NULL CHECK(fee_cents >= 0),
 status TEXT NOT NULL DEFAULT 'Agendado' CHECK(status IN ('Agendado','Confirmado','Concluído','Cancelado')),
 notes TEXT NOT NULL DEFAULT '' CHECK(length(notes) <= 4000),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
,
 FOREIGN KEY(pet_id,accompanying_tutor_id) REFERENCES pet_tutors(pet_id,tutor_id) ON DELETE RESTRICT
) STRICT;
INSERT INTO appointments_v2(id,pet_id,veterinarian_id,service_id,starts_at,duration_minutes,fee_cents,status,notes,created_at) SELECT id,pet_id,veterinarian_id,service_id,starts_at,duration_minutes,fee_cents,status,notes,created_at FROM appointments;
DROP TABLE appointments;
ALTER TABLE appointments_v2 RENAME TO appointments;
-- db.migrate recria índices, triggers e view do esquema 2 antes de confirmar.
