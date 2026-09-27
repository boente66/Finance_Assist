"""Persistência das parcelas de dívida."""

from database.database import Database


class DividaParcelaModel(Database):
    def __init__(self, db_name=None):
        super().__init__(db_name) if db_name else super().__init__()

    def add(self, dados):
        return self.execute_insert("""
            INSERT INTO divida_parcelas
                (ID_Divida, Numero_Parcela, Data_Vencimento, Valor_Previsto)
            VALUES (?, ?, ?, ?)
        """, (dados["ID_Divida"], dados["Numero_Parcela"],
              dados["Data_Vencimento"], dados["Valor_Previsto"]))

    def get_all(self, id_divida, id_usuario):
        return self.fetch_all("""
            SELECT p.* FROM divida_parcelas p
            JOIN dividas d ON d.ID_Divida=p.ID_Divida
            WHERE p.ID_Divida=? AND d.ID_Usuario=? ORDER BY p.Numero_Parcela
        """, (id_divida, id_usuario))

    def get_by_id(self, id_parcela, id_divida, id_usuario):
        return self.fetch_one("""
            SELECT p.* FROM divida_parcelas p
            JOIN dividas d ON d.ID_Divida=p.ID_Divida
            WHERE p.ID_Parcela=? AND p.ID_Divida=? AND d.ID_Usuario=?
        """, (id_parcela, id_divida, id_usuario))

    def apply_payment(self, id_parcela, valor, data_pagamento):
        cursor = self.execute_query("""
            UPDATE divida_parcelas
            SET Valor_Pago=MIN(Valor_Previsto, Valor_Pago + ?),
                Status=CASE WHEN Valor_Pago + ? + 0.005 >= Valor_Previsto
                            THEN 'PAGA' ELSE 'PARCIAL' END,
                Data_Pagamento=CASE WHEN Valor_Pago + ? + 0.005 >= Valor_Previsto
                                    THEN ? ELSE Data_Pagamento END
            WHERE ID_Parcela=? AND Status NOT IN ('PAGA','CANCELADA')
        """, (valor, valor, valor, data_pagamento, id_parcela))
        if cursor.rowcount != 1:
            raise ValueError("Parcela não está disponível para pagamento.")

    def mark_overdue(self, id_usuario, today):
        self.execute_query("""
            UPDATE divida_parcelas SET Status='ATRASADA'
            WHERE Status IN ('PENDENTE','PARCIAL') AND date(Data_Vencimento)<date(?)
              AND ID_Divida IN (SELECT ID_Divida FROM dividas WHERE ID_Usuario=?)
        """, (today, id_usuario))

    def cancel_pending(self, id_divida):
        self.execute_query("""
            UPDATE divida_parcelas SET Status='CANCELADA'
            WHERE ID_Divida=? AND Status IN ('PENDENTE','PARCIAL','ATRASADA')
        """, (id_divida,))
