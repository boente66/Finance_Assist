# Painel de fatura — análise visual e proposta para homologação

Estado: **somente análise; proposta não implementada**. Referência: tarefa de
cartões homologada em 15/11/2026. Preservado o fluxo cartão na lateral → contexto
da fatura à direita. Não foi criado dashboard nem alterada a ordem das colunas,
fontes, margens, cards ou hierarquia do painel.

A única mudança funcional em [painel_fatura.py](../views/painel_fatura.py) é a
habilitação de ações segundo Ativo: cartões inativos não oferecem novas compras,
créditos ou importações. A validação efetiva também ocorre nos Services.
Consulta e quitação de obrigações existentes continuam disponíveis.

## Método e evidências

Capturas Linux/Qt offscreen com tema Primavera, banco sintético isolado e 16
compras em dezembro/2099 para manter ciclo ABERTA sem depender do dia atual.
Nome deliberadamente longo, bandeira Mastercard e limite de R$ 15 mil. Não são
dados pessoais. Cenários medem shell completo, sidebar, lista e contexto real.
Escala base de fontes; resultados não comprovam outras escalas, todos os nomes,
todos os temas ou renderização nativa Windows/macOS.

- [1366×768, português](./evidencias/painel-fatura-analise/painel-1366x768-pt.png)
- [1280×720, português](./evidencias/painel-fatura-analise/painel-1280x720-pt.png)
- [1920×1080, português](./evidencias/painel-fatura-analise/painel-1920x1080-pt.png)
- [1366×768, inglês](./evidencias/painel-fatura-analise/painel-1366x768-en.png)
- [Medidas estruturadas](./evidencias/painel-fatura-analise/medidas.json)
- [Consulta de cartão inativo](./evidencias/cartoes-fase2/gerenciamento-inativos.png)

| Janela | Área do painel | Viewport da tabela | Scroll horizontal da tabela | Scroll vertical |
|---|---|---|---:|---|
| 1366×768 | 800×635 | 735×281 | máximo 0 | necessário para 16 linhas |
| 1280×720 | 736×587 | 671×176 | máximo 0 | necessário, menos linhas simultâneas |
| 1920×1080 | 1354×947 | 1299×593 | máximo 0 | não necessário neste conjunto |

Portanto, **não foi constatado excesso de scroll horizontal no grid** nesses
cenários. O scroll vertical é esperado para o volume. A lista lateral apresenta
scroll horizontal com nome longo, situação distinta do grid da fatura.

## Problemas, severidade e impacto

Severidade visual: alta impede ação/leitura financeira; média prejudica leitura
ou contexto; baixa é refinamento. Nenhum bloqueio crítico de operação foi
observado nas capturas de referência.

| Achado | Severidade | Evidência / impacto | Proposta, não aplicada |
|---|---|---|---|
| Tipo recebe espaço desproporcional | Média | Em 1920, Tipo e Descrição recebem 460 px cada; em 1366, 178 px cada. Descrição longa fica abreviada enquanto Tipo contém poucas palavras | Stretch apenas para Descrição; Tipo com largura limitada |
| Descrição abreviada sem tooltip configurado no render atual | Média | Texto sintético é cortado com elipse em 1366; dificulta reconhecer compra sem abrir edição | Tooltip e detalhe acessível por teclado, sem usar edição como única leitura |
| Bandeira/estado só aparecem na lista lateral | Média | No painel, nome e competência não informam bandeira/estado; ocultar inativos pode deixar consulta histórica à direita sem linha visível | Metadados compactos junto ao título, sem coluna repetida por lançamento |
| Fechamento e vencimento não estão claros no cabeçalho | Média | Lista mostra dia de vencimento; painel não expõe as duas datas do ciclo como informação principal | Exibir datas do ciclo em linha secundária do cabeçalho |
| Status da fatura fica concentrado no resumo inferior | Média | ABERTA/FECHADA/PAGA distante da seleção e misturado aos totais | Indicador textual junto à competência, mantendo resumo financeiro |
| Resumo inferior muito denso | Média | Em 1366, texto tem largura linear ~1348 px para 784 disponíveis, com quebra de linha; múltiplos totais em negrito/cor competem | Agrupar compras/créditos/estornos/ajustes separadamente de pago/saldo; quebra previsível e alinhamento |
| Textos do resumo/tipos/status parcialmente fixos em português | Média | Cabeçalhos traduzem; renderizadores ainda têm literais como Compras/Créditos/Compra/Fechada | Revisão específica de i18n do painel, sujeita à homologação desta análise |
| Menos espaço útil em 1280×720 | Média | Refluxo dos indicadores aumenta altura; viewport cai a 176 px | Compactar metadados/ações sem reduzir fonte dos valores, validar novamente |
| Lista lateral com nome longo exige scroll horizontal | Baixa/média | Nome extenso ocupa mais largura que a lista | Elipse+tooltip acessível na lista, conservando Nome completo no contexto |
| Várias linhas repetem status da mesma fatura | Baixa | Coluna Status ainda auxilia leitura de pagamento, mas repete contexto em compras | Manter inicialmente; somente discutir ocultação após teste com tipos mistos |

## Colunas e necessidade de coluna nova

Ordem atual: **Data → Descrição → Tipo → Categoria → Valor → Status**.
É uma ordem defensável: identifica quando/o quê, classificação, valor e situação.
Recomendo mantê-la na primeira revisão; o ganho principal está nas larguras,
sem nova coluna e sem remover dados.

| Coluna | Largura medida em 1366 | Proposta de prioridade |
|---|---:|---|
| Data | 100 px | Manter data completa; compacta |
| Descrição | 178 px | Maior prioridade de espaço, única coluna Stretch |
| Tipo | 178 px | Limitar aproximadamente a 80–110 px e tooltip |
| Categoria | 121 px | Aproximadamente 120–160 px, elipse com acesso integral |
| Valor | 92 px | Largura suficiente para montantes extremos; alinhar à direita |
| Status | 66 px | Dimensionar pela tradução; evitar cortar FECHADA/registrado |

Os intervalos são hipótese de protótipo, não valores homologados. Confirmar com
valores grandes, categorias extensas, crédito/estorno, pagamentos e pt/en/es.
Não adicionar Bandeira/Ativo/fechamento/vencimento por linha: são metadados do
cartão/ciclo, repetiriam informação e consumiriam largura do grid. Também não
há evidência que justifique nova coluna estética.

## Proposta de organização e hierarquia

Dentro do mesmo contexto à direita, sem tela separada:

1. Nome do cartão como título; bandeira e estado em linha secundária curta.
2. Competência e status da fatura próximos, com fechamento/vencimento legíveis.
3. Indicadores Limite/Usado/Disponível com pesos visuais consistentes.
4. Ações e filtros existentes com ordem/tabulação preservadas, quebra controlada.
5. Tabela com prioridade de Descrição e números financeiros íntegros.
6. Resumo compacto, agrupando composição da fatura e quitação/saldo pendente.

Estado do cartão e estado da fatura devem continuar conceitos distintos:
Inativo não significa PAGA, nem FECHADA significa cartão inativo. Não alterar
estado financeiro para facilitar apresentação.

## Espaçamento, fontes e contraste

O layout atual usa margens de painel 8/6/8/6 px, espaçamento geral 7 px,
indicadores 10 px e FlowLayout de ações com 8 px. As medidas exatas por cenário,
fontes e altura de linha estão no JSON. Em larguras abaixo de 760 px do painel,
o código reduz fonte da tabela e altura das linhas, aumentando densidade.

Proposta: manter tipografia financeira sem reduzir para compensar excesso de
conteúdo; limitar título longo por quebra/tooltip; estabelecer intervalos
consistentes de 8–12 px entre grupos. Usar hierarquia de peso com parcimônia no
rodapé. Cores de valor/estado precisam de redundância textual; contrastes devem
ser medidos por tema no protótipo, não considerados aprovados por inspeção.
No tema capturado, azul forte no resumo e saldos compete com o título e cards.

## Aceite visual futuro e riscos

Homologar protótipo em 1366×768 antes de aplicar: essenciais sem scroll horizontal,
valor/status/datas íntegros, título e descrição longa recuperáveis por teclado,
idioma consistente, ações alcançáveis, sem confundir Ativo com estado da fatura.
Repetir em 1280×720, 1920×1080, 125/150% de escala e temas claro/escuro; verificar
renderização nativa nos três sistemas.

Riscos: cabeçalho novo consumir altura e reduzir tabela; tradução aumentar
larguras; excesso de badges; ocultar coluna sem alternativa; mudar seleção,
ordenação/paginação ou IDs ao relayout; limite/saldo perderem destaque.
Não há autorização para implementar essas propostas nesta entrega.

## Decisões pendentes

- Aprovar ou ajustar cabeçalho com Nome/Bandeira/Ativo e status/datas do ciclo.
- Aprovar larguras e revisão do resumo; confirmar necessidade de manter Status
  por linha em cenário com compras, créditos e pagamentos.
- Autorizar separadamente revisão de tradução dos literais do painel e acessos
  de leitura de descrição longa.
- Homologar escala/fontes/contraste e plataformas. Até lá, somente o bloqueio
  funcional das ações de cartão inativo faz parte da implementação.
