from core.regional_format import RegionalFormat
import logging

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QDateEdit,
    QDialogButtonBox,
    QMessageBox,
    QDoubleSpinBox,
    QLabel,
    QCheckBox,
)
from PyQt5.QtCore import QDate, Qt

from controllers.schedule_controller import ScheduleController
from controllers.account_controller import AccountController
from controllers.category_controller import CategoryController
from controllers.favorecido_controller import FavorecidoController

from core.translator_app import TranslatorApp

logger = logging.getLogger(__name__)


class AgendamentoDialog(QDialog):

    TIPOS = [
        "Contas a Pagar",
        "Contas a Receber",
        "Transferências",
    ]

    PERIODICIDADES = [
        "Mensal",
        "Anual",
    ]

    def __init__(self, parent=None, agendamento_id=None):
        super().__init__(parent)

        self.agendamento_id = agendamento_id

        self.schedule_controller = ScheduleController()
        self.account_controller = AccountController()
        self.category_controller = CategoryController()
        self.favorecido_controller = FavorecidoController()

        self._build_ui()
        self._connect_signals()

        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

        if self.agendamento_id:
            self._carregar_para_edicao()

    # ==================================================
    # UI
    # ==================================================
    def _build_ui(self):
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)

        self.form = QFormLayout()
        self.form.setLabelAlignment(Qt.AlignRight)

        self.tipo_label = QLabel()
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(self.TIPOS)
        self.form.addRow(self.tipo_label, self.tipo_combo)

        self.desc_label = QLabel()
        self.descricao_input = QLineEdit()
        self.form.addRow(self.desc_label, self.descricao_input)

        self.conta_label = QLabel()
        self.conta_combo = QComboBox()
        self.form.addRow(self.conta_label, self.conta_combo)

        self.fav_label = QLabel()
        self.favorecido_combo = QComboBox()
        self.form.addRow(self.fav_label, self.favorecido_combo)

        self.cat_label = QLabel()
        self.categoria_combo = QComboBox()
        self.form.addRow(self.cat_label, self.categoria_combo)

        self.valor_label = QLabel()
        self.valor_spin = QDoubleSpinBox()
        self.valor_spin.setDecimals(2)
        self.valor_spin.setRange(0.01, 10_000_000)
        self.valor_spin.setPrefix("R$ "); RegionalFormat.configure_widget(self.valor_spin)
        self.form.addRow(self.valor_label, self.valor_spin)

        self.data_label = QLabel()
        self.data_vencimento = QDateEdit(QDate.currentDate())
        self.data_vencimento.setCalendarPopup(True)
        self.form.addRow(self.data_label, self.data_vencimento)

        self.recorrente_label = QLabel()
        self.recorrente_check = QCheckBox()
        self.form.addRow(self.recorrente_label, self.recorrente_check)

        self.periodicidade_label = QLabel()
        self.periodicidade_combo = QComboBox()
        self.periodicidade_combo.addItems(self.PERIODICIDADES)
        self.periodicidade_combo.setEnabled(False)
        self.form.addRow(self.periodicidade_label, self.periodicidade_combo)

        layout.addLayout(self.form)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        layout.addWidget(self.button_box)

        self.load_contas()
        self.load_favorecidos()
        self.load_categorias()

    # ==================================================
    # TRADUÇÃO
    # ==================================================
    def _atualizar_textos(self):
        if self.agendamento_id is None:
            self.setWindowTitle(
                TranslatorApp.get("Adicionar Agendamento")
            )
        else:
            self.setWindowTitle(
                TranslatorApp.get("Editar Agendamento")
            )

        self.tipo_label.setText(
            TranslatorApp.get("Tipo")
        )

        self.desc_label.setText(
            TranslatorApp.get("Descrição")
        )

        self.conta_label.setText(
            TranslatorApp.get("Conta")
        )

        self.fav_label.setText(
            TranslatorApp.get("Favorecido")
        )

        self.cat_label.setText(
            TranslatorApp.get("Categoria")
        )

        self.valor_label.setText(
            TranslatorApp.get("Valor")
        )

        self.data_label.setText(
            TranslatorApp.get("Vencimento")
        )

        self.recorrente_label.setText(
            TranslatorApp.get("Recorrente")
        )

        self.periodicidade_label.setText(
            TranslatorApp.get("Periodicidade")
        )

        self.button_box.button(
            QDialogButtonBox.Save
        ).setText(
            TranslatorApp.get("Salvar")
        )

        self.button_box.button(
            QDialogButtonBox.Cancel
        ).setText(
            TranslatorApp.get("Cancelar")
        )

    # ==================================================
    # CICLO DE VIDA
    # ==================================================
    def closeEvent(self, event):
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass

        super().closeEvent(event)

    # ==================================================
    # SIGNALS
    # ==================================================
    def _connect_signals(self):
        self.button_box.accepted.connect(self.save_agendamento)
        self.button_box.rejected.connect(self.reject)

        self.recorrente_check.stateChanged.connect(
            self._toggle_periodicidade
        )

    def _toggle_periodicidade(self):
        self.periodicidade_combo.setEnabled(
            self.recorrente_check.isChecked()
        )

    # ==================================================
    # DADOS
    # ==================================================
    def load_contas(self):
        self.conta_combo.clear()

        contas = self.account_controller.get_all_accounts()

        for conta in contas:
            self.conta_combo.addItem(
                conta["Nome_Conta"],
                conta["ID_Conta"]
            )

    def load_favorecidos(self):
        self.favorecido_combo.clear()

        favorecidos = self.favorecido_controller.listar_favorecidos()

        for favorecido in favorecidos:
            self.favorecido_combo.addItem(
                favorecido["Nome"],
                favorecido["ID_Favorecido"]
            )

    def load_categorias(self):
        self.categoria_combo.clear()

        categorias = self.category_controller.get_all_categories() or []

        for categoria in categorias:
            self.categoria_combo.addItem(
                categoria["Nome"],
                categoria["ID_Categoria"]
            )

    # ==================================================
    # EDIÇÃO
    # ==================================================
    def _carregar_para_edicao(self):
        dados = self.schedule_controller.get_schedule_by_id(
            self.agendamento_id
        )

        if not dados:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Aviso"),
                TranslatorApp.get("Agendamento não encontrado")
            )
            self.reject()
            return

        self.tipo_combo.setCurrentText(
            dados.get("Tipo", "")
        )

        self.descricao_input.setText(
            dados.get("Descricao", "")
        )

        self.valor_spin.setValue(
            float(dados.get("Valor", 0))
        )

        data = QDate.fromString(
            dados.get("Data", ""),
            "yyyy-MM-dd"
        )

        if data.isValid():
            self.data_vencimento.setDate(data)

        self._selecionar_combo_por_data(
            self.conta_combo,
            dados.get("ID_Conta")
        )

        self._selecionar_combo_por_data(
            self.favorecido_combo,
            dados.get("ID_Favorecido")
        )

        self._selecionar_combo_por_data(
            self.categoria_combo,
            dados.get("ID_Categoria")
        )

        recorrente = bool(
            dados.get("Recorrente", 0)
        )

        self.recorrente_check.setChecked(recorrente)
        self.periodicidade_combo.setEnabled(recorrente)

        periodicidade = dados.get("Periodicidade")

        if periodicidade:
            index = self.periodicidade_combo.findText(periodicidade)

            if index >= 0:
                self.periodicidade_combo.setCurrentIndex(index)

    def _selecionar_combo_por_data(self, combo, valor):
        if valor is None:
            return

        index = combo.findData(valor)

        if index >= 0:
            combo.setCurrentIndex(index)

    # ==================================================
    # SALVAR
    # ==================================================
    def save_agendamento(self):
        descricao = self.descricao_input.text().strip()

        if not descricao:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Atenção"),
                TranslatorApp.get("Descrição obrigatória.")
            )
            return

        id_conta = self.conta_combo.currentData()

        if not id_conta:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Atenção"),
                TranslatorApp.get("Conta obrigatória.")
            )
            return

        data = {
            "Tipo": self.tipo_combo.currentText(),
            "Descricao": descricao,
            "ID_Conta": id_conta,
            "ID_Favorecido": self.favorecido_combo.currentData(),
            "ID_Categoria": self.categoria_combo.currentData(),
            "Valor": float(self.valor_spin.value()),
            "Data": self.data_vencimento.date().toString("yyyy-MM-dd"),
            "Recorrente": 1 if self.recorrente_check.isChecked() else 0,
            "Periodicidade": (
                self.periodicidade_combo.currentText()
                if self.recorrente_check.isChecked()
                else None
            ),
        }

        try:
            if self.agendamento_id:
                self.schedule_controller.update_schedule(
                    self.agendamento_id,
                    data
                )
            else:
                self.schedule_controller.add_schedule(data)

            self.accept()

        except Exception as e:
            logger.exception("Erro ao salvar agendamento")

            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                f"{TranslatorApp.get('Erro ao salvar')}:\n{e}"
            )