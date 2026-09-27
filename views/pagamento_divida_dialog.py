"""Registro transparente de pagamento de dívida."""

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QLabel, QMessageBox, QVBoxLayout,
)

from controllers.account_controller import AccountController
from controllers.divida_controller import DividaController
from utilitarios.currency_formatter import CurrencyFormatter


class PagamentoDividaDialog(QDialog):
    def __init__(self, divida, parent=None):
        super().__init__(parent)
        self.divida = divida
        self.controller = DividaController(); self.accounts = AccountController()
        self.setWindowTitle("Registrar pagamento da dívida"); self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        info = QLabel(f"{divida['Descricao']}\nSaldo devedor: {CurrencyFormatter.format(divida['Saldo_Devedor'])}")
        info.setObjectName("infoBanner"); layout.addWidget(info)
        form = QFormLayout()
        self.conta = QComboBox()
        for item in self.accounts.get_all_accounts():
            self.conta.addItem(f"{item['Nome_Conta']} · {CurrencyFormatter.format(item['Saldo_Atual'])}", item["ID_Conta"])
        self.parcela = QComboBox(); self.parcela.addItem("Pagamento livre / amortização", None)
        for item in divida.get("Parcelas", []):
            if item["Status"] not in ("PAGA", "CANCELADA"):
                pending = float(item["Valor_Previsto"]) - float(item["Valor_Pago"])
                self.parcela.addItem(f"Parcela {item['Numero_Parcela']} · {CurrencyFormatter.format(pending)} · {item['Data_Vencimento']}", item["ID_Parcela"])
        self.valor = self._money(); self.juros = self._money(); self.multa = self._money(); self.desconto = self._money()
        self.data = QDateEdit(QDate.currentDate()); self.data.setCalendarPopup(True); self.data.setDisplayFormat("dd/MM/yyyy")
        for label, widget in (("Conta de pagamento", self.conta), ("Parcela", self.parcela),
                              ("Valor pago", self.valor), ("Juros incluídos", self.juros),
                              ("Multa incluída", self.multa), ("Desconto obtido", self.desconto),
                              ("Data do pagamento", self.data)):
            form.addRow(label, widget)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("Confirmar pagamento")
        buttons.accepted.connect(self.salvar); buttons.rejected.connect(self.reject); layout.addWidget(buttons)

    @staticmethod
    def _money():
        field = QDoubleSpinBox(); field.setRange(0, 999999999.99); field.setDecimals(2); field.setPrefix("R$ ")
        return field

    def salvar(self):
        try:
            if not self.conta.currentData():
                raise ValueError("Cadastre ou selecione uma conta para o pagamento.")
            self.controller.registrar_pagamento({
                "ID_Divida": self.divida["ID_Divida"], "ID_Parcela": self.parcela.currentData(),
                "ID_Conta": self.conta.currentData(), "Valor_Pago": self.valor.value(),
                "Valor_Juros": self.juros.value(), "Valor_Multa": self.multa.value(),
                "Valor_Desconto": self.desconto.value(), "Data_Pagamento": self.data.date().toString("yyyy-MM-dd"),
            })
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self, "Pagamento não realizado", str(exc))
