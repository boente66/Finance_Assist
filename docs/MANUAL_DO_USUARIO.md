# MANUAL DO USUÁRIO

## Finance Assist — Controle Financeiro Pessoal

**Versão:** 2.1.0-test.8  
**Atualização:** 12 de setembro de 2026  
**Projeto:** <https://github.com/boente66/Finance_Assist>  
**Instaladores:** <https://github.com/boente66/Finance_Assist/releases/tag/v2.1.0-test.8>

## 1. Apresentação

O Finance Assist organiza contas, lançamentos, cartões, faturas, metas,
categorias, favorecidos, agendamentos e relatórios em um único aplicativo.
Cada usuário acessa somente as informações permitidas pelo seu perfil.

Esta atualização preserva os bancos existentes. Para atualizar, feche o
aplicativo e instale a nova versão sobre a anterior. Não apague o arquivo
financeiro.db, a pasta .financeassist nem os backups.

## 2. Primeiro acesso

1. Abra o Finance Assist.
2. Informe usuário ou e-mail e senha.
3. Clique em **Entrar**.
4. Use a recuperação de senha quando não lembrar a credencial.

Após o login, o sistema mostra uma mensagem de boas-vindas, quando essa opção
estiver habilitada pelo administrador.

## 3. Usuários e permissões

### Usuário comum

- Gerencia suas contas, cartões, lançamentos e informações pessoais.
- Consulta saldos, faturas, metas, agendamentos e relatórios permitidos.
- Pode exportar seus dados e solicitar a exclusão da própria conta.

### Administrador

- Gerencia usuários e configurações gerais.
- Configura backup automático, retenção, alertas e mensagem de boas-vindas.
- Acessa os recursos administrativos definidos pelo sistema.

## 4. Contas e lançamentos

Abra **Contas e Lançamentos** e selecione uma conta. O painel mostra saldo,
movimentações e filtros disponíveis. Use **Atualizar** para reler os dados do
banco sem perder a seleção atual.

Para incluir uma movimentação, clique no botão de adicionar, escolha o tipo,
informe descrição, categoria, valor, data e os demais dados solicitados.

### Menu contextual

Clique com o botão direito sobre uma linha do extrato para abrir:

- **Copiar:** copia os dados do lançamento.
- **Colar:** cria um lançamento a partir dos dados copiados.
- **Editar:** abre o lançamento selecionado.
- **Excluir:** solicita confirmação e remove o lançamento.

O duplo clique também abre a edição. As mesmas ações estão disponíveis nas
linhas da fatura do cartão.

## 5. Cartões e faturas

Cadastre o cartão com nome, limite, fechamento e vencimento. Selecione o cartão,
o mês e o ano para consultar a fatura. O painel informa limite, valor usado,
disponível, total da fatura, lançamentos abertos e pagos.

### Importação de faturas

1. Selecione o cartão correto.
2. Clique em **Importar fatura**.
3. Escolha o arquivo PDF.
4. Informe a senha quando a instituição proteger o documento.
5. Revise os lançamentos reconhecidos antes de confirmar.

A importação reconhece layouts reais suportados pelo aplicativo. Como os bancos
podem alterar seus documentos, confira data, descrição e valor antes de salvar.
Não compartilhe senhas de PDF em mensagens ou documentos.

### Pagamento e exportação

Para pagar, escolha a fatura, clique em **Pagar**, selecione a conta de débito e
confirme. A exportação gera uma fatura organizada com identificação da conta ou
cartão, tabela de todos os lançamentos e total.

## 6. Agendamentos e alertas

Em **Agendamentos**, registre receitas, despesas, transferências e faturas
futuras. Use os filtros para localizar itens por período, origem, conta e status.

Quando habilitados pelo administrador, os alertas verificam agendamentos
vencidos em segundo plano. A verificação funciona enquanto o Finance Assist
estiver aberto.

## 7. Relatórios

Abra **Relatórios**, selecione período, conta e filtros. Atualize a consulta antes
de exportar. Se algum dado não aparecer, confira filtros, período, conta
selecionada e atualize a página.

## 8. Backup e restauração

### Backup manual

1. Abra **Perfil > Backup e Restauração**.
2. Escolha criar backup.
3. Defina o local e a senha de proteção.
4. Guarde o arquivo e a senha em local seguro.

### Backup automático

Em **Configurações**, o administrador pode definir:

- ativação e intervalo do backup automático;
- quantidade de cópias mantidas;
- ativação e intervalo dos alertas;
- exibição da mensagem de boas-vindas.

Os backups automáticos ficam em backups/automaticos dentro da pasta de dados.
A chave é protegida no dispositivo e não é armazenada no banco nem enviada ao
GitHub. A rotina executa somente enquanto o aplicativo estiver aberto.

Antes de restaurar, crie uma cópia manual do estado atual.

## 9. Atualização e instalação

### Windows

1. Baixe finance-assist_2.1.0-test.8_windows-x64.zip.
2. Confira o arquivo .sha256 correspondente.
3. Extraia o ZIP e execute o aplicativo.

### Ubuntu e derivados

Baixe o pacote adequado na release e instale sobre a versão existente com:

    sudo apt install ./finance-assist_2.1.0-test.8_amd64.deb

Há também um pacote identificado para Ubuntu 24.04. Os instaladores foram
validados em Ubuntu 22.04, 24.04 e 26.04.

## 10. Segurança e privacidade

- Use senha forte e não compartilhe suas credenciais.
- Faça backups periódicos e teste a restauração.
- Revise arquivos importados antes de confirmar.
- Proteja relatórios e faturas exportados.
- Saia do sistema em computadores compartilhados.
- A exclusão de conta deve ser confirmada, pois remove dados vinculados conforme
  as regras exibidas pelo aplicativo.

## 11. Solução de problemas

- **Painel vazio:** selecione novamente a conta ou cartão e clique em **Atualizar**.
- **Transação ausente:** confira conta, cartão, mês, ano, status e filtros.
- **PDF não reconhecido:** confirme o banco, a senha e a integridade do arquivo.
- **Menu não aparece:** clique com o botão direito diretamente sobre uma linha.
- **Alerta não aparece:** confira as configurações e mantenha o aplicativo aberto.
- **Backup ausente:** confira ativação, intervalo e pasta de dados.

## 12. Suporte, código e auditoria

- Repositório: <https://github.com/boente66/Finance_Assist>
- Versão test.8: <https://github.com/boente66/Finance_Assist/releases/tag/v2.1.0-test.8>
- Relatório: <https://github.com/boente66/Finance_Assist/blob/main/docs/AUDITORIA_INTERFACE_BACKUP_TEST8.md>

A versão 2.1.0-test.8 foi validada com 246 testes automatizados. Os instaladores
incluem arquivos SHA-256 para conferência da integridade.
