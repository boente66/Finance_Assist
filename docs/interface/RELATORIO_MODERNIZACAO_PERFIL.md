# Relatório Técnico — Modernização do Perfil e Pacote Linux de Teste

**Projeto:** Finance Assist — ControleFinanceiro

**Versão:** 2.1.0-test.1

**Plataforma do pacote:** Debian/Ubuntu compatível, `amd64`
**Classificação:** versão de teste

## 1. Objetivo

Adequar a tela de perfil ao modelo visual fornecido, preservar a arquitetura em
camadas, manter as funcionalidades existentes e disponibilizar um pacote `.deb`
identificado inequivocamente como teste para Linux.

## 2. Impacto calculado

| Camada | Arquivo/componente | Impacto |
|---|---|---|
| View | `views/perfil_view.py` | reconstrução responsiva da página |
| View | `views/perfil_dialogs.py` | edição pessoal e alteração de senha |
| View shell | `views/main_view.py` | atualização do cartão lateral após autoedição |
| Tema | `core/themes.py` | tokens QSS próprios do perfil |
| Controller | `controllers/user_controller.py` | entrada autenticada para autoedição |
| Service | `services/user_services.py` | autorização e preservação de privilégio |
| Model | `models/user_model.py` | reutilizado sem alteração |
| Sessão | `core/session.py` | reutilizada sem alteração |
| Versão | `core/version.py` | fonte única da versão do app e Debian |
| Testes | `tests/integration/test_perfil_modernizado.py` | interface e contratos críticos |
| Build | `ControleFinanceiro-teste.spec` e `packaging/linux/` | executável e pacote Debian |
| Documentação | README e notas da versão | anúncio e instruções de teste |

Não foram alterados fluxos financeiros, migrations, schema SQLite, transações,
agendamentos, pagamentos, backups ou restauração.

## 3. Arquitetura preservada

O fluxo de autoedição segue:

`PerfilView → UserController.update_own_profile → UserService.update_own_profile → UserModel.update_user`

O service valida que o identificador pertence ao usuário autenticado, verifica
duplicidade de login/e-mail e sempre obtém o nível de acesso do registro atual.
O campo enviado pela interface não pode promover nem rebaixar o usuário.

Preferências seguem o contrato já utilizado em Configurações. A alteração de
senha autentica primeiro a senha atual e somente então utiliza
`UserController.change_password`.

## 4. Interface implementada

- cabeçalho “Meu perfil” com descrição;
- cartão de identidade com iniciais, nome, login, e-mail e papel;
- cartão de dados pessoais com valores reais da sessão;
- diálogo de edição com validação dos campos obrigatórios e e-mail;
- cartão de preferências com temas e idiomas existentes;
- cartão de segurança e alteração de senha;
- data da sessão, último backup disponível e versão do aplicativo;
- duas colunas em largura ampla e coluna única com rolagem em largura compacta;
- compatibilidade com todos os temas existentes.

## 5. Segurança e privacidade

- nenhum dado pessoal foi codificado na view;
- a captura visual de validação utiliza dados fictícios;
- nível de acesso não é aceito como entrada da autoedição;
- senha atual é verificada antes da troca;
- campos de senha utilizam modo oculto;
- nenhum banco ou backup integra o pacote ou o commit.

## 6. Empacotamento Linux

O script `packaging/linux/build_deb.sh` gera primeiro o executável PyInstaller de
teste e depois monta o pacote `finance-assist_2.1.0-test.1_amd64.deb` em diretório
temporário. O pacote instala:

- executável em `/opt/finance-assist/finance-assist-test`;
- atalho em `/usr/bin/finance-assist-test`;
- entrada de menu “Finance Assist (Teste)”;
- ícone escalável;
- cópia da licença não comercial.

Também é produzido um arquivo SHA-256 para conferência do download.

## 7. Critérios de aceite

- dados da sessão exibidos corretamente;
- autoedição não altera privilégios;
- tema e idioma persistem pelos controllers existentes;
- senha atual inválida impede a alteração;
- cartões reorganizam sem perda de acesso;
- suíte integral sem regressões;
- `.deb` inspecionável por `dpkg-deb`;
- executável inicia no backend Qt offscreen;
- release e artefatos identificados como teste.

## 8. Limitações declaradas

- esta é uma versão de teste, não uma versão estável;
- o pacote inicial é destinado a `amd64` e ao ecossistema Debian;
- a validação automatizada não substitui testes em diferentes distribuições,
  versões de desktop e drivers gráficos;
- revisão humana especializada continua recomendada para a licença proprietária.

## 9. Validação executada

- 11 testes focais aprovados, cobrindo perfil, autoedição, privilégios,
  preferências, senha, shell principal e metadados Debian;
- compilação de sintaxe Python aprovada;
- `bash -n packaging/linux/build_deb.sh` aprovado;
- `git diff --check` aprovado;
- renderização offscreen aprovada em 1240×820 e 760×720;
- pacote Debian criado e metadados inspecionados por `dpkg-deb`;
- checksum SHA-256 validado;
- inspeção negativa sem banco, backup, log, cache ou ambiente virtual;
- smoke test do executável aprovado: aplicação permaneceu ativa por 12 segundos
  no backend Qt offscreen e foi encerrada pelo timeout controlado.

A suíte integral foi iniciada, mas interrompida externamente antes de emitir o
resumo final. Por isso, este relatório não a classifica como aprovada nesta
etapa. A distribuição permanece identificada como versão de teste.
