"""Persistência do módulo de dívidas."""

from database.database import Database


class DividaModel(Database):
    def __init__(self, db_name=None):
        super().__init__(db_name) if db_name else super().__init__()

    def add(self, dados):
        return self.execute_insert("""
            INSERT INTO dividas (
                ID_Usuario, ID_Favorecido, Numero_Contrato, Tipo_Divida,
                Tipo_Parcelamento, Descricao, Valor_Emprestado,
                Valor_Total_Contrato, Saldo_Devedor, Quantidade_Parcelas,
                Valor_Parcela, Taxa_Juros, Data_Contratacao,
                Primeiro_Vencimento, Dia_Vencimento, Status, Observacao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dados["ID_Usuario"], dados.get("ID_Favorecido"),
            dados.get("Numero_Contrato"), dados["Tipo_Divida"],
            dados["Tipo_Parcelamento"], dados["Descricao"],
            dados["Valor_Emprestado"], dados["Valor_Total_Contrato"],
            dados["Saldo_Devedor"], dados.get("Quantidade_Parcelas"),
            dados.get("Valor_Parcela"), dados.get("Taxa_Juros", 0),
            dados["Data_Contratacao"], dados.get("Primeiro_Vencimento"),
            dados.get("Dia_Vencimento"), dados.get("Status", "ATIVA"),
            dados.get("Observacao"),
        ))

    def get_by_id(self, id_divida, id_usuario):
        return self.fetch_one("""
            SELECT d.*, f.Nome AS Favorecido
            FROM dividas d
            LEFT JOIN favorecido f ON f.ID_Favorecido=d.ID_Favorecido
            WHERE d.ID_Divida=? AND d.ID_Usuario=?
        """, (id_divida, id_usuario))

    def get_all(self, id_usuario, status=None):
        return self.fetch_all("""
            SELECT d.*, f.Nome AS Favorecido,
                   COUNT(p.ID_Parcela) AS Total_Parcelas,
                   SUM(CASE WHEN p.Status='PAGA' THEN 1 ELSE 0 END) AS Parcelas_Pagas,
                   SUM(CASE WHEN p.Status NOT IN ('PAGA','CANCELADA') THEN 1 ELSE 0 END) AS Parcelas_Restantes,
                   MIN(CASE WHEN p.Status NOT IN ('PAGA','CANCELADA')
                            THEN p.Data_Vencimento END) AS Proximo_Vencimento
            FROM dividas d
            LEFT JOIN favorecido f ON f.ID_Favorecido=d.ID_Favorecido
            LEFT JOIN divida_parcelas p ON p.ID_Divida=d.ID_Divida
            WHERE d.ID_Usuario=? AND (? IS NULL OR d.Status=?)
            GROUP BY d.ID_Divida
            ORDER BY CASE d.Status WHEN 'ATRASADA' THEN 0 WHEN 'ATIVA' THEN 1 ELSE 2 END,
                     date(COALESCE(MIN(CASE WHEN p.Status NOT IN ('PAGA','CANCELADA')
                            THEN p.Data_Vencimento END), d.Primeiro_Vencimento)), d.ID_Divida
        """, (id_usuario, status, status))

    def update_balance_status(self, id_divida, id_usuario, saldo, status):
        cursor = self.execute_query("""
            UPDATE dividas SET Saldo_Devedor=?, Status=?,
                Atualizado_Em=CURRENT_TIMESTAMP
            WHERE ID_Divida=? AND ID_Usuario=?
        """, (saldo, status, id_divida, id_usuario))
        if cursor.rowcount != 1:
            raise ValueError("Dívida não encontrada.")

    def update_installment_value(self, id_divida, value):
        self.execute_query(
            "UPDATE dividas SET Valor_Parcela=? WHERE ID_Divida=?",
            (value, id_divida),
        )

    def mark_overdue(self, id_usuario):
        self.execute_query("""
            UPDATE dividas SET Status='ATRASADA', Atualizado_Em=CURRENT_TIMESTAMP
            WHERE ID_Usuario=? AND Status='ATIVA' AND EXISTS (
                SELECT 1 FROM divida_parcelas p WHERE p.ID_Divida=dividas.ID_Divida
                  AND p.Status='ATRASADA')
        """, (id_usuario,))

    def set_status(self, id_divida, id_usuario, status):
        cursor = self.execute_query("""
            UPDATE dividas SET Status=?, Atualizado_Em=CURRENT_TIMESTAMP
            WHERE ID_Divida=? AND ID_Usuario=?
        """, (status, id_divida, id_usuario))
        if cursor.rowcount != 1:
            raise ValueError("Dívida não encontrada.")
