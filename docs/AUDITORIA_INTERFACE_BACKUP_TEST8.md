# Auditoria de interface, backup e alertas — 2.1.0-test.8

Data: 12 de setembro de 2026.

## Interface corrigida

- O painel lateral de contas passou de 280 para 240 pixels no modo normal e as
  listas ficaram mais compactas.
- A fatura usa três indicadores na mesma linha a partir de 680 pixels.
- Os botões largos de paginação foram substituídos por controles circulares.
- Os botões de adicionar conta e cartão usam animação de foco e dica textual.
- A área vazia agora mostra uma mensagem de boas-vindas e orientação.
- O botão **Atualizar** relê contas, cartões, saldos e o painel selecionado sem
  perder a seleção.

## Menus contextuais

O botão **Ações** foi removido. Clique com o botão direito sobre uma linha da
fatura ou do extrato da conta. O menu oferece copiar, colar, editar e excluir.
O duplo clique abre a edição.

## Backup e alertas

O backup manual continua em **Perfil > Backup e Restauração**. Administradores
podem configurar em **Configurações**:

- backup automático e intervalo entre execuções;
- quantidade de backups automáticos mantidos;
- notificações de agendamentos vencidos e intervalo dos alertas;
- mensagem de boas-vindas.

Os backups automáticos são gravados em `backups/automaticos` dentro da pasta de
dados. A chave criptográfica é criada no dispositivo com permissão restrita e
não é gravada no SQLite nem enviada ao GitHub. A rotina só executa enquanto o
Finance Assist está aberto e mantém os bancos existentes intactos.

## Segurança de atualização

Não há migração destrutiva. Nenhuma tabela é apagada ou recriada pela instalação.
Os testes usam bancos descartáveis e conferem que o backup não altera o banco de
origem.

Validação local final: **246 testes automatizados aprovados**.

## Publicação

- GitHub Release `v2.1.0-test.8` publicada como prerelease com três instaladores
  e os respectivos arquivos SHA-256.
- Build multiplataforma aprovado no GitHub Actions, incluindo Windows e pacotes
  DEB para Ubuntu 22.04, 24.04 e 26.04.
- Validação dedicada do pacote Ubuntu 24.04 aprovada, incluindo atualização com
  preservação do banco existente.

Links: [release](https://github.com/boente66/Finance_Assist/releases/tag/v2.1.0-test.8),
[build multiplataforma](https://github.com/boente66/Finance_Assist/actions/runs/34713345483)
e [validação Ubuntu 24.04](https://github.com/boente66/Finance_Assist/actions/runs/34713354005).
