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

Regressão completa final do código enviado: **506 testes aprovados**, zero
falhas/erros, 15 avisos de depreciação de dependências, em 409,20 s. Inclui
o atalho com foco na lateral. A rodada completa anterior passou em 505 testes;
a rodada final inclui o cenário adicional.

```bash
TMPDIR=/dev/shm/finance-maintenance-tests QT_QPA_PLATFORM=offscreen \
  .venv-finance-assist/bin/python -m pytest -q tests
```

Rodada focada final: **113 testes aprovados**, incluindo **42 cenários IMP-003**,
zero falhas/erros, um aviso de depreciação, em 46,32 s. Inclui o atalho com foco
na lateral e a inatividade do atalho quando o painel está oculto.

Sintaxe da rotina Python de publicação e YAML do workflow aprovadas.

## Builds

**14 jobs aprovados**, zero falhas: suíte dividida em Ubuntu 24.04/26.04/Noble,
DEB geral, DEB Noble, instalação Ubuntu 22.04/24.04/26.04, OCR e inicialização
das telas, Windows x64, macOS Intel e Apple Silicon. Todos os cinco pacotes
foram compilados a partir do mesmo código, mantendo a versão numérica.

Código enviado/compilado:
[`5a31d8878a9f21ee46fd874e03c50d4e8117e872`](https://github.com/boente66/Finance_Assist/commit/5a31d8878a9f21ee46fd874e03c50d4e8117e872).

- [Build multiplataforma e instalação](https://github.com/boente66/Finance_Assist/actions/runs/44810476426).
- [Build Ubuntu 24.04/Mint 22](https://github.com/boente66/Finance_Assist/actions/runs/44810481513).

## Publicação concluída — 20/11/2026

[Publicação e conferência remota](https://github.com/boente66/Finance_Assist/actions/runs/44812372458)
aprovadas. Foram publicados e conferidos **13 arquivos**: cinco pacotes, o EXE
extraído sem alteração do ZIP Windows, seis arquivos SHA256 e um manifesto.
SHA256 de origem, CRC dos ZIPs, versão dos DEBs, tamanho e SHA256 remoto
conferidos. Os 36 arquivos anteriores foram preservados. A tag histórica
permaneceu inalterada; nenhuma nova versão numérica foi criada.

O EXE Windows é o aplicativo empacotado, não um instalador MSI. O DEB geral
mantém 2.1.0~test17; a variante Noble mantém 2.1.0~test17+ubuntu24.04.1.
Feche o aplicativo antes de substituir a instalação; no Linux, use
`apt install --reinstall` quando a mesma versão já estiver instalada.

| Plataforma | Pacote | Integridade |
| --- | --- | --- |
| Linux Ubuntu 22.04/24.04/26.04 | [Download](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_amd64_imp003-20261120.deb) | [SHA256](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_amd64_imp003-20261120.deb.sha256) |
| Ubuntu 24.04 / Mint 22 | [Download](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_ubuntu24.04_amd64_imp003-20261120.deb) | [SHA256](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_ubuntu24.04_amd64_imp003-20261120.deb.sha256) |
| Windows x64 — EXE | [Download](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/FinanceAssist-test.17-imp003-20261120-windows-x64.exe) | [SHA256](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/FinanceAssist-test.17-imp003-20261120-windows-x64.exe.sha256) |
| Windows x64 — ZIP | [Download](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_windows-x64_imp003-20261120.zip) | [SHA256](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_windows-x64_imp003-20261120.zip.sha256) |
| macOS Intel | [Download](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_macos-x64_imp003-20261120.zip) | [SHA256](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_macos-x64_imp003-20261120.zip.sha256) |
| macOS Apple Silicon | [Download](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_macos-arm64_imp003-20261120.zip) | [SHA256](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_macos-arm64_imp003-20261120.zip.sha256) |

[Manifesto SHA256 e origem dos builds](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/imp003-20261120-manifest.json).

Os seis links binários retornaram HTTP 200 após a publicação. README e notas
da distribuição apontam para os novos arquivos; documentos históricos mantêm
os links das publicações anteriores.
