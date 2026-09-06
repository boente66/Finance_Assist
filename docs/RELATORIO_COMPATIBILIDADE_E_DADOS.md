# Relatório de compatibilidade, persistência e experiência de uso

**Projeto:** Finance Assist

**Versão avaliada:** 2.1.0-test.3

**Data:** 6 set. 2026

**Escopo:** Ubuntu LTS, SQLite e inclusão rápida em lançamentos

## 1. Objetivo

Garantir que a aplicação possa ser testada em Ubuntu 24.04 e 26.04 sem usar o
banco real, que atualizações preservem os dados do usuário e que os fluxos de
lançamento mantenham acesso claro à criação de categorias e favorecidos.

## 2. Classes e arquivos afetados

| Camada | Elemento | Responsabilidade preservada |
|---|---|---|
| Configuração | `core/config.py`, `core/settings.py` | resolver ambiente, configuração e caminho de dados |
| Persistência | `database/database.py` | abrir SQLite e aplicar schema/migrations |
| Serviço | `services/backup_service.py` | usar o banco resolvido no ambiente atual |
| Apresentação | `views/animated_add_button.py` | feedback visual reutilizável, sem regra de negócio |
| Views | `TransactionDialogConta`, `FaturaDialog` | coletar dados e manter chamadas aos controllers existentes |
| Tema | `core/themes.py` | aparência por tokens para todos os temas |
| Entrega | workflow e metadados Debian | testar versões LTS e gerar um único DEB compatível |

Controllers, models financeiros, schema e regras de cálculo não foram alterados.

## 3. Estratégia de dados

| Ambiente | Caminho padrão | Resultado |
|---|---|---|
| Pacote/produção | `~/.financeassist/financeiro.db` | mantém o caminho histórico entre upgrades |
| Código-fonte/desenvolvimento | `.financeassist-development/financeiro.db` | não reutiliza o banco de produção ou o banco da raiz |
| Pytest | diretório temporário exclusivo | removido ao final e sem acesso a dados reais |

Overrides explícitos permanecem disponíveis por `FINANCE_ASSIST_DATA_DIR` e
`FINANCE_ASSIST_DB_PATH`. Caminhos relativos são resolvidos dentro do diretório
do ambiente, e não em função do diretório corrente do terminal.

Na primeira execução por código-fonte, um `financeiro.db` legado da raiz é
copiado com a API de backup do SQLite para o novo perfil de desenvolvimento. A
cópia ocorre apenas quando o destino ainda não existe; assim, preserva os dados
anteriores sem manter desenvolvimento e legado ligados ao mesmo arquivo.

## 4. Atualização e migrations

O empacotamento continua sem incorporar `*.db`, configuração, backup ou log. A
instalação atualiza apenas o executável e metadados. A reabertura de um banco
existente aplica as migrations registradas em `schema_migrations`; o teste de
reabertura confirma que um usuário inserido antes da atualização permanece
presente depois dela. Os testes legados cobrem banco novo, legado, parcialmente
migrado, índice único, chaves estrangeiras e concorrência.

Na inspeção SQLite realizada após as migrations:

- migrations 1, 2 e 3 estavam registradas;
- `transacoes.ID_Agendamento` estava presente;
- `idx_transacao_agendamento` era único e parcial;
- `pagamentos_fatura` possuía quatro chaves estrangeiras;
- `PRAGMA foreign_key_check` não retornou violações;
- `PRAGMA integrity_check` retornou `ok`.

## 5. Experiência de uso

Os diálogos de lançamento em conta e em cartão continuam abrindo os mesmos
diálogos de categoria e favorecido e chamando os controllers existentes. Os
atalhos agora têm formato circular de 36 px, foco por teclado, nome acessível,
tooltip, estados hover/pressed e animação curta de 150 ms. Cores e estados vêm
dos tokens de Primavera, Noite Intensa, Prosperidade, Verão Quente e da
configuração Personalizada.

## 6. Compatibilidade Linux

O DEB `amd64` permanece compilado no Ubuntu 22.04. A suíte completa passa a ser
executada separadamente em Ubuntu 24.04 e 26.04 com Python 3.12, Qt offscreen e
banco temporário. Essa estratégia verifica versões novas sem elevar
desnecessariamente a versão mínima das bibliotecas do binário.

## 7. Evidências locais

- testes focados: 28 aprovados;
- integração: 179 testes coletados e incluídos na suíte final;
- suíte completa: 205 aprovados;
- compilação de sintaxe: aprovada;
- inspeção SQLite: aprovada;
- `git diff --check`: aprovado.

Os jobs Ubuntu 24.04 e 26.04 são evidência remota e precisam estar verdes no
GitHub Actions antes de classificar essas plataformas como homologadas.

## 8. Conclusão

A arquitetura permanece `View → Controller → Service → Model`. O isolamento de
ambientes reduz o risco de dano a dados reais; o caminho histórico do pacote
preserva atualizações; e os atalhos visuais melhoram descoberta e acessibilidade
sem duplicar regras de cadastro.
