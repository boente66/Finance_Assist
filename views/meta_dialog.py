from utilitarios.currency_formatter import CurrencyFormatter
# -*- coding: utf-8 -*-
import logging

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QDateEdit,
    QHBoxLayout,
    QMessageBox,
)
from PyQt5.QtCore import QDate

from controllers.meta_controller import MetaController
from controllers.category_controller import CategoryController
from core.translator_app import TranslatorApp

logger = logging.getLogger(__name__)


class MetaDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.controller = MetaController()
        self.category_controller = CategoryController()

        self.setWindowTitle("Nova Meta")
        self.setMinimumWidth(400)

        self._init_ui()
        self._connect_events()
        self._carregar_categorias()

        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

        self._alterar_tipo()

    # ==================================================
    # UI
    # ==================================================
    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.lbl_nome = QLabel()
        layout.addWidget(self.lbl_nome)

        self.input_nome = QLineEdit()
        layout.addWidget(self.input_nome)

        self.lbl_tipo = QLabel()
        layout.addWidget(self.lbl_tipo)

        self.combo_tipo = QComboBox()
        self.combo_tipo.addItem("Categoria", "Categoria")
        self.combo_tipo.addItem("Economia", "Economia")
        self.combo_tipo.addItem("Objetivo", "Objetivo")
        layout.addWidget(self.combo_tipo)

        self.lbl_categoria = QLabel()
        layout.addWidget(self.lbl_categoria)

        self.combo_categoria = QComboBox()
        layout.addWidget(self.combo_categoria)

        self.lbl_valor = QLabel()
        layout.addWidget(self.lbl_valor)

        self.input_valor = QLineEdit()
        layout.addWidget(self.input_valor)

        self.lbl_inicio = QLabel()
        layout.addWidget(self.lbl_inicio)

        self.data_inicio = QDateEdit()
        self.data_inicio.setCalendarPopup(True)
        self.data_inicio.setDate(QDate.currentDate())
        layout.addWidget(self.data_inicio)

        self.lbl_fim = QLabel()
        layout.addWidget(self.lbl_fim)

        self.data_fim = QDateEdit()
        self.data_fim.setCalendarPopup(True)
        self.data_fim.setDate(QDate.currentDate().addMonths(1))
        layout.addWidget(self.data_fim)

        botoes = QHBoxLayout()

        self.btn_salvar = QPushButton()
        self.btn_salvar.setObjectName("addButton")

        self.btn_cancelar = QPushButton()

        botoes.addWidget(self.btn_salvar)
        botoes.addWidget(self.btn_cancelar)

        layout.addLayout(botoes)

    # ==================================================
    # EVENTOS
    # ==================================================
    def _connect_events(self):
        self.combo_tipo.currentIndexChanged.connect(
            self._alterar_tipo
        )

        self.btn_salvar.clicked.connect(
            self._salvar
        )

        self.btn_cancelar.clicked.connect(
            self.reject
        )

    # ==================================================
    # TRADUÇÃO
    # ==================================================
    def _atualizar_textos(self, *_):
        self.setWindowTitle(
            TranslatorApp.get("Nova Meta")
        )

        self.lbl_nome.setText(
            TranslatorApp.get("Nome da Meta")
        )

        self.lbl_tipo.setText(
            TranslatorApp.get("Tipo")
        )

        self.lbl_categoria.setText(
            TranslatorApp.get("Categoria")
        )

        self.lbl_valor.setText(
            TranslatorApp.get("Valor Alvo")
        )

        self.input_valor.setPlaceholderText(
            TranslatorApp.get("Ex: 1500,00")
        )

        self.lbl_inicio.setText(
            TranslatorApp.get("Data Início")
        )

        self.lbl_fim.setText(
            TranslatorApp.get("Data Fim")
        )

        self.btn_salvar.setText(
            TranslatorApp.get("Salvar")
        )

        self.btn_cancelar.setText(
            TranslatorApp.get("Cancelar")
        )

        self._traduzir_combo_tipo()

    def _traduzir_combo_tipo(self):
        atual = self.combo_tipo.currentData()

        self.combo_tipo.blockSignals(True)
        self.combo_tipo.clear()

        self.combo_tipo.addItem(
            TranslatorApp.get("Categoria"),
            "Categoria"
        )
        self.combo_tipo.addItem(
            TranslatorApp.get("Economia"),
            "Economia"
        )
        self.combo_tipo.addItem(
            TranslatorApp.get("Objetivo"),
            "Objetivo"
        )

        index = self.combo_tipo.findData(atual)

        if index >= 0:
            self.combo_tipo.setCurrentIndex(index)

        self.combo_tipo.blockSignals(False)

    # ==================================================
    # CARREGAR CATEGORIAS
    # ==================================================
    def _carregar_categorias(self):
        self.combo_categoria.clear()

        categorias = self.category_controller.get_all_categories() or []

        for cat in categorias:
            self.combo_categoria.addItem(
                cat.get("Nome", ""),
                cat.get("ID_Categoria")
            )

    # ==================================================
    # ALTERAR TIPO
    # ==================================================
    def _alterar_tipo(self, *_):
        tipo = self.combo_tipo.currentData()

        ativo = tipo == "Categoria"

        self.combo_categoria.setEnabled(ativo)
        self.lbl_categoria.setEnabled(ativo)

    # ==================================================
    # VALIDAR E SALVAR
    # ==================================================
    def _salvar(self):
        nome = self.input_nome.text().strip()
        tipo = self.combo_tipo.currentData()
        valor_txt = self.input_valor.text().strip()

        if not nome:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Informe o nome da meta.")
            )
            return

        try:
            valor = CurrencyFormatter.to_float(valor_txt)

            if valor <= 0:
                raise ValueError

        except ValueError:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Valor inválido.")
            )
            return

        data_inicio = self.data_inicio.date().toString("yyyy-MM-dd")
        data_fim = self.data_fim.date().toString("yyyy-MM-dd")

        if data_inicio > data_fim:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Data final inválida.")
            )
            return

        dados = {
            "Nome": nome,
            "Tipo": tipo,
            "Valor_Alvo": valor,
            "Data_Inicio": data_inicio,
            "Data_Fim": data_fim,
        }

        if tipo == "Categoria":
            id_categoria = self.combo_categoria.currentData()

            if not id_categoria:
                QMessageBox.warning(
                    self,
                    TranslatorApp.get("Erro"),
                    TranslatorApp.get("Selecione uma categoria.")
                )
                return

            dados["ID_Categoria"] = id_categoria

        try:
            self.controller.criar_meta(dados)
            self.accept()

        except Exception as e:
            logger.exception("Erro ao salvar meta")

            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                str(e)
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