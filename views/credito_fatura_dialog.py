from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)

from core.translator_app import TranslatorApp
from controllers.fatura_controller import FaturaController


class CreditoFaturaDialog(QDialog):
    TIPOS = ("Cashback", "Estorno", "Devolução", "Desconto", "Ajuste")

    def __init__(self, id_cartao=1, parent=None):
        super().__init__(parent)
        self.id_cartao = id_cartao
        self.controller = FaturaController()
        self.setWindowTitle("Adicionar crédito à fatura")
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.tipo_combo = QComboBox()
        for tipo in self.TIPOS:
            self.tipo_combo.addItem(tipo, tipo)
        self.natureza_combo = QComboBox()
        self.natureza_combo.addItems(("Reduzir fatura", "Aumentar fatura"))
        self.natureza_combo.setVisible(False)
        self.tipo_combo.currentIndexChanged.connect(
            lambda _: self.natureza_combo.setVisible(self.tipo_combo.currentData() == "Ajuste")
        )
        self.descricao_edit = QLineEdit()
        self.descricao_edit.setPlaceholderText("Ex.: Cashback da compra")
        self.valor_spin = QDoubleSpinBox()
        self.valor_spin.setRange(0.01, 999999999.99)
        self.valor_spin.setDecimals(2)
        self.valor_spin.setPrefix("R$ ")
        self.data_edit = QDateEdit(QDate.currentDate())
        self.data_edit.setCalendarPopup(True)
        self.origem_combo = QComboBox()
        self.origem_combo.addItem("Sem vínculo com compra", None)
        try:
            compras = self.controller.listar_compras_cartao(id_cartao) or []
        except ValueError:
            compras = []
        for compra in reversed(compras):
            texto = (
                f"{compra.get('Data', '')} — "
                f"{compra.get('Descricao', '')} — "
                f"R$ {float(compra.get('Valor', 0)):.2f}"
            )
            self.origem_combo.addItem(
                texto, compra.get("ID_Lancamento")
            )
        self.notas_edit = QTextEdit()
        self.notas_edit.setMaximumHeight(80)
        form.addRow("Tipo:", self.tipo_combo)
        form.addRow("Natureza do ajuste:", self.natureza_combo)
        form.addRow("Descrição:", self.descricao_edit)
        form.addRow("Valor positivo:", self.valor_spin)
        form.addRow("Data do crédito:", self.data_edit)
        form.addRow("Compra original:", self.origem_combo)
        form.addRow("Notas:", self.notas_edit)
        self.form = form
        layout.addLayout(form)

        self.buttons = buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.salvar)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

    def _atualizar_textos(self):
        self.setWindowTitle(TranslatorApp.get("Adicionar crédito à fatura"))
        for row in range(self.form.rowCount()):
            TranslatorApp._translate_widget(self.form.itemAt(row, QFormLayout.LabelRole).widget())
        for index in range(self.tipo_combo.count()):
            self.tipo_combo.setItemText(index, TranslatorApp.get(self.tipo_combo.itemData(index)))
        for index, label in enumerate(("Reduzir fatura", "Aumentar fatura")):
            self.natureza_combo.setItemText(index, TranslatorApp.get(label))
        self.origem_combo.setItemText(0, TranslatorApp.get("Sem vínculo com compra"))
        self.descricao_edit.setPlaceholderText(TranslatorApp.get("Ex.: Cashback da compra"))
        self.buttons.button(QDialogButtonBox.Save).setText(TranslatorApp.get("Salvar"))
        self.buttons.button(QDialogButtonBox.Cancel).setText(TranslatorApp.get("Cancelar"))

    def done(self, result):
        TranslatorApp.unbind(self)
        super().done(result)

    def salvar(self):
        try:
            tipo = self.tipo_combo.currentData()
            descricao = self.descricao_edit.text().strip() or tipo
            self.controller.adicionar_credito_fatura({
                "ID_Cartao": self.id_cartao,
                "Tipo_Credito": tipo,
                "Descricao": descricao,
                "Valor": self.valor_spin.value(),
                "Natureza_Ajuste": (
                    "Aumentar" if self.natureza_combo.currentIndex() == 1
                    else "Reduzir"
                ),
                "Data": self.data_edit.date().toString("yyyy-MM-dd"),
                "ID_Lancamento_Origem": self.origem_combo.currentData(),
                "Notas": self.notas_edit.toPlainText().strip(),
            })
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self, TranslatorApp.get("Crédito não registrado"), TranslatorApp.error(exc))
