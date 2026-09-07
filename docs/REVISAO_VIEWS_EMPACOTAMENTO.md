# Relatório técnico — views e dependências do executável

Projeto: Finance Assist. Revisão da versão 2.1.0-test.4; correção destinada à 2.1.0-test.5.

Data da revisão: 7 de setembro de 2026.

## Parecer final

**APROVADO PARA DISTRIBUIÇÃO COMO VERSÃO DE TESTE**, dentro da cobertura abaixo.
O build de release é o commit `d7b7f4e4a4461a90e9992359bb518ba89e0848ef`.
A [execução final 34095103102](https://github.com/boente66/Finance_Assist/actions/runs/34095103102)
concluiu todos os sete jobs com sucesso.

| Verificação final | Resultado |
|---|---|
| Suíte completa no Ubuntu 24.04 | APROVADO — 210 testes, 14 avisos de depreciação |
| Suíte completa no Ubuntu 26.04 | APROVADO |
| Inventário e execução de views no DEB | APROVADO |
| Inventário, execução e encerramento no Windows | APROVADO |
| Instalação do mesmo DEB no Ubuntu 22.04 | APROVADO |
| Instalação do mesmo DEB no Ubuntu 24.04 | APROVADO |
| Instalação do mesmo DEB no Ubuntu 26.04 | APROVADO |
| Renderização XCB e OCR real nas três versões Ubuntu | APROVADO |
| Banco novo isolado e preservação do banco sentinela existente | APROVADO |
| Todos os fluxos possíveis e equipamentos do mercado | NÃO VERIFICADO — não se afirma garantia universal |

O relatório do executável Windows distribuído contém 91 verificações aprovadas:
36 módulos, 39 widgets/diálogos e 16 imports de dependências, com lista de erros
vazia. Seu ZIP passou na conferência SHA256 e no teste de integridade do arquivo.
O DEB também registrou 91 verificações e zero erros no build. Após instalação,
a matriz executou adicionalmente a prova real de OCR. O SHA256 do DEB foi
conferido e seu conteúdo inspecionado: executável, atalho, ícone e licença,
sem bancos, logs ou backups pessoais. Versão Debian: `2.1.0~test5`, `amd64`.

Os instaladores e instruções estão na
[release v2.1.0-test.5](https://github.com/boente66/Finance_Assist/releases/tag/v2.1.0-test.5)
e no [README](../README.md#9-pacotes-de-teste).
O histórico abaixo registra a investigação e as tentativas intermediárias;
as pendências mencionadas nessas tentativas foram superadas pela execução final.

## Incidente e evidência

O Resumo Financeiro não carregava no executável distribuído. A inspeção do PYZ
do DEB baixado da release 2.1.0-test.4 confirmou a ausência de 17 módulos.
O mesmo resultado foi observado no binário local anterior.

Módulos ausentes:

```text
views.agendamento_dialog
views.agendamento_view
views.backup_view
views.configuracoes_view
views.date_range_dialog
views.design_mode_dialog
views.execute_schedule_dialog
views.favorecido_view
views.gerenciamento_usuarios_view
views.lista_categorias_view
views.meta_dialog
views.meta_view
views.perfil_dialogs
views.perfil_view
views.relatorio_view
views.resumo_financeiro_view
views.subcategoria_dialog
```

## Causa raiz

`MainView._resolve_view_class` utiliza `importlib.import_module` para a navegação.
Esses imports precisam ser declarados ao PyInstaller. O spec chamava
`collect_submodules('views')` antes de configurar o caminho do projeto; essa
coleta não localizava o pacote quando o build era iniciado pelo entry point do
ambiente virtual. A análise estática ainda incluía as views importadas
diretamente, produzindo um binário parcialmente funcional.

A documentação do PyInstaller esclarece que a pasta do spec não é incluída
automaticamente no caminho de busca do Python:
[Using Spec Files](https://pyinstaller.org/en/stable/spec-files.html).

O teste anterior só iniciava o login por 15 segundos. Ele validava bootloader,
Qt e criação de banco, mas não alcançava a navegação após autenticação.

## Traceback reproduzido

Não foi recebido o log original da máquina do usuário. O traceback abaixo é
da verificação executada nesta revisão contra o DEB publicado, e não uma
transcrição inventada do erro original:

```text
Traceback (most recent call last):
  File "packaging/verify_archive.py", line 20, in <module>
    verify(sys.argv[1])
  File "packaging/verify_archive.py", line 15, in verify
    raise RuntimeError('Views ausentes do executável: ' + ', '.join(missing))
RuntimeError: Views ausentes do executável: views.agendamento_dialog, views.agendamento_view, views.backup_view, views.configuracoes_view, views.date_range_dialog, views.design_mode_dialog, views.execute_schedule_dialog, views.favorecido_view, views.gerenciamento_usuarios_view, views.lista_categorias_view, views.meta_dialog, views.meta_view, views.perfil_dialogs, views.perfil_view, views.relatorio_view, views.resumo_financeiro_view, views.subcategoria_dialog
```

## Correções e prevenção

- Specs enumeram arquivos de views diretamente a partir de `SPECPATH`, com
  `pathex` explícito. O spec de teste gera um manifesto independente do PYZ.
- `packaging/verify_archive.py` compara cada módulo-fonte com o arquivo final;
  ausências interrompem o build.
- `run.py --self-test-views` prepara armazenamento temporário antes de importar
  configuração ou persistência. Não abre o banco pessoal.
- `core.packaged_view_check.run_check` importa os módulos, constrói widgets e
  diálogos com controllers reais e dados de teste, executa `on_load` quando
  disponível e renderiza com Qt offscreen. Erros registrados ou exceções fazem
  o processo retornar código diferente de zero.
- O build Linux e Windows executa esse teste antes de gerar o pacote final.
  A matriz Ubuntu repete o teste no executável instalado pelo `apt`.
- `MainView._handle_menu_click` registra falhas de resolução e informa o erro
  na barra de status, mantendo a tela anterior disponível.
- O log passa de um arquivo relativo ao diretório corrente para
  `DATA_DIR/finance-assist.log`, um local gravável. A configuração ocorre antes
  dos imports de models, evitando que o `basicConfig` legado selecione
  `database.log` no diretório corrente. O teste verifica que nenhum desses
  arquivos de log aparece no diretório de execução.

## Dependências

| Componente | Situação anterior | Correção |
|---|---|---|
| Views dinâmicas | 17 módulos ausentes | Inventário explícito e verificação do PYZ |
| `typing_extensions` | Ausente no ambiente/binário local inspecionado | Dependência explícita |
| `sentence_transformers`, `transformers`, `torch`, `sklearn` | Excluídos expressamente do spec de teste | Remoção das exclusões; runtime CPU |
| `argostranslate` | Excluído expressamente do spec de teste | Remoção da exclusão |
| Poppler | Não declarado no DEB | `poppler-utils` em Depends |
| Tesseract / português | Não declarados no DEB | `tesseract-ocr`, `tesseract-ocr-por` em Depends |
| Bibliotecas XCB | Cinco ausentes no build Ubuntu | `libxcb-icccm4`, `libxcb-image0`, `libxcb-keysyms1`, `libxcb-render-util0`, `libxcb-shape0` no build e Depends |

Bibliotecas Python são verificadas por importação no processo congelado.
Modelos de aprendizado não são bibliotecas: seu download inicial depende da
rede e do provedor. O ZIP Windows exige instalação externa de Poppler e
Tesseract para OCR; o DEB resolve esses programas pelo gerenciador de pacotes.

## Limites da validação

Carregar e renderizar todas as views não equivale a provar 100% de todos os
fluxos, entradas possíveis, impressoras, serviços de e-mail ou ambientes
gráficos. A suíte de integração complementa o teste de empacotamento.
Os diálogos de edição recebem fixtures de apresentação; esse teste não
substitui os testes de gravação, autorização e transações financeiras.

O resultado de cada execução é registrado em JSON (`checked`, `errors`, `ok`).
## Evidências obtidas

- Executável local corrigido: 36 módulos de views presentes; 39 widgets/diálogos
  construídos e renderizados; 12 imports de dependências, totalizando 87
  checagens aprovadas e zero erros.
- Código-fonte: 75 checagens de módulos e widgets aprovadas, com banco temporário.
- Suíte completa no Ubuntu 24.04: 210 aprovados, 14 avisos de depreciação
  (execução 34076884314, commit `baeaa8c`).
- Suíte completa no Ubuntu 26.04: job aprovado na mesma execução.
- Primeira execução CI da correção: build DEB e instalação/testes de views
  aprovados nas três versões Ubuntu. O teste Windows retornou falha, exigindo
  revisão da espera do processo e coleta explícita do relatório de diagnóstico.
- Dependências declaradas no ambiente local: `pip check` sem incompatibilidades.
- Sintaxe Python e `git diff --check`: aprovados.
- Execução local completa: `210 passed, 14 warnings in 867.76s`.
- Teste local das views após descarte explícito dos widgets: aprovado,
  com encerramento normal do processo.

A prova funcional adicional de OCR gera um PDF de imagem, extrai seu texto com
o fluxo real `MakePDF.ler_pdf` e exige reconhecimento de “FINANCE”. Na matriz
Ubuntu, a renderização também usa XCB com Xvfb, além do offscreen usado no build.

O DEB do commit `717960e` passou na instalação, renderização XCB e OCR nas
três versões Ubuntu: [execução 34076267690](https://github.com/boente66/Finance_Assist/actions/runs/34076267690).
Essa execução não aprova Windows, cujo job falhou. A validação seguinte é
[34076884314](https://github.com/boente66/Finance_Assist/actions/runs/34076884314).

### Pontos de código envolvidos

- `MainView._handle_menu_click` e `MainView._resolve_view_class`
  (`views/main_view.py`): navegação dinâmica e diagnóstico da falha de import.
- `run.py`: isolamento do modo de teste antes da configuração do banco e
  seleção de diretório gravável para logs.
- `core.packaged_view_check.run_check`: construção das telas com persistência
  temporária, captura de erros, checkpoints e prova real de OCR.
- `MakePDF._ocr_pdf_sistema` (`utilitarios/makepdf.py`): ambiente do subprocesso
  separado das bibliotecas do bootloader Linux.
- `packaging/windows/runtime_binaries.py`: seleção consistente de DLLs MSVC;
  não altera controllers, models, schema ou regras financeiras.

### Falha gráfica adicional reproduzida

A execução com XCB revelou uma falha não detectável pelo backend offscreen:

```text
qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
This application failed to start because no Qt platform plugin could be initialized.
Aborted
Process completed with exit code 134.
```

Os logs do PyInstaller confirmaram `Library not found` para
`libxcb-shape.so.0`, `libxcb-icccm.so.4`, `libxcb-render-util.so.0`,
`libxcb-keysyms.so.1` e `libxcb-image.so.0`. Essas bibliotecas estavam presentes
no desktop local, mas ausentes no ambiente limpo de build. Foram adicionadas
ao build e às dependências do DEB, mantendo a prova XCB obrigatória.

### Diagnóstico Windows

O processo terminou com código `-1073741819` (`0xC0000005`, violação de acesso)
durante `import:argostranslate.translate`, após importar com sucesso as
bibliotecas financeiras, gráficas e `sentence_transformers`. Trata-se de falha
nativa, por isso não produziu traceback Python. O relatório incremental passou
a preservar a última etapa alcançada e o build captura stdout/stderr.

Foi introduzida a restrição `ctranslate2==4.6.0` somente no Windows como candidato
de compatibilidade. Sua aprovação depende da execução congelada; as dependências
nativas da tradução também passaram a ser importadas individualmente no teste.

A verificação individual confirmou que CTranslate2, spaCy e Stanza carregavam.
O erro localizado foi no ONNX Runtime, dependência da segmentação de texto:

```text
File "onnxruntime\\capi\\_pybind_state.py", line 32, in <module>
ImportError: DLL load failed while importing onnxruntime_pybind11_state:
A dynamic link library (DLL) initialization routine failed.
```

Foi fixado `onnxruntime==1.22.1` no Windows para validação dessa combinação.
A execução 34076267690 mostrou que essa restrição, isoladamente, não resolveu
o erro. A próxima validação seleciona o runtime C++ redistribuível completo
do Visual Studio e substitui cópias antigas, inclusive as coletadas dentro
de bibliotecas Qt. O build interrompe se o runtime não estiver disponível;
dois testes verificam a substituição e a rejeição de diretório incompleto.
Essa hipótese só será considerada aprovada após o teste do executável Windows.
Na execução 34076884314, a substituição do MSVC eliminou o erro de importação:
todas as dependências e views foram verificadas, com `errors: []`. O processo,
porém, ainda encerrou com violação de acesso depois do relatório. A verificação
passou a entregar explicitamente os eventos Qt `DeferredDelete` antes de
destruir QApplication, mantendo faulthandler ativo durante a finalização nativa.
A publicação Windows permanece condicionada ao código de saída zero.
O faulthandler da execução 34077560754 localizou a violação de acesso em
`run.py:44`, na chamada a `QMessageBox.critical` pelo tratador global durante
o encerramento. O teste agora usa o tratador de exceção de console e fecha
as conexões do banco temporário e os logs antes da remoção do diretório,
necessária no Windows (arquivos abertos não podem ser removidos como no Linux).
O teste local passou após esse ajuste; a aprovação congelada continua obrigatória.

A execução [34094220640](https://github.com/boente66/Finance_Assist/actions/runs/34094220640)
aprovou todos os sete jobs após essa correção, incluindo o encerramento do
executável Windows. O runtime MSVC utilizado foi `14.44.35211.0`. Portanto,
não foi necessário ignorar códigos de erro ou terminar o processo à força.
A falha de inicialização nativa e sua repetição pelo import de Argos explicam
por que não havia relatório final nas primeiras tentativas. Não se atribui
essa falha a CTranslate2 com base apenas no nome do import de tradução.

### OCR em versões novas do Ubuntu

Após corrigir o XCB, todas as views renderizaram. O OCR passou no Ubuntu 22.04,
mas a execução real no 24.04 revelou:

```text
pdfinfo: /tmp/_MEI.../libstdc++.so.6: version `GLIBCXX_3.4.32' not found
(required by /lib/x86_64-linux-gnu/libpoppler.so.134)
RuntimeError: O OCR do PDF de teste não retornou o texto esperado
```

O bootloader altera `LD_LIBRARY_PATH` para carregar suas bibliotecas. Poppler e
Tesseract pertencem ao sistema e não devem herdar esse caminho. A correção em
`MakePDF._ocr_pdf_sistema` fornece uma cópia do ambiente aos subprocessos com o
caminho original restaurado. O ambiente global não é alterado, preservando os
outros fluxos e threads do aplicativo. O processamento mantém a ordem numérica
das páginas e usa armazenamento temporário, limites de execução e argumentos
sem shell. Dois testes exercitam o ambiente de um processo filho real.
