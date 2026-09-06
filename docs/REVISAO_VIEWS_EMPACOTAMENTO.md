# Relatório técnico — views e dependências do executável

Projeto: Finance Assist. Revisão da versão 2.1.0-test.4; correção destinada à 2.1.0-test.5.

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
  `DATA_DIR/finance-assist.log`, um local gravável.

## Dependências

| Componente | Situação anterior | Correção |
|---|---|---|
| Views dinâmicas | 17 módulos ausentes | Inventário explícito e verificação do PYZ |
| `typing_extensions` | Ausente no ambiente/binário local inspecionado | Dependência explícita |
| `sentence_transformers`, `transformers`, `torch`, `sklearn` | Excluídos expressamente do spec de teste | Remoção das exclusões; runtime CPU |
| `argostranslate` | Excluído expressamente do spec de teste | Remoção da exclusão |
| Poppler | Não declarado no DEB | `poppler-utils` em Depends |
| Tesseract / português | Não declarados no DEB | `tesseract-ocr`, `tesseract-ocr-por` em Depends |

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
As evidências finais de build e publicação serão acrescentadas após a validação.
