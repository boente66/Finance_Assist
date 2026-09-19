import logging
from database.database import Database
from models.credito_model import CreditoModel

logger = logging.getLogger(__name__)


class LancamentoModel(Database):

    def __init__(self, db_name=None):
        super().__init__(db_name) if db_name else super().__init__()
        self.credito = CreditoModel(db_name)

    # ============================================================
    # CRIAR LANÇAMENTO
    # ============================================================
    def add_lancamento(self, dados: dict) -> bool:

        obrigatorios = [
            "ID_Usuario",
            "ID_Cartao",
            "Descricao",
            "Valor",
            "Data",
            "Competencia_Mes",
            "Competencia_Ano"
        ]

        for campo in obrigatorios:
            if campo not in dados:
                raise ValueError(f"{campo} é obrigatório.")

        cartao = self.credito.get_cartao_by_id(
            dados["ID_Cartao"],
            dados["ID_Usuario"]
        )

        if not cartao:
            raise PermissionError("Cartão não pertence ao usuário.")

        tipo_movimento = dados.get("Tipo_Movimento", "COMPRA")
        valor = float(dados["Valor"])
        if tipo_movimento not in {"COMPRA", "CREDITO", "PAGAMENTO"}:
            raise ValueError("Tipo de movimento da fatura inválido.")
        if tipo_movimento == "COMPRA" and valor <= 0:
            raise ValueError("Compra de cartão deve possuir valor positivo.")
        if tipo_movimento in {"CREDITO", "PAGAMENTO"} and valor >= 0:
            raise ValueError(
                "Crédito ou pagamento de fatura deve possuir valor negativo."
            )

        data = dados["Data"]
        if not isinstance(data, str):
            data = data.strftime("%Y-%m-%d")

        sql = """
            INSERT INTO lancamentos (
                ID_Cartao,
                ID_Fatura,
                Data,
                Competencia_Mes,
                Competencia_Ano,
                Descricao,
                Valor,
                ID_Categoria,
                ID_Favorecido,
                Num_Parcelas,
                Parcela_Atual,
                Paga,
                Notas,
                ID_Usuario,
                ID_Conta,
                ID_Transacao,
                Previsto,
                Tipo_Movimento,
                ID_Lancamento_Origem
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            dados["ID_Cartao"],
            dados.get("ID_Fatura"),
            data,
            int(dados["Competencia_Mes"]),
            int(dados["Competencia_Ano"]),
            dados["Descricao"],
            valor,
            dados.get("ID_Categoria"),
            dados.get("ID_Favorecido"),  # 🔥 NOVO
            int(dados.get("Num_Parcelas", 1)),
            int(dados.get("Parcela_Atual", 1)),
            int(dados.get("Paga", 0)),
            dados.get("Notas"),
            dados["ID_Usuario"],
            dados.get("ID_Conta"),
            dados.get("ID_Transacao"),
            int(dados.get("Previsto", 0)),
            tipo_movimento,
            dados.get("ID_Lancamento_Origem")
        )

        self.execute_query(sql, params)
        return True

    # ============================================================
    # BUSCAR POR ID
    # ============================================================
    def get_lancamento_by_id(self, id_lancamento, id_usuario):

        sql = """
            SELECT *
            FROM lancamentos
            WHERE ID_Lancamento = ?
              AND ID_Usuario = ?
        """

        return self.fetch_one(sql, (id_lancamento, id_usuario))

    def get_import_candidates(
        self,
        id_cartao,
        id_usuario,
        data_inicio,
        data_fim
    ):
        """Inclui pagos: o pagamento não muda a identidade da compra."""
        if not data_inicio or not data_fim:
            return []
        return self.fetch_all("""
            SELECT
                ID_Lancamento, ID_Cartao, ID_Usuario, Data, Descricao, Valor,
                Competencia_Mes, Competencia_Ano, Parcela_Atual,
                Num_Parcelas, Paga
            FROM lancamentos
            WHERE ID_Cartao = ?
              AND ID_Usuario = ?
              AND date(Data) BETWEEN date(?) AND date(?)
            ORDER BY date(Data), ID_Lancamento
        """, (id_cartao, id_usuario, data_inicio, data_fim))

    # ============================================================
    # ATUALIZAR
    # ============================================================
    def update_lancamento(self, id_lancamento, dados, id_usuario):

        obrigatorios = [
            "Descricao",
            "Valor",
            "Data",
            "Competencia_Mes",
            "Competencia_Ano"
        ]

        for campo in obrigatorios:
            if campo not in dados:
                raise ValueError(f"{campo} é obrigatório.")

        cartao = self.credito.get_cartao_by_id(
            dados["ID_Cartao"],
            id_usuario
        )

        if not cartao:
            raise PermissionError("Cartão inválido.")

        tipo_movimento = dados.get("Tipo_Movimento", "COMPRA")
        valor = float(dados["Valor"])
        if tipo_movimento != "COMPRA" or valor <= 0:
            raise ValueError(
                "Somente compras positivas podem ser editadas neste formulário."
            )

        data = dados["Data"]
        if not isinstance(data, str):
            data = data.strftime("%Y-%m-%d")

        sql = """
            UPDATE lancamentos
            SET Descricao = ?,
                Valor = ?,
                Data = ?,
                Competencia_Mes = ?,
                Competencia_Ano = ?,
                ID_Categoria = ?,
                ID_Favorecido = ?,  -- 🔥 NOVO
                Num_Parcelas = ?,
                Parcela_Atual = ?,
                Notas = ?,
                Previsto = ?,
                Tipo_Movimento = ?,
                ID_Lancamento_Origem = ?
            WHERE ID_Lancamento = ?
              AND ID_Usuario = ?
        """

        self.execute_query(sql, (
            dados["Descricao"],
            valor,
            data,
            int(dados["Competencia_Mes"]),
            int(dados["Competencia_Ano"]),
            dados.get("ID_Categoria"),
            dados.get("ID_Favorecido"),  # 🔥 NOVO
            int(dados.get("Num_Parcelas", 1)),
            int(dados.get("Parcela_Atual", 1)),
            dados.get("Notas"),
            int(dados.get("Previsto", 0)),
            tipo_movimento,
            dados.get("ID_Lancamento_Origem"),
            id_lancamento,
            id_usuario
        ))

        return True

    # ============================================================
    # FATURA
    # ============================================================
    def get_lancamentos_por_fatura(self, id_cartao, mes, ano, id_usuario):

        sql = """
        SELECT l.*,
               c.Nome AS Categoria,
               f.Nome AS Favorecido
        FROM lancamentos l
        LEFT JOIN categorias c
            ON c.ID_Categoria = l.ID_Categoria
        LEFT JOIN favorecido f
            ON f.ID_Favorecido = l.ID_Favorecido
        WHERE l.ID_Cartao = ?
          AND l.ID_Usuario = ?
          AND l.Competencia_Mes = ?
          AND l.Competencia_Ano = ?
        ORDER BY l.Data
        """

        return self.fetch_all(
            sql,
            (id_cartao, id_usuario, int(mes), int(ano))
        )

    # ============================================================
    # PREVISTOS
    # ============================================================
    def get_lancamentos_previstos(self, id_cartao, mes, ano, id_usuario):

        sql = """
            SELECT *
            FROM lancamentos
            WHERE ID_Cartao = ?
              AND ID_Usuario = ?
              AND Competencia_Mes = ?
              AND Competencia_Ano = ?
              AND Previsto = 1
            ORDER BY Data
        """

        return self.fetch_all(
            sql,
            (id_cartao, id_usuario, int(mes), int(ano))
        )

    # ============================================================
    # REAIS
    # ============================================================
    def get_lancamentos_reais(self, id_cartao, mes, ano, id_usuario):

        sql = """
            SELECT *
            FROM lancamentos
            WHERE ID_Cartao = ?
              AND ID_Usuario = ?
              AND Competencia_Mes = ?
              AND Competencia_Ano = ?
              AND Previsto = 0
            ORDER BY Data
        """

        return self.fetch_all(
            sql,
            (id_cartao, id_usuario, int(mes), int(ano))
        )

    # ============================================================
    # NÃO PAGOS
    # ============================================================
    def get_lancamentos_nao_pagos(self, id_cartao, id_usuario):

        sql = """
            SELECT *
            FROM lancamentos
            WHERE ID_Cartao = ?
              AND ID_Usuario = ?
              AND Paga = 0
        """

        return self.fetch_all(sql, (id_cartao, id_usuario))

    def get_lancamentos_para_limite(self, id_cartao, id_usuario):
        return self.fetch_all("""
            SELECT *
            FROM lancamentos
            WHERE ID_Cartao = ?
              AND ID_Usuario = ?
              AND Previsto = 0
            ORDER BY Data, ID_Lancamento
        """, (id_cartao, id_usuario))

    # ============================================================
    # MARCAR COMO PAGO
    # ============================================================
    def marcar_como_pago(
        self,
        id_lancamento,
        id_transacao,
        id_usuario=None
    ):

        sql = """
            UPDATE lancamentos
            SET Paga = 1,
                ID_Transacao = ?,
                Previsto = 0
            WHERE ID_Lancamento = ?
              AND (? IS NULL OR ID_Usuario = ?)
              AND Paga = 0
        """

        cursor = self.execute_query(
            sql,
            (
                id_transacao,
                id_lancamento,
                id_usuario,
                id_usuario,
            )
        )

        if cursor.rowcount != 1:
            raise ValueError(
                "Lançamento não encontrado ou já estava pago."
            )

        return True

    def marcar_fatura_como_quitada(
        self, id_cartao, mes, ano, id_usuario
    ):
        self.execute_query("""
            UPDATE lancamentos
            SET Paga = 1, Previsto = 0
            WHERE ID_Cartao = ?
              AND Competencia_Mes = ?
              AND Competencia_Ano = ?
              AND ID_Usuario = ?
        """, (id_cartao, int(mes), int(ano), id_usuario))
        return True

    # ============================================================
    # CONFIRMAR PREVISTOS
    # ============================================================
    def confirmar_previstos(self, id_cartao, mes, ano, id_usuario):

        sql = """
            UPDATE lancamentos
            SET Previsto = 0
            WHERE ID_Cartao = ?
              AND ID_Usuario = ?
              AND Competencia_Mes = ?
              AND Competencia_Ano = ?
              AND Previsto = 1
        """

        self.execute_query(
            sql,
            (id_cartao, id_usuario, int(mes), int(ano))
        )

        return True

    # ============================================================
    # EXCLUIR
    # ============================================================
    def excluir_lancamento(self, id_lancamento, id_usuario):

        sql = """
            DELETE FROM lancamentos
            WHERE ID_Lancamento = ?
              AND ID_Usuario = ?
        """

        self.execute_query(sql, (id_lancamento, id_usuario))
        return True

    # ============================================================
    # VERIFICAR PREVISTO
    # ============================================================
    def existe_previsto(self, id_cartao, descricao, mes, ano, id_usuario):

        sql = """
            SELECT 1
            FROM lancamentos
            WHERE ID_Cartao = ?
            AND Descricao = ?
            AND Competencia_Mes = ?
            AND Competencia_Ano = ?
            AND ID_Usuario = ?
            AND Previsto = 1
            LIMIT 1
        """

        return self.fetch_one(sql, (
            id_cartao, descricao, mes, ano, id_usuario
        )) is not None

    # ============================================================
    # POR CARTÃO
    # ============================================================
    def get_lancamentos_por_cartao(self, id_cartao, id_usuario):

        sql = """
            SELECT *
            FROM lancamentos
            WHERE ID_Cartao = ?
              AND ID_Usuario = ?
            ORDER BY Data
        """

        return self.fetch_all(sql, (id_cartao, id_usuario))
