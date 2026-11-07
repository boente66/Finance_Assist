# Correção do ajuste de saldo — 7 de novembro de 2026

## Regra definitiva

O ajuste de saldo atualiza diretamente `contas.Saldo_Atual`, respeitando o usuário proprietário. Não cria registros em `transacoes`, tipo especial, histórico financeiro ou migração de reclassificação. A edição do saldo pelo cadastro de contas segue a mesma regra.

A implementação local anterior que criava o tipo `Ajuste` e a migração 9 foi removida antes da publicação. Registros antigos de receita/despesa não são reclassificados nem excluídos automaticamente. Nenhum banco de uso real foi alterado nesta validação.

O painel apresenta explicitamente o saldo atual, inclusive sem transações no período. A coluna de saldo deriva do saldo efetivo da conta e dos movimentos posteriores à linha, preservando paginação e filtros. A lista de contas e o painel atualizam após salvar; cancelar não grava.

Receitas, despesas, categorias, gráficos e relatórios permanecem baseados exclusivamente nos lançamentos financeiros. A diferença de saldo não participa desses totais.

## Validação

Os testes cobrem aumento, redução, zeragem, ausência de mudança, reabertura, preservação dos totais e relatórios, ausência de novos lançamentos, falha de gravação e atualização pela interface Qt. Ver também [testes de ajuste](../tests/integration/test_balance_adjustment_neutral.py) e [regressões da Fase 1](../tests/integration/test_phase1_homologated_fixes.py).

Execuções direcionadas, todas aprovadas:

- Ajustes de saldo, regressões da Fase 1 e migrações existentes: **33 aprovados**.
- Ajustes de saldo (incluindo conta vazia), backup portátil e formatos regionais: **15 aprovados**.
- Ausência de migração especial, arquitetura MSCV e catálogos de tradução: **8 aprovados**.

Os grupos se sobrepõem; as contagens não representam testes únicos. `git diff --check` sem erros. Não foi repetida a suíte completa nesta correção.

Alterações locais, sem publicação. A Fase 2 permanece em espera.
