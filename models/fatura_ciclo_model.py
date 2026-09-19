from database.database import Database


class FaturaCicloModel(Database):
    def garantir(
        self,
        id_cartao,
        mes,
        ano,
        id_usuario,
        data_fechamento,
        data_vencimento,
        status="ABERTA",
    ):
        self.execute_query("""
            INSERT INTO faturas_cartao (
                ID_Cartao, Competencia_Mes, Competencia_Ano, ID_Usuario,
                Status, Data_Fechamento, Data_Vencimento
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(
                ID_Cartao, Competencia_Mes, Competencia_Ano, ID_Usuario
            ) DO UPDATE SET
                Data_Fechamento = excluded.Data_Fechamento,
                Data_Vencimento = excluded.Data_Vencimento,
                Atualizado_Em = CURRENT_TIMESTAMP
        """, (
            id_cartao, int(mes), int(ano), id_usuario,
            status, data_fechamento, data_vencimento,
        ))
        return self.obter(id_cartao, mes, ano, id_usuario)

    def obter(self, id_cartao, mes, ano, id_usuario):
        return self.fetch_one("""
            SELECT *
            FROM faturas_cartao
            WHERE ID_Cartao = ?
              AND Competencia_Mes = ?
              AND Competencia_Ano = ?
              AND ID_Usuario = ?
        """, (id_cartao, int(mes), int(ano), id_usuario))

    def definir_status(
        self,
        id_cartao,
        mes,
        ano,
        id_usuario,
        status,
        data_evento,
    ):
        if status not in {"ABERTA", "FECHADA", "PAGA"}:
            raise ValueError("Status de fatura inválido.")
        campo_evento = (
            "Fechada_Em" if status == "FECHADA"
            else "Paga_Em" if status == "PAGA"
            else None
        )
        evento_sql = f", {campo_evento} = ?" if campo_evento else ""
        params = [status]
        if campo_evento:
            params.append(data_evento)
        params.extend([id_cartao, int(mes), int(ano), id_usuario])
        self.execute_query(f"""
            UPDATE faturas_cartao
            SET Status = ?, Atualizado_Em = CURRENT_TIMESTAMP {evento_sql}
            WHERE ID_Cartao = ?
              AND Competencia_Mes = ?
              AND Competencia_Ano = ?
              AND ID_Usuario = ?
        """, tuple(params))
        return self.obter(id_cartao, mes, ano, id_usuario)
