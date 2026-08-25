# Auditoria de escala visual e responsividade

**Projeto:** Finance Assist

**Versão:** 2.1.0-test.2

**Data:** 24 de agosto de 2026

**Escopo:** todas as classes visuais existentes em `views/`, tema global e
geometria compartilhada de janelas.

## 1. Objetivo e método

A auditoria avaliou as 37 classes Qt declaradas nos 36 módulos Python da camada
`views`. Foram pesquisados tamanhos fixos, mínimos, fontes criadas por código,
folhas de estilo locais e tokens globais. A análise também confrontou as telas
com os limites aplicados por `WindowManager` e com os cinco temas disponíveis.

Não houve alteração de controller, service, model, schema ou regra financeira.
As correções ficaram restritas à apresentação, à geometria dos diálogos, aos
testes correspondentes e ao empacotamento.

## 2. Resultado executivo

| Área | Situação anterior | Classificação | Solução aplicada |
|---|---|---|---|
| Tema global | base 10 pt, título 22 pt, valores 18 pt e linhas 38 px | impacto alto | base 9 pt, título 18 pt, valores 14–15 pt e linhas 34 px |
| Tema personalizado | aceitava título 36 pt, campos 64 px e linhas 72 px | impacto alto | controles e gerador limitados a intervalos seguros |
| Login | marca 25 pt, janela mínima 720×540 e composição sempre completa | impacto alto | marca 20 pt, mínimo 600×500 e ocultação progressiva do painel decorativo |
| Perfil | avatar 116 px e ícones/títulos superdimensionados | impacto médio | avatar 96 px e hierarquia reduzida proporcionalmente |
| Intervalo de datas | mínimo de 600 px e título com CSS local | impacto médio | mínimo 420×360, tokens globais e calendários empilháveis |
| Criar conta | diálogo travado em 360×260 | impacto médio | diálogo redimensionável, centralizado e limitado à tela |
| Demais telas | mínimos funcionais de tabelas e formulários | adequado | preservados para não prejudicar operação e legibilidade |

## 3. Padrão visual estabelecido

- texto base: 9 pt, personalizável entre 8 e 12 pt;
- título principal: 18 pt, limitado entre 15 e 20 pt;
- subtítulo: 10 pt, limitado entre 8 e 11 pt;
- tabelas: 9 pt, limitado entre 8 e 11 pt;
- botões e campos: 34 px, limitado entre 30 e 42 px;
- linhas de tabela: 34 px, limitado entre 30 e 44 px;
- títulos e indicadores maiores permanecem reservados à hierarquia principal;
- diálogos continuam limitados a 90% da área útil pelo `WindowManager`.

Os limites defensivos no gerador de QSS também protegem configurações antigas
ou temas JSON importados com métricas acima do padrão. O editor visual apresenta
os mesmos intervalos, evitando discrepância entre a preferência exibida e o
resultado renderizado.

## 4. Arquivos afetados

| Arquivo | Responsabilidade da mudança |
|---|---|
| `core/themes.py` | tokens padrão, limites e componentes compartilhados |
| `views/design_mode_dialog.py` | faixas coerentes no editor de tema |
| `views/login_dialog.py` | escala e composição responsiva |
| `views/date_range_dialog.py` | empilhamento e remoção de estilo local |
| `views/criar_conta_dialog.py` | remoção de tamanho fixo e ajuste à tela |
| `tests/interface/test_window_responsiveness.py` | cenário compacto de login |
| `tests/integration/test_interface_visual_scale.py` | regressão de escala e diálogos |

## 5. Preservação funcional

O login continua chamando `authenticate_user`; criar conta continua chamando
`AccountController.create_account`; o intervalo de datas mantém os mesmos
valores `yyyy-MM-dd`. Nenhum nome de campo persistido ou contrato de operação foi
alterado. Painéis com tabelas, gráficos e formulários mantiveram rolagem e seus
controles funcionais.

## 6. Critérios de aceite

- nenhuma fonte de conteúdo comum excede 20 pt;
- nenhum tema personalizado produz campos ou botões maiores que 42 px;
- login utilizável em 600×500 e nas resoluções 1024×768 e 1280×720;
- diálogos não excedem 90% da área disponível;
- telas decorativas cedem espaço ao formulário em largura/altura reduzidas;
- temas Primavera, Noite Intensa, Prosperidade, Verão Quente e Personalizado
  continuam usando o sistema centralizado de tokens.

## 7. Riscos residuais

A validação automatizada offscreen confirma geometria e presença dos controles,
mas não substitui homologação visual manual em cada combinação de escala DPI,
fonte instalada, compositor Linux e configuração de acessibilidade do Windows.
A versão permanece explicitamente classificada como teste.
