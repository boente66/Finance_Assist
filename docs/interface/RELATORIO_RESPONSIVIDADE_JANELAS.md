# Relatório Técnico Formal — Responsividade e Gerenciamento de Janelas

**Projeto:** Finance Assist — Controle Financeiro

**Data:** 2 de agosto de 2026

**Escopo:** janela principal, persistência de geometria, menu compacto, layouts responsivos, diálogos, múltiplos monitores e validação offscreen

**Situação:** implementação concluída e validada; sem `git add`, commit ou push

## 1. Resumo executivo

Foi implementada uma etapa específica de responsividade e gerenciamento de janelas, preservando a interface modernizada, a barra de título nativa do Linux e todas as regras financeiras existentes.

A solução usa `QSettings`, a geometria disponível das telas Qt, layouts fluidos, `QSplitter`, `QScrollArea` e políticas de rolagem. Não houve alteração em controllers, services, models, banco, migrações ou fluxos P0.

A suíte integral terminou com **128 testes aprovados**. A sintaxe, o diff e a renderização offscreen também foram validados.

## 2. Janela principal e controles nativos

`MainView` continua sendo um `QMainWindow` com moldura nativa. Não foi utilizado `FramelessWindowHint` nem barra de título personalizada.

Permanecem disponíveis:

- minimizar;
- maximizar;
- restaurar;
- redimensionar pelas bordas;
- mover pela barra de título;
- fechar;
- duplo clique nativo na barra de título;
- `Alt+F4`, sem interceptação.

Os flags `WindowMinimizeButtonHint`, `WindowMaximizeButtonHint` e `WindowCloseButtonHint` são confirmados pelos testes. `F11` alterna entre maximizado e restaurado. `Ctrl+Shift+M` recolhe ou expande o menu lateral.

## 3. Tamanho inicial

`WindowManager.default_geometry` consulta a tela Qt e utiliza aproximadamente 86% da `availableGeometry`. A geometria é centralizada e limitada à área disponível.

A janela não inicia obrigatoriamente maximizada. Na ausência de preferência válida, usa o tamanho proporcional da tela. O mínimo funcional da `MainView` foi reduzido para 820×600, permitindo operação compacta em resoluções menores sem reduzir excessivamente fontes.

## 4. Persistência e restauração

As preferências são gravadas em `QSettings`, separadas pelo usuário:

- geometria normal;
- estado maximizado;
- preferência de menu compacto;
- largura expandida do menu lateral.

Ao restaurar:

- blobs de geometria inválidos são rejeitados;
- a janela precisa manter uma área visível mínima em alguma tela conectada;
- geometrias fora das telas recebem fallback centralizado;
- estado minimizado é removido;
- maximizado é restaurado separadamente;
- mudança de resolução ou remoção de monitor não deixa a janela inacessível.

Nenhuma dessas preferências é gravada no banco financeiro.

## 5. Múltiplos monitores

`WindowManager.screen_for` prioriza:

1. a tela da janela pai;
2. a tela que contém o centro da janela de referência;
3. a tela da própria janela;
4. a tela primária como fallback.

Diálogos são centralizados na `availableGeometry` da tela da janela pai. A restauração compara a geometria salva com todas as telas retornadas por `QApplication.screens()`.

O ambiente de validação disponibilizou apenas uma tela virtual. A lógica multimonitor foi exercitada por geometria e fallback, mas a movimentação entre dois monitores físicos permanece como validação manual recomendada.

## 6. Menu lateral compacto e opções do usuário

O menu possui dois estados:

### Expandido

- marca e nome Finance Assist;
- ícone e texto das páginas;
- cartão do usuário com iniciais, nome e detalhe;
- Perfil, Gerenciamento de Usuários e Backup conforme permissão;
- Configurações e Sair;
- controle discreto para recolher.

### Compacto

- largura de 72 px;
- logotipo e ícones vetoriais visíveis;
- item ativo preservado;
- textos substituídos por tooltips;
- avatar do usuário;
- Configurações e Sair acessíveis;
- controle para expandir.

O modo compacto é ativado automaticamente abaixo de 1080 px de largura, sem impedir a escolha manual. A preferência manual compacta permanece mesmo em janela maximizada.

### Correção das opções administrativas

A barra lateral passou a usar `QScrollArea` com scrollbar vertical automática. Quando o submenu do usuário é expandido em pouca altura, a área rola até as opções e mantém Perfil, Gerenciamento de Usuários, Backup e Sair visíveis. O fundo do submenu permanece escuro e a barra usa o destaque do tema, corrigindo o baixo contraste observado em 720p.

## 7. Componentes responsivos criados

### `core/window_manager.py`

- cálculo proporcional e centralizado;
- seleção da tela correta;
- validação de geometria;
- fallback para área visível;
- persistência em QSettings;
- remoção do estado minimizado;
- limite e centralização de diálogos;
- filtro global para `QDialog`.

### `views/responsive_layout.py`

`FlowLayout` reorganiza automaticamente botões e filtros em novas linhas conforme a largura, usando `heightForWidth` e os tamanhos naturais dos widgets.

### Contrato `set_compact_mode`

Views com composição complexa recebem a largura disponível e reorganizam seus componentes sem consultar dados ou alterar regras.

## 8. Páginas ajustadas

### Resumo Financeiro

- cinco cards em 5, 3 ou 2 colunas;
- gráfico e próximos lançamentos em uma ou duas colunas;
- análise, metas e contas em 1, 2 ou 3 colunas;
- scroll vertical preservado;
- gráfico acompanha o painel disponível.

### Agendamentos/Projeção

- ações e filtros utilizam fluxo com quebra de linha;
- filtros estruturais e busca permanecem acessíveis;
- tabela mantém todas as dez colunas e rolagem horizontal;
- cards de totais reorganizam-se em 5, 3 ou 2 colunas;
- faturas virtuais, tipos, valores e cálculos permanecem intactos.

O saldo projetado global não foi criado porque a view atual não possui seleção inequívoca de saldo-base para compromissos de contas diferentes. Não foi introduzido cálculo visual alternativo ao `ScheduleService`.

### Contas e Lançamentos

- painel de contas/cartões e conteúdo passaram a usar `QSplitter`;
- usuário pode ajustar a divisão;
- painel esquerdo reduz a largura em modo compacto;
- `PainelFatura.set_cartao` e `set_competencia` permanecem inalterados.

### Painel de Fatura

- Limite, Usado e Disponível usam 3, 2 ou 1 coluna;
- Lançar, Pagar, PDF e Status quebram linha quando necessário;
- Mês e Ano usam fluxo responsivo;
- tabela mantém rolagem horizontal;
- paginação e textos de resumo permanecem acessíveis;
- resumo e próximas faturas aceitam quebra de texto.

### Categorias e Favorecidos

- ações e filtros quebram linha;
- buscas mantêm largura mínima utilizável;
- tabelas preservam rolagem horizontal;
- mínimo rígido de Favorecidos foi reduzido.

### Relatórios

- seletor lateral e conteúdo usam `QSplitter`;
- larguras podem ser ajustadas sem cortar o conteúdo;
- stacked pages e tabelas existentes foram preservados.

### Metas

A view já utilizava `QScrollArea`; o comportamento existente foi preservado.

### Configurações e Modo Design

- ações e seletor de banco podem quebrar linha;
- Modo Design usa `QSplitter` entre propriedades e preview;
- propriedades continuam dentro de `QScrollArea`;
- ações finais usam `FlowLayout` e permanecem alcançáveis.

## 9. Diálogos

Foi instalado um filtro global no `QApplication` para todos os `QDialog`:

- escolhe a tela da janela pai;
- limita largura e altura a 90% da área disponível;
- reduz mínimos incompatíveis com a tela;
- centraliza o diálogo;
- impede abertura fora das telas conectadas.

O Login mantém composição compacta, não é maximizado automaticamente, possui botão nativo de minimizar e é limitado a 90% da tela. Sua dimensão mínima passou a 720×540.

Diálogos canceláveis continuam usando o comportamento Qt de Esc. Ordem de tabulação e ações Enter já definidas foram preservadas.

## 10. Temas

Foram testados em modo compacto:

- Primavera;
- Noite Intensa;
- Prosperidade;
- Verão Quente;
- Personalizado.

O QSS central recebeu apenas seletores para menu compacto, submenu, controle de recolhimento e scrollbar lateral. Ícones do shell são desenhados vetorialmente porque os SVGs legados baseados em `currentColor` não permaneciam visíveis em todos os backends Qt.

Nenhum tema altera a geometria salva ou remove os controles nativos da janela.

## 11. Testes automatizados

Foi criado `tests/interface/test_window_responsiveness.py`, com cenários para:

- resize;
- maximizar e restaurar;
- salvar e restaurar geometria;
- rejeitar estado minimizado;
- fallback de geometria inválida;
- retorno de janela fora da tela;
- recolher e expandir menu;
- persistência do menu;
- tooltips e ícones no modo compacto;
- scrollbar e opções administrativas em altura reduzida;
- reorganização dos cards;
- acessibilidade dos filtros;
- rolagem de tabelas;
- limite de diálogos;
- Login compacto e minimizável;
- Painel de Fatura reduzido;
- Agendamentos reduzido;
- cinco temas no modo compacto;
- flags nativos;
- proibição de inicialização do banco real.

Resultados:

| Verificação | Resultado |
|---|---|
| Testes focados finais de janela/menu | 27 aprovados |
| Suíte completa `pytest -q` | 128 aprovados |
| Duração da suíte completa | 670,87 s — 11m10s |
| Avisos | 14 depreciações de Matplotlib/Pyparsing; nenhuma falha |
| Sintaxe Python | Aprovada |
| `git diff --check` | Aprovado |

## 12. Validação offscreen

Foram executadas e inspecionadas renderizações temporárias, não versionadas e sem dados reais:

- MainView expandida em 1440×900;
- MainView compacta em 1024×720;
- sidebar administrativa expandida em 900×600;
- menu compacto com ícones;
- cards em múltiplas linhas;
- submenu do usuário com rolagem;
- Login limitado à tela;
- Painel de Fatura e Agendamentos em largura reduzida por testes.

Maximização, restauração, minimização, geometria inválida e retorno à área visível foram simulados pelo backend Qt offscreen.

## 13. Limitações restantes

- arrastar fisicamente pelas quatro bordas e duplo clique real na barra de título dependem do gerenciador de janelas do sistema; a implementação preserva os controles nativos, mas o backend offscreen não simula mouse no desktop;
- não havia monitor físico secundário disponível;
- telas abaixo do mínimo funcional podem exigir rolagem e não são o alvo principal;
- o gráfico de saldo projetado mostrado no modelo não foi criado, pois isso exigiria novo contrato financeiro;
- avisos de depreciação pertencem às dependências instaladas.

## 14. Arquivos pertencentes à tarefa

Novos:

- `core/window_manager.py`;
- `views/responsive_layout.py`;
- `tests/interface/__init__.py`;
- `tests/interface/test_window_responsiveness.py`;
- `docs/interface/RELATORIO_RESPONSIVIDADE_JANELAS.md`.

Alterados:

- `run.py`;
- `core/themes.py`;
- `views/main_view.py`;
- `views/login_dialog.py`;
- `views/resumo_financeiro_view.py`;
- `views/agendamento_view.py`;
- `views/transacao_view.py`;
- `views/painel_fatura.py`;
- `views/lista_categorias_view.py`;
- `views/favorecido_view.py`;
- `views/relatorio_view.py`;
- `views/configuracoes_view.py`;
- `views/design_mode_dialog.py`;
- `tests/integration/test_login_visual.py`;
- `tests/integration/test_main_shell_visual.py`.

## 15. Alterações preexistentes e exclusões

O worktree estava limpo no início desta tarefa. Nenhuma alteração preexistente foi sobrescrita. O histórico publicado anteriormente foi preservado.

Devem permanecer fora de futuro commit:

- ambientes `.venv/`, `venv/`, `env/`, `assistente/`, `financeiro1/` e equivalentes;
- bancos `*.db`, `*.sqlite`, `*.sqlite3` e journals;
- backups;
- logs;
- caches e `__pycache__`;
- builds e distribuições;
- capturas e scripts temporários em `/tmp`.

## 16. Conclusão

A aplicação agora inicia proporcionalmente à tela, restaura uma geometria segura, preserva controles nativos, suporta menu compacto persistente e reorganiza os principais conteúdos sem alterar dados ou regras financeiras.

O conjunto encontra-se tecnicamente validado para revisão manual. Conforme solicitado, não foram executados `git add`, commit ou push.
