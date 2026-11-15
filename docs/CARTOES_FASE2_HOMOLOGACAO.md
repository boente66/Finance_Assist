# Cartões — relatório para homologação da Fase 2

Data: 15/11/2026. Base inicial: `3638121`. Estado: implementação local validada;
aguarda homologação humana. Sem commit, push, release ou recompilação.

## 1. Autorização e escopo

Após a [análise prévia](./CARTOES_FASE2_ANALISE_PREVIA.md), o responsável aprovou
NULL para ausência de bandeira e as duas normalizações individuais propostas,
inicialmente em cópia isolada. A implementação está limitada ao cadastro/edição
contextual de cartões, preservando View → Controller → Service → Model → Database.
Não foram iniciados os demais itens da Fase 2 nem sincronização em nuvem.

Os três bancos originais não foram migrados/normalizados por esta tarefa.
**Ao executar futuramente este código em um banco original, sua inicialização
aplicará a migration 9.** Por isso a homologação deve usar ambiente de teste/cópia
com destino explícito; não iniciar este checkout no banco instalado antes do aceite.
A migration não renomeia cartões: normalização é ação separada e revisada.

## 2. Estrutura anterior e final proposta

Anterior: ID_Cartao INTEGER PRIMARY KEY AUTOINCREMENT; Nome TEXT NOT NULL;
Limite REAL NOT NULL DEFAULT 0; Dia_Fechamento INTEGER NOT NULL;
Dia_Vencimento INTEGER NOT NULL; Ativo INTEGER DEFAULT 1; ID_Usuario INTEGER,
FK para usuarios com ON DELETE CASCADE. Sem índice explícito de credito,
sem UNIQUE/CHECK adicional. DDL completo na análise prévia.

Final: mesmas colunas, PK/FK/defaults, com **Bandeira TEXT DEFAULT NULL** adicional.
Banco novo recebe o campo no CREATE; banco antigo recebe ALTER TABLE aditivo.
A ordem física da coluna pode diferir entre banco novo e migrado; o código usa
nomes de coluna, não offsets. Nenhum ID é recriado nem tabela reconstruída.

Migration 9 `optional_card_network`, em [database.py](../database/database.py):

```sql
-- Executado apenas quando PRAGMA table_info não contém Bandeira:
ALTER TABLE credito ADD COLUMN Bandeira TEXT DEFAULT NULL;
```

Usa executor transacional e registro de migrations existentes. O validador exige
coluna TEXT opcional. Reexecução verifica sem duplicar coluna/migration. Coluna
pré-existente compatível é aceita; schema incompatível deve produzir erro, não
ser silenciosamente reconstruído. Não altera Nome, limite, dias, Ativo ou vínculos.

## 3. SQL, inconsistências e preservação

Consultas executadas: table_info, foreign_key_list, index_list, sqlite_master,
contagens, nomes, NULL/vazio, duplicidade por usuário, JOINs de vínculos,
LEFT JOINs de órfãos, pesquisa de bandeiras no Nome, schema_migrations,
foreign_key_check e integrity_check. SQL detalhado na análise prévia.

| Banco original inspecionado em leitura | Cartões | Faturas | Lançamentos | Pagamentos | Integrity | FK |
|---|---:|---:|---:|---:|---|---|
| Legado na raiz | 1 | tabela ausente | 0 | 0 | ok | sem violações |
| Desenvolvimento local | 0 | 0 | 0 | 0 | ok | sem violações |
| Instalado | 3 | 49 | 189 | 14 | ok | sem violações |

Nenhum nome NULL/vazio, duplicidade por usuário segundo lower(trim(Nome)),
usuário inválido ou referência órfã nas FKs levantadas. Ausência de movimento não
é erro. Configuração de desenvolvimento referencia banco inexistente de pasta
antiga: diagnóstico registrado; nenhuma configuração corrigida automaticamente.

Cópia consistente do banco instalado feita por SQLite backup API. Antes da
normalização, a migration e suas reexecuções preservaram todas as tabelas de
negócio e todos os valores anteriores de credito. Na cópia limpa normalizada,
comparação célula a célula contra o original permitiu apenas os dois pares
Nome/Bandeira aprovados; as demais células e relações permaneceram iguais.
Nova checagem: integrity_check=ok e foreign_key_check sem linhas.

## 4. Normalização e registros ambíguos

Duas normalizações aprovadas executadas **somente na cópia**, retirando token
independente Mastercard do início/fim do Nome e definindo Bandeira=Mastercard.
Não houve correção de grafia, acentos ou interpretação de produto bancário.
Limite, dias, status, IDs, faturas, lançamentos e pagamentos preservados.

O registro do banco legado cujo nome é apenas a bandeira foi mantido intacto:
retirar o token deixaria Nome vazio. Sem nome comercial fictício ou inferência.

Relatório individual privado contém banco, ID_Cartao (nome real da PK; não existe
ID_Credito), valor anterior, nome proposto, bandeira e motivo. Evidências com
nomes/IDs reais ficam fora do repositório e não devem integrar commit/push.
A entrega pública registra somente totais e procedimentos.

## 5. Camadas e arquivos da implementação

| Arquivo | Impacto |
|---|---|
| [database.py](../database/database.py) | Campo em schema novo e migration 9 idempotente/aditiva |
| [credito_model.py](../models/credito_model.py) | INSERT com Bandeira/Ativo; leituras por SELECT *; UPDATE por allowlist somente de campos enviados; exclusão lógica inalterada |
| [card_networks.py](../services/card_networks.py) | Catálogo canônico de domínio e normalização de ausência/case/espaços; rejeição de valor arbitrário |
| [fatura_service.py](../services/fatura_service.py) | Validação antes de persistir; omissão preserva, None explícito limpa; mantém titularidade |
| [fatura_controller.py](../controllers/fatura_controller.py) | Mapeamento de bandeira e edição parcial para Service; expõe catálogo sem SQLite |
| [criar_cartao_dialog.py](../views/criar_cartao_dialog.py) | QComboBox contextual no cadastro/edição, padrão neutro, seleção persistida; só envia campos efetivamente alterados na edição |
| [card_network_selector.py](../views/card_network_selector.py) | Ícones locais, texto comercial sem tradução, fallback genérico |
| [i18n_catalogs.py](../core/i18n_catalogs.py) | Bandeira, opção neutra, botão Salvar cartão e erro em inglês/espanhol offline |
| [card-networks/](../assets/icons/card-networks/) | 11 SVGs, licença, procedência/hash e aviso de marcas |
| [test_card_networks.py](../tests/integration/test_card_networks.py) | Regressões específicas de migration, dados, camadas, CRUD, formulário, tradução e backup |
| [test_migrations_p0_avancadas.py](../tests/integration/test_migrations_p0_avancadas.py) | Expectativas incluem migration 9; demais assertivas preservadas |
| [test_balance_adjustment_neutral.py](../tests/integration/test_balance_adjustment_neutral.py) | Versão máxima esperada passa a 9; preservação de transações continua exigida |
| [test_correcao_ciclo_fatura.py](../tests/integration/test_correcao_ciclo_fatura.py) | Data do cenário de movimentação fixada antes do fechamento; regra financeira não alterada |
| Documentos e [evidências visuais](./evidencias/cartoes-fase2/) | Análise prévia e relatório para homologação; capturas usam dados sintéticos |

O cadastro já recebia Ativo no Controller, mas o INSERT ignorava o valor. Agora
persiste o status do formulário, preservando listagem de ativos/inativos e
exclusão lógica. Na edição, somente alterar Bandeira não regrava limite, dias,
Nome ou Ativo. Isso também protege limites legados com precisão superior à
exibida ou fora da faixa inicial do widget. Não há mudança na política financeira.

## 6. Catálogo consolidado para a proposta de homologação

Opção inicial neutra: **Sem bandeira**, armazenada como NULL. Não conta nas 14.

| Opção comercial | Escopo e cuidado |
|---|---|
| Visa | Rede internacional; não inferir por emissor |
| Mastercard | Rede internacional, independente do nome comercial |
| Elo | Rede brasileira |
| American Express | Nome comercial mantido integralmente |
| Hipercard | Manter para legado; não confundir produto atual com rede histórica |
| Diners Club | Rede internacional; não inferir a partir de Discover |
| Discover | Distinta de Diners Club/JCB/UnionPay apesar de acordos de rede |
| JCB | Rede internacional |
| UnionPay | Rede internacional |
| Maestro | Rede/modalidade de débito histórica, mantida para representar legado; não presumir crédito ou emissão atual |
| Cabal | Rede brasileira/regional, confirmada por instituidor |
| Banescard | Legado de bandeira própria; produto Banescard Visa atual não é evidência de bandeira Banescard |
| Aura | Opção histórica do catálogo solicitado; continuidade de emissão atual não confirmada nesta pesquisa |
| Sorocred | Opção de legado; nome/emissor Afinz não determina a bandeira; há cartões Afinz Visa |

Decisão técnica da proposta: manter os 14 nomes para compatibilidade/histórico,
sem alegar que todos são redes de crédito atualmente em emissão. Não acrescentar
“Outra” nem permitir texto livre. Catálogo final de distribuição é parte deste
aceite humano. A presença da opção não anuncia aceitação de pagamentos.

Fontes consultadas em 15/11/2026:

- [Banestes — conclusão da transição para Visa](https://www.banestes.com.br/informes/2023/2023_04_13_01.html): Banescard próprio deve ser tratado como legado.
- [Mastercard — transição de Maestro na Europa](https://www.mastercard.com/news/europe/en/perspectives/en/2021/blog-from-valerie-nowak-why-this-maestro-is-retiring-after-30-years): não caracterizar Maestro como nova rede de crédito.
- [Sicoob Pagamentos — instituidor Cabal](https://www.sicoob.com.br/sicoobpagamento): referência primária para Cabal.
- [CERC — encerramento do arranjo Hipercard e migração](https://www.cerc.com/wp-content/uploads/2025/07/Instituicao-de-pagamento-__-Arranjo-de-pagamento-Encerramento-do-Arranjo-Hipercard-e-Migracao-para-Mastercard-1.pdf): tratar a rede como legado, sem renomear automaticamente cartão histórico.
- [Afinz — perguntas frequentes](https://afinz.com.br/atendimento/perguntas-frequentes/): produtos com bandeira Visa, não inferir rede Sorocred do emissor.
- [Discover — redes e parceiros globais](https://www.discoverglobalnetwork.com/our-network/global-cardholders/): relações internacionais não tornam os nomes intercambiáveis.

## 7. Recursos gráficos e uso offline

Dez representações comerciais e um cartão genérico de
[svg-credit-card-payment-icons](https://github.com/aaronfagan/svg-credit-card-payment-icons),
sob Apache-2.0, sem alterações na arte (somente CRLF→LF quando necessário). [SOURCE.json](../assets/icons/card-networks/SOURCE.json)
fixa commit, origem e SHA256; [LICENSE](../assets/icons/card-networks/LICENSE)
preserva a licença; [README](../assets/icons/card-networks/README.md) documenta uso
identificador e limite de direitos de marca. Não há aprovação/endosso dos titulares.

Cabal, Banescard, Aura e Sorocred usam **ícone genérico + texto comercial**:
não foram localizadas e incorporadas artes com fonte/licença verificadas para
essas quatro nesta entrega. Nenhum logotipo inventado. Homologar esse fallback
ou fornecer/aprovar arte antes da distribuição. Texto permanece mesmo se recurso
não carregar. Sem bandeira também usa o cartão genérico, nunca marca comercial.

Os specs existentes já incluem a pasta assets recursivamente. A resolução parte
do caminho do módulo, compatível com recursos extraídos pelo PyInstaller, sem
depender do diretório de trabalho ou de download em execução. Não foi recompilado
pacote para confirmar o resultado em cada SO; isso exige autorização posterior.

## 8. CRUD e comportamento financeiro

Validação SQL direta precedeu alterações de Model/Service/Controller/View, após
migration e normalização aprovadas em cópia: INSERT sem/com Bandeira, leitura
após reabrir conexão, UPDATE de Nome/Bandeira, preservação ao alterar outro campo,
retorno para NULL e exclusão lógica. Nenhum DELETE de cartão original.

Testes automatizados exercitam todas as 14 opções por Controller → Service →
Model, incluindo nova conexão SQLite, listagem e edição; neutros e valores
inválidos; status inativo; atualização parcial; isolamento por usuário e
dependências preservadas após exclusão lógica. Service valida catálogo; Model
não conhece combobox nem rótulos traduzidos. Views/Controllers sem import de
Models, Database ou sqlite3.

Bandeira não participa de cálculo, competência, ciclo, pagamento, crédito,
estorno, parcelamento, projeção ou seleção do layout de importação. Fatura e
relatórios mantêm seus IDs/JOINs e comportamento anterior. O formato da lista
de contas/cartões à esquerda e contexto à direita permanece; nenhuma nova tela
de gerenciamento/dashboard foi criada. Proposta de apresentação futura
“Nome · Bandeira” fica reservada à homologação visual, não aplicada nesta tarefa.

## 9. Backup, tradução e evidências visuais

Backup A com Mastercard → arquivo .kp criptografado → restauração B preserva
Bandeira. Teste adicional remove o campo do payload para simular backup antigo:
restaurar em schema atualizado produz NULL e preserva ID. Formato .kp e regras
de backup não foram alterados. Cliente antigo sem migration 9 não tem garantia
de restaurar backup novo contendo coluna desconhecida; usar versão atualizada.

| Português | Inglês | Espanhol |
|---|---|---|
| Bandeira | Card network | Red de tarjeta |
| Sem bandeira | No card network | Sin red |
| Salvar cartão | Save card | Guardar tarjeta |

Os nomes das 14 opções comerciais não passam pelo tradutor. Mudar idioma atualiza
rótulos e opção neutra sem mudar o valor selecionado. Capturas offscreen em Linux,
com tema Primavera e dados sintéticos; formulários mediram 420×524, cabendo na
área de referência 1366×768. Não equivalem à homologação humana de cada SO.

- [Cadastro em português](./evidencias/cartoes-fase2/cadastro-pt.png)
- [Cadastro em inglês](./evidencias/cartoes-fase2/cadastro-en.png)
- [Cadastro em espanhol](./evidencias/cartoes-fase2/cadastro-es.png)
- [Selector com 15 opções](./evidencias/cartoes-fase2/selector-pt.png)
- [Edição com Mastercard selecionada](./evidencias/cartoes-fase2/edicao-pt.png)

## 10. Execução de testes

Resultado inicial focado: 39 aprovados no Python do sistema. Após revisão da
preservação de limite, adicionados três cenários adicionais ao conjunto.
Conjunto final focado: 42 testes de cartões + 2 regressões corrigidas, todos os
44 aprovados em 7,18 s no ambiente do projeto.
A tentativa inicial da suíte completa no Python do sistema parou na coleta por
dependências ausentes (incluindo matplotlib); não é resultado funcional da
aplicação. A execução válida usa o ambiente do projeto com dependências presentes:

```bash
QT_QPA_PLATFORM=offscreen .venv-finance-assist/bin/python -m pytest -q tests
```

Uma execução em disco foi interrompida por lentidão de I/O e repetida integralmente
com TMPDIR em diretório tmpfs isolado, sem desabilitar FKs, transactions ou testes:

```bash
mkdir -p /dev/shm/finance-assist-cartoes-tests
TMPDIR=/dev/shm/finance-assist-cartoes-tests QT_QPA_PLATFORM=offscreen \
  .venv-finance-assist/bin/python -m pytest -q tests
```

A primeira execução integral terminou com 427 aprovados e 2 falhos. Os dois
falharam também isoladamente: uma expectativa de contagem ainda era 8 em vez
de 9 migrations; o outro cenário esperava novembro ABERTA depois do dia 10.
Corrigida a expectativa de versão e fixada a data apenas no teste; comparação
AST confirmou que o método financeiro atualizar_lancamento não foi alterado.
O cenário continua exigindo mover vínculo sem duplicar e sem liberar FECHADA.
Após as correções, a suíte inteira foi executada novamente.

**Resultado final da suíte completa: 429 aprovados, 0 falhos, 0 erros e 0
ignorados, em 130,44 s; processo terminou com código 0.**

| Verificação | Resultado |
|---|---|
| Suíte completa tests/ | 429 aprovados; 0 falhos; 0 erros; 0 ignorados |
| Casos específicos de cartões incluídos na suíte | 42 aprovados |
| Repetição focada com dois cenários de regressão | 44 aprovados |
| PRAGMA integrity_check da cópia normalizada | ok |
| PRAGMA foreign_key_check da cópia normalizada | nenhuma violação |
| Round-trip de backup e payload legado | aprovados |
| Compilação sintática / verificação do diff | aprovadas |

Foram emitidos 15 avisos de depreciação nas dependências matplotlib/pyparsing e
PyPDF2; não há testes ignorados por esses avisos. Nenhuma dependência do projeto
foi atualizada nesta tarefa. O teste em ambiente temporário inicialmente tentado
não é usado como ambiente de validação final.

Evidência JUnit local: `/tmp/finance-assist-cartoes-validation/full-suite-final.xml`;
log correspondente: `/tmp/finance-assist-cartoes-validation/full-suite-final.log`.
Esses arquivos de execução não integram o commit proposto. O resultado acima
inclui todos os testes descobertos em tests/, sem excluir arquivos/casos.

Validação SQL em cópia: nova/legada/repetida, preservação, normalização e CRUD
aprovados; PRAGMA integrity_check=ok, PRAGMA foreign_key_check sem violações.
Compilação sintática e git diff --check realizados; não são build de instalador.
Também verificados os 11 hashes/SVGs (sem scripts nem referências externas) e
os links locais dos relatórios. Rechecagem dos três bancos originais após os
testes: ainda sem Bandeira, contagens 1/0/3, integridade ok e nenhuma violação FK.

## 11. Riscos e decisões do aceite

1. Homologar formulário, catálogo incluindo legado e fallback genérico de quatro
   redes. Eventuais logos novos exigem procedência/licença apropriadas.
2. Homologação visual executada por automação Linux offscreen; Windows/macOS e
   aplicação empacotada permanecem pendentes de ambiente/autorização próprios.
3. Aprovar execução real da migration/normalizações em destino definido, após
   backup consistente e verificações; os bancos originais permanecem intactos.
4. Resolver humanamente o cartão legado cujo Nome é só a bandeira; ele não será
   apagado ou renomeado automaticamente.
5. Configuração de desenvolvimento com caminho antigo foi apenas diagnosticada;
   ajuste de destino deve ser explícito, sem apontar testes para produção.
6. Nenhuma publicação com teste falhando. Somente após aceite explícito: commit
   objetivo, push, SHA/arquivos/resultados. Não criar release nem instaladores.

O planejamento amplo da Fase 2 já existia como arquivo não rastreado; seu escopo
não foi implementado nem incluído na publicação desta mudança.
Resultados privados, bancos e diretórios antigos de validação não integrarão
o commit desta tarefa.
