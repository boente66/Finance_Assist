# Finance Assist 2.1.0-test.17 — recompilação da Fase 1

Publicação: 30/10/2026. Binários compilados em 26/10/2026.

Pacotes do commit `f9f8ba65a69beb00c35431ceb0fa9d4f74947634`, preservando
as versões internas `2.1.0-test.17` e Debian `2.1.0~test17`.
Esta pré-release separa os novos binários da publicação original da test.17.

Inclui correções de edição de transações e saldos, histórico de ajustes,
limite de pagamento de dívida, validação de CPF/CNPJ, catálogos de tradução
offline e projeção de faturas. O ajuste de empacotamento Linux foi registrado
separadamente. O isolamento de idioma dos novos testes também foi corrigido.

**Homologação da Fase 1 pendente.** Permanecem achados em documentos legados,
traduções e validação manual integral. Veja o [registro de validação](../VALIDACAO_FASE1_PUBLICACAO_TESTE.md).

## Origem dos instaladores

- [Windows, macOS Intel/ARM e DEB Ubuntu 22.04](https://github.com/boente66/Finance_Assist/actions/runs/40419566979): sucesso.
- [DEB Ubuntu 24.04/Mint 22](https://github.com/boente66/Finance_Assist/actions/runs/40419570906): sucesso.

Os testes de integração dos workflows e os testes de instalação Linux passaram.
Foram conferidos os SHA256 dos cinco arquivos antes da publicação.
