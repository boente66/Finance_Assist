# -*- coding: utf-8 -*-
from database.database import Database
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TransactionModel(Database):

    def __init__(self, db_name=None):
        super().__init__(db_name) if db_name else super().__init__()

    # ============================================================
    # CREATE
    # ============================================================
    def add_transaction(self, dados: dict):
        sql = """
            INSERT INTO transacoes (
                ID_Conta,
                Descricao,
                Valor,
                Data,
                Tipo,
                ID_Categoria,
                ID_Favorecido,
                Notas,
                ID_Usuario,
                ID_Agendamento
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        cur = self.execute_query(sql, (
            dados.get("ID_Conta"),
            dados.get("Descricao"),
            dados.get("Valor"),
            dados.get("Data"),
            dados.get("Tipo"),
            dados.get("ID_Categoria"),
            dados.get("ID_Favorecido"),
            dados.get("Notas"),
            dados.get("ID_Usuario"),
            dados.get("ID_Agendamento")
        ))
        return cur.lastrowid

    def get_transaction_by_schedule(self, id_agendamento, id_usuario):
        return self.fetch_one("""
            SELECT *
            FROM transacoes
            WHERE ID_Agendamento = ?
              AND ID_Usuario = ?
        """, (id_agendamento, id_usuario))

    # ============================================================
    # READ
    # ============================================================
    def get_transactions_by_account(self, id_conta, id_usuario):
        return self.fetch_all("""
            SELECT
                t.ID_Transacao,
                t.Descricao,
                t.Valor,
                t.Data,
                t.Tipo,
                t.Notas,

                t.ID_Categoria,
                t.ID_Favorecido,

                COALESCE(c.Nome, '') AS Categoria,
                COALESCE(f.Nome, '') AS Favorecido

            FROM transacoes t

            LEFT JOIN categorias c 
                ON c.ID_Categoria = t.ID_Categoria

            LEFT JOIN favorecido f 
                ON f.ID_Favorecido = t.ID_Favorecido

            WHERE t.ID_Conta = ?
              AND t.ID_Usuario = ?

            ORDER BY date(t.Data) DESC, t.ID_Transacao DESC
        """, (id_conta, id_usuario))

    def get_transactions_by_account_periodo(
        self,
        id_conta,
        data_inicio,
        data_fim,
        id_usuario
    ):
        return self.fetch_all("""
            SELECT
                t.ID_Transacao,
                t.Descricao,
                t.Valor,
                t.Data,
                t.Tipo,
                t.Notas,

                t.ID_Categoria,
                t.ID_Favorecido,

                COALESCE(c.Nome, '') AS Categoria,
                COALESCE(f.Nome, '') AS Favorecido

            FROM transacoes t

            LEFT JOIN categorias c 
                ON c.ID_Categoria = t.ID_Categoria

            LEFT JOIN favorecido f 
                ON f.ID_Favorecido = t.ID_Favorecido

            WHERE t.ID_Conta = ?
              AND t.ID_Usuario = ?
              AND date(t.Data) BETWEEN date(?) AND date(?)

            ORDER BY date(t.Data) DESC, t.ID_Transacao DESC
        """, (id_conta, id_usuario, data_inicio, data_fim))

    def get_transaction_by_id(self, id_transacao, id_usuario):
        return self.fetch_one("""
            SELECT
                t.*,
                COALESCE(c.Nome, '') AS Categoria,
                COALESCE(f.Nome, '') AS Favorecido
            FROM transacoes t
            LEFT JOIN categorias c ON c.ID_Categoria = t.ID_Categoria
            LEFT JOIN favorecido f ON f.ID_Favorecido = t.ID_Favorecido
            WHERE t.ID_Transacao = ?
              AND t.ID_Usuario = ?
        """, (id_transacao, id_usuario))

    # ============================================================
    # UPDATE
    # ============================================================
    def update_transaction(self, id_transacao, dados, id_usuario):
        sql = """
            UPDATE transacoes
            SET
                Descricao = ?,
                Valor = ?,
                Data = ?,
                ID_Categoria = ?,
                ID_Favorecido = ?,
                Notas = ?
            WHERE ID_Transacao = ?
              AND ID_Usuario = ?
        """

        self.execute_query(sql, (
            dados.get("Descricao"),
            dados.get("Valor"),
            dados.get("Data"),
            dados.get("ID_Categoria"),
            dados.get("ID_Favorecido"),
            dados.get("Notas"),
            id_transacao,
            id_usuario
        ))

    # ============================================================
    # DELETE
    # ============================================================
    def delete_transaction(self, id_transacao, id_usuario):
        self.execute_query("""
            DELETE FROM transacoes
            WHERE ID_Transacao = ?
              AND ID_Usuario = ?
        """, (id_transacao, id_usuario))

    # ============================================================
    # MÉTODOS PARA METAS
    # ============================================================
    def somar_despesas_categoria_periodo(
        self,
        id_categoria,
        id_usuario,
        data_inicio=None,
        data_fim=None
    ):
        sql = """
            SELECT ABS(SUM(Valor)) AS total
            FROM transacoes
            WHERE ID_Categoria = ?
              AND ID_Usuario = ?
              AND Valor < 0
        """
        params = [id_categoria, id_usuario]

        if data_inicio and data_fim:
            sql += " AND date(Data) BETWEEN date(?) AND date(?)"
            params.extend([data_inicio, data_fim])

        resultado = self.fetch_one(sql, tuple(params))
        return float(resultado["total"] or 0)

    def somar_receitas_periodo(
        self,
        id_usuario,
        data_inicio=None,
        data_fim=None
    ):
        sql = """
            SELECT SUM(Valor) AS total
            FROM transacoes
            WHERE ID_Usuario = ?
              AND Valor > 0
        """
        params = [id_usuario]

        if data_inicio and data_fim:
            sql += " AND date(Data) BETWEEN date(?) AND date(?)"
            params.extend([data_inicio, data_fim])

        resultado = self.fetch_one(sql, tuple(params))
        return float(resultado["total"] or 0)

    def calcular_economia_periodo(
        self,
        id_usuario,
        data_inicio=None,
        data_fim=None
    ):
        sql = """
            SELECT SUM(Valor) AS total
            FROM transacoes
            WHERE ID_Usuario = ?
        """
        params = [id_usuario]

        if data_inicio and data_fim:
            sql += " AND date(Data) BETWEEN date(?) AND date(?)"
            params.extend([data_inicio, data_fim])

        resultado = self.fetch_one(sql, tuple(params))
        return float(resultado["total"] or 0)



    # ============================================================
    # SALDO ANTES DO PERÍODO
    # ============================================================
    def get_saldo_antes_periodo(
        self,
        id_conta,
        data_inicio,
        id_usuario
    ):
        resultado = self.fetch_one("""
            SELECT COALESCE(SUM(Valor), 0) AS Saldo
            FROM transacoes
            WHERE ID_Conta = ?
              AND ID_Usuario = ?
              AND date(Data) < date(?)
        """, (id_conta, id_usuario, data_inicio))

        return float(resultado["Saldo"] or 0)


    # ============================================================
    # RESUMO E ANÁLISE
    # ============================================================
    def get_resumo_financeiro(self, user_id):
        sql = """
            SELECT
                SUM(CASE WHEN Valor > 0 THEN Valor ELSE 0 END) AS Receitas,
                SUM(CASE WHEN Valor < 0 THEN ABS(Valor) ELSE 0 END) AS Despesas
            FROM transacoes
            WHERE ID_Usuario = ?
              AND strftime('%Y-%m', Data) = strftime('%Y-%m', 'now')
        """
        return self.fetch_one(sql, (user_id,))

    def get_analise_mensal(self, user_id):
        sql = """
            SELECT
                SUM(CASE WHEN Valor > 0 THEN Valor ELSE 0 END) AS Receitas,
                SUM(CASE WHEN Valor < 0 THEN ABS(Valor) ELSE 0 END) AS Despesas
            FROM transacoes
            WHERE ID_Usuario = ?
              AND strftime('%Y-%m', Data) = strftime('%Y-%m', 'now')
        """

        resultado = self.fetch_one(sql, (user_id,))

        receitas = float(resultado["Receitas"] or 0)
        despesas = float(resultado["Despesas"] or 0)

        return {
            "Saldo_Atual": receitas - despesas,
            "Receitas_A_Receber": receitas,
            "DespesasAPagar": despesas,
            "BalancoParaOMes": receitas - despesas
        }
     
    def get_account_saldo(self, id_conta,id_usuario):
        return self.fetch_one("""
            SELECT Saldo_Atual
            FROM contas
            WHERE ID_Conta = ?
              AND ID_Usuario = ?
        """, (id_conta, id_usuario))
