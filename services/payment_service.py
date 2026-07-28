# -*- coding: utf-8 -*-
import logging

from core.operation_result import operation_result
from database.database import DatabaseError
from services.transaction_service import TransactionService
from services.schedule_service import ScheduleService

logger = logging.getLogger(__name__)


class PaymentService:
    """Baixa atômica e idempotente de agendamentos."""

    TIPO_PAGAR = "Contas a Pagar"
    TIPO_RECEBER = "Contas a Receber"
    TIPO_TRANSFERENCIA = "Transferências"
    STATUS_PERMITIDOS = ("AGENDADO", "ATRASADO")

    def __init__(self, db_name=None):
        self.transaction_service = TransactionService(db_name)
        self.schedule_service = ScheduleService(db_name)

    def baixar_agendamento(self, dados_execucao: dict, id_usuario: int):
        try:
            if not dados_execucao:
                raise ValueError("Dados da baixa não informados.")

            if not id_usuario:
                raise PermissionError("Usuário não informado.")

            id_agendamento = dados_execucao.get("ID_Agendamento")
            if not id_agendamento:
                raise ValueError("ID_Agendamento é obrigatório.")

            transaction_model = self.transaction_service.transaction_model
            account_model = self.transaction_service.account_model
            schedule_model = self.schedule_service.schedule_model

            with transaction_model.unit_of_work(
                account_model,
                schedule_model,
                immediate=True
            ):
                agendamento = schedule_model.get_schedule_by_id(
                    id_agendamento,
                    id_usuario
                )

                if not agendamento:
                    owner = schedule_model.get_schedule_owner(id_agendamento)
                    if owner:
                        raise PermissionError(
                            "Agendamento não pertence ao usuário."
                        )
                    raise LookupError("Agendamento não encontrado.")

                existente = transaction_model.get_transaction_by_schedule(
                    id_agendamento,
                    id_usuario
                )

                if existente:
                    return operation_result(
                        False,
                        "JA_PROCESSADO",
                        "Este agendamento já foi processado.",
                        {"ID_Transacao": existente["ID_Transacao"]}
                    )

                self._validar_agendamento(agendamento)

                valor_final = self._calcular_valor_final(dados_execucao)
                tipo_transacao = self._tipo_transacao(agendamento)
                valor_transacao = (
                    abs(valor_final)
                    if tipo_transacao == "Receita"
                    else -abs(valor_final)
                )

                transacao = {
                    "ID_Conta": dados_execucao.get("ID_Conta"),
                    "Descricao": (
                        dados_execucao.get("Descricao")
                        or agendamento.get("Descricao")
                        or "Baixa de agendamento"
                    ),
                    "Valor": valor_transacao,
                    "Data": dados_execucao.get("Data"),
                    "Tipo": tipo_transacao,
                    "ID_Usuario": id_usuario,
                    "ID_Agendamento": id_agendamento,
                    "ID_Categoria": (
                        dados_execucao.get("ID_Categoria")
                        or agendamento.get("ID_Categoria")
                    ),
                    "ID_Favorecido": (
                        dados_execucao.get("ID_Favorecido")
                        or agendamento.get("ID_Favorecido")
                    ),
                    "Notas": self._montar_notas(
                        dados_execucao,
                        valor_final
                    ),
                }

                self._validar_transacao(transacao)
                self.transaction_service._criar_transacao_base(
                    transacao,
                    validar_saldo=True
                )

                criada = transaction_model.get_transaction_by_schedule(
                    id_agendamento,
                    id_usuario
                )
                if not criada:
                    raise RuntimeError(
                        "A transação da baixa não pôde ser vinculada."
                    )

                schedule_model.mark_executed(id_agendamento, id_usuario)

                proximo_id = None
                if agendamento.get("Recorrente"):
                    novo = self.schedule_service._criar_proximo_agendamento(
                        agendamento
                    )
                    proximo_id = novo.get("ID_Agendamento") if novo else None

            return operation_result(
                True,
                "OK",
                "Agendamento executado com sucesso.",
                {
                    "ID_Agendamento": id_agendamento,
                    "ID_Transacao": criada["ID_Transacao"],
                    "ID_Proximo_Agendamento": proximo_id,
                }
            )

        except PermissionError as exc:
            logger.warning("Baixa de agendamento não autorizada: %s", exc)
            return operation_result(False, "NAO_AUTORIZADO", str(exc))

        except LookupError as exc:
            return operation_result(False, "NAO_ENCONTRADO", str(exc))

        except (TypeError, ValueError) as exc:
            codigo = (
                "CONFLITO"
                if "status" in str(exc).lower()
                or "disponível" in str(exc).lower()
                else "DADOS_INVALIDOS"
            )
            logger.warning("Baixa de agendamento recusada: %s", exc)
            return operation_result(False, codigo, str(exc))

        except DatabaseError:
            logger.exception("Erro de banco na baixa de agendamento")
            return operation_result(
                False,
                "ERRO_BANCO",
                "Não foi possível executar o agendamento."
            )

        except Exception:
            logger.exception("Erro na baixa de agendamento")
            return operation_result(
                False,
                "ERRO_INTERNO",
                "Não foi possível executar o agendamento."
            )

    def _validar_agendamento(self, agendamento: dict):
        tipo = agendamento.get("Tipo")
        status = agendamento.get("Status")

        if tipo == self.TIPO_TRANSFERENCIA:
            raise ValueError(
                "Transferência deve ser baixada pelo fluxo de transferência."
            )

        if tipo not in (self.TIPO_PAGAR, self.TIPO_RECEBER):
            raise ValueError(f"Tipo de agendamento inválido: {tipo}")

        if status not in self.STATUS_PERMITIDOS:
            raise ValueError(
                f"Agendamento com status '{status}' não está disponível."
            )

    def _validar_transacao(self, transacao: dict):
        if not transacao.get("ID_Conta"):
            raise ValueError("Conta obrigatória.")
        if not transacao.get("Data"):
            raise ValueError("Data obrigatória.")
        if not transacao.get("Descricao"):
            raise ValueError("Descrição obrigatória.")
        if float(transacao.get("Valor", 0)) == 0:
            raise ValueError("Valor inválido.")

    def _calcular_valor_final(self, dados_execucao: dict) -> float:
        valor_previsto = float(dados_execucao.get("Valor_Previsto", 0))
        desconto = float(dados_execucao.get("Desconto", 0))
        multa = float(dados_execucao.get("Multa", 0))
        juros = float(dados_execucao.get("Juros", 0))
        valor_final = valor_previsto + multa + juros - desconto

        if valor_final <= 0:
            raise ValueError("Valor final inválido.")
        return valor_final

    def _tipo_transacao(self, agendamento: dict) -> str:
        if agendamento.get("Tipo") == self.TIPO_RECEBER:
            return "Receita"
        if agendamento.get("Tipo") == self.TIPO_PAGAR:
            return "Despesa"
        raise ValueError("Tipo de agendamento inválido.")

    def _montar_notas(self, dados_execucao: dict, valor_final: float) -> str:
        partes = []
        if dados_execucao.get("Notas"):
            partes.append(dados_execucao["Notas"])
        partes.extend([
            "Baixa de agendamento:",
            f"Valor previsto: {dados_execucao.get('Valor_Previsto', 0)}",
            f"Desconto: {dados_execucao.get('Desconto', 0)}",
            f"Multa: {dados_execucao.get('Multa', 0)}",
            f"Juros: {dados_execucao.get('Juros', 0)}",
            f"Valor final: {valor_final}",
        ])
        return "\n".join(partes)
