# Revisão final das correções P0

**Projeto:** ControleFinanceiro
**Data:** 26/07/2026
**Escopo:** correção exclusiva dos bloqueadores registrados na revisão P0
**Commit/push:** não realizados

## 1. Recomendação final

**SEGURO PARA COMMIT COM RESSALVAS**

Os bloqueadores técnicos das correções P0 foram eliminados e as duas formas exigidas de execução do pytest concluíram com 51 testes aprovados. A ressalva é de higiene do worktree: há mudanças preexistentes e não relacionadas misturadas no diretório, portanto o commit deve selecionar explicitamente apenas os arquivos P0 listados neste relatório. Não deve ser usado `git add .`.

Não foram implementados itens P1 nem realizadas refatorações gerais.

## 2. Resultado dos bloqueadores

### 2.1. Propriedade de conexão em `Database.unit_of_work`

**Status: CORRIGIDO.**

Implementação:

- `Database._connection_state` preserva conexão, estado transacional e condição de compartilhamento (`database/database.py:1008`).
- `Database._bind_connection` vincula temporariamente sem fechar a conexão anterior (`database/database.py:994`).
- `Database._restore_connection_state` restaura integralmente o participante (`database/database.py:1021`).
- `Database.unit_of_work` restaura os participantes no `finally` e restaura também o estado anterior do proprietário (`database/database.py:1026-1072`).
- `Database.close`, `commit` e `rollback` recusam operações feitas por participante sobre conexão compartilhada (`database/database.py:96-108`, `database/database.py:976-992`).
- Unidade aninhada é explicitamente recusada com `RuntimeError` claro (`database/database.py:1042-1045`).
- Participante que já possui transação ativa é recusado antes de qualquer troca de conexão (`database/database.py:1047-1052`).
- O rollback e o begin usam a mesma conexão local capturada pela unidade de trabalho.

Política final:

1. Cada `Database` permanece proprietário da conexão que abriu.
2. A conexão do participante é preservada, nunca fechada silenciosamente.
3. Durante a unidade de trabalho, o participante recebe temporariamente a conexão do proprietário e não pode fechá-la, confirmá-la ou revertê-la.
4. No encerramento, com sucesso ou erro, a conexão e os estados anteriores são restaurados.
5. Unidade aninhada não é suportada e é recusada explicitamente.

Evidências:

- `tests/integration/test_unit_of_work.py:6-143`.
- Participante vinculado e restaurado.
- Proprietário utilizável depois de `participant.close()`.
- Participante utilizável depois da unidade.
- Restauração após exceção.
- Recusa sem dano de participante com transação ativa.
- Recusa de aninhamento.
- Um único `COMMIT` no sucesso.
- Um único `ROLLBACK` na falha.

### 2.2. Restauração de backup

**Status: CORRIGIDO.**

Implementação:

- Ordem de restauração explícita em `BackupModel.RESTORE_ORDER` (`models/backup_model.py:35-49`).
- Ordem de exclusão explicitamente inversa (`models/backup_model.py:51`).
- A reinserção não depende mais da ordem do dicionário (`models/backup_model.py:160-174`).
- A restauração executa `BEGIN IMMEDIATE`, mantém `foreign_keys` ativo e usa `defer_foreign_keys` apenas durante a transação (`models/backup_model.py:152-155`).
- `PRAGMA foreign_key_check` é executado antes do commit (`models/backup_model.py:176-183`).
- Qualquer falha executa rollback integral na mesma conexão (`models/backup_model.py:185-190`).
- Tabelas desconhecidas no payload são recusadas antes da alteração do banco (`models/backup_model.py:142-147`).
- Nomes usam microssegundos e UUID, com criação exclusiva do arquivo (`models/backup_model.py:104-111`).
- Backup preventivo usa prefixo próprio e tem colisão explicitamente verificada (`services/backup_service.py:121-145`).
- Falha no preventivo cancela a restauração antes de qualquer modificação.
- O caminho do preventivo é retornado tanto no sucesso quanto na falha de restauração (`services/backup_service.py:146-164`).

Ordem final de restauração:

1. `usuarios`
2. `recuperacao_senha`, quando presente em backup legado
3. `categorias`
4. `contas`
5. `credito`
6. `favorecido`
7. `pessoa_fisica`
8. `pessoa_juridica`
9. `metas`
10. `agendamentos`
11. `transacoes`
12. `lancamentos`
13. `pagamentos_fatura`

Novos backups continuam excluindo `recuperacao_senha`. A tabela é aceita somente para compatibilidade de restauração com arquivos antigos.

Evidências:

- `tests/integration/test_backup_permissions.py:156-326`.
- Backup com agendamento executado restaurado com sucesso.
- Vínculo `transacoes.ID_Agendamento` preservado.
- `foreign_key_check` vazio.
- Payload inconsistente causa rollback total.
- Estado anterior permanece idêntico após falha.
- Backup preventivo permanece disponível.
- Dois backups no mesmo segundo têm nomes diferentes.
- Preventivo não colide com o arquivo restaurado.
- Backup lógico legado sem campos P0 é restaurado.

### 2.3. Migrações P0

**Status: CORRIGIDO COM RESSALVA.**

Foram criadas três migrações versionadas, registradas em `schema_migrations`:

| Versão | Nome | Finalidade |
|---|---|---|
| 1 | `legacy_columns` | Colunas legadas idempotentes necessárias ao schema atual |
| 2 | `p0_transacoes_agendamento` | Reconstrução de `transacoes`, FK e índice único parcial |
| 3 | `p0_pagamentos_fatura` | Reconstrução/validação da tabela, FKs, UNIQUEs e índice de competência |

Infraestrutura:

- Tabela de versão: `Database._ensure_migration_table` (`database/database.py:491`).
- Execução individual e transacional: `Database._run_migration` (`database/database.py:510`).
- A versão só é inserida depois de migration, validação de schema e `foreign_key_check` (`database/database.py:537-557`).
- Falhas fazem rollback e retornam diagnóstico com versão e nome (`database/database.py:559-567`).
- Migrações já registradas são no-op após validação do schema.

`transacoes`:

- Colunas são inspecionadas antes da alteração.
- Coluna sem FK, coluna sem índice e índice incorreto são detectados.
- A tabela é reconstruída para adicionar a FK que SQLite não permite adicionar por `ALTER COLUMN` (`database/database.py:671-803`).
- IDs e contagem são preservados.
- Índices e triggers existentes com SQL explícito são recriados.
- Vínculos órfãos bloqueiam a migração com mensagem recuperável.
- O índice final é `UNIQUE`, parcial e restrito a valores não nulos.

`pagamentos_fatura`:

- Colunas, quatro FKs, duas constraints UNIQUE e índice composto são verificados (`database/database.py:805-851`).
- Schema completo sem constraints é reconstruído preservando linhas e IDs (`database/database.py:853-925`).
- Tabela incompleta vazia é recuperada automaticamente.
- Tabela incompleta com dados não mapeáveis falha antes de descartar a tabela e preserva integralmente os registros.

Ressalva aceita pela especificação: schemas incompletos com dados que não possuem as colunas essenciais não podem ser convertidos automaticamente sem inventar informação. Nesses casos a inicialização falha com diagnóstico recuperável, a migração 3 não é marcada e os dados permanecem intactos.

Evidências:

- `tests/integration/test_migrations_p0.py`.
- `tests/integration/test_migrations_p0_avancadas.py:91-329`.
- Banco novo.
- Banco legado sem P0 e com dados.
- Coluna sem índice.
- Coluna e índice sem FK.
- Índice incorreto.
- `pagamentos_fatura` completa sem constraints e com dados.
- Tabela incompleta vazia.
- Tabela incompleta com dados não mapeáveis.
- Migração interrompida simulada.
- Reexecução idempotente.
- Inicialização concorrente.
- Constraints UNIQUE ativas.
- Contagens e IDs preservados.
- `foreign_key_check` vazio.

### 2.4. Sincronização da inicialização

**Status: CORRIGIDO.**

- A leitura e escrita de `_initialized_paths` são protegidas por `_initialization_lock` (`database/database.py:18-20`).
- `_initializing_paths` mantém um `Event` por caminho (`database/database.py:35-66`).
- O lock global é mantido apenas para consultar/alterar os registros; criação de tabelas e migrações acontecem fora dele.
- A segunda thread aguarda a inicialização do mesmo arquivo e recebe sua própria conexão utilizável.
- Se a inicialização falhar, o caminho não é marcado como concluído e as threads aguardando podem tentar novamente.

Evidência: `test_inicializacao_concorrente_do_mesmo_banco` em `tests/integration/test_migrations_p0_avancadas.py:306-329`.

### 2.5. Isolamento do pytest e ambientes virtuais

**Status: CORRIGIDO.**

- `pytest.ini` define `testpaths = tests`.
- `norecursedirs` exclui `.venv`, `venv`, `env`, `ENV`, `financeiro1`, `build-env`, builds, caches e dependências vendorizadas.
- `.gitignore` passou a ignorar `financeiro1/`, caches de ferramentas e dependências locais.
- Nenhum ambiente foi apagado ou adicionado ao Git.

O erro anterior de coleta de `PyInstaller.utils.conftest` não voltou a ocorrer.

## 3. Validação executada

### Testes integrados

```bash
pytest -q tests/integration
```

```text
51 passed in 347.12s (0:05:47)
```

### Suíte completa pela raiz

```bash
pytest -q
```

```text
51 passed in 302.06s (0:05:02)
```

### Diff

```bash
git diff --check
git diff --cached --check
```

Resultado: ambos concluíram com código zero e sem mensagens.

### Sintaxe

```text
Sintaxe Python válida: 121 arquivos
```

### Schema SQLite depois das migrações

```text
migrations = [1: legacy_columns, 2: p0_transacoes_agendamento,
              3: p0_pagamentos_fatura]
transacoes.ID_Agendamento FK = presente
pagamentos_fatura FKs = 4
idx_transacao_agendamento = UNIQUE parcial
idx_pagamento_fatura_competencia = presente
pagamentos_schema_valid = True
foreign_key_check = []
```

## 4. Arquivos alterados nesta correção de bloqueadores

- `.gitignore`
- `pytest.ini`
- `database/database.py`
- `models/backup_model.py`
- `services/backup_service.py`
- `services/transaction_service.py`
- `tests/integration/test_backup_permissions.py`
- `tests/integration/test_migrations_p0_avancadas.py`
- `tests/integration/test_unit_of_work.py`
- `REVISAO_CORRECOES_P0.md`

## 5. Arquivos P0 anteriores que devem entrar no futuro commit

Além dos arquivos da seção anterior, o commit P0 deve selecionar:

- `AUDITORIA.md`
- `core/operation_result.py`
- `controllers/backup_controller.py`
- `controllers/fatura_controller.py`
- `controllers/schedule_controller.py`
- `models/account_model.py`
- `models/category_model.py`
- `models/credito_model.py`
- `models/lancamento_model.py`
- `models/pagamento_fatura_model.py`
- `models/schedule_model.py`
- `models/transaction_model.py`
- `services/fatura_service.py`
- `services/payment_service.py`
- `services/schedule_service.py`
- `views/TransferDialog.py`
- `views/agendamento_view.py`
- `views/backup_view.py`
- `views/main_view.py`
- `views/painel_fatura.py`
- `tests/integration/conftest.py`
- `tests/integration/test_agendamento_atomicidade.py`
- `tests/integration/test_fatura_atomicidade.py`
- `tests/integration/test_migrations_p0.py`
- `tests/integration/test_transferencia_atomicidade.py`

## 6. Mudanças que devem ficar fora do commit P0

Mudanças preexistentes e não relacionadas:

- `models/ia_aprendizado_model.py`
- `models/layouts/itau_layout.py`
- `services/categorizacao_service.py`
- `services/importacao_service.py`
- `services/infrastructure/xlsx_service.py`
- `services/reconhecer_service.py`
- `views/painel_account.py`
- `views/subcategoria_dialog.py`
- `models/categoria_map_model.py`
- `models/layouts/picpay_layout.py`

Ambientes e artefatos que não devem entrar:

- `financeiro1/`
- `build-env/`
- `.venv/`
- `venv/`
- `env/`
- caches, builds, bancos locais, backups e logs ignorados pelo `.gitignore`

## 7. Bloqueadores restantes

Não restam bloqueadores técnicos P0 conhecidos após esta validação.

Permanece apenas a ressalva operacional de preparar um commit seletivo, pois o worktree contém mudanças anteriores fora do escopo. Nenhum arquivo foi indexado nesta etapa.

## 8. Conclusão

As correções P0 passaram a ter:

- unidade de trabalho com propriedade explícita e restauração segura de conexão;
- restauração de backup atômica, ordenada e validada por foreign keys;
- migrações P0 versionadas, idempotentes e recuperáveis;
- inicialização sincronizada entre threads;
- suíte isolada de ambientes virtuais;
- 51 testes reais aprovados nas duas formas exigidas de execução.

**SEGURO PARA COMMIT COM RESSALVAS**
