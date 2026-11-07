# Formatos regionais e backup portátil — 7 de novembro de 2026

## Apresentação por idioma

| Idioma | Região | Moeda apresentada | Data apresentada |
|---|---|---|---|
| Português | Brasil | R$ 1.234,56 | 07/11/2026 |
| Inglês | Estados Unidos | $1,234.56 | 11/07/2026 |
| Espanhol | Espanha | 1.234,56 € | 07/11/2026 |

A troca de idioma altera a apresentação e a interpretação dos campos, sem conversão cambial e sem regravar os valores monetários ou as datas ISO do banco. O sistema atual não mantém moeda independente por conta.

A [configuração regional](../core/regional_format.py) centraliza o locale dos campos Qt, símbolos e formatos. Os [formatadores monetários](../utilitarios/currency_formatter.py) e de [datas](../utilitarios/date_formatter.py) usam esse padrão na apresentação. A conversão explicitamente brasileira e os contratos ISO permanecem disponíveis para armazenamento/importação.

Dívidas e empréstimos aplicam o padrão ao cadastro, pagamento, agendamento, listagem, próximo vencimento e detalhes de parcelas/pagamentos. A troca de idioma atualiza formulários já abertos mantendo seus valores e datas. Juros percentuais não recebem símbolo monetário.

Campos monetários de outros módulos também foram conectados ao padrão regional. A leitura manual dos campos de transação, ajuste de saldo, lançamento de cartão e metas usa o formatador central. Números negativos em parênteses no padrão americano também são reconhecidos.

## Correção do backup existente

O backup lógico criptografado deixava de fora dívidas, parcelas, pagamentos de dívidas e informes fiscais. Agora inclui as 17 tabelas de dados do aplicativo. Tokens de recuperação de senha e controle de migrações permanecem excluídos; o banco de destino mantém suas próprias migrações.

A extração ocorre em uma única transação de leitura. A gravação usa arquivo temporário, sincronização do conteúdo e renomeação final, para não apresentar arquivo incompleto como backup pronto.

A validação transfere um backup protegido por senha para um banco separado e compara integralmente todas as tabelas de dados, incluindo saldos, pagamentos e vínculos. Não foi feito upload de dados de uso real.

A necessidade de obter uma cópia coerente, em vez de copiar um banco SQLite enquanto ele muda, é descrita na [documentação oficial do SQLite](https://www.sqlite.org/howtocorrupt.html).

## Nuvem adiada e publicação autorizada

Foi solicitada a definição entre:

1. Backup criptografado em pasta sincronizada pelo usuário, com restauração em outra máquina.
2. Sincronização automática ao fazer login, mediante definição do serviço e do tratamento de alterações simultâneas.

As correções do backup existente não constituem sincronização automática. Não foram criados conta remota, backend, integração OAuth ou cliente Android. Em 07/11/2026, o responsável autorizou publicar e recompilar as correções existentes, com links diretos, excluindo o backup em nuvem desta entrega. A definição da integração em nuvem permanece pendente e não bloqueia esta recompilação.

## Validação anterior à correção definitiva de saldo

Para a mudança posterior de comportamento do ajuste, consulte a [validação específica](./CORRECAO_AJUSTE_SALDO_2026-11-07.md).

- [Formatos regionais e formulário de dívida aberto](../tests/integration/test_regional_formats.py): testes direcionados aprovados nos três idiomas.
- [Backup portátil completo e interrupção de gravação](../tests/integration/test_backup_portable_all_tables.py): testes direcionados aprovados.
- Dívidas, permissões de backup e catálogo offline: execução direcionada com 27 aprovados.
- Regressão completa encerrada normalmente em dois processos: **247 + 141 = 388 aprovados; 0 falhos; 0 ignorados**. Durações: 72,07 s e 71,18 s.
- Validação anterior do backup: 2 aprovados. Ajustes de saldo agora atualizam apenas a conta e não geram lançamentos; veja a correção definitiva de saldo.
- `git diff --check`: sem erros. Alterações ainda locais, sem commit, envio ao GitHub ou recompilação nesta solicitação.
