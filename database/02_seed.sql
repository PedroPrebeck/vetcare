-- Dados FICTÍCIOS para apresentação. Execute apenas em banco vazio.
-- Agenda relativa à data de São Paulo (UTC-3): a demonstração continua útil em outras datas.
PRAGMA foreign_keys=ON;
BEGIN;
INSERT INTO tutors(id,name,phone,email,address) VALUES
 (1,'Marina Oliveira','(71) 99900-1001','marina@example.com','Salvador, BA'),
 (2,'Rafael Santos','(71) 99900-1002','rafael@example.com','Salvador, BA'),
 (3,'Camila Costa','(71) 99900-1003',NULL,'Lauro de Freitas, BA'),
 (4,'Lucas Almeida','(71) 99900-1004',NULL,'Salvador, BA'),
 (5,'Juliana Lima','(71) 99900-1005','juliana@example.com','Salvador, BA'),
 (6,'Bruno Rocha','(71) 99900-1006',NULL,'Salvador, BA');
INSERT INTO pets(id,name,species,breed,sex,birth_date,weight_kg,notes) VALUES
 (1,'Luna','Cão','Shih-tzu','Fêmea','2022-04-12',5.2,''),
 (2,'Thor','Cão','Golden retriever','Macho','2021-07-20',28.0,''),
 (3,'Mel','Gato','Sem raça definida','Fêmea','2023-01-10',3.8,''),
 (4,'Nino','Gato','Siamês','Macho','2020-11-05',4.5,''),
 (5,'Amora','Cão','Poodle','Fêmea','2024-03-15',4.0,''),
 (6,'Bento','Cão','Sem raça definida','Macho','2022-06-01',12.0,''),
 (7,'Pipoca','Ave','Calopsita','Não informado','2024-01-10',0.09,''),
 (8,'Olívia','Gato','Sem raça definida','Fêmea','2025-02-10',2.7,'');
INSERT INTO pet_tutors(pet_id,tutor_id) VALUES (1,1),(1,2),(2,2),(3,3),(4,4),(5,5),(6,6),(7,1),(8,3);
INSERT INTO veterinarians(id,name,crmv,specialty,phone) VALUES
 (1,'Ana Martins','BA-DEMO-001','Clínica geral','(71) 99900-2001'),
 (2,'Felipe Souza','BA-DEMO-002','Dermatologia','(71) 99900-2002');
INSERT INTO services(id,name,price_cents,duration_minutes) VALUES
 (1,'Consulta clínica',18000,30),(2,'Vacinação',9000,20),
 (3,'Retorno',0,20),(4,'Consulta dermatológica',24000,45);
INSERT INTO appointments(id,pet_id,accompanying_tutor_id,veterinarian_id,service_id,starts_at,duration_minutes,fee_cents,status,notes) VALUES
 (1,1,1,1,1,date('now','-3 hours')||'T08:30',30,18000,'Concluído',''),
 (2,2,2,1,2,date('now','-3 hours')||'T09:30',20,9000,'Confirmado',''),
 (3,3,3,2,4,date('now','-3 hours')||'T10:00',45,24000,'Agendado',''),
 (4,4,4,1,3,date('now','-3 hours')||'T11:00',20,0,'Agendado',''),
 (5,5,5,2,1,date('now','-3 hours')||'T14:00',30,18000,'Confirmado',''),
 (6,6,6,1,1,date('now','-3 hours')||'T15:30',30,18000,'Agendado',''),
 (7,8,3,1,1,date('now','-3 hours','+1 day')||'T09:00',30,18000,'Agendado',''),
 (8,7,1,2,1,date('now','-3 hours','+2 days')||'T10:30',30,18000,'Agendado',''),
 (9,2,2,1,1,date('now','-3 hours','-2 days')||'T10:00',30,18000,'Concluído','');
INSERT INTO medical_records(appointment_id,complaint,diagnosis,treatment,weight_kg) VALUES
 (1,'Avaliação de rotina','Registro fictício para demonstração','Orientações fictícias de acompanhamento',5.2),
 (9,'Avaliação de rotina','Registro fictício para demonstração','Retorno de acompanhamento',28.0);
INSERT INTO payments(appointment_id,amount_cents,method,paid_at) VALUES
 (1,18000,'Pix',date('now','-3 hours')),
 (9,18000,'Cartão',date('now','-3 hours','-2 days'));
COMMIT;
