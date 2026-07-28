from database.database import Database


class PagamentoFaturaModel(Database):

    def __init__(self, db_name=None):
        super().__init__(db_name) if db_name else super().__init__()

    def get_by_key(self, chave_idempotencia, id_usuario):
        return self.fetch_one("""
            SELECT *
            FROM pagamentos_fatura
            WHERE Chave_Idempotencia = ?
              AND ID_Usuario = ?
        """, (chave_idempotencia, id_usuario))

    def get_last_by_invoice(self, id_cartao, mes, ano, id_usuario):
        return self.fetch_one("""
            SELECT *
            FROM pagamentos_fatura
            WHERE ID_Cartao = ?
              AND Competencia_Mes = ?
              AND Competencia_Ano = ?
              AND ID_Usuario = ?
            ORDER BY ID_Pagamento DESC
            LIMIT 1
        """, (id_cartao, int(mes), int(ano), id_usuario))

    def add_payment(
        self,
        chave_idempotencia,
        id_cartao,
        mes,
        ano,
        id_conta,
        id_transacao,
        id_usuario,
        valor
    ):
        return self.execute_insert("""
            INSERT INTO pagamentos_fatura (
                Chave_Idempotencia,
                ID_Cartao,
                Competencia_Mes,
                Competencia_Ano,
                ID_Conta,
                ID_Transacao,
                ID_Usuario,
                Valor
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            chave_idempotencia,
            id_cartao,
            int(mes),
            int(ano),
            id_conta,
            id_transacao,
            id_usuario,
            valor,
        ))
