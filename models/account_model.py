import logging
from database.database import Database, DatabaseError

logger = logging.getLogger(__name__)


class AccountModel(Database):
    """
    Modelo de persistência de contas.
    Responsável APENAS por acesso ao banco de dados.
    NÃO contém regra de negócio.
    """

    def __init__(self, db_name=None):
        super().__init__(db_name) if db_name else super().__init__()

    # --------------------------------------------------
    # CREATE
    # --------------------------------------------------
    def add_account(self, nome, instituicao, tipo, saldo, id_usuario):
        sql = """
            INSERT INTO contas (
                Nome_Conta,
                Instituicao,
                Tipo,
                Saldo_Atual,
                ID_Usuario
            )
            VALUES (?, ?, ?, ?, ?)
        """
        try:
            self.execute_query(sql, (
                nome,
                instituicao,
                tipo,
                saldo,
                id_usuario
            ))
        except Exception as e:
            logger.exception("Erro ao criar conta")
            raise DatabaseError(str(e))

    # --------------------------------------------------
    # READ
    # --------------------------------------------------
    def get_accounts_by_user(self, id_usuario):
        sql = """
            SELECT *
            FROM contas
            WHERE ID_Usuario = ?
            ORDER BY Nome_Conta
        """
        return self.fetch_all(sql, (id_usuario,))

    def get_account_by_id(self, id_conta, id_usuario):
        sql = """
            SELECT *
            FROM contas
            WHERE ID_Conta = ?
              AND ID_Usuario = ?
        """
        return self.fetch_one(sql, (id_conta, id_usuario))

    def get_account_by_name(self, nome_conta, id_usuario):
        sql = """
            SELECT *
            FROM contas
            WHERE Nome_Conta = ?
              AND ID_Usuario = ?
        """
        return self.fetch_one(sql, (nome_conta, id_usuario))

    # --------------------------------------------------
    # UPDATE (dados completos)
    # --------------------------------------------------
    def update_account(self, id_conta, nome, instituicao, tipo, saldo, id_usuario):
        sql = """
            UPDATE contas
            SET Nome_Conta = ?,
                Instituicao = ?,
                Tipo = ?,
                Saldo_Atual = ?
            WHERE ID_Conta = ?
              AND ID_Usuario = ?
        """
        try:
            self.execute_query(sql, (
                nome,
                instituicao,
                tipo,
                saldo,
                id_conta,
                id_usuario
            ))
        except Exception as e:
            logger.exception("Erro ao atualizar conta")
            raise DatabaseError(str(e))

    # --------------------------------------------------
    # UPDATE (AJUSTE DE SALDO — EXPLÍCITO)
    # --------------------------------------------------
    def update_account_balance(self, id_conta, novo_saldo):
        """
        Ajuste direto de saldo (usado por ajuste manual ou correções).
        """
        sql = """
            UPDATE contas
            SET Saldo_Atual = ?
            WHERE ID_Conta = ?
        """
        try:
            self.execute_query(sql, (novo_saldo, id_conta))
        except Exception as e:
            logger.exception("Erro ao ajustar saldo da conta")
            raise DatabaseError(str(e))

    # --------------------------------------------------
    # DELETE
    # --------------------------------------------------
    def delete_account(self, id_conta, id_usuario):
        sql = """
            DELETE FROM contas
            WHERE ID_Conta = ?
              AND ID_Usuario = ?
        """
        try:
            self.execute_query(sql, (id_conta, id_usuario))
        except Exception as e:
            logger.exception("Erro ao excluir conta")
            raise DatabaseError(str(e))



    def definir_saldo(self, id_conta, valor, id_usuario):
        sql = """
            UPDATE contas
            SET Saldo_Atual = ?
            WHERE ID_Conta = ?
              AND ID_Usuario = ?
        """
        try:
            self.execute_query(sql, (valor, id_conta, id_usuario))
        except Exception as e:
            logger.exception(f"Erro ao definir saldo da conta {id_conta} para o usuário {id_usuario}")
            raise DatabaseError(str(e))

    def update_saldo(self, id_conta, valor, id_usuario):
        sql = """
            UPDATE contas
            SET Saldo_Atual = Saldo_Atual + ?
            WHERE ID_Conta = ?
              AND ID_Usuario = ?
        """
        try:
            self.execute_query(sql, (valor, id_conta, id_usuario))
        except Exception as e:
            logger.exception(f"Erro ao atualizar saldo da conta {id_conta} para o usuário {id_usuario}")
            raise DatabaseError(str(e))
