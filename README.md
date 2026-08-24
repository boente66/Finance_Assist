<div align="center">
  <img src="assets/icons/finance_assist.svg" alt="Logotipo do Finance Assist" width="88">
  <h1>Finance Assist</h1>
  <p><strong>Gestão financeira pessoal em uma aplicação desktop organizada, segura e executada localmente.</strong></p>
  <p>Versão atual: <code>2.1.0-test.1</code> · Estágio: teste para Linux</p>
</div>

> [!IMPORTANT]
> Esta versão é destinada a testes e homologação. Ela não deve ser tratada como
> versão estável nem como substituta de orientação contábil, fiscal, jurídica ou
> de investimento. Antes de instalar, atualizar ou restaurar dados, mantenha um
> backup válido e verificável.

## 1. Apresentação

O **Finance Assist** é um sistema desktop de controle financeiro desenvolvido em
Python e PyQt5. Seu objetivo é reunir contas, movimentações, cartões, faturas,
agendamentos, metas, categorias, favorecidos e relatórios em uma interface única.

A aplicação trabalha prioritariamente com dados locais. O banco principal é um
arquivo SQLite configurável, e a interface é construída com Qt Widgets por meio
das ligações fornecidas pelo PyQt5. A escolha é compatível com aplicações desktop
baseadas em janelas, diálogos, tabelas e formulários (RIVERBANK COMPUTING, [s. d.];
THE QT COMPANY, 2025).

### Objetivos do projeto

- oferecer visão consolidada da situação financeira cadastrada;
- registrar receitas, despesas e transferências entre contas;
- apoiar planejamento por metas, agendamentos e projeções;
- manter separação entre interface, coordenação, regras de negócio e persistência;
- proteger fluxos sensíveis, como autenticação, backup e operações financeiras;
- disponibilizar interface responsiva para diferentes resoluções de desktop.

## 2. Situação da versão

| Item | Situação atual |
|---|---|
| Nome comercial | Finance Assist |
| Versão da aplicação | `2.1.0-test.1` |
| Versão do pacote Debian | `2.1.0~test1` |
| Branch principal | `main` |
| Repositório oficial | [boente66/Finance_Assist](https://github.com/boente66/Finance_Assist) |
| Distribuição publicada | pacote Debian de teste para Linux `amd64` |
| Windows e macOS | código potencialmente portável, mas sem pacote oficial homologado nesta versão |
| Licença | proprietária, source-available e limitada a uso não comercial |

As notas específicas da versão estão em
[`docs/releases/v2.1.0-test.1.md`](docs/releases/v2.1.0-test.1.md).

## 3. Funcionalidades

### 3.1 Resumo financeiro

- consolidação dos saldos das contas;
- indicadores de receitas, despesas e resultado do período;
- visão de cartões e faturas;
- exibição de próximos lançamentos e agendamentos;
- acompanhamento visual de metas financeiras;
- gráficos e análises obtidos pelos controllers existentes.

### 3.2 Contas e movimentações

- cadastro e edição de contas;
- lançamento de receitas e despesas;
- transferências entre contas;
- ajuste controlado de saldo;
- filtros por período;
- importação e exportação de movimentações.

As transferências críticas utilizam unidade de trabalho transacional. Se uma
etapa falha, a operação deve ser revertida integralmente, evitando débito sem o
crédito correspondente.

### 3.3 Cartões e faturas

- cadastro e edição de cartões de crédito;
- lançamentos vinculados a cartão e competência;
- acompanhamento do total, valor em aberto e valor pago;
- pagamento de fatura com registro de idempotência;
- integração de faturas previstas com a projeção de agendamentos;
- geração de relatório em PDF nos fluxos disponíveis.

### 3.4 Planejamento

- contas a pagar e a receber;
- transferências agendadas;
- recorrência e parcelamento;
- execução e cancelamento controlados;
- prevenção de execução duplicada por vínculo persistente;
- projeção do impacto dos compromissos futuros no saldo;
- metas financeiras com acompanhamento de progresso.

### 3.5 Organização e relatórios

- categorias e subcategorias de receita e despesa;
- cadastro e consulta de favorecidos;
- relatório diário, anual e informe de rendimentos, conforme os fluxos atuais;
- exportação para CSV, XLSX e PDF nos módulos que oferecem essa função;
- importação de PDF, CSV, XLSX, XLS e TXT;
- reconhecimento de layouts bancários implementados no projeto.

> [!NOTE]
> A qualidade da importação depende do formato e da consistência do arquivo de
> origem. O usuário deve revisar categorias, favorecidos, datas e valores antes
> de confirmar dados importados.

### 3.6 Usuários e personalização

- autenticação local;
- cadastro administrativo e gerenciamento de usuários;
- perfil e alteração da própria senha;
- níveis de acesso `admin` e `usuario`;
- idiomas Português, Inglês e Espanhol nos textos cadastrados no tradutor;
- temas Primavera, Noite Intensa, Prosperidade, Verão Quente e Personalizado;
- layouts responsivos com áreas de rolagem em resoluções reduzidas.

## 4. Arquitetura

O projeto utiliza uma arquitetura em camadas, com responsabilidades distintas:

```text
Usuário
  ↓
View / Dialog
  ↓
Controller
  ↓
Service
  ↓
Model
  ↓
Database / SQLite
```

| Camada | Responsabilidade |
|---|---|
| `views/` | interface, interação, apresentação, foco, responsividade e tradução |
| `controllers/` | mediação entre interface, sessão e casos de uso |
| `services/` | validações, autorização e regras de negócio |
| `models/` | consultas, persistência e transformação de dados |
| `database/` | conexão SQLite, schema, migrations e unidade de trabalho |
| `core/` | sessão, configuração, temas, tradução, versão e contratos compartilhados |
| `workers/` | tarefas executadas fora do fluxo principal da interface |
| `utilitarios/` | formatação, caminhos, criptografia e funções auxiliares |

### Princípios adotados

- a view não deve executar SQL nem definir regra financeira;
- o controller deve preservar contratos estáveis para a interface;
- o service concentra autorização e validação de negócio;
- o model é responsável pela persistência;
- operações compostas críticas devem compartilhar a mesma transação;
- migrations devem aceitar banco novo, legado e parcialmente atualizado.

O SQLite exige que o suporte a chaves estrangeiras seja habilitado em cada
conexão; o projeto executa `PRAGMA foreign_keys = ON` ao conectar. Essa conduta
segue a documentação oficial do mecanismo (SQLITE, 2026).

## 5. Segurança e privacidade

### 5.1 Senhas de usuário

As senhas novas são protegidas com **PBKDF2-HMAC-SHA256**, salt aleatório
individual e 600 mil iterações. A comparação usa função resistente a diferenças
temporais. Hashes SHA-256 legados continuam sendo aceitos apenas para permitir o
primeiro login válido e são atualizados automaticamente para o formato atual.

O uso de função derivadora lenta, salt exclusivo e fator de trabalho ajustável
segue as orientações documentadas pela Python Software Foundation e pela OWASP
(PYTHON SOFTWARE FOUNDATION, 2026; OWASP FOUNDATION, [s. d.]).

### 5.2 Autorizações

- criação e gerenciamento de usuários são submetidos às permissões do service;
- alteração do próprio perfil não permite elevar o nível de acesso;
- backup e restauração globais são restritos a administradores;
- o sistema preserva pelo menos um administrador nos fluxos protegidos;
- dados de senha não são retornados pelas consultas públicas de usuário.

### 5.3 Integridade financeira

- transferências, execução de agendamentos e pagamento de faturas possuem testes
  de atomicidade;
- agendamentos executados são vinculados de forma única à transação gerada;
- pagamentos de fatura possuem chave de idempotência e vínculo com a transação;
- restauração valida chaves estrangeiras antes do commit;
- migrations são registradas na tabela `schema_migrations`.

### 5.4 Backup

O backup lógico usa a extensão `.kp`, serializa as tabelas autorizadas e protege
o conteúdo com **AES-GCM**. A chave é derivada da senha informada pelo usuário. A
restauração cria primeiro um backup preventivo, executa as inserções em transação
e verifica a integridade referencial antes do commit.

> [!WARNING]
> A segurança do backup depende da senha escolhida e da guarda do arquivo. Perder
> a senha pode tornar o conteúdo irrecuperável. Armazene backups fora do mesmo
> disco do banco principal e teste periodicamente a restauração em ambiente
> controlado.

### 5.5 Limites de proteção

- a aplicação não substitui criptografia integral do disco do sistema operacional;
- quem possui acesso à conta do sistema e aos arquivos locais pode copiar o banco;
- logs podem conter mensagens operacionais e devem ser protegidos;
- nenhum software elimina todos os riscos de falha, fraude ou perda de dados;
- vulnerabilidades não devem ser publicadas com dados pessoais ou credenciais.

## 6. Persistência e localização dos dados

O banco padrão chama-se `financeiro.db`. O caminho pode ser alterado em
`configuracoes.json`.

| Execução | Diretório padrão |
|---|---|
| Código-fonte | raiz local do projeto |
| Aplicação empacotada | `~/.financeassist/` |

Arquivos `.db`, `.sqlite`, `.sqlite3`, backups, logs, caches e ambientes virtuais
não devem ser enviados ao Git. Eles podem conter informações financeiras ou
identificadores pessoais.

## 7. Requisitos técnicos

### Para executar pelo código-fonte

- Python 3.12 recomendado para reproduzir o ambiente validado;
- suporte gráfico compatível com Qt5;
- `pip` e `venv`;
- dependências listadas em [`requirements.txt`](requirements.txt);
- pacote `cryptography` para criação e restauração de backups protegidos;
- `pytest` para executar os testes.

Dependências principais:

- PyQt5 para a interface;
- SQLite por meio do módulo `sqlite3` da biblioteca padrão;
- pandas e openpyxl para dados tabulares e planilhas;
- Matplotlib para gráficos;
- ReportLab e bibliotecas PDF para relatórios e extração;
- Pillow e pytesseract para processamento de imagens e OCR;
- PyInstaller para empacotamento.

## 8. Instalação para desenvolvimento

Clone o repositório oficial:

```bash
git clone https://github.com/boente66/Finance_Assist.git
cd Finance_Assist
```

Crie e ative um ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

No Windows PowerShell, a ativação equivalente é:

```powershell
.venv\Scripts\Activate.ps1
```

Instale as dependências:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install cryptography pytest
```

Inicie o aplicativo:

```bash
python run.py
```

> [!CAUTION]
> Não execute o projeto com um banco de produção durante desenvolvimento ou
> teste. Configure um arquivo SQLite separado e mantenha cópias de segurança.

## 9. Instalação do pacote Linux de teste

Baixe o `.deb` e o checksum correspondente no
[Release v2.1.0-test.1](https://github.com/boente66/Finance_Assist/releases/tag/v2.1.0-test.1).

Confira a integridade do arquivo:

```bash
sha256sum -c finance-assist_2.1.0-test.1_amd64.deb.sha256
```

Instale o pacote:

```bash
sudo apt install ./finance-assist_2.1.0-test.1_amd64.deb
```

Depois da instalação, procure por **Finance Assist (Teste)** no menu de
aplicativos ou execute:

```bash
finance-assist-test
```

O pacote atual foi preparado para distribuições compatíveis com Debian em
arquitetura `amd64`. Compatibilidade com cada distribuição, compositor e ambiente
gráfico deve ser homologada separadamente.

## 10. Testes e qualidade

A suíte contém testes de integração e de interface. Os testes financeiros usam
arquivos SQLite temporários, e os testes visuais podem executar Qt em modo
offscreen. O pytest fornece descoberta automática, fixtures e relatórios de
assertivas adequados a esse tipo de suíte (PYTEST DEVELOPMENT TEAM, [s. d.]).

Execute toda a suíte:

```bash
QT_QPA_PLATFORM=offscreen pytest -q
```

Execute apenas a integração:

```bash
QT_QPA_PLATFORM=offscreen pytest -q tests/integration
```

Verifique sintaxe e integridade textual do diff:

```bash
python -m compileall -q core controllers services models views database
git diff --check
```

Áreas cobertas incluem:

- atomicidade de transferências, faturas e agendamentos;
- migrations em banco novo, legado e parcialmente migrado;
- backup, restauração e permissões;
- armazenamento e migração de senhas;
- temas, responsividade, login, perfil e cadastro de usuários;
- metadados do pacote Linux.

## 11. Estrutura resumida

```text
Finance_Assist/
├── assets/                 # ícones e identidade visual
├── controllers/            # coordenação dos casos de uso
├── core/                   # configuração e infraestrutura compartilhada
├── database/               # schema, migrations e transações
├── docs/                   # relatórios técnicos e notas de versão
├── models/                 # persistência e acesso aos dados
├── packaging/linux/        # arquivos do pacote Debian
├── services/               # regras de negócio e integrações
├── tests/                  # testes de integração e interface
├── utilitarios/            # funções auxiliares
├── views/                  # telas e diálogos PyQt5
├── workers/                # tarefas auxiliares
├── run.py                  # ponto de entrada
├── requirements.txt        # dependências Python
└── LICENSE                 # licença proprietária não comercial
```

## 12. Limitações conhecidas

- esta é uma versão de teste, sem garantia de estabilidade para produção;
- não existe sincronização em nuvem nativa do banco financeiro;
- valores monetários ainda usam a representação adotada pelo schema atual;
- qualidade de OCR e importação varia conforme arquivo, idioma e resolução;
- tradução depende da cobertura existente em `translations.json`;
- validação automatizada não substitui homologação manual em todos os sistemas;
- relatórios são informativos e dependem da correção dos dados cadastrados.

## 13. Uso responsável

O usuário é responsável por:

- validar valores, datas, categorias, saldos e favorecidos;
- manter backups e testar sua recuperação;
- proteger senha, sessão, dispositivo e arquivos exportados;
- observar obrigações fiscais, contábeis e legais aplicáveis;
- não usar uma versão de teste como única fonte de informação financeira.

## 14. Contribuições e relato de problemas

Antes de propor uma alteração:

1. confirme que ela respeita a separação `View → Controller → Service → Model`;
2. não inclua bancos, backups, logs, credenciais ou dados pessoais;
3. adicione testes proporcionais ao risco;
4. execute a suíte relacionada e `git diff --check`;
5. descreva comportamento anterior, mudança, risco e evidências de validação.

Ao relatar um problema, informe versão, sistema operacional, ambiente gráfico,
passos para reprodução e mensagem de erro sanitizada. Nunca publique banco,
backup, token, senha, CPF, e-mail ou extrato real.

## 15. Licença e uso comercial

Copyright © 2026 Leonardo Boente. Todos os direitos reservados.

O Finance Assist é disponibilizado sob licença proprietária **source-available**
para uso exclusivamente não comercial. A licença não é aprovada como open source
pela Open Source Initiative. Venda, SaaS, serviço pago, monetização, uso
empresarial em produção ou obtenção de vantagem econômica exigem autorização
prévia e escrita do titular.

Consulte o texto juridicamente aplicável em [`LICENSE`](LICENSE). A proteção de
programas de computador e direitos autorais no Brasil é disciplinada, entre
outras normas, pelas Leis nº 9.609/1998 e nº 9.610/1998 (BRASIL, 1998a, 1998b).

Solicitações de licença comercial devem ser encaminhadas pelo perfil
[boente66](https://github.com/boente66).

## 16. Autor

**Leonardo Boente**

GitHub: [@boente66](https://github.com/boente66)

## 17. Referências

As referências abaixo foram organizadas conforme os elementos essenciais da
ABNT NBR 6023:2018. Para documentos digitais, são informados título, entidade
responsável, endereço eletrônico e data de acesso.

ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. **NBR 6023: informação e
documentação — referências — elaboração**. Rio de Janeiro: ABNT, 2018.

BRASIL. **Lei nº 9.609, de 19 de fevereiro de 1998**. Dispõe sobre a proteção da
propriedade intelectual de programa de computador, sua comercialização no País,
e dá outras providências. Brasília, DF: Presidência da República, 1998a.
Disponível em: <https://www.planalto.gov.br/ccivil_03/leis/l9609.htm>. Acesso em:
24 ago. 2026.

BRASIL. **Lei nº 9.610, de 19 de fevereiro de 1998**. Altera, atualiza e consolida
a legislação sobre direitos autorais e dá outras providências. Brasília, DF:
Presidência da República, 1998b. Disponível em:
<https://www.planalto.gov.br/ccivil_03/leis/l9610.htm>. Acesso em: 24 ago. 2026.

OWASP FOUNDATION. **Password Storage Cheat Sheet**. [S. l.]: OWASP Cheat Sheet
Series, [s. d.]. Disponível em:
<https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html>.
Acesso em: 24 ago. 2026.

PYTEST DEVELOPMENT TEAM. **pytest documentation**. [S. l.], [s. d.]. Disponível em:
<https://docs.pytest.org/en/stable/>. Acesso em: 24 ago. 2026.

PYTHON SOFTWARE FOUNDATION. **hashlib — secure hashes and message digests**.
Python 3 documentation. [S. l.], 2026. Disponível em:
<https://docs.python.org/3/library/hashlib.html>. Acesso em: 24 ago. 2026.

RIVERBANK COMPUTING. **What is PyQt?** [S. l.], [s. d.]. Disponível em:
<https://riverbankcomputing.com/software/pyqt/>. Acesso em: 24 ago. 2026.

SQLITE. **SQLite Foreign Key Support**. [S. l.], 2026. Disponível em:
<https://www.sqlite.org/foreignkeys.html>. Acesso em: 24 ago. 2026.

THE QT COMPANY. **Qt Widgets**. Qt 5.15 documentation. [S. l.], 2025. Disponível
em: <https://doc.qt.io/archives/qt-5.15/qtwidgets-index.html>. Acesso em: 24 ago.
2026.
