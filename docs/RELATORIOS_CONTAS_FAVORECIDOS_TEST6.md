# Revisão de relatórios, encerramento de acesso e favorecidos

Versão: 2.1.0-test.6 — versão de teste. Data: 9 de setembro de 2026.

## 1. Escopo e preservação de dados

Revisão dos relatórios diário, anual e informe; encerramento voluntário do
acesso; cadastro e edição de favorecidos PF/PJ. Foram mantidas as camadas
view → controller → service → model → SQLite. Não houve substituição do banco
do usuário, exclusão de histórico ou alteração das regras de lançamentos.

“Encerrar minha conta” significa desativação do acesso, não eliminação definitiva
dos dados pessoais. A interface informa expressamente que o histórico permanece.
A eliminação definitiva, seus critérios e a política de retenção não estão
implementados nesta entrega.

## 2. Causas identificadas e correções

| Área | Causa no código anterior | Solução |
|---|---|---|
| Relatório anual | A tela possuía tabela, mas não carregava dados ao selecionar a seção. | Seletor de ano, botão Gerar e carregamento ao abrir a seção. |
| Tabela após estado vazio | O estado vazio reduzia a tabela a uma coluna; o preenchimento não restaurava as cinco colunas. | Restauração explícita de colunas, cabeçalhos e campos por nome. |
| Informe incompleto | `INNER JOIN` descartava transações sem favorecido. Documento nulo podia interromper a formatação. | `LEFT JOIN` limitado ao usuário e tratamento de documento ausente. |
| Histórico antigo | Anos limitados na interface e datas legadas `dd/mm/yyyy` não interpretadas pelo filtro SQLite. | Anos consultados nos dados, opção Todo histórico e normalização apenas na leitura. |
| Erros ocultos | Exceções SQL eram convertidas em listas vazias. | Propagação ao controller, registro do erro e mensagem de falha distinta de ausência de dados. |
| Gráfico | Distribuição com total zero podia falhar antes do preenchimento da tabela. | Tabela preenchida primeiro e tratamento do gráfico sem movimentação. |
| Indicadores | Valores anteriores permaneciam quando a consulta retornava vazia. | Limpeza de totais e gráfico. |
| Classificação do informe | Texto atribuía tributação/dedutibilidade e IRRF zero sem dados suficientes. | Relatório auxiliar das transações registradas, com receitas, despesas e resultado, sem classificação fiscal presumida. |
| Encerramento da conta | Controller enviava senha a parâmetro que esperava dados do usuário; a operação existente excluía registros. | Verificação da senha e identidade, proteção do último administrador e desativação transacional com invalidação de tokens e limpeza da sessão autenticada. |
| Favorecido duplicado | Consulta prévia fora da transação permitia corrida entre cadastros simultâneos. | `BEGIN IMMEDIATE` e nova consulta de CPF/CNPJ dentro da transação, limitada ao usuário. |
| Documento compartilhado entre usuários | Índices globais únicos impediam duas pessoas de cadastrar o mesmo favorecido em seus históricos separados. | Migração 5 troca os índices por índices de busca e triggers que garantem unicidade dentro do usuário, sem apagar ou regravar registros. |
| Documento inválido na edição | A edição aceitava CPF `123`, embora o cadastro rejeitasse. | Validação de comprimento, tipo e nome antes da escrita; teste verifica que a rejeição preserva o cadastro. |
| Falha na consulta de anos | Informe e totais anteriores podiam permanecer na tela. | Limpeza dos relatórios e bloqueio de PDF/impressão quando o carregamento dos períodos falha. |
| Edição PF/PJ | Interface permitia trocar o tipo, mas o model não realizava essa conversão. | Tipo bloqueado durante a edição; demais campos continuam editáveis. |

## 3. Classes e métodos afetados

- `RelatorioModel`: consultas diárias, anuais, anos disponíveis e `_informe`.
- `RelatorioService`: validação de período e `gerar_texto_informe`.
- `RelatorioController`: consulta autenticada de anos e tratamento de erros.
- `RelatorioView`: `on_load`, `load_diario`, `load_anual`, `preview`, exportação e preenchimento da tabela.
- `Database`: migração aditiva 4, `usuarios.Ativo`, padrão 1 para usuários existentes; migração 5 ajusta a unicidade de CPF/CNPJ por usuário.
- `UserModel`, `UserService`, `UserController`: autenticação e encerramento do próprio acesso.
- `PerfilView`: confirmação, senha e saída após encerramento; `GerenciamentoUsuariosView`: status de acesso.
- `FavorecidoModel.add_favorecido`, `FavorecidoService.criar` e `FavorecidoDialog`: validação, concorrência e retorno do identificador persistido.

A confirmação/rollback do encerramento usa `Database.unit_of_work` existente.
A migração não remove a tabela `usuarios`, não reconstrói transações e não limpa
o banco. CPF/CNPJ são normalizados e têm o comprimento verificado; não foi
introduzida validação de dígitos verificadores nesta revisão.

## 4. Estratégia de testes

Os testes novos usam SQLite temporário, os models, services e controllers reais,
além de widgets Qt offscreen. Não abrem o banco de desenvolvimento nem o banco
pessoal instalado. Substituições são limitadas ao caminho temporário do banco
e às respostas dos diálogos modais de confirmação.

- Favorecidos: cadastro PF e PJ pelo botão, leitura persistida, edição,
  documento/telefone normalizados e presença do favorecido no informe.
- Concorrência: duas conexões tentando cadastrar o mesmo documento;
  isolamento entre usuários com documento igual.
- Atomicidade: trigger SQLite provoca falha na pessoa física; nenhum registro
  parcial permanece na tabela de favorecidos.
- Relatórios: dados sem favorecido/documento, isolamento por usuário,
  exclusão de transferências internas, datas legadas, período diário,
  falha SQL, recuperação da tabela, anual, total zero e PDF real.
- Conta: senha incorreta, identidade, último administrador, encerramento com
  histórico preservado, token revogado, rollback por falha e saída da interface.
- Migração: banco legado e parcialmente migrado, integridade SQLite e chaves
  estrangeiras; backup/restauração mantendo o status encerrado e transações.

## 5. Estado da validação e distribuição

Código validado: `548bdf7a5523596d64fcb740bbe0705d3ba9fd0f`.

- Ubuntu 24.04: **241 testes aprovados**, 20,88 s.
- Ubuntu 26.04: **241 testes aprovados**, 18,75 s.
- Verificação local de favorecidos, encerramento e migrações: **31 testes aprovados**, 464,23 s.
- Sintaxe dos 148 arquivos Python verificada; `git diff --check` sem erros.
- Dependências instaladas: `pip check` sem incompatibilidades.
- Os avisos da suíte referem-se a APIs depreciadas de bibliotecas (Matplotlib/Pyparsing e PyPDF2); não são falhas dos fluxos testados.

Evidências: [CI multiplataforma](https://github.com/boente66/Finance_Assist/actions/runs/34423936095)
e [CI Ubuntu 24.04/Mint](https://github.com/boente66/Finance_Assist/actions/runs/34423938712).

Os dois fluxos de CI foram aprovados. O DEB geral foi instalado e iniciado em
Ubuntu 22.04, 24.04 e 26.04; os testes confirmaram a preservação de um banco
preexistente, a criação limpa para novos usuários e o funcionamento das views.
O DEB nativo Ubuntu 24.04/Mint passou pela instalação, pelas views, pelo OCR e
pelo teste de banco preexistente. O pacote Windows passou pelo inventário e pelo
teste das views. Os três arquivos e seus checksums foram publicados na
[pré-release v2.1.0-test.6](https://github.com/boente66/Finance_Assist/releases/tag/v2.1.0-test.6).

Não foi recebido um traceback do aplicativo instalado para este incidente.
As causas acima foram identificadas por inspeção e cenários reproduzíveis; erros
injetados pelos testes não são apresentados como logs reais do usuário.

## 6. Limites

Aprovação automatizada não equivale a garantia de funcionamento de 100% em todo
hardware ou ambiente. A versão continua de teste. Atualizações devem ser feitas
sem apagar a pasta de dados; recomenda-se backup antes da instalação.
