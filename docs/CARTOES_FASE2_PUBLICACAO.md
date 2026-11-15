# Cartões — implementação homologada e publicação

Autorização de implementação/GitHub/instaladores recebida em 15/11/2026.
Versão mantida: 2.1.0-test.17; não criar nova release automaticamente.

## Entrega funcional

- Nome e Bandeira independentes; NULL representa Sem bandeira. Catálogo de 14
  redes, incluindo opções históricas, com texto comercial sem tradução.
- Migration 9 `optional_card_network`: disponibilidade confirmada no main
  remoto (schema anterior até 8); aditiva, idempotente, sem recriar credito,
  alterar IDs/FKs ou normalizar Nome automaticamente.
- CREATE agora persiste Ativo recebido; UPDATE é parcial e não regrava campos
  financeiros ao alterar somente Bandeira/estado. Service rejeita estado inválido.
- Cartões inativos ocultos por padrão; checkbox Mostrar cartões inativos altera
  somente visualização. Nome/Bandeira/Ativo aparecem na lista contextual existente.
  Inativar/Reativar estão no menu do cartão; não existe novo dashboard.
- Novas compras, créditos, importação em lote e novos agendamentos de cartão
  inativo são recusados no Service. Ações correspondentes ficam desabilitadas no
  painel; callbacks antigos/clipboard também não podem persistir novas compras.
- Consulta histórica, projeção de obrigações e pagamento de fatura já existente
  continuam disponíveis: inativar não é quitar nem apagar dívida. Reativação
  preserva integralmente Bandeira e vínculos.
- API legada excluir_cartao continua fazendo inativação. Novo comando Excluir
  definitivamente inspeciona todas as FKs reais de todas as tabelas, incluindo
  compostas/tabelas futuras, e usa BEGIN IMMEDIATE para verificar e excluir na
  mesma transação. Qualquer vínculo bloqueia DELETE, inclusive FK CASCADE e
  ciclo de fatura vazio; UI oferece inativação. Sem mudanças em FKs/JOINs.
- Traduções offline PT/EN/ES dos novos controles; backup preserva Bandeira e
  Ativo, inclusive restauração de payload antigo sem Bandeira em schema novo.

Recursos/licenças e detalhes da primeira validação:
[relatório de homologação](./CARTOES_FASE2_HOMOLOGACAO.md). As dez representações
comerciais licenciadas e o fallback genérico para quatro redes foram apresentados
nessa homologação. Nenhum logotipo foi inventado ou buscado em runtime.

## Validação final local

452 testes aprovados, **0 falhos, 0 erros e 0 ignorados**, em 174,77 s.
15 avisos de depreciação de dependências; nenhuma falha foi suprimida.
Os 76 testes focados também passaram antes da suíte completa.

```bash
TMPDIR=/dev/shm/finance-assist-cartoes-tests QT_QPA_PLATFORM=offscreen \
  .venv-finance-assist/bin/python -m pytest -q tests
```

Cobertura: novo/legado/coluna pré-existente/reexecução da migration, CRUD,
catálogo/neutro/inválido, Ativo 1→0→1, ocultação sem escrita, edição contextual,
preservação de limites legados, exclusão permitida e bloqueada por histórico/FKs
futuras, isolamento por usuário, inativo sem novos movimentos, dívida/projeção/
pagamento histórico, backup/restauração, tradução, arquitetura e regressões.
PRAGMA integrity_check/foreign_key_check e comparações da cópia normalizada
aprovados. Bancos, backups e dados individuais não integram o Git.

## Escopo de arquivos

- Database: [database.py](../database/database.py).
- Model: [credito_model.py](../models/credito_model.py).
- Services: [card_networks.py](../services/card_networks.py),
  [fatura_service.py](../services/fatura_service.py),
  [schedule_service.py](../services/schedule_service.py).
- Controller: [fatura_controller.py](../controllers/fatura_controller.py).
- Views: [criar_cartao_dialog.py](../views/criar_cartao_dialog.py),
  [card_network_selector.py](../views/card_network_selector.py),
  [transacao_view.py](../views/transacao_view.py),
  [painel_fatura.py](../views/painel_fatura.py) (somente habilitação funcional).
- Tradução: [i18n_catalogs.py](../core/i18n_catalogs.py).
- Recursos: [card-networks/](../assets/icons/card-networks/) com licença, fontes e hashes.
- Testes: [test_card_networks.py](../tests/integration/test_card_networks.py),
  [test_card_lifecycle.py](../tests/integration/test_card_lifecycle.py),
  [test_migrations_p0_avancadas.py](../tests/integration/test_migrations_p0_avancadas.py),
  [test_balance_adjustment_neutral.py](../tests/integration/test_balance_adjustment_neutral.py),
  [test_correcao_ciclo_fatura.py](../tests/integration/test_correcao_ciclo_fatura.py).
- Documentos: análise prévia, homologação, este relatório e análise UX separada;
  capturas em [cartões](./evidencias/cartoes-fase2/) e
  [painel](./evidencias/painel-fatura-analise/).

## Painel de fatura — saída separada

[Análise UX e proposta para nova homologação](./ANALISE_UX_PAINEL_FATURA_FASE2.md).
Capturas de 1366×768, 1280×720 e 1920×1080 e idioma inglês. Não foi implementada
mudança definitiva de layout, colunas, fontes, espaçamento ou hierarquia.

## Normalização e builds

As duas normalizações determinísticas homologadas foram validadas em cópia
consistente, comparando todas as tabelas; somente Nome/Bandeira mudaram.
O caso ambíguo continua intacto. Aplicação autorizada aos dados locais e seus
backups/checagens será registrada abaixo sem divulgar dados individuais.

Builds multiplataforma e Ubuntu 24.04 serão disparados no commit de implementação
após push. Resultados, SHA e links atualizados serão registrados após conclusão.
Pacotes novos receberão identificação cartoes-20261115, preservando arquivos
anteriores na release de teste existente. O manifesto dos pacotes explicitará
o SHA real de compilação: a tag histórica da release não será movida.
