# Revisão de traduções e inserção no banco — 31/10/2026

A homologação manual das faturas foi informada pelo usuário. Esta revisão
preserva as regras financeiras e verifica as correções manuais de tradução
e a persistência usando bancos temporários, sem escrever no banco real.

## Erros encontrados e corrigidos

- As alterações manuais chamavam `TranslatorApp.translate`, método inexistente.
  As telas agora usam a API correta e aplicam o idioma também na abertura.
- A consulta ao nome do mês escrevia português na sessão e disparava listeners.
  Agora apenas lê o idioma, inclusive quando recebido como `pt_BR`.
- O cache de textos usava `id()` de wrappers Python de objetos Qt. Foi reproduzido
  um formulário com “Conta de pagamento” exibindo “Vencimento”. O texto original
  agora pertence ao próprio objeto Qt, independentemente da vida do wrapper.
- Frases híbridas foram substituídas por traduções completas. Cada catálogo
  inglês/espanhol contém 692 entradas, incluindo validações, dívidas, faturas,
  configurações, temas e seleção de datas. Os placeholders são preservados.
- Os seletores de tipo de dívida e crédito usam dados estáveis, separados do
  texto exibido. Trocar o idioma não altera o tipo nem a direção gravados.
- Formulários e detalhes de dívida acompanham PT → EN → ES → PT enquanto
  abertos. Foram traduzidos títulos, campos, botões, estados e cabeçalhos.
- A ausência de tradução automática não grava mais o texto original como se
  fosse uma tradução válida, evitando um cache que impediria nova tentativa.
- A persistência JSON das traduções usava duas localizações diferentes. O
  armazenamento agora compartilha a pasta de dados com `TranslationModel`,
  em vez de depender de permissão de escrita na instalação.

## Verificação de todas as tabelas

O teste compara o inventário descoberto no SQLite com a lista coberta, para
falhar se surgir uma tabela da aplicação sem cenário correspondente.

| Tabela | Caminho de inserção verificado |
|---|---|
| usuarios | UserModel.add_user |
| recuperacao_senha | PasswordResetModel.create_token |
| categorias | CategoryModel.add_category |
| contas | AccountModel.add_account |
| credito | CreditoModel.add_cartao |
| favorecido | FavorecidoService.criar, PF e PJ |
| pessoa_fisica | Cadastro de favorecido PF |
| pessoa_juridica | Cadastro de favorecido PJ |
| transacoes | Pagamentos reais de dívida e fatura |
| agendamentos | Criação de dívida com parcelas |
| lancamentos | Compra real de cartão |
| faturas_cartao | Sincronização do ciclo pela compra/pagamento |
| pagamentos_fatura | FaturaService.pagar_fatura |
| dividas | DividaService.criar |
| divida_parcelas | Criação de dívida fixa |
| pagamentos_divida | DividaService.registrar_pagamento |
| informes_fiscais | RelatorioService.salvar_informe_fiscal |
| metas | MetaModel.add_meta |
| schema_migrations | Inicialização/migrações do schema |

As 19 tabelas têm conferência de conteúdo por conexão independente e rollback
após inserção com falha intermediária. Todas as chaves estrangeiras declaradas
são percorridas com tentativas de inserir referências inexistentes. Também
são verificados `integrity_check`, `foreign_key_check` e a manutenção automática
de `sqlite_sequence`, tabela interna em que a aplicação não deve inserir
manualmente.

A persistência JSON, que não corresponde a uma tabela SQL, tem testes próprios
de gravação, reabertura entre os dois componentes e falha de substituição
atômica preservando o conteúdo anterior.

## Evidências e rastreabilidade

- [Testes de todas as tabelas](../tests/integration/test_database_all_tables.py).
- [Regressão de tradução e persistência JSON](../tests/integration/test_translation_review.py).
- [Cobertura de textos fixos offline](../tests/integration/test_i18n_offline_catalogs.py).

A primeira montagem do teste geral passou o registro de cartão inteiro onde
se exigia seu identificador; a fixture foi corrigida para respeitar o contrato
do Model, sem alterar as asserções de persistência. Não foi uma falha do produto.
A regressão de formulários revelou e reproduziu a colisão de wrappers Qt,
corrigida no tradutor. A coleta estática passou a examinar somente os diretórios
de código da aplicação, evitando exigir entradas de catálogo para textos
artificiais dos próprios testes e percorrer ambientes virtuais.

## Resultado automatizado

Regressão completa do código final, nos dois grupos do projeto:

| Execução | Aprovados | Falhos | Ignorados | Tempo |
|---|---:|---:|---:|---:|
| Integração A–M | 235 | 0 | 0 | 106,38 s |
| Integração N–Z e interface | 137 | 0 | 0 | 102,33 s |
| Total da regressão | **372** | **0** | **0** | Grupos paralelos |
| Traduções/JSON e catálogos, execução específica | 24 | 0 | 0 | 70,95 s |

Os 24 testes específicos são parte da cobertura da regressão; não se somam
novamente aos 372. Os testes de todas as tabelas correspondem a 40 casos:
inventário/integridade, 19 de persistência, 19 de rollback e um que percorre
todas as chaves estrangeiras.

Os dois processos finais encerraram normalmente com código 0. Foi usado
`TMPDIR=/dev/shm`: arquivos SQLite reais em diretório temporário na RAM,
preservando conexões independentes e sem usar bancos SQLite `:memory:`.
A primeira execução em disco avançou lentamente; foi preservada e encerrada
após a substituição integral concluída, sem contabilizá-la como aprovação.
O N–Z anterior também havia encerrado normalmente com 131 testes aprovados;
a repetição final incluiu os seis casos acrescentados durante a revisão.

`git diff --check`: aprovado. O envio das correções ao GitHub foi autorizado
pelo usuário após a conclusão desta revisão.
A aprovação manual das faturas informada pelo usuário foi preservada; este
registro não declara homologação integral de toda a Fase 1.
