"""Agendamento manual para dívida de pagamento livre."""

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QDateEdit, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QMessageBox, QVBoxLayout
from core.translator_app import TranslatorApp
from controllers.divida_controller import DividaController


class AgendamentoDividaDialog(QDialog):
    def __init__(self, divida, parent=None):
        super().__init__(parent); self.divida = divida; self.controller = DividaController()
        self.setWindowTitle("Agendar pagamento livre"); self.setMinimumWidth(390)
        layout = QVBoxLayout(self); form = QFormLayout()
        self.valor = QDoubleSpinBox(); self.valor.setRange(0.01, 999999999.99); self.valor.setDecimals(2); self.valor.setPrefix("R$ ")
        self.data = QDateEdit(QDate.currentDate().addMonths(1)); self.data.setCalendarPopup(True); self.data.setDisplayFormat("dd/MM/yyyy")
        self.form = form
        form.addRow("Valor previsto", self.valor); form.addRow("Vencimento", self.data); layout.addLayout(form)
        self.buttons = buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); buttons.button(QDialogButtonBox.Save).setText("Criar agendamento")
        buttons.accepted.connect(self.salvar); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

    def _atualizar_textos(self):
        self.setWindowTitle(TranslatorApp.get("Agendar pagamento livre"))
        for row in range(self.form.rowCount()):
            TranslatorApp._translate_widget(self.form.itemAt(row, QFormLayout.LabelRole).widget())
        self.buttons.button(QDialogButtonBox.Save).setText(TranslatorApp.get("Criar agendamento"))
        self.buttons.button(QDialogButtonBox.Cancel).setText(TranslatorApp.get("Cancelar"))

    def done(self, result):
        TranslatorApp.unbind(self)
        super().done(result)

    def salvar(self):
        try:
            self.controller.agendar_pagamento_livre({
                "ID_Divida": self.divida["ID_Divida"], "Valor": self.valor.value(),
                "Data": self.data.date().toString("yyyy-MM-dd"),
            })
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self, TranslatorApp.get("Agendamento não criado"), TranslatorApp.error(exc))
