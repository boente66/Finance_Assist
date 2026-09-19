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
        self.tipo_combo.addItems(self.TIPOS)
        self.natureza_combo = QComboBox()
        self.natureza_combo.addItems(("Reduzir fatura", "Aumentar fatura"))
        self.natureza_combo.setVisible(False)
        self.tipo_combo.currentTextChanged.connect(
            lambda tipo: self.natureza_combo.setVisible(tipo == "Ajuste")
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
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.salvar)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def salvar(self):
        try:
            tipo = self.tipo_combo.currentText()
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
            QMessageBox.warning(self, "Crédito não registrado", str(exc))
