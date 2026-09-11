# Auditoria das melhorias de faturas — 2.1.0-test.7

Data: 10 de setembro de 2026.

## Problemas encontrados e soluções

| Área | Problema | Solução |
|---|---|---|
| Painel | Tabela e controles ocupavam espaço excessivo em larguras menores. | Indicadores responsivos, fonte e altura compactas, ícones menores e botões adaptáveis. |
| Ações | Não havia edição do lançamento nem menu acessível pelo botão esquerdo. | Novo `EditarFaturaDialog` e menu Ações com copiar, colar, editar e excluir. |
| Consistência | Instâncias diferentes do controller podiam manter uma fatura antiga em cache. | Leitura atualizada do SQLite após cada operação. |
| Exclusão | Uma ação poderia alterar lançamentos já pagos. | Service impede edição e exclusão após o pagamento. |
| Importação | O layout genérico aceitava tabelas ambíguas e a tela nem oferecia PDF. | Layout genérico removido; reconhecimento explícito por emissor e revisão antes da gravação. |
| PicPay | Pagamentos e créditos poderiam ser tratados como novas despesas. | Parser específico exclui esses movimentos e fecha o total de despesas do mês. |
| Nubank | Parcelas de financiamento aparecem em múltiplas linhas no texto extraído. | Parser recompõe a linha, preserva a parcela e exclui pagamentos/saldos. |
| Itaú Mastercard | A página mistura compras, encargos, limites, pagamentos e próximas parcelas em colunas paralelas. | Parser restringe a leitura à seção de lançamentos atuais, preserva parcelas e fecha o total apresentado. |
| PDF protegido | Não existia entrada de senha no fluxo de fatura. | Solicitação mascarada e senha transitória encaminhada apenas ao leitor. |
| Extrato PDF | Saída era texto corrido. | Documento com identidade visual, título da conta, período, tabela paginada e resultado. |
| Fatura PDF | Saída era texto corrido e simples. | Documento com cartão, competência, totais e todos os lançamentos em tabela paginada. |

## Preservação do banco

Não há migração destrutiva nesta alteração. Tabelas de usuários, contas,
cartões, lançamentos e transações não são apagadas ou recriadas. Importações só
são persistidas depois da revisão do usuário e continuam sujeitas à reconciliação
de duplicidades existente.

## Documentos reais utilizados

Os parsers foram conferidos localmente com faturas PicPay, Nubank e Itaú Mastercard fornecidas
pelo usuário. Os PDFs não fazem parte do repositório e seus dados pessoais não
são copiados para fixtures; os testes usam trechos anonimizados representativos.

## Validação

- 243 testes automatizados aprovados no ambiente local, incluindo regressão de
  migrações, operações atômicas, relatórios, interface e telas empacotadas.
- Faturas reais conferidas localmente: PicPay, 10 despesas e R$ 330,55; Nubank,
  6 despesas e R$ 207,84; Itaú Mastercard, 8 despesas e R$ 69,40.
- Busca de privacidade confirmou que senha, CPF, número do cartão, endereço e os
  PDFs fornecidos não foram adicionados às alterações desta versão. Os testes
  contêm somente exemplos anonimizados.

## Distribuição

- [Build multiplataforma aprovado](https://github.com/boente66/Finance_Assist/actions/runs/34554788498):
  Windows x64, código no Ubuntu 24.04/26.04 e instalação do DEB base nas três
  versões suportadas do Ubuntu.
- [Build Ubuntu 24.04/Mint 22.x aprovado](https://github.com/boente66/Finance_Assist/actions/runs/34554803836):
  instalação limpa e atualização sobre banco sentinela preservado.
- [Pré-release v2.1.0-test.7](https://github.com/boente66/Finance_Assist/releases/tag/v2.1.0-test.7):
  três instaladores e respectivos checksums SHA-256 publicados.
