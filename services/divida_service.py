"""Regras de negócio de dívidas, parcelas e pagamentos."""

import hashlib
import uuid
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from dateutil.relativedelta import relativedelta

from models.account_model import AccountModel
from models.divida_model import DividaModel
from models.divida_parcela_model import DividaParcelaModel
from models.pagamento_divida_model import PagamentoDividaModel
from models.favorecido_model import FavorecidoModel
from models.schedule_model import ScheduleModel
from models.transaction_model import TransactionModel


class DividaService:
    CENT = Decimal("0.01")
    TIPOS = {
        "Empréstimo bancário", "Financiamento", "Carnê/crediário",
        "Dívida com pessoa", "Renegociação", "Parcelamento informal", "Outro",
    }

    def __init__(self, db_name=None):
        self.model = DividaModel(db_name)
        self.installments = DividaParcelaModel(db_name)
        self.payments = PagamentoDividaModel(db_name)
        self.accounts = AccountModel(db_name)
        self.payees = FavorecidoModel(db_name)
        self.schedules = ScheduleModel(db_name)
        self.transactions = TransactionModel(db_name)

    @classmethod
    def _money(cls, value):
        return Decimal(str(value or 0)).quantize(cls.CENT, ROUND_HALF_UP)

    @staticmethod
    def _date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return datetime.fromisoformat(str(value)).date()

    def criar(self, dados, id_usuario):
        dados = dict(dados or {})
        descricao = str(dados.get("Descricao") or "").strip()
        tipo = str(dados.get("Tipo_Divida") or "Outro").strip()
        parcelamento = str(dados.get("Tipo_Parcelamento") or "FIXO").upper()
        emprestado = self._money(dados.get("Valor_Emprestado"))
        total = self._money(dados.get("Valor_Total_Contrato") or emprestado)
        if not descricao:
            raise ValueError("Informe a descrição da dívida.")
        if tipo not in self.TIPOS:
            raise ValueError("Tipo de dívida inválido.")
        if parcelamento not in {"FIXO", "LIVRE"}:
            raise ValueError("Tipo de parcelamento inválido.")
        if emprestado <= 0 or total <= 0 or total < emprestado:
            raise ValueError("Os valores do contrato são inválidos.")
        favorecido = dados.get("ID_Favorecido")
        if favorecido and not self.payees.get_favorecido_by_id(
            favorecido, id_usuario
        ):
            raise PermissionError("Favorecido não pertence ao usuário.")

        quantidade = int(dados.get("Quantidade_Parcelas") or 0)
        primeiro = dados.get("Primeiro_Vencimento")
        if parcelamento == "FIXO" and (quantidade < 1 or not primeiro):
            raise ValueError("Informe parcelas e primeiro vencimento.")
        if parcelamento == "LIVRE":
            quantidade, primeiro = 0, None

        payload = {
            **dados,
            "ID_Usuario": id_usuario,
            "Descricao": descricao,
            "Tipo_Divida": tipo,
            "Tipo_Parcelamento": parcelamento,
            "Valor_Emprestado": float(emprestado),
            "Valor_Total_Contrato": float(total),
            "Saldo_Devedor": float(total),
            "Quantidade_Parcelas": quantidade or None,
            "Valor_Parcela": None,
            "Data_Contratacao": self._date(
                dados.get("Data_Contratacao") or date.today()
            ).isoformat(),
            "Primeiro_Vencimento": (
                self._date(primeiro).isoformat() if primeiro else None
            ),
        }

        with self.model.unit_of_work(
            self.installments, self.schedules, self.payees, immediate=True
        ):
            debt_id = self.model.add(payload)
            if parcelamento == "FIXO":
                cents, remainder = divmod(int(total * 100), quantidade)
                values = [
                    Decimal(cents + (1 if i >= quantidade - remainder else 0)) / 100
                    for i in range(quantidade)
                ]
                first_due = self._date(primeiro)
                for index, value in enumerate(values, 1):
                    due = first_due + relativedelta(months=index - 1)
                    installment_id = self.installments.add({
                        "ID_Divida": debt_id,
                        "Numero_Parcela": index,
                        "Data_Vencimento": due.isoformat(),
                        "Valor_Previsto": float(value),
                    })
                    schedule_id = self.schedules.add_schedule({
                        "Tipo": "Contas a Pagar",
                        "Data": due.isoformat(),
                        "Valor": float(value),
                        "Descricao": f"Dívida: {descricao} ({index}/{quantidade})",
                        "Status": "AGENDADO",
                        "ID_Favorecido": favorecido,
                        "ID_Usuario": id_usuario,
                    })
                    self.schedules.link_debt_installment(
                        schedule_id, debt_id, installment_id, id_usuario
                    )
                self.model.update_installment_value(debt_id, float(values[0]))
        return debt_id

    def listar(self, id_usuario, status=None):
        self.atualizar_atrasos(id_usuario)
        return self.model.get_all(id_usuario, status)

    def obter(self, id_divida, id_usuario):
        debt = self.model.get_by_id(id_divida, id_usuario)
        if not debt:
            raise ValueError("Dívida não encontrada.")
        return {
            **debt,
            "Parcelas": self.installments.get_all(id_divida, id_usuario),
            "Pagamentos": self.payments.get_all(id_divida, id_usuario),
        }

    def registrar_pagamento(self, dados, id_usuario):
        dados = dict(dados or {})
        debt = self.model.get_by_id(dados.get("ID_Divida"), id_usuario)
        if not debt or debt["Status"] in {"QUITADA", "CANCELADA"}:
            raise ValueError("Dívida não está disponível para pagamento.")
        account = self.accounts.get_account_by_id(dados.get("ID_Conta"), id_usuario)
        if not account:
            raise PermissionError("Conta não pertence ao usuário.")
        paid = self._money(dados.get("Valor_Pago"))
        interest = self._money(dados.get("Valor_Juros"))
        fine = self._money(dados.get("Valor_Multa"))
        discount = self._money(dados.get("Valor_Desconto"))
        amortized = paid - interest - fine + discount
        if paid <= 0 or min(interest, fine, discount) < 0 or amortized <= 0:
            raise ValueError("Composição do pagamento inválida.")
        balance = self._money(debt["Saldo_Devedor"])
        amortized = min(amortized, balance)
        if self._money(account["Saldo_Atual"]) < paid:
            raise ValueError("Saldo insuficiente.")
        installment_id = dados.get("ID_Parcela")
        installment = None
        if installment_id:
            installment = self.installments.get_by_id(
                installment_id, debt["ID_Divida"], id_usuario
            )
            if not installment:
                raise ValueError("Parcela não pertence à dívida.")
            pending = self._money(installment["Valor_Previsto"]) - self._money(
                installment["Valor_Pago"]
            )
            if amortized > pending:
                raise ValueError("Pagamento excede o saldo da parcela.")
            if not dados.get("ID_Agendamento"):
                linked_schedule = self.schedules.get_by_debt_installment(
                    debt["ID_Divida"], installment_id, id_usuario
                )
                if linked_schedule:
                    dados["ID_Agendamento"] = linked_schedule["ID_Agendamento"]
        payment_date = self._date(
            dados.get("Data_Pagamento") or date.today()
        ).isoformat()
        # Repetições automáticas precisam da chave estável fornecida pelo
        # agendamento. Pagamentos manuais iguais são operações financeiras
        # distintas e, portanto, recebem uma chave própria.
        key_base = dados.get("Chave_Idempotencia") or f"manual:{uuid.uuid4().hex}"
        key = hashlib.sha256(str(key_base).encode()).hexdigest()

        participants = [
            self.installments, self.payments, self.accounts,
            self.transactions,
        ]
        if dados.get("ID_Agendamento"):
            participants.append(self.schedules)
        with self.model.unit_of_work(*participants, immediate=True):
            existing = self.payments.get_by_key(key, id_usuario)
            if existing:
                return existing["ID_Pagamento"]
            transaction_id = self.transactions.add_transaction({
                "ID_Conta": account["ID_Conta"],
                "Descricao": f"Pagamento de dívida - {debt['Descricao']}",
                "Valor": -float(paid),
                "Data": payment_date,
                "Tipo": "Despesa",
                "ID_Favorecido": debt.get("ID_Favorecido"),
                "ID_Usuario": id_usuario,
                "ID_Agendamento": dados.get("ID_Agendamento"),
                "Notas": dados.get("Observacao"),
            })
            self.accounts.update_saldo(account["ID_Conta"], -float(paid), id_usuario)
            payment_id = self.payments.add({
                **dados,
                "Chave_Idempotencia": key,
                "ID_Usuario": id_usuario,
                "ID_Transacao": transaction_id,
                "Valor_Pago": float(paid),
                "Valor_Juros": float(interest),
                "Valor_Multa": float(fine),
                "Valor_Desconto": float(discount),
                "Valor_Amortizado": float(amortized),
                "Data_Pagamento": payment_date,
            })
            if installment:
                self.installments.apply_payment(
                    installment_id, float(amortized), payment_date
                )
            new_balance = max(balance - amortized, Decimal("0.00"))
            self.model.update_balance_status(
                debt["ID_Divida"], id_usuario, float(new_balance),
                "QUITADA" if new_balance == 0 else "ATIVA",
            )
            if dados.get("ID_Agendamento"):
                self.schedules.mark_executed(
                    dados["ID_Agendamento"], id_usuario
                )
        return payment_id

    def agendar_pagamento_livre(self, dados, id_usuario):
        debt = self.model.get_by_id(dados.get("ID_Divida"), id_usuario)
        if not debt or debt["Tipo_Parcelamento"] != "LIVRE":
            raise ValueError("O agendamento manual é exclusivo para dívida LIVRE.")
        if debt["Status"] not in {"ATIVA", "ATRASADA"}:
            raise ValueError("Dívida não está disponível para agendamento.")
        value = self._money(dados.get("Valor"))
        due = self._date(dados.get("Data"))
        if value <= 0:
            raise ValueError("Informe um valor maior que zero.")
        schedule_id = self.schedules.add_schedule({
            "Tipo": "Contas a Pagar", "Data": due.isoformat(),
            "Valor": float(value),
            "Descricao": dados.get("Descricao") or f"Dívida: {debt['Descricao']}",
            "Status": "AGENDADO", "ID_Favorecido": debt.get("ID_Favorecido"),
            "ID_Usuario": id_usuario,
        })
        self.schedules.link_debt_installment(
            schedule_id, debt["ID_Divida"], None, id_usuario
        )
        return schedule_id

    def encerrar(self, id_divida, status, id_usuario):
        if status not in {"RENEGOCIADA", "CANCELADA"}:
            raise ValueError("Status de encerramento inválido.")
        debt = self.model.get_by_id(id_divida, id_usuario)
        if not debt or debt["Status"] in {"QUITADA", "CANCELADA"}:
            raise ValueError("Dívida não está disponível para encerramento.")
        with self.model.unit_of_work(
            self.installments, self.schedules, immediate=True
        ):
            self.model.set_status(id_divida, id_usuario, status)
            self.installments.cancel_pending(id_divida)
            self.schedules.cancel_by_debt(id_divida, id_usuario)
        return True

    def executar_agendamento(self, agendamento, dados_execucao, id_usuario):
        """Converte uma previsão de dívida em transação e pagamento reais."""
        if not agendamento.get("ID_Divida"):
            raise ValueError("Agendamento não está vinculado a uma dívida.")
        if agendamento.get("Status") not in {"AGENDADO", "ATRASADO"}:
            raise ValueError("Agendamento não está disponível para execução.")
        previsto = self._money(dados_execucao.get("Valor_Previsto"))
        juros = self._money(dados_execucao.get("Juros"))
        multa = self._money(dados_execucao.get("Multa"))
        desconto = self._money(dados_execucao.get("Desconto"))
        return self.registrar_pagamento({
            "ID_Divida": agendamento["ID_Divida"],
            "ID_Parcela": agendamento.get("ID_Parcela_Divida"),
            "ID_Agendamento": agendamento["ID_Agendamento"],
            "ID_Conta": dados_execucao.get("ID_Conta"),
            "Valor_Pago": float(previsto + juros + multa - desconto),
            "Valor_Juros": float(juros),
            "Valor_Multa": float(multa),
            "Valor_Desconto": float(desconto),
            "Data_Pagamento": dados_execucao.get("Data") or date.today(),
            "Observacao": dados_execucao.get("Notas"),
            "Chave_Idempotencia": f"agendamento-divida:{agendamento['ID_Agendamento']}",
        }, id_usuario)

    def atualizar_atrasos(self, id_usuario):
        today = date.today().isoformat()
        with self.model.unit_of_work(self.installments, immediate=True):
            self.installments.mark_overdue(id_usuario, today)
            self.model.mark_overdue(id_usuario)
