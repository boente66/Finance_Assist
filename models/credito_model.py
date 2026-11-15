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
                    Bandeira,
                    Limite,
                    Dia_Fechamento,
                    Dia_Vencimento,
                    ID_Usuario,
                    Ativo
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dados["Nome"],
                    dados.get("Bandeira"),
                    round(float(dados["Limite"]), 2),
                    dados["Dia_Fechamento"],
                    dados["Dia_Vencimento"],
                    dados["ID_Usuario"],
                    dados.get("Ativo", 1),
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
    def get_all_cartoes(self, id_usuario: int, incluir_inativos=False):
        try:
            sql = """
                SELECT *
                FROM credito
                WHERE ID_Usuario = ? AND (? OR Ativo = 1)
                ORDER BY Nome
            """
            return self.fetch_all(sql, (id_usuario, int(bool(incluir_inativos))))
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
            atual = self.get_cartao_by_id(id_cartao, id_usuario)
            if not atual:
                return False
            # Só atualizar os campos enviados: corrigir bandeira não pode
            # arredondar/regravar limite ou substituir dados de outro editor.
            campos = ("Nome", "Bandeira", "Limite", "Dia_Fechamento",
                      "Dia_Vencimento", "Ativo")
            alterados = [campo for campo in campos if campo in dados]
            if not alterados:
                return True
            valores = [round(float(dados[campo]), 2) if campo == "Limite"
                       else dados[campo] for campo in alterados]
            assignments = ", ".join(f"{campo} = ?" for campo in alterados)
            self.execute_query(
                f"UPDATE credito SET {assignments} WHERE ID_Cartao = ? AND ID_Usuario = ?",
                (*valores, id_cartao, id_usuario),
            )
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

    def get_card_dependencies(self, id_cartao, id_usuario):
        """Inspeciona todas as FKs reais, inclusive compostas/tabelas futuras."""
        if not self.get_cartao_by_id(id_cartao, id_usuario):
            raise ValueError("Cartão não encontrado.")

        def identifier(value):
            return '"' + value.replace('"', '""') + '"'

        dependencies = []
        for table in self.fetch_all("SELECT name FROM sqlite_master WHERE type='table'"):
            groups = {}
            for fk in self.fetch_all(f"PRAGMA foreign_key_list({identifier(table['name'])})"):
                if fk['table'].casefold() == 'credito':
                    groups.setdefault(fk['id'], []).append(fk)
            for key, columns in groups.items():
                conditions = ' AND '.join(
                    f"d.{identifier(fk['from'])}=c.{identifier(fk['to'] or 'ID_Cartao')}"
                    for fk in columns
                )
                row = self.fetch_one(
                    f"SELECT COUNT(*) AS total FROM {identifier(table['name'])} d "
                    f"JOIN credito c ON {conditions} WHERE c.ID_Cartao=? AND c.ID_Usuario=?",
                    (id_cartao, id_usuario),
                )
                dependencies.append({'tabela': table['name'], 'fk': key, 'total': row['total']})
        return dependencies

    def delete_card_without_dependencies(self, id_cartao, id_usuario):
        # Defesa adicional: nunca permitir cascata por este método, mesmo
        # chamado fora do Service. Lock cobre inspeção e DELETE na mesma UoW.
        with self.unit_of_work(immediate=True):
            if any(row['total'] for row in self.get_card_dependencies(id_cartao, id_usuario)):
                raise ValueError("O cartão possui histórico ou vínculos. Inative-o para preservar os dados.")
            return self.execute_query(
                'DELETE FROM credito WHERE ID_Cartao=? AND ID_Usuario=?',
                (id_cartao, id_usuario),
            ).rowcount == 1
