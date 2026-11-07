# Finance Assist test.17 — recompilação de 07/11/2026

Publicação autorizada pelo responsável após avaliação das correções. Mantém a versão de teste `2.1.0-test.17` e não inicia a Fase 2.

## Correções incluídas

- Ajuste de saldo altera somente o saldo da conta, sem gerar receita ou despesa; painel e extrato refletem o saldo efetivo.
- Formatos de moeda e data acompanham português, inglês e espanhol, sem conversão cambial nem alteração do armazenamento.
- Backup local portátil criptografado inclui as 17 tabelas de dados, com leitura consistente e gravação atômica.

Backup em nuvem excluído desta entrega: requer elaboração própria e permanece pendente.

## Validação

- [Compilação multiplataforma e testes](https://github.com/boente66/Finance_Assist/actions/runs/42389025525): concluídos com sucesso no commit `c2bdccb949e9520e70d5f9028e272f0938ded1a2`.
- [Compilação e instalação Ubuntu 24.04/Mint 22.x](https://github.com/boente66/Finance_Assist/actions/runs/42389027937): concluídas com sucesso no mesmo commit.
- Testes de integração no Ubuntu 24.04 e 26.04; instalação do DEB no Ubuntu 22.04, 24.04 e 26.04, com verificação de banco limpo, preservação de dados e inicialização das telas.
- Pacotes Windows x64, macOS Intel e Apple Silicon com testes de empacotamento e inicialização das telas.

## Downloads diretos

- [Linux DEB Ubuntu 22.04/24.04/26.04](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_amd64.deb) · [SHA256](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_amd64.deb.sha256)
- [Linux DEB Ubuntu 24.04 / Mint 22.x](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_ubuntu24.04_amd64.deb) · [SHA256](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_ubuntu24.04_amd64.deb.sha256)
- [Windows x64](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_windows-x64.zip) · [SHA256](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_windows-x64.zip.sha256)
- [macOS Apple Silicon](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_macos-arm64.zip) · [SHA256](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_macos-arm64.zip.sha256)
- [macOS Intel](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_macos-x64.zip) · [SHA256](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_macos-x64.zip.sha256)
