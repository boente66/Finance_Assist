# Manual de faturas e exportações

## Abrir uma fatura

1. Acesse **Cartões** e selecione o cartão.
2. Escolha o mês e o ano da fatura.
3. Use o filtro **Todos**, **Abertos** ou **Pagos**.

O cabeçalho mostra limite, valor usado e limite disponível. A tabela apresenta
data, descrição, categoria, valor e estado do lançamento. Em janelas estreitas,
os indicadores são reorganizados, os botões usam ícones e a fonte da tabela é
reduzida para manter o conteúdo legível.

## Criar e editar lançamentos

- **Lançar** abre o cadastro de uma nova despesa.
- Um clique seleciona uma linha.
- Dois cliques abrem **Editar lançamento da fatura**.
- O botão **Ações**, aberto com o botão esquerdo, oferece **Copiar**, **Colar**,
  **Editar** e **Excluir**.

**Copiar** guarda os dados do lançamento selecionado. **Colar** cria uma nova
cópia na competência exibida e sempre a deixa em aberto. **Editar** altera apenas
o lançamento selecionado; as demais parcelas não são recriadas. **Excluir** pede
confirmação. Lançamentos de uma fatura paga não podem ser editados ou excluídos.

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
