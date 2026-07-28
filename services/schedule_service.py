# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from dateutil.relativedelta import relativedelta

from models.schedule_model import ScheduleModel
from models.account_model import AccountModel

from services.fatura_service import FaturaService

logger = logging.getLogger(__name__)


class ScheduleService:
    """
    Serviço responsável pelas regras de negócio de agendamentos.

    Responsabilidades:
    - criar agendamentos
    - editar agendamentos
    - cancelar agendamentos
    - listar agendamentos
    - marcar agendamento como executado
    - gerar recorrência
    - gerar previsão de cartão
    - calcular saldo previsto

    Observação:
    A execução financeira da baixa pertence ao PaymentService.
    """

    TIPOS_CARTAO = ("Cartao", "Cartão")

    MAPA_TIPO_TRANSACAO = {
        "Contas a Receber": "Receita",
        "Contas a Pagar": "Despesa",
        "Transferências": "Transferência",
    }

    STATUS_EXECUTAVEIS = ("AGENDADO", "ATRASADO")
    STATUS_CANCELAVEIS = ("AGENDADO", "ATRASADO")

    def __init__(self, db_name=None):
        self.schedule_model = ScheduleModel(db_name)
        self.account_model = AccountModel(db_name)
        self.fatura_service = FaturaService(db_name)

    # ============================================================
    # CRIAÇÃO
    # ============================================================
    def add_schedule(self, schedule_data: dict) -> bool:
        try:
            if not schedule_data:
                raise ValueError("schedule_data não pode ser vazio.")

            if "ID_Usuario" not in schedule_data:
                raise ValueError("ID_Usuario é obrigatório.")

            schedule_data.setdefault("Recorrente", 0)
            schedule_data.setdefault("Periodicidade", None)
            schedule_data.setdefault("Ativo", 1)
            schedule_data.setdefault("Status", "AGENDADO")
            schedule_data.setdefault("Parcelas", 1)

            self.schedule_model.add_schedule(schedule_data)

            if schedule_data.get("Tipo") in self.TIPOS_CARTAO:
                self._gerar_previsto_cartao(schedule_data)

            return True

        except Exception:
            logger.exception("Erro ao adicionar agendamento")
            return False

    # ============================================================
    # EXECUÇÃO / STATUS
    # ============================================================
    def executar_agendamento(self, schedule_id: int, id_usuario: int) -> bool:
        """
        Marca o agendamento como EXECUTADO.

        A execução financeira pertence ao PaymentService.

        Este método apenas:
        - valida o agendamento
        - marca como EXECUTADO
        - gera recorrência, se existir
        - gera previsão futura de cartão, se necessário
        """

        try:
            ag = self.schedule_model.get_schedule_by_id(
                schedule_id,
                id_usuario
            )

            if not ag:
                raise ValueError("Agendamento não encontrado.")

            if ag.get("Status") not in self.STATUS_EXECUTAVEIS:
                raise ValueError(
                    "Somente agendamentos AGENDADOS ou ATRASADOS podem ser executados."
                )

            self.schedule_model.update_status(
                schedule_id,
                id_usuario,
                "EXECUTADO"
            )

            if ag.get("Recorrente"):
                novo = self._criar_proximo_agendamento(ag)

                if novo and novo.get("Tipo") in self.TIPOS_CARTAO:
                    self._gerar_previsto_cartao(novo)

            return True

        except Exception:
            logger.exception("Erro ao executar agendamento")
            return False

    # ============================================================
    # RECORRÊNCIA
    # ============================================================
    def _criar_proximo_agendamento(self, agendamento: dict):
        nova_data = self._calcular_proxima_data(
            agendamento["Data"],
            agendamento.get("Periodicidade")
        )

        novo = {
            **agendamento,
            "Data": nova_data,
            "Status": "AGENDADO",
            "ID_Pai": (
                agendamento.get("ID_Pai")
                or agendamento["ID_Agendamento"]
            ),
        }

        novo.pop("ID_Agendamento", None)

        novo["ID_Agendamento"] = self.schedule_model.add_schedule(novo)

        return novo

    # ============================================================
    # CONSULTAS
    # ============================================================
    def get_schedule_by_id(self, schedule_id: int, id_usuario: int):
        return self.schedule_model.get_schedule_by_id(
            schedule_id,
            id_usuario
        )

    def get_upcoming_schedules(self, user_id: int):
        try:
            return self.schedule_model.get_upcoming_schedules(user_id)

        except Exception:
            logger.exception("Erro ao obter próximos agendamentos")
            return []

    def get_all_schedules(self, user_id: int):
        try:
            return self.schedule_model.get_all_schedules(user_id)

        except Exception:
            logger.exception("Erro ao obter todos os agendamentos")
            return []

    # ============================================================
    # ATUALIZAÇÃO
    # ============================================================
    def update_schedule(self, schedule_id: int, schedule_data: dict) -> bool:
        try:
            id_usuario = schedule_data.get("ID_Usuario")

            if not id_usuario:
                raise ValueError("ID_Usuario é obrigatório.")

            atual = self.schedule_model.get_schedule_by_id(
                schedule_id,
                id_usuario
            )

            if not atual:
                raise ValueError("Agendamento não encontrado.")

            self.schedule_model.update_schedule(
                schedule_id,
                id_usuario,
                schedule_data
            )

            return True

        except Exception:
            logger.exception("Erro ao atualizar agendamento")
            return False

    # ============================================================
    # CARTÃO / FATURA PREVISTA
    # ============================================================
    def _gerar_previsto_cartao(self, agendamento: dict):
        try:
            cartao_id = agendamento.get("ID_Cartao")
            id_usuario = agendamento.get("ID_Usuario")

            if not cartao_id:
                return

            cartao = self.fatura_service.buscar_cartao_por_id(
                cartao_id,
                id_usuario
            )

            if not cartao:
                return

            dia_fechamento = cartao["Dia_Fechamento"]
            data = agendamento["Data"]

            mes, ano = self.fatura_service.aplicar_fatura(
                data,
                dia_fechamento
            )

            self.fatura_service.registrar_despesa_cartao(
                {
                    "Descricao": agendamento.get("Descricao"),
                    "Valor": agendamento.get("Valor"),
                    "Data": data,
                    "ID_Cartao": cartao_id,
                    "ID_Usuario": id_usuario,
                    "Num_Parcelas": int(agendamento.get("Parcelas", 1)),
                    "ID_Categoria": agendamento.get("ID_Categoria"),
                    "ID_Favorecido": agendamento.get("ID_Favorecido"),
                    "Previsto": 1,
                    "Competencia_Mes": mes,
                    "Competencia_Ano": ano,
                }
            )

        except Exception:
            logger.exception("Erro ao gerar lançamento previsto do cartão")

    # ============================================================
    # CANCELAMENTO
    # ============================================================
    def cancel_schedule(self, schedule_id: int, id_usuario: int) -> bool:
        try:
            ag = self.schedule_model.get_schedule_by_id(
                schedule_id,
                id_usuario
            )

            if not ag:
                raise ValueError("Agendamento não encontrado.")

            if ag.get("Status") not in self.STATUS_CANCELAVEIS:
                raise PermissionError(
                    "Somente agendamentos AGENDADOS ou ATRASADOS podem ser cancelados."
                )

            self.schedule_model.cancel_schedule(
                schedule_id,
                id_usuario
            )

            return True

        except Exception:
            logger.exception(
                "Erro ao cancelar agendamento %s",
                schedule_id
            )
            return False

    # ============================================================
    # SALDO PREVISTO
    # ============================================================
    def calcular_saldo_previsto_conta(
        self,
        id_conta: int,
        id_usuario: int
    ) -> float:
        try:
            conta = self.account_model.get_account_by_id(
                id_conta,
                id_usuario
            )

            if not conta:
                raise ValueError("Conta não encontrada.")

            saldo_atual = float(conta.get("Saldo_Atual", 0))

            agendamentos = (
                self.schedule_model
                .get_agendamentos_ativos_por_conta(
                    id_conta,
                    id_usuario
                )
            )

            total_pagar = 0.0
            total_receber = 0.0

            for ag in agendamentos:
                valor = float(ag.get("Valor", 0))

                if ag.get("Tipo") == "Contas a Pagar":
                    total_pagar += valor

                elif ag.get("Tipo") == "Contas a Receber":
                    total_receber += valor

            return saldo_atual - total_pagar + total_receber

        except Exception:
            logger.exception(
                "Erro ao calcular saldo previsto da conta %s",
                id_conta
            )
            return 0.0

    # ============================================================
    # DATA
    # ============================================================
    def _calcular_proxima_data(self, data_str, periodicidade):
        data = datetime.strptime(data_str, "%Y-%m-%d")

        if periodicidade == "Mensal":
            nova = data + relativedelta(months=1)

        elif periodicidade == "Anual":
            nova = data + relativedelta(years=1)

        else:
            nova = data

        return nova.strftime("%Y-%m-%d")
