# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QDialogButtonBox,
    QMessageBox,
    QLabel,
)

from core.translator_app import TranslatorApp


class SubcategoriaDialog(QDialog):

    def __init__(self, parent=None, controller=None, categoria_pai_id=None):
        super().__init__(parent)

        if controller is None:
            raise RuntimeError("Controller não informado.")

        self.controller = controller
        self.categoria_pai_id = categoria_pai_id

        self.setMinimumWidth(300)
        self.setWindowTitle("Nova Subcategoria")

        self._montar_ui()
        self._connect_events()
        self._carregar_categorias_pai()
        self._selecionar_categoria_pai()

        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

    # ==================================================
    # UI
    # ==================================================
    def _montar_ui(self):
        layout = QVBoxLayout(self)

        self.form = QFormLayout()

        self.nome_input = QLineEdit()
        self.categoria_pai_combo = QComboBox()

        self.nome_label = QLabel("")
        self.categoria_pai_label = QLabel("")

        self.form.addRow(self.nome_label, self.nome_input)
        self.form.addRow(self.categoria_pai_label, self.categoria_pai_combo)

        layout.addLayout(self.form)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        layout.addWidget(self.buttons)

    # ==================================================
    # EVENTOS
    # ==================================================
    def _connect_events(self):
        self.buttons.accepted.connect(self._accept_if_valid)
        self.buttons.rejected.connect(self.reject)

    # ==================================================
    # TRADUÇÃO
    # ==================================================
    def _atualizar_textos(self, *_):
        self.setWindowTitle(TranslatorApp.get("Nova Subcategoria"))

        self.nome_label.setText(TranslatorApp.get("Nome") + ":")

        self.categoria_pai_label.setText(TranslatorApp.get("Categoria Pai") + ":")

        self.buttons.button(QDialogButtonBox.Ok).setText(TranslatorApp.get("OK"))

        self.buttons.button(QDialogButtonBox.Cancel).setText(
            TranslatorApp.get("Cancelar")
        )

    # ==================================================
    # CARREGAR CATEGORIAS PAI
    # ==================================================
    def _carregar_categorias_pai(self):
        try:
            categorias = self.controller.get_all_categories() or []

            self.categoria_pai_combo.clear()

            for cat in categorias:
                if cat.get("ID_Categoria_Pai") is None:
                    self.categoria_pai_combo.addItem(
                        cat.get("Nome", ""), cat.get("ID_Categoria")
                    )

        except Exception as e:
            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                f"{TranslatorApp.get('Erro ao carregar categorias')}: {e}",
            )

    # ==================================================
    # SELECIONAR CATEGORIA PAI
    # ==================================================
    def _selecionar_categoria_pai(self):
        if not self.categoria_pai_id:
            return

        index = self.categoria_pai_combo.findData(self.categoria_pai_id)

        if index >= 0:
            self.categoria_pai_combo.setCurrentIndex(index)

    # ==================================================
    # VALIDAÇÃO
    # ==================================================
    def _accept_if_valid(self):
        dados = self.get_data()

        if dados:
            self.accept()

    # ==================================================
    # RETORNO
    # ==================================================
    def get_data(self):
        nome = self.nome_input.text().strip()

        if not nome:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Atenção"),
                TranslatorApp.get("O nome da subcategoria não pode estar vazio."),
            )
            return None

        id_categoria_pai = self.categoria_pai_combo.currentData()

        if not id_categoria_pai:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Atenção"),
                TranslatorApp.get("Selecione uma categoria pai."),
            )
            return None

        return {
            "Nome": nome,
            "ID_Categoria_Pai": id_categoria_pai,
        }

    # ==================================================
    # CICLO DE VIDA
    # ==================================================
    def closeEvent(self, event):
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass

        super().closeEvent(event)
