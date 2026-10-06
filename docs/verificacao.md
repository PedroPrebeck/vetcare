# Verificação da versão 1.0

Verificação executada em 6 de outubro de 2026 com Python 3.12, SQLite 3.53.1 e Chromium 153.0.8010.0.

## Banco e API

Comando: `python -m unittest discover -s tests -v`.

Resultado: 22 testes passaram. A suíte usa banco temporário e cobre:

- Carga inicial e integridade física do banco.
- Cadastro de tutor e animal, agendamento, conclusão e pagamento parcial.
- Exigência de token CSRF e objeto JSON.
- Conflitos por veterinário e animal, horários adjacentes e reagendamento.
- Liberação de horário após cancelamento.
- Bloqueio de pagamento acima do saldo e de cancelamento após receber.
- Bloqueio de troca dos vínculos da consulta após receber.
- Preservação do preço acordado após mudar o catálogo.
- Imutabilidade de pagamentos e prontuários.
- Rollback da conclusão quando o INSERT do prontuário falha.
- Ausência de conclusão quando os campos clínicos são inválidos.
- Chaves estrangeiras, unicidade de CRMV e restrições de arquivamento.
- Recusa de valores com mais de duas casas decimais e datas inexistentes.
- Recusa do seed em um banco já preenchido, preservando os dados.

Os quatro scripts SQL foram executados em sequência em uma base de demonstração. `integrity_check` devolveu `ok`, e `foreign_key_check` não encontrou violações. Os exemplos de transações conservaram seis tutores, oito animais e nove consultas após seus rollbacks.

## Interface

O fluxo foi executado pelo navegador: criar tutor, vincular animal, agendar consulta, preencher prontuário e receber R$ 50,00 de uma consulta de R$ 180,00. O financeiro exibiu saldo de R$ 130,00, e o histórico exibiu o prontuário salvo.

A visualização foi inspecionada em 1440 px e 390 px de largura. Não foram observados erros de JavaScript nem rolagem horizontal no documento. As tabelas mantêm uma área própria de rolagem em telas pequenas.

A captura da visão geral foi feita antes dos cadastros de teste, usando apenas os dados fictícios do seed. O PDF foi renderizado e inspecionado para conferir tabelas, diagramas, sumário e scripts.

## Alcance da verificação

Os comandos foram executados no Linux. Os comandos do README para Windows usam o executável do ambiente virtual sem ativação, mas não foram executados em uma instalação Windows nesta verificação. Não foram realizados testes de carga, avaliação clínica dos registros ou ensaio de operação em produção.
