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
  Status. Favorecido utiliza LEFT JOIN por ID e usuário na consulta do painel; ausente permanece vazio, sem remover linhas ou alterar valores.
- Descrição recebe a maior largura inicial e absorve o espaço adicional da janela até o usuário ajustar as colunas. Colunas podem ser redimensionadas
  manualmente; o ajuste não é sobrescrito ao redimensionar a janela. Rolagem
  horizontal mantém todas as colunas acessíveis. Elipse e tooltip preservam
  acesso ao texto integral, inclusive nos nomes da lista lateral.
- Tabela ocupa o espaço vertical disponível. Paginação aparece apenas quando
  necessária. Resumo inferior separado em composição e quitação da fatura.
- Traduções offline PT-BR, EN e ES para a apresentação, categorias ausentes, filtros e atualização de idioma. Meses acompanham a configuração da sessão.

Nenhuma alteração de schema, cálculo, ciclo, persistência ou regras de cartão
ativo/inativo. Consultar e pagar dívida de cartão inativo continua permitido;
compras, créditos e importações continuam bloqueados pelas regras existentes.

## Validação e distribuição

Regressão completa local: **464 testes aprovados**, zero falhas/erros/ignorados,
15 avisos de depreciação de dependências, em 114,65 s.

```bash
TMPDIR=/dev/shm/finance-assist-invoice-tests QT_QPA_PLATFORM=offscreen \
  .venv-finance-assist/bin/python -m pytest -q tests
```

Rodada focada final: **103 testes aprovados**, um aviso de depreciação, em 10,58 s.

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

Em PT: viewport da tabela de 659×178 em 1280×720, 745×226 em 1366×768 e
1309×545 em 1920×1080. Rolagem horizontal disponível sem ocultar colunas;
resumo e ações acessíveis. As capturas comprovam estes cenários no Linux;
os builds nativos validam inicialização das telas em cada plataforma.

Publicação concluída em **17/11/2026**, usando os builds de 16/11/2026.
Código compilado: [dc0e3a06e7ec445ba05f1de1491f48d0ecb83681](https://github.com/boente66/Finance_Assist/commit/dc0e3a06e7ec445ba05f1de1491f48d0ecb83681).

Os dois workflows de compilação terminaram com sucesso, com **14 jobs aprovados**:

- [Multiplataforma](https://github.com/boente66/Finance_Assist/actions/runs/43981933339): testes em Ubuntu 24.04/26.04, DEB geral, instalação em Ubuntu 22.04/24.04/26.04, Windows e macOS Intel/ARM.
- [Ubuntu 24.04/Mint 22](https://github.com/boente66/Finance_Assist/actions/runs/43981937427): testes, compilação, instalação, OCR e inicialização das telas.
- [Publicação e conferência remota](https://github.com/boente66/Finance_Assist/actions/runs/44209456773): SHA de origem, checksums, CRC dos ZIPs e integridade dos arquivos publicados.

A rotina de publicação também passou por verificação de sintaxe/YAML e pelos
**7 testes de metadados de empacotamento**. A publicação preservou arquivos
anteriores e conferiu os checksums idênticos já existentes.

Todos os cinco pacotes foram recompilados a partir do SHA acima. SHA256 de
origem conferidos; CRC integral dos ZIPs validado. O EXE foi extraído sem
alterações do ZIP Windows aprovado; não é um instalador MSI. Os DEBs mantêm
2.1.0~test17; variante Noble mantém 2.1.0~test17+ubuntu24.04.1.

| Plataforma | Pacote | Integridade |
| --- | --- | --- |
| Linux Ubuntu 22.04/24.04/26.04 | [Download](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_amd64_painel-fatura-20261116.deb) | [SHA256](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_amd64_painel-fatura-20261116.deb.sha256) |
| Ubuntu 24.04 / Mint 22 | [Download](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_ubuntu24.04_amd64_painel-fatura-20261116.deb) | [SHA256](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_ubuntu24.04_amd64_painel-fatura-20261116.deb.sha256) |
| Windows x64 — EXE | [Download](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/FinanceAssist-test.17-painel-fatura-20261116-windows-x64.exe) | [SHA256](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/FinanceAssist-test.17-painel-fatura-20261116-windows-x64.exe.sha256) |
| Windows x64 — ZIP | [Download](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_windows-x64_painel-fatura-20261116.zip) | [SHA256](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_windows-x64_painel-fatura-20261116.zip.sha256) |
| macOS Intel | [Download](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_macos-x64_painel-fatura-20261116.zip) | [SHA256](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_macos-x64_painel-fatura-20261116.zip.sha256) |
| macOS Apple Silicon | [Download](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_macos-arm64_painel-fatura-20261116.zip) | [SHA256](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/finance-assist_2.1.0-test.17_macos-arm64_painel-fatura-20261116.zip.sha256) |

[Manifesto de origem, builds, tamanhos e SHA256](https://github.com/boente66/Finance_Assist/releases/download/rebuild-v2.1.0-test.17-20261107/painel-fatura-20261116-manifest.json).
Os **13 arquivos publicados** tiveram tamanho e SHA256 remoto conferidos contra
os arquivos validados. Publicação na pré-release test.17 existente, sem criar
versão numérica ou mover a tag histórica. Pacotes anteriores preservados.

Para atualizar um DEB test.17 instalado, feche o aplicativo e use `--reinstall`.
