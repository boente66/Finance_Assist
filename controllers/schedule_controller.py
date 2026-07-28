import logging
from services.schedule_service import ScheduleService
from core.session import Session
from core.translator_app import TranslatorApp
from services.payment_service import PaymentService

logger = logging.getLogger(__name__)


class ScheduleController:
    """
    Controller de Agendamentos.

    Responsável por:
    - Validar sessão
    - Encaminhar dados ao Service
    - Padronizar erros
    """

    def __init__(self):
        self.schedule_service = ScheduleService()
        self.payment_service = PaymentService()

    # ============================================================
    # 🔥 UTIL
    # ============================================================
    def _get_usuario_id(self) -> int:
        usuario = Session.get_usuario()

        if not usuario:
            raise PermissionError(
                TranslatorApp.get("Usuário não autenticado")
            )

        return usuario["ID_Usuario"]

    # ============================================================
    # CRIAR AGENDAMENTO
    # ============================================================
    def add_schedule(self, schedule_data: dict) -> bool:
        try:
            user_id = self._get_usuario_id()

            schedule_data["ID_Usuario"] = user_id

            return self.schedule_service.add_schedule(schedule_data)

        except Exception:
            logger.exception("Erro ao criar agendamento")
            raise

    # ============================================================
    # PRÓXIMOS AGENDAMENTOS
    # ============================================================
    def get_upcoming_schedules(self) -> list:
        try:
            user_id = self._get_usuario_id()

            return self.schedule_service.get_upcoming_schedules(user_id)

        except Exception:
            logger.exception("Erro ao buscar próximos agendamentos")
            return []

    # ============================================================
    # ATUALIZAR
    # ============================================================
    def update_schedule(self, schedule_id: int, schedule_data: dict) -> bool:
        try:
            user_id = self._get_usuario_id()

            schedule_data["ID_Usuario"] = user_id

            return self.schedule_service.update_schedule(
                schedule_id,
                schedule_data
            )

        except Exception:
            logger.exception("Erro ao atualizar agendamento")
            return False

    # ============================================================
    # BUSCAR POR ID
    # ============================================================
    def get_schedule_by_id(self, schedule_id: int):
        try:
            user_id = self._get_usuario_id()

            return self.schedule_service.get_schedule_by_id(
                schedule_id,
                user_id
            )

        except Exception:
            logger.exception("Erro ao buscar agendamento")
            return None

    # ============================================================
    # BUSCAR TODOS
    # ============================================================
    def get_all_schedules(self) -> list:
        try:
            user_id = self._get_usuario_id()

            return self.schedule_service.get_all_schedules(user_id)

        except Exception:
            logger.exception("Erro ao listar agendamentos")
            return []

    # ============================================================
    # CANCELAR
    # ============================================================
    def cancel_schedule(self, schedule_id: int) -> bool:
        try:
            user_id = self._get_usuario_id()

            return self.schedule_service.cancel_schedule(
                schedule_id,
                user_id
            )

        except Exception:
            logger.exception("Erro ao cancelar agendamento")
            return False

    def cancelar_agendamento(self, schedule_id: int) -> bool:
        return self.cancel_schedule(schedule_id)
    
        # ============================================================
    # BAIXAR / EXECUTAR AGENDAMENTO
    # ============================================================
    def execute_schedule(self, dados_execucao: dict) -> dict:
        """
        Executa a baixa de um agendamento.

        Fluxo:
        Dialog
            ↓
        ScheduleController
            ↓
        PaymentService
            ↓
        TransactionService
            ↓
        ScheduleService
        """

        try:
            user_id = self._get_usuario_id()

            return self.payment_service.baixar_agendamento(
                dados_execucao,
                user_id
            )

        except Exception:
            logger.exception("Erro ao executar agendamento")
            raise


    
