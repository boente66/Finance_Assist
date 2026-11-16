# Painel de fatura homologado

Autorização final do responsável recebida em 16/11/2026, incluindo implementação,
commit, push e publicação após testes e builds aprovados. Encerra a pendência
visual da [análise anterior](./ANALISE_UX_PAINEL_FATURA_FASE2.md).
A versão permanece **2.1.0-test.17**, Debian **2.1.0~test17**.

## Implementação

- Fluxo preservado: cartão na lateral e fatura à direita.
- Cabeçalho com Nome, Bandeira, Ativo/Inativo, competência, status da fatura,
  fechamento e vencimento retornados pelo serviço existente.
- Indicadores Limite/Usado/Disponível e ações existentes preservados.
- Tabela: Data, Estabelecimento/Favorecido, Descrição, Tipo, Categoria, Valor,
  Status. Favorecido utiliza o JOIN existente; ausente permanece vazio.
- Descrição recebe a maior largura inicial. Colunas podem ser redimensionadas
  manualmente; o ajuste não é sobrescrito ao redimensionar a janela. Rolagem
  horizontal mantém todas as colunas acessíveis. Elipse e tooltip preservam
  acesso ao texto integral, inclusive nos nomes da lista lateral.
- Tabela ocupa o espaço vertical disponível. Paginação aparece apenas quando
  necessária. Resumo inferior separado em composição e quitação da fatura.
- Traduções offline PT-BR, EN e ES para os textos da nova apresentação.

Nenhuma alteração de schema, cálculo, ciclo, persistência ou regras de cartão
ativo/inativo. Consultar e pagar dívida de cartão inativo continua permitido;
compras, créditos e importações continuam bloqueados pelas regras existentes.

## Validação e distribuição

Regressão completa local: **461 testes aprovados**, zero falhas/erros/ignorados,
15 avisos de depreciação de dependências, em 103,90 s.

```bash
TMPDIR=/dev/shm/finance-assist-invoice-tests QT_QPA_PLATFORM=offscreen \
  .venv-finance-assist/bin/python -m pytest -q tests
```

Inclui cálculos e ciclos de fatura, atomicidade, pagamentos parciais, cartão
ativo/inativo, integridade, backup, catálogos offline e interface. Os nove novos
cenários de idioma × resolução verificam largura manual preservada, favorecido,
descrição integral no tooltip, identidade do lançamento e acesso à quitação.

Capturas sintéticas da janela completa, tema Primavera/Qt offscreen:

- [1366×768 PT](./evidencias/painel-fatura-homologado/painel-1366x768-pt.png)
- [1280×720 PT](./evidencias/painel-fatura-homologado/painel-1280x720-pt.png)
- [1920×1080 PT](./evidencias/painel-fatura-homologado/painel-1920x1080-pt.png)
- [1366×768 EN](./evidencias/painel-fatura-homologado/painel-1366x768-en.png)
- [1366×768 ES](./evidencias/painel-fatura-homologado/painel-1366x768-es.png)
- [Medidas dos nove cenários](./evidencias/painel-fatura-homologado/medidas.json)

Em PT: viewport da tabela de 649×156 em 1280×720, 735×204 em 1366×768 e
1289×531 em 1920×1080. Rolagem horizontal disponível sem ocultar colunas;
resumo e ações acessíveis. As capturas comprovam estes cenários no Linux;
os builds nativos validam inicialização das telas em cada plataforma.

Builds e links finais serão registrados após sua conclusão.
