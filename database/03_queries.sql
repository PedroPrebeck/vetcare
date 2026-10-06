-- Consultas didáticas: execute após 01_schema.sql e 02_seed.sql.
PRAGMA foreign_keys=ON;

-- Q1: agenda do dia, com JOIN entre as entidades do atendimento.
SELECT a.id,substr(a.starts_at,12,5) AS horario,p.name AS animal,
 t.name AS tutor,v.name AS veterinario,s.name AS servico,a.status
FROM appointments a
JOIN pets p ON p.id=a.pet_id
JOIN tutors t ON t.id=p.tutor_id
JOIN veterinarians v ON v.id=a.veterinarian_id
JOIN services s ON s.id=a.service_id
WHERE substr(a.starts_at,1,10)=date('now','-3 hours')
ORDER BY a.starts_at;

-- Q2: animais de cada tutor. LEFT JOIN inclui quem não tem animal cadastrado.
SELECT t.id,t.name,COUNT(p.id) AS animais_ativos
FROM tutors t LEFT JOIN pets p ON p.tutor_id=t.id AND p.active=1
GROUP BY t.id,t.name ORDER BY animais_ativos DESC,t.name;

-- Q3: receita por forma de pagamento no mês corrente.
-- Receita significa caixa recebido, não soma dos serviços agendados.
SELECT method,SUM(amount_cents) / 100.0 AS recebido_reais
FROM payments
WHERE substr(paid_at,1,7)=strftime('%Y-%m','now','-3 hours')
GROUP BY method ORDER BY recebido_reais DESC;

-- Q4: consultas concluídas com saldo. A view agrega pagamentos uma única vez.
SELECT a.id,p.name AS animal,t.name AS tutor,
 a.fee_cents / 100.0 AS valor_reais,
 a.received_cents / 100.0 AS recebido_reais,
 a.balance_cents / 100.0 AS saldo_reais
FROM appointment_balances a
JOIN pets p ON p.id=a.pet_id JOIN tutors t ON t.id=p.tutor_id
WHERE a.status='Concluído' AND a.balance_cents>0
ORDER BY a.starts_at;

-- Q5: histórico clínico. Troque 1 pelo ID desejado ao executar no SQLite.
SELECT a.starts_at,v.name AS veterinario,r.complaint,r.diagnosis,
 r.treatment,r.weight_kg
FROM medical_records r
JOIN appointments a ON a.id=r.appointment_id
JOIN veterinarians v ON v.id=a.veterinarian_id
WHERE a.pet_id=1 ORDER BY a.starts_at DESC;

-- Q6: volume de atendimentos concluídos por veterinário.
SELECT v.name,COUNT(a.id) AS atendimentos
FROM veterinarians v LEFT JOIN appointments a
 ON a.veterinarian_id=v.id AND a.status='Concluído'
GROUP BY v.id,v.name ORDER BY atendimentos DESC;

-- Q7: inspeção da integridade física e dos vínculos.
PRAGMA integrity_check;
PRAGMA foreign_key_check;

-- Q8: observe o índice usado na consulta de agenda por intervalo.
-- Range de datas aproveita idx_agenda_date, ao contrário de substr na coluna.
EXPLAIN QUERY PLAN SELECT * FROM appointments
WHERE starts_at >= date('now','-3 hours') || 'T00:00'
 AND starts_at < date('now','-3 hours','+1 day') || 'T00:00';
