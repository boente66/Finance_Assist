from core.regional_format import RegionalFormat
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QComboBox,
    QDoubleSpinBox,
    QDateEdit,
    QTextEdit,
    QDialogButtonBox,
    QLineEdit,
    QMessageBox,
    QCheckBox,
    QLabel,
)
from PyQt5.QtCore import QDate

from controllers.account_controller import AccountController
from controllers.category_controller import CategoryController
from controllers.favorecido_controller import FavorecidoController
from controllers.transaction_controller import TransactionController

from core.translator_app import TranslatorApp


class EditTransactionDialog(QDialog):

    def __init__(self, transacao, parent=None, modo_temporario=False):
        super().__init__(parent)

        self.modo_temporario = modo_temporario
        self.transacao = transacao or {}

        self.transaction_controller = TransactionController()
        self.account_controller = AccountController()
        self.category_controller = CategoryController()
        self.favorecido_controller = FavorecidoController()

        self.setMinimumSize(520, 420)

        self._build_ui()
        self._preencher_campos()

        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

    # ======================================================
    # UI
    # ======================================================
    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.form = QFormLayout()

        self.lbl_conta = QLabel()
        self.lbl_tipo = QLabel()
        self.lbl_desc = QLabel()
        self.lbl_valor = QLabel()
        self.lbl_categoria = QLabel()
        self.lbl_favorecido = QLabel()
        self.lbl_data = QLabel()
        self.lbl_notas = QLabel()
        self.lbl_destino = QLabel()

        # Conta origem
        self.conta_origem_combo = QComboBox()
        self.contas = self.account_controller.get_all_accounts() or []

        for conta in self.contas:
            self.conta_origem_combo.addItem(
                conta.get("Nome_Conta", ""),
                conta.get("ID_Conta")
            )

        self.form.addRow(self.lbl_conta, self.conta_origem_combo)

        # Tipo
        self.tipo_combo = QComboBox()

        tipos = [
            ("Despesa", "Despesa"),
            ("Receita", "Receita"),
        ]

        for texto, valor in tipos:
            self.tipo_combo.addItem(texto, valor)

        self.form.addRow(self.lbl_tipo, self.tipo_combo)

        # Descrição
        self.desc_edit = QLineEdit()
        self.form.addRow(self.lbl_desc, self.desc_edit)

        # Valor
        self.valor_spin = QDoubleSpinBox()
        self.valor_spin.setPrefix("R$ "); RegionalFormat.configure_widget(self.valor_spin)
        self.valor_spin.setRange(0.01, 1_000_000.00)
        self.valor_spin.setDecimals(2)
        self.form.addRow(self.lbl_valor, self.valor_spin)

        # Categoria
        self.categoria_combo = QComboBox()
        categorias = self.category_controller.get_all_categories() or []

        for cat in categorias:
            self.categoria_combo.addItem(
                cat.get("Nome", ""),
                cat.get("ID_Categoria")
            )

        self.form.addRow(self.lbl_categoria, self.categoria_combo)

        # Favorecido
        self.favorecido_combo = QComboBox()
        self._carregar_favorecidos()
        self.form.addRow(self.lbl_favorecido, self.favorecido_combo)

        # Data
        self.data_edit = QDateEdit()
        self.data_edit.setCalendarPopup(True)
        self.data_edit.setDate(QDate.currentDate())
        self.form.addRow(self.lbl_data, self.data_edit)

        # Notas
        self.notas_edit = QTextEdit()
        self.notas_edit.setFixedHeight(80)
        self.form.addRow(self.lbl_notas, self.notas_edit)

        # Converter em transferência
        self.transfer_checkbox = QCheckBox()
        self.transfer_checkbox.stateChanged.connect(
            self._toggle_transferencia
        )
        self.form.addRow(QLabel(""), self.transfer_checkbox)

        # Conta destino
        self.conta_destino_combo = QComboBox()

        for conta in self.contas:
            self.conta_destino_combo.addItem(
                conta.get("Nome_Conta", ""),
                conta.get("ID_Conta")
            )

        self.form.addRow(self.lbl_destino, self.conta_destino_combo)

        self.lbl_destino.setVisible(False)
        self.conta_destino_combo.setVisible(False)

        layout.addLayout(self.form)

        # Botões
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )

        layout.addWidget(self.button_box)

        self.button_box.accepted.connect(self.salvar)
        self.button_box.rejected.connect(self.reject)

    # ======================================================
    # TRADUÇÃO
    # ======================================================
    def _atualizar_textos(self):
        self.setWindowTitle(
            TranslatorApp.get("Editar Transação")
        )

        self.lbl_conta.setText(
            TranslatorApp.get("Conta:")
        )

        self.lbl_tipo.setText(
            TranslatorApp.get("Tipo:")
        )

        self.lbl_desc.setText(
            TranslatorApp.get("Descrição:")
        )

        self.lbl_valor.setText(
            TranslatorApp.get("Valor:")
        )

        self.lbl_categoria.setText(
            TranslatorApp.get("Categoria:")
        )

        self.lbl_favorecido.setText(
            TranslatorApp.get("Favorecido:")
        )

        self.lbl_data.setText(
            TranslatorApp.get("Data:")
        )

        self.lbl_notas.setText(
            TranslatorApp.get("Notas:")
        )

        self.lbl_destino.setText(
            TranslatorApp.get("Conta destino:")
        )

        self.desc_edit.setPlaceholderText(
            TranslatorApp.get("Descrição")
        )

        self.transfer_checkbox.setText(
            TranslatorApp.get("Converter em transferência")
        )

        self.button_box.button(
            QDialogButtonBox.Cancel
        ).setText(
            TranslatorApp.get("Cancelar")
        )

        if self.transfer_checkbox.isChecked():
            self.button_box.button(
                QDialogButtonBox.Save
            ).setText(
                TranslatorApp.get("Converter")
            )
        else:
            self.button_box.button(
                QDialogButtonBox.Save
            ).setText(
                TranslatorApp.get("Salvar")
            )

    # ======================================================
    # DADOS
    # ======================================================
    def _preencher_campos(self):
        self.desc_edit.setText(
            self.transacao.get("Descricao", "")
        )

        valor = abs(
            float(self.transacao.get("Valor", 0))
        )
        self.valor_spin.setValue(valor)

        tipo = self.transacao.get("Tipo", "Despesa")
        index_tipo = self.tipo_combo.findData(tipo)

        if index_tipo >= 0:
            self.tipo_combo.setCurrentIndex(index_tipo)

        idx_conta = self.conta_origem_combo.findData(
            self.transacao.get("ID_Conta")
        )

        if idx_conta >= 0:
            self.conta_origem_combo.setCurrentIndex(idx_conta)

        idx_cat = self.categoria_combo.findData(
            self.transacao.get("ID_Categoria")
        )

        if idx_cat >= 0:
            self.categoria_combo.setCurrentIndex(idx_cat)

        idx_fav = self.favorecido_combo.findData(
            self.transacao.get("ID_Favorecido")
        )

        if idx_fav >= 0:
            self.favorecido_combo.setCurrentIndex(idx_fav)

        data = self.transacao.get("Data")

        if data:
            data_qt = QDate.fromString(data, "yyyy-MM-dd")

            if data_qt.isValid():
                self.data_edit.setDate(data_qt)

        self.notas_edit.setText(
            self.transacao.get("Notas", "")
        )

    def _carregar_favorecidos(self):
        self.favorecido_combo.clear()

        favorecidos = (
            self.favorecido_controller.listar_favorecidos()
            or []
        )

        for fav in favorecidos:
            self.favorecido_combo.addItem(
                fav.get("Nome", ""),
                fav.get("ID_Favorecido")
            )

    # ======================================================
    # TRANSFERÊNCIA
    # ======================================================
    def _toggle_transferencia(self):
        converter = self.transfer_checkbox.isChecked()

        self.lbl_destino.setVisible(converter)
        self.conta_destino_combo.setVisible(converter)

        self.lbl_tipo.setVisible(not converter)
        self.tipo_combo.setVisible(not converter)

        self.lbl_categoria.setVisible(not converter)
        self.categoria_combo.setVisible(not converter)

        self.lbl_favorecido.setVisible(not converter)
        self.favorecido_combo.setVisible(not converter)

        self.lbl_notas.setVisible(not converter)
        self.notas_edit.setVisible(not converter)

        self._atualizar_textos()

    def _converter_em_transferencia(self):
        id_transacao = self.transacao.get("ID_Transacao")
        id_origem = self.conta_origem_combo.currentData()
        id_destino = self.conta_destino_combo.currentData()

        if not id_transacao:
            raise ValueError("Transação inválida.")

        if not id_destino:
            raise ValueError("Conta destino obrigatória.")

        if id_origem == id_destino:
            raise ValueError(
                "Conta origem e destino não podem ser iguais."
            )

        self.transaction_controller.converter_em_transferencia(
            id_transacao,
            id_destino
        )

        QMessageBox.information(
            self,
            TranslatorApp.get("Sucesso"),
            TranslatorApp.get(
                "Transação convertida em transferência."
            )
        )

        self.accept()

    # ======================================================
    # SALVAR
    # ======================================================
    def salvar(self):
        try:
            if self.transfer_checkbox.isChecked():
                self._converter_em_transferencia()
                return

            valor = self.valor_spin.value()
            tipo = self.tipo_combo.currentData()

            if tipo == "Despesa":
                valor = -abs(valor)
            else:
                valor = abs(valor)

            dados = {
                "ID_Conta": self.conta_origem_combo.currentData(),
                "Tipo": tipo,
                "Descricao": self.desc_edit.text().strip(),
                "Valor": valor,
                "ID_Categoria": self.categoria_combo.currentData(),
                "ID_Favorecido": self.favorecido_combo.currentData(),
                "Data": self.data_edit.date().toString("yyyy-MM-dd"),
                "Notas": self.notas_edit.toPlainText(),
                "ID_Transacao": self.transacao.get("ID_Transacao"),
            }

            if self.modo_temporario:
                self.dados_editados = dados
                self.accept()
                return

            self.transaction_controller.update_transaction(dados)

            QMessageBox.information(
                self,
                TranslatorApp.get("Sucesso"),
                TranslatorApp.get(
                    "Transação atualizada com sucesso."
                ),
            )

            self.accept()

        except Exception as e:
            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                str(e)
            )

    # ======================================================
    # CICLO DE VIDA
    # ======================================================
    def closeEvent(self, event):
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass

        super().closeEvent(event)
