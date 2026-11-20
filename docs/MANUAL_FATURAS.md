# Manual de faturas e exportações

## Abrir uma fatura

1. Acesse **Contas e Lançamentos** e selecione o cartão na lista lateral.
2. Escolha o mês e o ano da fatura.
3. Use o filtro **Todos**, **Abertos** ou **Pagos**.

O cabeçalho mostra Nome do cartão, Bandeira, estado Ativo/Inativo, competência,
status da fatura, fechamento e vencimento. Os indicadores exibem Limite, Usado e
Disponível. O resumo inferior separa **Composição da fatura** (compras, créditos,
estornos e ajustes) de **Quitação da fatura** (pagamentos e saldo a pagar).

A tabela apresenta Data, Estabelecimento/Favorecido, Descrição, Tipo, Categoria,
Valor e Status. Arraste a borda dos cabeçalhos para ajustar qualquer coluna.
Descrição recebe prioridade de espaço enquanto não houver ajuste manual. Use
rolagem horizontal quando necessário e passe o ponteiro sobre o texto abreviado
para ler o conteúdo completo. Nomes longos na lista de cartões também têm tooltip.

Cartão inativo continua permitindo consulta e pagamento de obrigações existentes;
novas compras, créditos e importações exigem reativação. Idioma e formatos seguem
as configurações da aplicação em português, inglês e espanhol.

## Criar e editar lançamentos

- **Lançar** abre o cadastro de uma nova despesa.
- Um clique seleciona uma linha.
- Dois cliques abrem **Editar lançamento da fatura**.
- O menu aberto com o botão direito sobre a linha oferece **Copiar**, **Colar**,
  **Editar** e **Excluir**.

**Copiar** guarda os dados do lançamento selecionado. **Colar** cria uma nova
cópia na competência aberta exibida. **Editar** altera apenas
o lançamento selecionado; as demais parcelas não são recriadas. **Excluir** pede
confirmação. Lançamentos de uma fatura fechada ou paga não podem ser editados
ou excluídos.

## Ciclo aberta, fechada e paga

- A fatura **ABERTA** recebe compras da competência atual.
- No dia de fechamento ela passa para **FECHADA** e mantém o saldo pendente.
- O sistema abre a competência seguinte; compras posteriores entram somente
  nela.
- Pagar registra o pagamento no histórico da fatura, uma saída negativa na
  conta e muda o ciclo quitado para **PAGA**. O pagamento não é duplicado na
  tabela de movimentos e as compras originais permanecem positivas.

## Adicionar crédito ou estorno

Use **Adicionar crédito** para cashback, estorno, devolução, desconto ou ajuste.
Digite o valor positivo; o sistema o grava com sinal negativo na fatura e
recompõe o limite. Um estorno pode ser associado à compra original, que continua
visível no histórico. Se o crédito chegar depois do fechamento, ele entra na
competência aberta em que foi recebido.

## Importar uma fatura em PDF

1. Abra o cartão correto e clique em **Importar fatura**.
2. Escolha um PDF suportado.
3. Se o arquivo estiver protegido, informe a senha quando solicitado.
4. Revise todos os itens na tela temporária.
5. Confirme somente os lançamentos que devem entrar no sistema.

Layouts validados nesta versão:

- PicPay Mastercard: compras nacionais e encargos; pagamentos e créditos são
  excluídos para não criar despesas duplicadas.
- Nubank: compras e parcelas de financiamento; pagamentos recebidos e linhas de
  saldo sem valor são excluídos.
- Itaú Mastercard: lançamentos atuais e compras parceladas; pagamentos e compras
  exibidas apenas como previsão das próximas faturas são excluídos.

O sistema confere possíveis duplicidades antes da gravação. Um PDF desconhecido
é recusado e não é interpretado por regras genéricas. A senha do PDF é usada
somente durante a leitura e não é salva no banco ou nas configurações.

## Manutenção excepcional de fatura fechada ou paga (IMP-003)

Selecione o cartão e a competência desejados. Com o painel da fatura aberto,
pressione **Ctrl+D**. O texto **Modo de ajuste temporário ativo** confirma a
autorização para editar compras existentes ou excluir movimentos permitidos.
Pressione **Ctrl+D** novamente para voltar ao bloqueio normal.

A autorização termina ao trocar cartão ou competência, sair do painel, fazer
logout ou fechar o aplicativo. Não é gravada no banco nem restaurada ao abrir
o programa. A fatura continua com seu status real **Fechada** ou **Paga**.

O ajuste não permite mudar cartão, competência, parcelamento ou proprietário.
Pagamentos não podem ser editados ou excluídos por esse modo. Compras com
estornos vinculados não podem ser apagadas enquanto houver esse vínculo.

Em uma fatura paga, alterar o total preserva os pagamentos e seus vínculos
originais. O painel informa a diferença entre total e pagamentos, o saldo a
pagar ou o saldo credor. Uma diferença positiva pode receber um pagamento
complementar real pela ação **Pagar**, inclusive após encerrar o ajuste.
Nenhum pagamento é criado automaticamente para manter a aparência de quitação.

## Exportar a fatura

Clique em **PDF** e escolha o destino. O documento contém identidade visual do
Finance Assist, nome do cartão, competência, total, valor em aberto e uma tabela
paginada com todos os lançamentos da fatura selecionada.

## Exportar o extrato de uma conta

No painel da conta, clique em **Exportar**, selecione **PDF** e escolha o arquivo.
O documento mostra **Extrato da &lt;nome da conta&gt;**, período, ícone do Finance
Assist, tabela de transações e resultado do período. CSV e XLSX continuam
disponíveis para tratamento dos dados em planilhas.

## Atualização e dados existentes

Feche o aplicativo antes de instalar uma nova versão. Instale o pacote sobre a
versão anterior. Não apague o arquivo `financeiro.db`, os backups ou a pasta de
dados `.financeassist`. Esta melhoria não precisa remover nem reconstruir as
tabelas financeiras existentes.
