# Auditoria do Controle Financeiro

## Correções críticas P0 — etapa 1

- [x] Backup e restauração globais restritos a administradores na interface,
  controller e service. Novos backups não exportam tokens de recuperação.
- [x] Transferências entre contas executadas em uma única conexão e transação,
  com rollback integral em qualquer falha.
- [x] Baixa de agendamentos atômica e idempotente, com vínculo persistente e
  único entre agendamento e transação.
- [x] Pagamento de faturas atômico e idempotente, com registro persistente da
  operação e rollback integral.

Esses itens são cobertos pelos testes em `tests/integration/`.

## Itens posteriores — não alterados nesta etapa

- [ ] Recuperação de senha.
- [x] Encerramento da própria conta com senha, bloqueio de acesso e histórico preservado (test.6).
- [ ] Eliminação definitiva dos dados pessoais.
- [ ] Detecção de importação duplicada.
- [x] Tratamento de erros, datas legadas e transações sem favorecido nos relatórios (test.6).
- [ ] Migração de hash de senha.
- [ ] Migração de valores monetários para `Decimal` ou centavos inteiros.
- [ ] Melhorias gerais de acessibilidade e experiência de uso.

## Atualização test.6

Causas, soluções, preservação dos bancos e evidências de validação:
[relatório da auditoria](docs/RELATORIOS_CONTAS_FAVORECIDOS_TEST6.md).
