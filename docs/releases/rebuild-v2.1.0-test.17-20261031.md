# Finance Assist test.17 — recompilação autorizada após homologação da Fase 1

Esta publicação disponibiliza instaladores recompilados da versão de teste
já existente. Não constitui lançamento ou divulgação de uma próxima versão.
Permanecem `2.1.0-test.17` e Debian `2.1.0~test17`.

O responsável declarou encerrada a Fase 1 em 31/10/2026 e autorizou
recompilar os instaladores e atualizar os links diretos para os usuários.
A Fase 2 aguarda autorização de início. A divulgação de uma próxima versão
permanece suspensa até a conclusão da auditoria.
Veja o [registro de homologação](../HOMOLOGACAO_FASE1.md).

## Conteúdo recompilado

Código-fonte homologado: `54d973557c0d321d19200b187016e89cd0acd849`.
O macOS ARM usa `80e3cc4979adeed2db6930a463d91f020d76184c`, que altera
apenas o executor de CI e seu teste de metadados; as fontes da aplicação são
idênticas às do commit homologado.
Inclui as correções homologadas e a revisão de traduções e persistência,
validada localmente por 372 testes aprovados. Não há alteração das regras
de negócio das faturas nesta recompilação.

## Origem dos pacotes

- [Windows, macOS Intel e DEB Ubuntu 22.04](https://github.com/boente66/Finance_Assist/actions/runs/41220652419): jobs concluídos com sucesso; o ARM foi cancelado pelo provedor antes de iniciar.
- [Recuperação da compilação macOS ARM com executor suportado](https://github.com/boente66/Finance_Assist/actions/runs/41236694144): aplicativo compilado e validado no macOS 15.
- [DEB Ubuntu 24.04/Mint 22](https://github.com/boente66/Finance_Assist/actions/runs/41220655164).

Os cinco jobs de empacotamento usados nesta publicação concluíram com sucesso.
Os testes e as instalações Linux do fluxo original foram aprovados, incluindo
Ubuntu 22.04, 24.04, 26.04 e a variante Ubuntu 24.04/Mint 22.
O único cancelamento inicial foi o executor macOS 14 antes de executar código;
o pacote ARM foi recuperado com sucesso no macOS 15.
Os SHA256 dos cinco instaladores foram conferidos antes da publicação.
