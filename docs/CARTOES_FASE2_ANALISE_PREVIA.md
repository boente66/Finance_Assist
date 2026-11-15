# Cadastro de cartões — análise prévia e decisão de persistência

Data: 15/11/2026. Estado: análise concluída, aguardando decisão antes de alterar.
Esta é a primeira entrega da tarefa, não o relatório de homologação final.

## Método

Leitura direta com sqlite3, URI `mode=ro` e `PRAGMA query_only=ON`, sem importar
Database ou inicializar o aplicativo, para não executar migrations implicitamente.
Não foram alterados bancos, cartões, nomes, IDs, configurações ou código.
Nomes e IDs individuais constam em evidência local privada separada; não incluir
dados financeiros reais em futuro commit/push.

## Bancos encontrados

| Origem | Cartões | Faturas vinculadas | Lançamentos vinculados | Pagamentos vinculados | Integridade | Violações FK |
|---|---:|---:|---:|---:|---|---:|
| Banco legado na raiz do projeto | 1 | Tabela ausente | 0 | 0 | ok | 0 |
| Banco de desenvolvimento nesta pasta | 0 | 0 | 0 | 0 | ok | 0 |
| Banco do aplicativo instalado em ~/.financeassist | 3 | 49 | 189 | 14 | ok | 0 |

Nos três bancos: nenhum Nome NULL/vazio, nenhuma duplicidade de nome por usuário
pela comparação `lower(trim(Nome))`, nenhum cartão com usuário inexistente e
nenhuma referência órfã nas FKs que apontam para credito. Agendamentos vinculados:
zero nos três bancos. Não possuir lançamentos é situação válida, não registro órfão.

A configuração de desenvolvimento aponta para uma pasta antiga chamada
ControleFinanceiro, cujo banco referenciado não foi encontrado. O banco local de
desenvolvimento existe, mas não corresponde a esse caminho configurado. Não foi
corrigida configuração automaticamente. Os testes deverão usar destino temporário
explícito, sem depender dessa configuração ou acessar o banco instalado.

## Estrutura anterior

```sql
CREATE TABLE credito (
    ID_Cartao INTEGER PRIMARY KEY AUTOINCREMENT,
    Nome TEXT NOT NULL,
    Limite REAL NOT NULL DEFAULT 0,
    Dia_Fechamento INTEGER NOT NULL,
    Dia_Vencimento INTEGER NOT NULL,
    Ativo INTEGER DEFAULT 1,
    ID_Usuario INTEGER,
    FOREIGN KEY(ID_Usuario) REFERENCES usuarios(ID_Usuario) ON DELETE CASCADE
);
```

Mesma estrutura encontrada nos três bancos. Não existe Bandeira, índice explícito,
UNIQUE adicional ou CHECK em credito. A PK inteira é a própria chave de linha;
não há índice independente listado por `PRAGMA index_list(credito)`.

FKs entrantes: agendamentos, lancamentos, pagamentos_fatura e, nos bancos atuais,
faturas_cartao. Lancamentos/faturas têm ON DELETE CASCADE; agendamentos e
pagamentos_fatura usam NO ACTION. A aplicação atualmente faz exclusão lógica
por Ativo=0: preservar essa regra, sem DELETE físico.

Migrations: banco legado registra 1–3; desenvolvimento e instalado registram
1–8. O código atual tem migrations até 8 e executor transacional com validador
e foreign_key_check. A proposta é acrescentar migration 9, verificando novamente
o número disponível antes de implementar; não editar migrations já aplicadas.

## Consultas executadas

```sql
PRAGMA table_info(credito);
PRAGMA foreign_key_list(credito);
PRAGMA index_list(credito);
PRAGMA foreign_key_check;
PRAGMA integrity_check;
SELECT type, name, sql FROM sqlite_master WHERE tbl_name='credito';
SELECT count(*) AS n FROM credito;
SELECT ID_Cartao, Nome, ID_Usuario FROM credito;
SELECT ID_Cartao FROM credito WHERE Nome IS NULL OR TRIM(Nome)='';
SELECT ID_Usuario, lower(trim(Nome)) AS nome, count(*) AS n
FROM credito GROUP BY ID_Usuario, lower(trim(Nome)) HAVING count(*)>1;
SELECT c.ID_Cartao FROM credito c
LEFT JOIN usuarios u ON u.ID_Usuario=c.ID_Usuario WHERE u.ID_Usuario IS NULL;
SELECT Versao, Nome FROM schema_migrations ORDER BY Versao;
```

Foi executado PRAGMA foreign_key_list em todas as tabelas para levantar as
referências entrantes. Para cada referência real encontrada, foram executados
JOIN para contagem de vínculos e LEFT JOIN para contagem de órfãos, usando o
nome da tabela e coluna obtidos do schema. Exemplo efetivamente usado:

```sql
SELECT count(*) AS n FROM lancamentos d
JOIN credito c ON d.ID_Cartao=c.ID_Cartao;
SELECT count(*) AS n FROM lancamentos d
LEFT JOIN credito c ON d.ID_Cartao=c.ID_Cartao
WHERE d.ID_Cartao IS NOT NULL AND c.ID_Cartao IS NULL;
```

Nomes foram pesquisados por SQL com `lower(Nome) LIKE '%visa%'`,
`'%mastercard%'`, `'%elo%'`, `'%american express%'`, `'%hipercard%'`,
`'%diners%'`, `'%discover%'`, `'%jcb%'`, `'%unionpay%'`, `'%maestro%'`,
`'%cabal%'`, `'%banescard%'`, `'%aura%'` e `'%sorocred%'` combinados com OR.
A triagem complementar por limites de palavra evita classificar trecho casual
de nome como bandeira. Uma pesquisa LIKE isolada não autoriza normalização.

## Decisão proposta — apresentar antes de aplicar

| Persistência | Avaliação |
|---|---|
| NULL | Recomendada: ausência explícita, independente de idioma, compatível com linha legada e backup antigo sem a coluna |
| String vazia | Evitar como representação canônica: introduz segunda forma de ausência sem vantagem |
| Texto Sem bandeira | Evitar no banco: texto de interface em português vira dado de domínio e exige tradução/mapeamento especial |

Proposta: `Bandeira TEXT NULL DEFAULT NULL`; catálogo comercial canônico no
Service, sem valores arbitrários; None, vazio e opção neutra da interface
normalizados para NULL. Exibição sempre “Sem bandeira” / “No card network” /
“Sin red”, conforme idioma; nomes comerciais não traduzidos.

Banco novo recebe a coluna no CREATE TABLE; antigo recebe ALTER TABLE ADD COLUMN
apenas se necessário. Sem recriar tabela, alterar PK/IDs ou adicionar índice
desnecessário. Migration estrutural não deve inferir nem alterar Nome. Operação
de normalização é separada, auditável e condicionada ao aceite dos registros.

Na edição, chave Bandeira omitida deve preservar o valor existente; chave
explicitamente neutra deve remover a bandeira. Distinguir os dois casos para
consumidores antigos que ainda não enviem esse campo.

## Normalização — nenhuma executada

O banco instalado contém dois candidatos com uma única ocorrência independente
de Mastercard no início/fim e nome comercial restante não vazio. A proposta
individual, com ID_Cartao real (não existe ID_Credito no schema), valor anterior,
nome proposto, bandeira e motivo, está na evidência privada.

O banco legado da raiz contém um nome constituído apenas pela bandeira. Removê-la
deixaria Nome vazio; preservar integralmente para decisão humana. Não inventar
nome comercial, corrigir grafia, acentuação ou produto bancário.

Proposta de execução posterior: validar primeiro em cópia consistente e isolada,
comparando todas as colunas financeiras e relações antes/depois. Não alterar
automaticamente o banco instalado como efeito de testes ou de abrir um Model.
Aplicação nos dados reais exige destino e registros explicitamente aprovados.

## Impacto arquitetural levantado

- [database.py](../database/database.py): schema novo, migration aditiva e validador.
- [credito_model.py](../models/credito_model.py): INSERT/UPDATE precisam incluir
  Bandeira; SELECT * já a retornará. Exclusão lógica permanece. CREATE atualmente
  não inclui Ativo recebido do Controller: verificar no CRUD antes de ajustar o
  formulário para não prometer status que não foi persistido.
- [fatura_service.py](../services/fatura_service.py): validar catálogo e ausência,
  preservar valor em edição com chave omitida; nenhuma participação no cálculo.
- [fatura_controller.py](../controllers/fatura_controller.py): mapeamento explícito
  de bandeira entre payload da View e Service, sem SQLite/SQL.
- [criar_cartao_dialog.py](../views/criar_cartao_dialog.py): cadastro e edição
  contextuais existentes, QComboBox neutro por padrão e seleção ao editar.
- [transacao_view.py](../views/transacao_view.py),
  [painel_fatura.py](../views/painel_fatura.py): preservar seleção por ID e layout;
  apresentação definitiva de Nome/Bandeira só após homologação visual.
- [backup_model.py](../models/backup_model.py): SELECT * por tabela e restauração
  pelas chaves do registro sugerem inclusão natural; comprovar round-trip e
  restauração de backup antigo em banco atualizado, sem assumir sucesso.
- [relatorio_model.py](../models/relatorio_model.py),
  [relatorio_service.py](../services/relatorio_service.py),
  [importacao_service.py](../services/importacao_service.py) e
  [layouts/](../models/layouts/): não usar bandeira como emissor/layout/destino
  nem alterar vínculos financeiros; validar consumidores nas regressões.

## Catálogo, ícones e próximas etapas

Os 14 nomes sugeridos ainda não constituem catálogo validado: marcas de legado,
emissor e modalidade de débito precisam de revisão de escopo. Exemplo: a própria
[Afinz](https://afinz.com.br/atendimento/perguntas-frequentes/) descreve cartões
com bandeira Visa; não inferir bandeira Sorocred a partir de emissor/nome Afinz.
Pesquisa completa e licenças gráficas serão documentadas antes de consolidar.
Nenhum logotipo foi baixado/adicionado; ícones devem vir de fonte com uso
permitido e acompanhar o pacote offline. Não criar logotipos artificiais.

Próximo passo condicionado: aprovar persistência NULL e proposta de normalização.
Então executar a ordem solicitada: banco/migration → validação SQL → normalização
aprovada em cópia → CRUD SQL → Model → Service → Controller → View → testes →
evidências e homologação humana → relatório final → GitHub autorizado.

Até aqui: zero normalizações; zero alterações de aplicação/schema; CRUD novo,
backup e suíte completa ainda não executados. Não há commit/push/release/build.
