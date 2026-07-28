import logging
from database.database import Database, DatabaseError

logger = logging.getLogger(__name__)


class CreditoModel(Database):
    """
    Modelo para gerenciamento de cartões de crédito.
    - CRUD completo
    - Soft delete
    - Filtragem por usuário
    """

    def __init__(self, db_name=None):
        super().__init__(db_name) if db_name else super().__init__()

    # ============================================================
    # CREATE
    # ============================================================
    def add_cartao(self, dados: dict):
        try:
            cartao_id = self.execute_insert(
                """
                INSERT INTO credito (
                    Nome,
                    Limite,
                    Dia_Fechamento,
                    Dia_Vencimento,
                    ID_Usuario
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    dados["Nome"],
                    round(float(dados["Limite"]), 2),
                    dados["Dia_Fechamento"],
                    dados["Dia_Vencimento"],
                    dados["ID_Usuario"],
                ),
            )

            if not cartao_id:
                raise DatabaseError("Falha ao obter ID do cartão inserido.")

            cartao = self.fetch_one(
                "SELECT * FROM credito WHERE ID_Cartao = ?",
                (cartao_id,)
            )

            if not cartao:
                raise DatabaseError("Cartão inserido, mas não foi possível recuperá-lo.")

            return cartao

        except Exception as e:
            raise DatabaseError(f"Erro ao criar cartão: {e}")

    # ============================================================
    # READ
    # ============================================================
    def get_all_cartoes(self, id_usuario: int):
        try:
            sql = """
                SELECT *
                FROM credito
                WHERE Ativo = 1 AND ID_Usuario = ?
                ORDER BY Nome
            """
            return self.fetch_all(sql, (id_usuario,))
        except Exception as e:
            logger.error(f"Erro ao listar cartões: {e}")
            return []

    def get_inactive_cartoes(self, id_usuario: int):
        try:
            sql = """
                SELECT *
                FROM credito
                WHERE Ativo = 0 AND ID_Usuario = ?
                ORDER BY Nome
            """
            return self.fetch_all(sql, (id_usuario,))
        except Exception as e:
            logger.error(f"Erro ao listar cartões inativos: {e}")
            return []

    def get_cartao_by_id(self, id_cartao: int, id_usuario: int):
        try:
            sql = """
                SELECT *
                FROM credito
                WHERE ID_Cartao = ? AND ID_Usuario = ?
            """
            return self.fetch_one(sql, (id_cartao, id_usuario))
        except Exception as e:
            logger.error(f"Erro ao buscar cartão: {e}")
            return None

    # ============================================================
    # UPDATE
    # ============================================================
    def update_cartao(self, id_cartao: int, dados: dict, id_usuario: int):
        try:
            sql = """
                UPDATE credito
                SET
                    Nome = ?,
                    Limite = ?,
                    Dia_Fechamento = ?,
                    Dia_Vencimento = ?,
                    Ativo = ?
                WHERE ID_Cartao = ? AND ID_Usuario = ?
            """

            params = (
                dados.get("Nome"),
                round(float(dados.get("Limite", 0)), 2),
                dados.get("Dia_Fechamento"),
                dados.get("Dia_Vencimento"),
                dados.get("Ativo", 1),
                id_cartao,
                id_usuario,
            )

            self.execute_query(sql, params)
            return True

        except Exception as e:
            logger.error(f"Erro ao atualizar cartão: {e}")
            return False

    # ============================================================
    # SOFT DELETE / RESTAURAÇÃO
    # ============================================================
    def _set_ativo(self, id_cartao: int, id_usuario: int, ativo: int):
        try:
            sql = """
                UPDATE credito
                SET Ativo = ?
                WHERE ID_Cartao = ? AND ID_Usuario = ?
            """
            self.execute_query(sql, (ativo, id_cartao, id_usuario))
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar status do cartão: {e}")
            return False

    def delete_cartao(self, id_cartao: int, id_usuario: int):
        return self._set_ativo(id_cartao, id_usuario, 0)

    def restore_cartao(self, id_cartao: int, id_usuario: int):
        return self._set_ativo(id_cartao, id_usuario, 1)
