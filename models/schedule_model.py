from database.database import Database
import logging

logger = logging.getLogger(__name__)


class ScheduleModel(Database):

    def __init__(self, db_name=None):
        super().__init__(db_name) if db_name else super().__init__()

    # ------------------------------------------------------------------
    # ADD
    # ------------------------------------------------------------------
    def add_schedule(self, schedule_data: dict) -> int:
        query = """
        INSERT INTO agendamentos (
            Tipo, Data, Valor, Descricao, Status,
            ID_Categoria, ID_Favorecido, ID_Conta, ID_Cartao,
            ID_Usuario, Recorrente, Periodicidade, Ativo, ID_Pai, Parcelas
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        return self.execute_insert(
            query,
            (
                schedule_data["Tipo"],
                schedule_data["Data"],
                schedule_data["Valor"],
                schedule_data.get("Descricao"),
                schedule_data.get("Status", "AGENDADO"),
                schedule_data.get("ID_Categoria"),
                schedule_data.get("ID_Favorecido"),
                schedule_data.get("ID_Conta"),
                schedule_data.get("ID_Cartao"),
                schedule_data["ID_Usuario"],
                int(schedule_data.get("Recorrente", 0)),
                schedule_data.get("Periodicidade"),
                int(schedule_data.get("Ativo", 1)),
                schedule_data.get("ID_Pai"),
                int(schedule_data.get("Parcelas", 1)),
            ),
        )

    def get_schedule_transaction(self, schedule_id: int, id_usuario: int):
        return self.fetch_one("""
            SELECT ID_Transacao, ID_Agendamento, ID_Usuario
            FROM transacoes
            WHERE ID_Agendamento = ?
              AND ID_Usuario = ?
        """, (schedule_id, id_usuario))

    # ------------------------------------------------------------------
    # SELECT TODOS
    # ------------------------------------------------------------------
    def get_all_schedules(self, id_usuario: int) -> list:
        query = """
        SELECT
            a.*,
            cat.Nome AS Categoria,
            f.Nome AS Favorecido,
            c.Nome_Conta AS Conta,
            cr.Nome AS Cartao
        FROM agendamentos a
        LEFT JOIN categorias cat
            ON a.ID_Categoria = cat.ID_Categoria
        LEFT JOIN favorecido f
            ON a.ID_Favorecido = f.ID_Favorecido
        LEFT JOIN contas c
            ON a.ID_Conta = c.ID_Conta
        LEFT JOIN credito cr
            ON a.ID_Cartao = cr.ID_Cartao
        WHERE a.ID_Usuario = ?
        ORDER BY date(a.Data), a.ID_Agendamento
        """

        try:
            return self.fetch_all(query, (id_usuario,))
        except Exception as e:
            logger.error(
                "Erro ao carregar agendamentos do usuário %s: %s",
                id_usuario,
                e,
                exc_info=True,
            )
            return []

    # ------------------------------------------------------------------
    # SELECT PRÓXIMOS
    # ------------------------------------------------------------------
    def get_upcoming_schedules(self, id_usuario: int) -> list:
        query = """
        SELECT
            a.ID_Agendamento,
            a.Data,
            a.Valor,
            a.Descricao,
            a.Status
        FROM agendamentos a
        WHERE a.ID_Usuario = ?
          AND a.Status IN ('AGENDADO', 'ATRASADO')
          AND date(a.Data) >= date('now')
        ORDER BY date(a.Data), a.ID_Agendamento
        LIMIT 5
        """

        try:
            return self.fetch_all(query, (id_usuario,))
        except Exception as e:
            logger.error(
                "Erro ao obter próximos agendamentos do usuário %s: %s",
                id_usuario,
                e,
                exc_info=True,
            )
            return []

    # ------------------------------------------------------------------
    # SELECT POR ID
    # ------------------------------------------------------------------
    def get_schedule_by_id(self, schedule_id: int, id_usuario: int) -> dict | None:
        query = """
        SELECT
            a.*,
            cat.Nome AS Categoria,
            f.Nome AS Favorecido,
            c.Nome_Conta AS Conta,
            cr.Nome AS Cartao
        FROM agendamentos a
        LEFT JOIN categorias cat
            ON a.ID_Categoria = cat.ID_Categoria
        LEFT JOIN favorecido f
            ON a.ID_Favorecido = f.ID_Favorecido
        LEFT JOIN contas c
            ON a.ID_Conta = c.ID_Conta
        LEFT JOIN credito cr
            ON a.ID_Cartao = cr.ID_Cartao
        WHERE a.ID_Agendamento = ?
          AND a.ID_Usuario = ?
        """

        try:
            return self.fetch_one(query, (schedule_id, id_usuario))
        except Exception as e:
            logger.error(
                "Erro ao buscar agendamento %s do usuário %s: %s",
                schedule_id,
                id_usuario,
                e,
                exc_info=True,
            )
            return None

    def get_schedule_owner(self, schedule_id: int):
        return self.fetch_one("""
            SELECT ID_Usuario
            FROM agendamentos
            WHERE ID_Agendamento = ?
        """, (schedule_id,))

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------
    def update_schedule(
        self,
        schedule_id: int,
        id_usuario: int,
        schedule_data: dict
    ) -> None:
        query = """
        UPDATE agendamentos
        SET Tipo = ?,
            Data = ?,
            Valor = ?,
            Descricao = ?,
            ID_Categoria = ?,
            ID_Favorecido = ?,
            ID_Conta = ?,
            ID_Cartao = ?,
            Recorrente = ?,
            Periodicidade = ?,
            Ativo = ?,
            Parcelas = ?
        WHERE ID_Agendamento = ?
          AND ID_Usuario = ?
        """

        self.execute_query(
            query,
            (
                schedule_data["Tipo"],
                schedule_data["Data"],
                schedule_data["Valor"],
                schedule_data.get("Descricao"),
                schedule_data.get("ID_Categoria"),
                schedule_data.get("ID_Favorecido"),
                schedule_data.get("ID_Conta"),
                schedule_data.get("ID_Cartao"),
                int(schedule_data.get("Recorrente", 0)),
                schedule_data.get("Periodicidade"),
                int(schedule_data.get("Ativo", 1)),
                int(schedule_data.get("Parcelas", 1)),
                schedule_id,
                id_usuario,
            ),
        )

    # ------------------------------------------------------------------
    # UPDATE STATUS
    # ------------------------------------------------------------------
    def update_status(self, schedule_id: int, id_usuario: int, status: str) -> None:
        query = """
        UPDATE agendamentos
        SET Status = ?
        WHERE ID_Agendamento = ?
          AND ID_Usuario = ?
        """

        cursor = self.execute_query(query, (status, schedule_id, id_usuario))
        return cursor.rowcount

    def mark_executed(self, schedule_id: int, id_usuario: int) -> None:
        cursor = self.execute_query("""
            UPDATE agendamentos
            SET Status = 'EXECUTADO'
            WHERE ID_Agendamento = ?
              AND ID_Usuario = ?
              AND Status IN ('AGENDADO', 'ATRASADO')
        """, (schedule_id, id_usuario))

        if cursor.rowcount != 1:
            raise ValueError(
                "Agendamento não está disponível para execução."
            )

    # ------------------------------------------------------------------
    # CANCELAR
    # ------------------------------------------------------------------
    def cancel_schedule(self, schedule_id: int, id_usuario: int) -> None:
        query = """
        UPDATE agendamentos
        SET Status = 'CANCELADO'
        WHERE ID_Agendamento = ?
          AND ID_Usuario = ?
        """

        self.execute_query(query, (schedule_id, id_usuario))

    # ------------------------------------------------------------------
    # MARCAR ATRASADOS
    # ------------------------------------------------------------------
    def mark_as_overdue(self, id_usuario: int, data_hoje: str) -> None:
        query = """
        UPDATE agendamentos
        SET Status = 'ATRASADO'
        WHERE ID_Usuario = ?
          AND Status = 'AGENDADO'
          AND date(Data) < date(?)
        """

        self.execute_query(query, (id_usuario, data_hoje))

    # ------------------------------------------------------------------
    # INATIVAR
    # ------------------------------------------------------------------
    def set_inactive(self, schedule_id: int, id_usuario: int) -> None:
        query = """
        UPDATE agendamentos
        SET Ativo = 0,
            Status = 'INATIVO'
        WHERE ID_Agendamento = ?
          AND ID_Usuario = ?
        """

        self.execute_query(query, (schedule_id, id_usuario))

    # ------------------------------------------------------------------
    # AGENDAMENTOS ATIVOS POR CONTA
    # ------------------------------------------------------------------
    def get_agendamentos_ativos_por_conta(self, id_conta, id_usuario) -> list:
        query = """
        SELECT Tipo, Valor
        FROM agendamentos
        WHERE ID_Conta = ?
          AND ID_Usuario = ?
          AND Ativo = 1
          AND Status IN ('AGENDADO', 'ATRASADO')
        """

        try:
            return self.fetch_all(query, (id_conta, id_usuario))
        except Exception as e:
            logger.error(
                "Erro ao buscar agendamentos da conta: %s",
                e,
                exc_info=True,
            )
            return []
