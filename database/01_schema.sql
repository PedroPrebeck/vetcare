-- VetCare | SQLite 3.37+ | criação não destrutiva, esquema versão 2.
-- Cada conexão deve habilitar foreign_keys. Valores monetários são CENTAVOS.
PRAGMA foreign_keys = ON;
BEGIN;
CREATE TABLE IF NOT EXISTS tutors (
 id INTEGER PRIMARY KEY,
 name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 2 AND 100),
 phone TEXT NOT NULL CHECK(length(trim(phone)) BETWEEN 8 AND 25),
 email TEXT CHECK(email IS NULL OR length(email) <= 150),
 address TEXT NOT NULL DEFAULT '' CHECK(length(address) <= 250),
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
) STRICT;
CREATE TABLE IF NOT EXISTS pets (
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
-- Vínculo N:N. Arquivar o vínculo preserva a referência das consultas antigas.
CREATE TABLE IF NOT EXISTS pet_tutors (
 pet_id INTEGER NOT NULL REFERENCES pets(id) ON DELETE RESTRICT,
 tutor_id INTEGER NOT NULL REFERENCES tutors(id) ON DELETE RESTRICT,
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 PRIMARY KEY(pet_id,tutor_id)
) STRICT;
CREATE TABLE IF NOT EXISTS veterinarians (
 id INTEGER PRIMARY KEY,
 name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 2 AND 100),
 crmv TEXT NOT NULL UNIQUE CHECK(length(trim(crmv)) BETWEEN 3 AND 30),
 specialty TEXT NOT NULL DEFAULT 'Clínica geral' CHECK(length(specialty) <= 100),
 phone TEXT NOT NULL DEFAULT '' CHECK(length(phone) <= 25),
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1))
) STRICT;
CREATE TABLE IF NOT EXISTS services (
 id INTEGER PRIMARY KEY,
 name TEXT NOT NULL UNIQUE CHECK(length(trim(name)) BETWEEN 2 AND 100),
 price_cents INTEGER NOT NULL CHECK(price_cents >= 0),
 duration_minutes INTEGER NOT NULL DEFAULT 30 CHECK(duration_minutes BETWEEN 10 AND 240),
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1))
) STRICT;
-- Preço e duração são snapshots: alterações no catálogo não reescrevem o passado.
-- Datas da agenda usam horário civil America/Sao_Paulo: YYYY-MM-DDTHH:MM.
CREATE TABLE IF NOT EXISTS appointments (
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
CREATE TABLE IF NOT EXISTS medical_records (
 id INTEGER PRIMARY KEY,
 appointment_id INTEGER NOT NULL UNIQUE REFERENCES appointments(id) ON DELETE RESTRICT,
 complaint TEXT NOT NULL CHECK(length(trim(complaint)) BETWEEN 2 AND 4000),
 diagnosis TEXT NOT NULL CHECK(length(trim(diagnosis)) BETWEEN 2 AND 4000),
 treatment TEXT NOT NULL DEFAULT '' CHECK(length(treatment) <= 4000),
 weight_kg REAL CHECK(weight_kg IS NULL OR weight_kg > 0),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
) STRICT;
CREATE TABLE IF NOT EXISTS payments (
 id INTEGER PRIMARY KEY,
 appointment_id INTEGER NOT NULL REFERENCES appointments(id) ON DELETE RESTRICT,
 amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
 method TEXT NOT NULL CHECK(method IN ('Pix','Dinheiro','Cartão')),
 paid_at TEXT NOT NULL CHECK(date(paid_at,'+0 days') IS NOT NULL AND date(paid_at,'+0 days')=paid_at),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
) STRICT;
-- Índices nas FKs e na agenda evitam varreduras nas consultas mais frequentes.
CREATE INDEX IF NOT EXISTS idx_pet_tutors_tutor ON pet_tutors(tutor_id,active);
CREATE INDEX IF NOT EXISTS idx_appointments_companion ON appointments(accompanying_tutor_id);
CREATE INDEX IF NOT EXISTS idx_agenda_vet ON appointments(veterinarian_id,starts_at);
CREATE INDEX IF NOT EXISTS idx_agenda_pet ON appointments(pet_id,starts_at);
CREATE INDEX IF NOT EXISTS idx_agenda_service ON appointments(service_id);
CREATE INDEX IF NOT EXISTS idx_agenda_date ON appointments(starts_at,status);
CREATE INDEX IF NOT EXISTS idx_payments_appointment ON payments(appointment_id);
-- Novas consultas exigem um tutor ativo e vinculado ao animal.
-- NULL é reservado aos registros anteriores à migração, não aos novos INSERTs.
CREATE TRIGGER IF NOT EXISTS appointment_companion_insert BEFORE INSERT ON appointments
BEGIN
 SELECT RAISE(ABORT,'Selecione um tutor ativo vinculado ao paciente.')
 WHERE NEW.accompanying_tutor_id IS NULL OR NOT EXISTS (
 SELECT 1 FROM pet_tutors pt JOIN tutors t ON t.id=pt.tutor_id
 WHERE pt.pet_id=NEW.pet_id AND pt.tutor_id=NEW.accompanying_tutor_id AND pt.active=1 AND t.active=1);
END;
CREATE TRIGGER IF NOT EXISTS appointment_companion_update BEFORE UPDATE OF pet_id,accompanying_tutor_id ON appointments
WHEN NEW.pet_id IS NOT OLD.pet_id OR NEW.accompanying_tutor_id IS NOT OLD.accompanying_tutor_id
BEGIN
 SELECT RAISE(ABORT,'Selecione um tutor ativo vinculado ao paciente.')
 WHERE NEW.accompanying_tutor_id IS NULL OR NOT EXISTS (
 SELECT 1 FROM pet_tutors pt JOIN tutors t ON t.id=pt.tutor_id
 WHERE pt.pet_id=NEW.pet_id AND pt.tutor_id=NEW.accompanying_tutor_id AND pt.active=1 AND t.active=1);
END;
-- Intervalos semiabertos [início,fim): consultas consecutivas são permitidas.
CREATE TRIGGER IF NOT EXISTS appointment_no_overlap_insert BEFORE INSERT ON appointments
WHEN NEW.status <> 'Cancelado'
BEGIN
 SELECT RAISE(ABORT,'Conflito de horário: veterinário ou paciente ocupado.')
 WHERE EXISTS(SELECT 1 FROM appointments a WHERE a.status <> 'Cancelado'
 AND (a.veterinarian_id=NEW.veterinarian_id OR a.pet_id=NEW.pet_id)
 AND datetime(a.starts_at) < datetime(NEW.starts_at,'+' || NEW.duration_minutes || ' minutes')
 AND datetime(NEW.starts_at) < datetime(a.starts_at,'+' || a.duration_minutes || ' minutes'));
END;
CREATE TRIGGER IF NOT EXISTS appointment_no_overlap_update BEFORE UPDATE ON appointments
WHEN NEW.status <> 'Cancelado'
BEGIN
 SELECT RAISE(ABORT,'Conflito de horário: veterinário ou paciente ocupado.')
 WHERE EXISTS(SELECT 1 FROM appointments a WHERE a.id <> NEW.id AND a.status <> 'Cancelado'
 AND (a.veterinarian_id=NEW.veterinarian_id OR a.pet_id=NEW.pet_id)
 AND datetime(a.starts_at) < datetime(NEW.starts_at,'+' || NEW.duration_minutes || ' minutes')
 AND datetime(NEW.starts_at) < datetime(a.starts_at,'+' || a.duration_minutes || ' minutes'));
END;
CREATE TRIGGER IF NOT EXISTS appointment_history_guard BEFORE UPDATE ON appointments
WHEN EXISTS(SELECT 1 FROM medical_records WHERE appointment_id=OLD.id)
BEGIN SELECT RAISE(ABORT,'Consulta com prontuário não pode ser alterada.'); END;
CREATE TRIGGER IF NOT EXISTS appointment_finance_guard BEFORE UPDATE ON appointments
WHEN (NEW.status='Cancelado' OR NEW.pet_id<>OLD.pet_id OR NEW.veterinarian_id<>OLD.veterinarian_id OR NEW.service_id<>OLD.service_id OR NEW.fee_cents < (SELECT COALESCE(SUM(amount_cents),0) FROM payments WHERE appointment_id=OLD.id))
 AND EXISTS(SELECT 1 FROM payments WHERE appointment_id=OLD.id)
BEGIN SELECT RAISE(ABORT,'Consulta com recebimentos não pode trocar vínculos, ser cancelada ou ter valor inferior ao recebido.'); END;
CREATE TRIGGER IF NOT EXISTS record_completed_only BEFORE INSERT ON medical_records
BEGIN
 SELECT RAISE(ABORT,'Prontuário exige consulta concluída.')
 WHERE COALESCE((SELECT status FROM appointments WHERE id=NEW.appointment_id),'') <> 'Concluído';
END;
CREATE TRIGGER IF NOT EXISTS payment_limit BEFORE INSERT ON payments
BEGIN
 SELECT RAISE(ABORT,'Pagamento excede o saldo ou consulta está cancelada.')
 WHERE NOT EXISTS(SELECT 1 FROM appointments a WHERE a.id=NEW.appointment_id AND a.status <> 'Cancelado'
 AND NEW.amount_cents + (SELECT COALESCE(SUM(amount_cents),0) FROM payments WHERE appointment_id=a.id) <= a.fee_cents);
END;
-- Recebimentos e prontuários são append-only no escopo didático, estorno é evolução futura.
CREATE TRIGGER IF NOT EXISTS payment_no_update BEFORE UPDATE ON payments
BEGIN SELECT RAISE(ABORT,'Recebimentos não podem ser editados.'); END;
CREATE TRIGGER IF NOT EXISTS payment_no_delete BEFORE DELETE ON payments
BEGIN SELECT RAISE(ABORT,'Recebimentos não podem ser removidos.'); END;
CREATE TRIGGER IF NOT EXISTS record_no_update BEFORE UPDATE ON medical_records
BEGIN SELECT RAISE(ABORT,'Prontuários não podem ser editados.'); END;
CREATE TRIGGER IF NOT EXISTS record_no_delete BEFORE DELETE ON medical_records
BEGIN SELECT RAISE(ABORT,'Prontuários não podem ser removidos.'); END;
-- A view calcula saldo, evitando armazenar um total derivado sujeito a inconsistências.
CREATE VIEW IF NOT EXISTS appointment_balances AS
 SELECT a.*, COALESCE(p.received_cents,0) AS received_cents,
 a.fee_cents - COALESCE(p.received_cents,0) AS balance_cents
 FROM appointments a LEFT JOIN
 (SELECT appointment_id,SUM(amount_cents) AS received_cents FROM payments GROUP BY appointment_id) p
 ON p.appointment_id=a.id;
PRAGMA user_version = 2;
COMMIT;
