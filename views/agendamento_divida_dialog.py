"""Agendamento manual para dívida de pagamento livre."""

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QDateEdit, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QMessageBox, QVBoxLayout
from controllers.divida_controller import DividaController


class AgendamentoDividaDialog(QDialog):
    def __init__(self, divida, parent=None):
        super().__init__(parent); self.divida = divida; self.controller = DividaController()
        self.setWindowTitle("Agendar pagamento livre"); self.setMinimumWidth(390)
        layout = QVBoxLayout(self); form = QFormLayout()
        self.valor = QDoubleSpinBox(); self.valor.setRange(0.01, 999999999.99); self.valor.setDecimals(2); self.valor.setPrefix("R$ ")
        self.data = QDateEdit(QDate.currentDate().addMonths(1)); self.data.setCalendarPopup(True); self.data.setDisplayFormat("dd/MM/yyyy")
        form.addRow("Valor previsto", self.valor); form.addRow("Vencimento", self.data); layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); buttons.button(QDialogButtonBox.Save).setText("Criar agendamento")
        buttons.accepted.connect(self.salvar); buttons.rejected.connect(self.reject); layout.addWidget(buttons)

    def salvar(self):
        try:
            self.controller.agendar_pagamento_livre({
                "ID_Divida": self.divida["ID_Divida"], "Valor": self.valor.value(),
                "Data": self.data.date().toString("yyyy-MM-dd"),
            })
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self, "Agendamento não criado", str(exc))
