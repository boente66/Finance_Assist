"""Formulário de cadastro de dívida."""

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QLineEdit, QMessageBox, QSpinBox, QVBoxLayout,
)

from controllers.divida_controller import DividaController
from controllers.favorecido_controller import FavorecidoController
from core.translator_app import TranslatorApp


class DividaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.controller = DividaController()
        self.payees = FavorecidoController()
        self.setWindowTitle("Cadastrar dívida")
        self.setMinimumWidth(540)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.descricao = QLineEdit(); self.descricao.setPlaceholderText("Ex.: Financiamento do veículo")
        self.credor = QComboBox(); self.credor.addItem("Sem credor vinculado", None)
        for item in self.payees.listar_favorecidos():
            self.credor.addItem(item["Nome"], item["ID_Favorecido"])
        self.contrato = QLineEdit(); self.contrato.setPlaceholderText("Opcional")
        self.tipo = QComboBox();
        for tipo in self.controller.tipos_disponiveis():
            self.tipo.addItem(tipo, tipo)
        self.modelo = QComboBox(); self.modelo.addItem("Parcelas definidas (FIXO)", "FIXO"); self.modelo.addItem("Pagamentos livres (LIVRE)", "LIVRE")
        self.emprestado = self._money(); self.total = self._money(); self.juros = self._money(); self.juros.setSuffix(" %")
        self.parcelas = QSpinBox(); self.parcelas.setRange(1, 600); self.parcelas.setValue(12)
        self.contratacao = QDateEdit(QDate.currentDate()); self.contratacao.setCalendarPopup(True); self.contratacao.setDisplayFormat("dd/MM/yyyy")
        self.vencimento = QDateEdit(QDate.currentDate().addMonths(1)); self.vencimento.setCalendarPopup(True); self.vencimento.setDisplayFormat("dd/MM/yyyy")
        for label, widget in (("Descrição", self.descricao), ("Credor", self.credor),
                              ("Número do contrato", self.contrato), ("Tipo", self.tipo),
                              ("Forma de pagamento", self.modelo), ("Valor recebido", self.emprestado),
                              ("Total contratado", self.total), ("Taxa de juros", self.juros),
                              ("Quantidade de parcelas", self.parcelas), ("Data da contratação", self.contratacao),
                              ("Primeiro vencimento", self.vencimento)):
            form.addRow(label, widget)
        self.form = form
        layout.addLayout(form)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Save).setText("Cadastrar dívida")
        self.buttons.accepted.connect(self.salvar); self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.modelo.currentIndexChanged.connect(self._toggle_modelo)
        self._toggle_modelo()
        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

    def _atualizar_textos(self):
        for row in range(self.form.rowCount()):
            TranslatorApp._translate_widget(self.form.itemAt(row, QFormLayout.LabelRole).widget())
        self.descricao.setPlaceholderText(TranslatorApp.get("Ex.: Financiamento do veículo"))
        self.contrato.setPlaceholderText(TranslatorApp.get("Opcional"))
        self.credor.setItemText(0, TranslatorApp.get("Sem credor vinculado"))
        for i in range(self.tipo.count()):
            self.tipo.setItemText(i, TranslatorApp.get(self.tipo.itemData(i)))
        self.modelo.setItemText(0, TranslatorApp.get("Parcelas definidas (FIXO)"))
        self.modelo.setItemText(1, TranslatorApp.get("Pagamentos livres (LIVRE)"))
        self.setWindowTitle(TranslatorApp.get("Cadastrar dívida"))
        self.buttons.button(QDialogButtonBox.Save).setText(TranslatorApp.get("Cadastrar dívida"))
        self.buttons.button(QDialogButtonBox.Cancel).setText(TranslatorApp.get("Cancelar"))


    def done(self, result):
        TranslatorApp.unbind(self)
        super().done(result)

    @staticmethod
    def _money():
        field = QDoubleSpinBox(); field.setRange(0, 999999999.99); field.setDecimals(2)
        field.setPrefix("R$ "); field.setSingleStep(10)
        return field

    def _toggle_modelo(self):
        fixed = self.modelo.currentData() == "FIXO"
        self.parcelas.setEnabled(fixed); self.vencimento.setEnabled(fixed)

    def salvar(self):
        try:
            self.controller.criar({
                "Descricao": self.descricao.text(), "ID_Favorecido": self.credor.currentData(),
                "Numero_Contrato": self.contrato.text(), "Tipo_Divida": self.tipo.currentData(),
                "Tipo_Parcelamento": self.modelo.currentData(), "Valor_Emprestado": self.emprestado.value(),
                "Valor_Total_Contrato": self.total.value(), "Taxa_Juros": self.juros.value(),
                "Quantidade_Parcelas": self.parcelas.value(),
                "Data_Contratacao": self.contratacao.date().toString("yyyy-MM-dd"),
                "Primeiro_Vencimento": self.vencimento.date().toString("yyyy-MM-dd"),
            })
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self, TranslatorApp.get("Não foi possível cadastrar"), TranslatorApp.error(exc))

    # =====================================================
    # CICLO DE VIDA
    # =====================================================
    def closeEvent(self, event):
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass

        super().closeEvent(event)
