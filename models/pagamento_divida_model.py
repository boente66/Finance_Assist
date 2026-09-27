"""Persistência dos pagamentos efetivos de dívida."""

from database.database import Database


class PagamentoDividaModel(Database):
    def __init__(self, db_name=None):
        super().__init__(db_name) if db_name else super().__init__()

    def get_by_key(self, key, id_usuario):
        return self.fetch_one("""
            SELECT * FROM pagamentos_divida
            WHERE Chave_Idempotencia=? AND ID_Usuario=?
        """, (key, id_usuario))

    def add(self, dados):
        return self.execute_insert("""
            INSERT INTO pagamentos_divida (
                Chave_Idempotencia, ID_Divida, ID_Parcela, ID_Conta,
                ID_Transacao, ID_Usuario, Valor_Pago, Valor_Juros,
                Valor_Multa, Valor_Desconto, Valor_Amortizado,
                Data_Pagamento, Observacao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (dados["Chave_Idempotencia"], dados["ID_Divida"],
              dados.get("ID_Parcela"), dados["ID_Conta"], dados["ID_Transacao"],
              dados["ID_Usuario"], dados["Valor_Pago"], dados.get("Valor_Juros", 0),
              dados.get("Valor_Multa", 0), dados.get("Valor_Desconto", 0),
              dados["Valor_Amortizado"], dados["Data_Pagamento"],
              dados.get("Observacao")))

    def get_all(self, id_divida, id_usuario):
        return self.fetch_all("""
            SELECT p.*, c.Nome_Conta AS Conta FROM pagamentos_divida p
            JOIN contas c ON c.ID_Conta=p.ID_Conta
            WHERE p.ID_Divida=? AND p.ID_Usuario=?
            ORDER BY date(p.Data_Pagamento), p.ID_Pagamento
        """, (id_divida, id_usuario))
