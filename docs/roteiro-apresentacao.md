# Roteiro de apresentação

A sequência abaixo demonstra as relações e as regras do banco usando a interface. Os registros criados nesta apresentação devem ser fictícios.

## 1. Apresentar o problema e o modelo

Explique que a consulta liga animal, veterinário e serviço. O animal pertence a um tutor. Prontuário e pagamento são registros dependentes da consulta.

Abra o diagrama e identifique as sete entidades, as FKs e a relação opcional de um prontuário por consulta. Mostre que vários pagamentos podem atender uma única cobrança.

## 2. Cadastrar tutor e animal

Na tela Tutores, crie um cadastro fictício. Na tela Pacientes, crie um animal vinculado a esse tutor. Mostre que o vínculo é obrigatório e que o telefone fica no tutor, sem repetição no animal ou na consulta.

## 3. Demonstrar a agenda

Escolha um horário livre do dia e agende uma consulta. Tente criar outra consulta no mesmo horário com o mesmo veterinário. O sistema deve exibir um conflito.

Repita o teste com outro veterinário e o mesmo animal. Depois agende uma consulta imediatamente após o final da primeira. Use esse exemplo para explicar o intervalo semiaberto.

## 4. Demonstrar o prontuário

Abra a consulta e selecione Atender. Preencha queixa, avaliação e conduta com texto fictício. Salve e confira o status Concluído. Abra o histórico do paciente.

Explique a transação UPDATE + INSERT: se a criação do prontuário falha, a conclusão também é desfeita. Mostre que a consulta concluída não tem edição.

## 5. Demonstrar recebimentos

No Financeiro, receba parte do valor e confira a diminuição do saldo. Tente receber um valor acima do saldo restante. Registre o restante correto e confira que a cobrança sai da lista de saldos.

Explique por que dinheiro usa INTEGER em centavos e por que o saldo é calculado pela view.

## 6. Demonstrar preservação do preço

Agende uma consulta clínica. Altere o preço do serviço no catálogo. Confira que a consulta existente conserva o valor, enquanto um novo agendamento usa o novo preço.

## 7. Examinar o SQL

Abra 01_schema.sql e localize uma PK, uma FK, uma CHECK, uma UNIQUE e um trigger. Execute 03_queries.sql em um banco de demonstração e mostre uma consulta com JOIN e uma agregação de recebimentos.

Execute 04_transactions.sql e explique o ROLLBACK. Os exemplos inserem e removem registros temporários sem deixar alteração permanente.

## Perguntas que o modelo responde

- Por que o prontuário referencia a consulta? A consulta já informa animal, veterinário e serviço.
- Por que não guardar o nome do tutor na consulta? O JOIN obtém esse dado sem duplicação.
- Por que o preço aparece em serviço e consulta? O serviço guarda o catálogo atual, enquanto a consulta conserva a condição do agendamento.
- Por que arquivar? Para retirar opções de novos registros e manter o histórico.
- Por que pagamento é uma tabela separada? Uma cobrança pode receber vários pagamentos em datas e formas diferentes.
- Por que SQLite? A apresentação precisa de um banco relacional em arquivo, sem administrar um servidor externo.

## Antes da apresentação

Verifique se o PDF abre, inicie o app, teste um cadastro e tenha uma cópia do banco. Repetir a apresentação em uma base já preenchida pode ocupar os horários usados nos exemplos. Use outro arquivo de banco para uma demonstração nova.
