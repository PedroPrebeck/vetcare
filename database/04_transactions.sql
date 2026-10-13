-- Exemplos de DML sem efeito permanente: cada transação termina em ROLLBACK.
-- Use um banco de demonstração. IDs negativos são reservados aqui para os exemplos.
PRAGMA foreign_keys=ON;

-- INSERT: cadastrar tutor e animal vinculados de forma atômica.
BEGIN IMMEDIATE;
INSERT INTO tutors(id,name,phone) VALUES(-1,'Tutor de exemplo','(71) 99999-0000');
INSERT INTO pets(id,name,species,sex) VALUES(-1,'Animal exemplo','Cão','Macho');
INSERT INTO pet_tutors(pet_id,tutor_id) VALUES(-1,-1);
SELECT p.name,t.name FROM pets p JOIN pet_tutors pt ON pt.pet_id=p.id JOIN tutors t ON t.id=pt.tutor_id WHERE p.id=-1;
ROLLBACK;

-- UPDATE: alterar preço do catálogo. A consulta antiga conserva fee_cents.
BEGIN;
UPDATE services SET price_cents=20000 WHERE id=1;
SELECT s.price_cents AS preco_atual,a.fee_cents AS preco_da_consulta
FROM services s JOIN appointments a ON a.service_id=s.id WHERE s.id=1;
ROLLBACK;

-- DELETE: remover apenas registros de exemplo sem dependências restantes.
-- A interface usa arquivamento para os cadastros da clínica.
BEGIN;
INSERT INTO tutors(id,name,phone) VALUES(-2,'Tutor temporário','(71) 99999-0001');
INSERT INTO pets(id,name,species) VALUES(-2,'Animal temporário','Gato');
INSERT INTO pet_tutors(pet_id,tutor_id) VALUES(-2,-2);
DELETE FROM pet_tutors WHERE pet_id=-2;
DELETE FROM pets WHERE id=-2;
DELETE FROM tutors WHERE id=-2;
ROLLBACK;

-- Na aplicação, concluir um atendimento executa UPDATE + INSERT sob a mesma
-- transação (api.py, finish_appointment). COMMIT ocorre só quando ambos passam.
-- Chaves estrangeiras, checks e triggers também atuam em DML executado fora da API.
