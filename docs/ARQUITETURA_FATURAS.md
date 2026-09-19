# Arquitetura das faturas de cartão

## Fonte de verdade

Cada tabela tem uma responsabilidade única:

| Tabela | Responsabilidade |
| --- | --- |
| `credito` | Cadastro do cartão: limite, fechamento, vencimento e proprietário. |
| `faturas_cartao` | Ciclo mensal do cartão e seu estado `ABERTA`, `FECHADA` ou `PAGA`. |
| `lancamentos` | Movimentos da fatura: compra, crédito, estorno, ajuste e encargo. |
| `pagamentos_fatura` | Fonte oficial, idempotente e auditável dos pagamentos. |
| `transacoes` | Movimento real da conta bancária usada no pagamento. |
| `contas` | Saldo da conta bancária. |

`faturas_cartao.ID_Fatura` é a identidade da fatura. `lancamentos.ID_Fatura` e
`pagamentos_fatura.ID_Fatura` apontam para ela. O estado financeiro da fatura é
lido de `faturas_cartao.Status`; a coluna histórica `lancamentos.Paga` continua
somente para compatibilidade com bancos antigos e não decide o ciclo.

```mermaid
erDiagram
    usuarios ||--o{ credito : possui
    credito ||--o{ faturas_cartao : gera
    faturas_cartao ||--o{ lancamentos : contem
    faturas_cartao ||--o{ pagamentos_fatura : recebe
    contas ||--o{ transacoes : movimenta
    pagamentos_fatura ||--|| transacoes : debita
    lancamentos ||--o| lancamentos : estorna

    faturas_cartao {
        integer ID_Fatura PK
        integer ID_Cartao FK
        integer Competencia_Mes
        integer Competencia_Ano
        integer ID_Usuario FK
        text Status
    }
    lancamentos {
        integer ID_Lancamento PK
        integer ID_Fatura FK
        integer ID_Cartao FK
        real Valor
        text Tipo_Movimento
        integer ID_Lancamento_Origem FK
    }
    pagamentos_fatura {
        integer ID_Pagamento PK
        integer ID_Fatura FK
        integer ID_Conta FK
        integer ID_Transacao FK
        real Valor
        text Chave_Idempotencia
    }
```

## Regras de consistência

- A combinação cartão, competência e usuário é única em `faturas_cartao`.
- Gatilhos do SQLite recusam um `ID_Fatura` incompatível com cartão,
  competência ou usuário nos lançamentos e pagamentos.
- Compra e encargo usam valor positivo. Crédito e estorno usam valor negativo;
  ajuste pode ser positivo ou negativo.
- O pagamento existe em `pagamentos_fatura`, cria uma saída negativa em
  `transacoes` e não cria outro registro em `lancamentos`.
- Ao fechar um ciclo, compras novas são vinculadas automaticamente à próxima
  competência aberta.
- A migração é aditiva: cria e preenche vínculos sem apagar as tabelas ou os
  registros existentes.

Por compatibilidade entre bancos novos e migrados no SQLite, `ID_Fatura` nos
filhos é validado por triggers e chave lógica. As colunas `ID_Cartao`,
`Competencia_Mes`, `Competencia_Ano` e `ID_Usuario`
permanecem nos registros filhos durante a compatibilidade com versões antigas.
Elas são dados espelhados e validados, não uma segunda fonte de estado.
