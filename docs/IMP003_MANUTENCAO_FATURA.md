# IMP-003 — manutenção temporária de fatura

Implementação autorizada pelo responsável pelo produto em 20/11/2026.
Mantém a versão 2.1.0-test.17 e não adiciona schema, tabela, coluna ou flag de
desbloqueio persistente. Publicação condicionada à regressão e aos builds.

## Bloqueios encontrados

`FaturaService.atualizar_lancamento` e `excluir_lancamento` exigiam ciclo ABERTA.
A edição também exigia destino aberto. `pagar_fatura` recusava qualquer ciclo
PAGA; a projeção de compromissos descartava ciclos PAGA e lançamentos já
marcados como pagos. A baixa repetida de lançamentos já pagos era recusada
pelo Model. Esses pontos impediam representar e quitar diferenças reais
depois de uma correção excepcional.

## Capacidade e arquitetura

`PainelFatura` registra Ctrl+D no contexto do painel e exibe um indicador
textual traduzido. Solicita a autorização ao `FaturaController`, que fornece
o usuário autenticado ao `FaturaService`. O Service confere propriedade e
status FECHADA/PAGA e emite uma capacidade opaca por `InvoiceMaintenance`.

A capacidade existe apenas em memória e vincula banco, usuário, cartão,
competência e ID da fatura, com referência fraca ao painel proprietário.
Não é um booleano que possa ser passado para ignorar as validações.
O diálogo recebe explicitamente a mesma capacidade e a encaminha por
Controller → Service → Model → Database. O Service valida novamente o contexto
dentro da transação de edição/exclusão. Token revogado ou de outro contexto
é recusado, inclusive se apresentado a uma operação normalmente permitida.

Trocar cartão/competência, ocultar/fechar o painel, logout e fechamento da
janela principal revogam a capacidade. `Session.set_usuario` revoga todas as
capacidades, inclusive ao autenticar novamente o mesmo usuário. Um processo
novo começa sem autorizações. O indicador desaparece com a revogação.

## Comportamento financeiro

- FECHADA permanece FECHADA. Edição e exclusão autorizadas não reabrem o ciclo.
- PAGA permanece PAGA; pagamentos, transações e saldo da conta não são
  alterados automaticamente pela edição. A marca histórica Paga e o vínculo
  original do lançamento à transação também são preservados.
- Totais são derivados dos movimentos e pagamentos reais. O painel apresenta
  diferença assinada, saldo pendente e saldo credor, sem mascarar discrepâncias.
- Um saldo positivo aparece na projeção e admite pagamento complementar real,
  com as validações financeiras existentes. A baixa não reescreve lançamentos
  já pagos. Dados legados marcados como pagos sem pagamento conciliado continuam
  impedidos de gerar um novo débito automaticamente.
- Apenas compras existentes são editáveis; pagamentos nunca são excluídos por
  esse modo. O ajuste não muda proprietário, cartão, competência ou parcelas.
  Categoria/favorecido devem pertencer ao usuário. Valores devem ser positivos
  e finitos. Exclusão de origem com movimentos vinculados é bloqueada.
- Compras novas, créditos e importações mantêm as regras de cartão ativo/inativo.

## Classes alteradas

`InvoiceMaintenance` (nova), `Session`, `FaturaController`, `FaturaService`,
`LancamentoModel`, `PainelFatura`, `EditarFaturaDialog` e `MainView`.
Catálogos offline EN/ES complementam os textos originais PT-BR.

## Validação

O conjunto dedicado verifica atalho real via QTest, revogação, isolamento de
usuário/contexto, ausência de persistência, processo novo sem autorizações,
rollback, vínculos financeiros, pagamento complementar, diálogo desatualizado,
PT-BR/EN/ES e painel nas dimensões disponíveis para 1280×720, 1366×768 e
1920×1080.

Regressão completa local: **505 testes aprovados**, zero falhas/erros,
15 avisos de depreciação de dependências, em 432,98 s. O teste adicional de
atalho com foco na lateral integra a rodada focada final e a regressão de CI.

```bash
TMPDIR=/dev/shm/finance-maintenance-tests QT_QPA_PLATFORM=offscreen \
  .venv-finance-assist/bin/python -m pytest -q tests
```

Rodada focada final: **113 testes aprovados**, incluindo **42 cenários IMP-003**,
zero falhas/erros, um aviso de depreciação, em 46,32 s. Inclui o atalho com foco
na lateral e a inatividade do atalho quando o painel está oculto.

Sintaxe da rotina Python de publicação e YAML do workflow aprovadas.
Os resultados dos builds e publicação serão registrados após conclusão,
mantendo os instaladores anteriores disponíveis.
