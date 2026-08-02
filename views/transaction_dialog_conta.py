# -*- coding: utf-8 -*-
import logging
import os
import re

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QTextEdit,
    QDateEdit,
    QMessageBox,
)
from PyQt5.QtCore import QDate
from PyQt5.QtGui import QIcon

from controllers.main_controller import MainController
from controllers.favorecido_controller import FavorecidoController
from controllers.category_controller import CategoryController

from core.translator_app import TranslatorApp
from utilitarios.ion_path import IonPath

logger = logging.getLogger(__name__)


class TransactionDialogConta(QDialog):

    def __init__(self, parent=None, id_conta=None):
        super().__init__(parent)

        if id_conta is None:
            raise ValueError("Conta inválida")

        self.id_conta = id_conta

        self.main_controller = MainController()
        self.favorecido_controller = FavorecidoController()
        self.category_controller = CategoryController()

        self._icon_cache = {}

        self._init_ui()
        self._configurar_ui()
        self._carregar_categorias()
        self._carregar_favorecidos()
        self._conectar_eventos()

        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

    # ======================================================
    # UI
    # ======================================================
    def _init_ui(self):
        self.resize(616, 404)
        self.setMinimumSize(616, 404)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        tipo_layout = QHBoxLayout()

        self.tipo_label = QLabel()
        self.tipo_combo = QComboBox()

        tipo_layout.addWidget(self.tipo_label)
        tipo_layout.addWidget(self.tipo_combo)

        layout.addLayout(tipo_layout)

        top_layout = QHBoxLayout()

        desc_layout = QVBoxLayout()
        self.descricao_label = QLabel()
        self.descricao_edit = QLineEdit()
        self.descricao_edit.setMinimumHeight(28)

        desc_layout.addWidget(self.descricao_label)
        desc_layout.addWidget(self.descricao_edit)

        data_layout = QVBoxLayout()
        self.data_label = QLabel()
        self.data_edit = QDateEdit()
        self.data_edit.setCalendarPopup(True)
        self.data_edit.setMinimumHeight(28)

        data_layout.addWidget(self.data_label)
        data_layout.addWidget(self.data_edit)

        top_layout.addLayout(desc_layout)
        top_layout.addLayout(data_layout)
        top_layout.setStretch(0, 2)
        top_layout.setStretch(1, 1)

        layout.addLayout(top_layout)

        mid_layout = QHBoxLayout()

        fav_layout = QVBoxLayout()
        self.lbl_favorecido = QLabel()

        fav_row = QHBoxLayout()
        self.favorecido_combo = QComboBox()
        self.favorecido_combo.setMinimumHeight(28)

        self.btn_add_fav = QPushButton("+")
        self.btn_add_fav.setIcon(self._icon("add"))
        self.btn_add_fav.setFixedSize(28, 28)

        fav_row.addWidget(self.favorecido_combo)
        fav_row.addWidget(self.btn_add_fav)

        fav_layout.addWidget(self.lbl_favorecido)
        fav_layout.addLayout(fav_row)

        cat_layout = QVBoxLayout()
        self.lbl_categoria = QLabel()

        cat_row = QHBoxLayout()
        self.categoria_combo = QComboBox()
        self.categoria_combo.setMinimumHeight(28)

        self.btn_add_cat = QPushButton("+")
        self.btn_add_cat.setIcon(self._icon("add"))
        self.btn_add_cat.setFixedSize(28, 28)

        cat_row.addWidget(self.categoria_combo)
        cat_row.addWidget(self.btn_add_cat)

        cat_layout.addWidget(self.lbl_categoria)
        cat_layout.addLayout(cat_row)

        mid_layout.addLayout(fav_layout)
        mid_layout.addLayout(cat_layout)

        layout.addLayout(mid_layout)

        valor_layout = QVBoxLayout()

        self.valor_label = QLabel()
        self.valor_edit = QLineEdit()
        self.valor_edit.setMinimumHeight(28)

        valor_layout.addWidget(self.valor_label)
        valor_layout.addWidget(self.valor_edit)

        layout.addLayout(valor_layout)

        notas_layout = QVBoxLayout()

        self.notas_label = QLabel()
        self.notas_edit = QTextEdit()

        notas_layout.addWidget(self.notas_label)
        notas_layout.addWidget(self.notas_edit)

        layout.addLayout(notas_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancelar = QPushButton()
        self.btn_salvar = QPushButton()
        self.btn_cancelar.setObjectName("secondaryButton")

        btn_layout.addWidget(self.btn_cancelar)
        btn_layout.addWidget(self.btn_salvar)

        layout.addLayout(btn_layout)

    # ======================================================
    # TRADUÇÃO
    # ======================================================
    def _atualizar_textos(self):
        self.setWindowTitle(
            TranslatorApp.get("Novo Lançamento")
        )

        self.tipo_label.setText(
            TranslatorApp.get("Tipo:")
        )

        self.descricao_label.setText(
            TranslatorApp.get("Descrição:")
        )

        self.descricao_edit.setPlaceholderText(
            TranslatorApp.get("Descrição")
        )

        self.data_label.setText(
            TranslatorApp.get("Data:")
        )

        self.lbl_categoria.setText(
            TranslatorApp.get("Categoria:")
        )

        self.valor_label.setText(
            TranslatorApp.get("Valor:")
        )

        self.valor_edit.setPlaceholderText(
            TranslatorApp.get("0,00")
        )

        self.notas_label.setText(
            TranslatorApp.get("Notas:")
        )

        self.btn_cancelar.setText(
            TranslatorApp.get("Cancelar")
        )

        self.btn_salvar.setText(
            TranslatorApp.get("Salvar")
        )

        self._update_label()

    # ======================================================
    # ICON
    # ======================================================
    def _icon(self, nome):
        if nome in self._icon_cache:
            return self._icon_cache[nome]

        try:
            path = IonPath.resource("assets", "icons", f"{nome}.svg")
            icon = QIcon(path) if os.path.exists(path) else QIcon()
            self._icon_cache[nome] = icon
            return icon

        except Exception:
            logger.exception("Erro ao carregar ícone: %s", nome)
            return QIcon()

    # ======================================================
    # CONFIG
    # ======================================================
    def _configurar_ui(self):
        self.tipo_combo.clear()
        self.tipo_combo.addItem("Despesa", "Despesa")
        self.tipo_combo.addItem("Receita", "Receita")
        self.tipo_combo.setCurrentIndex(0)

        self.data_edit.setDate(QDate.currentDate())
        self.btn_salvar.setDefault(True)
        self.descricao_edit.setFocus()
        self.setTabOrder(self.tipo_combo, self.descricao_edit)
        self.setTabOrder(self.descricao_edit, self.data_edit)
        self.setTabOrder(self.data_edit, self.favorecido_combo)
        self.setTabOrder(self.favorecido_combo, self.categoria_combo)
        self.setTabOrder(self.categoria_combo, self.valor_edit)
        self.setTabOrder(self.valor_edit, self.notas_edit)
        self.setTabOrder(self.notas_edit, self.btn_salvar)

    # ======================================================
    # DADOS
    # ======================================================
    def _carregar_categorias(self, selecionar_id=None):
        self.categoria_combo.clear()
        self.categoria_combo.addItem(
            TranslatorApp.get("Nenhum"),
            None
        )

        categorias = self.category_controller.get_all_categories() or []

        for categoria in categorias:
            self.categoria_combo.addItem(
                categoria.get("Nome", ""),
                categoria.get("ID_Categoria")
            )

        if selecionar_id:
            index = self.categoria_combo.findData(selecionar_id)
            if index >= 0:
                self.categoria_combo.setCurrentIndex(index)

    def _carregar_favorecidos(self, selecionar_id=None):
        self.favorecido_combo.clear()
        self.favorecido_combo.addItem(
            TranslatorApp.get("Nenhum"),
            None
        )

        favorecidos = self.favorecido_controller.listar_favorecidos() or []

        for favorecido in favorecidos:
            self.favorecido_combo.addItem(
                favorecido.get("Nome", ""),
                favorecido.get("ID_Favorecido")
            )

        if selecionar_id:
            index = self.favorecido_combo.findData(selecionar_id)
            if index >= 0:
                self.favorecido_combo.setCurrentIndex(index)

    # ======================================================
    # EVENTOS
    # ======================================================
    def _conectar_eventos(self):
        self.btn_salvar.clicked.connect(self.salvar)
        self.btn_cancelar.clicked.connect(self.reject)

        self.valor_edit.textChanged.connect(self._formatar_moeda)
        self.tipo_combo.currentIndexChanged.connect(self._update_label)

        self.btn_add_cat.clicked.connect(self._adicionar_categoria)
        self.btn_add_fav.clicked.connect(self._adicionar_favorecido)

    def _adicionar_categoria(self):
        try:
            from views.categoria_dialog import CategoriaDialog

            dialog = CategoriaDialog(parent=self)

            if dialog.exec_() == QDialog.Accepted:
                dados = dialog.get_data()

                nova_id = self.category_controller.add_category(
                    dados["Nome"],
                    dados["Tipo"]
                )

                self._carregar_categorias(nova_id)

        except Exception as e:
            logger.exception("Erro ao adicionar categoria")
            QMessageBox.warning(
                self,
                TranslatorApp.get("Erro"),
                str(e)
            )

    def _adicionar_favorecido(self):
        try:
            from views.FavorecidoDialog import FavorecidoDialog

            dialog = FavorecidoDialog(parent=self)

            if dialog.exec_() == QDialog.Accepted:
                dados = dialog.get_dados()

                novo_id = self.favorecido_controller.criar_favorecido(
                    dados
                )

                self._carregar_favorecidos(novo_id)

        except Exception as e:
            logger.exception("Erro ao adicionar favorecido")
            QMessageBox.warning(
                self,
                TranslatorApp.get("Erro"),
                str(e)
            )

    # ======================================================
    # LABEL DINÂMICA
    # ======================================================
    def _update_label(self):
        tipo = self.tipo_combo.currentData()

        if tipo == "Receita":
            self.lbl_favorecido.setText(
                TranslatorApp.get("Receber de:")
            )
        else:
            self.lbl_favorecido.setText(
                TranslatorApp.get("Pagar para:")
            )

    # ======================================================
    # MOEDA
    # ======================================================
    def _formatar_moeda(self):
        texto = re.sub(r"[^\d]", "", self.valor_edit.text())

        if not texto:
            return

        valor = int(texto) / 100

        self.valor_edit.blockSignals(True)
        self.valor_edit.setText(
            f"{valor:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
        self.valor_edit.blockSignals(False)

    # ======================================================
    # SALVAR
    # ======================================================
    def salvar(self):
        try:
            descricao = self.descricao_edit.text().strip()

            if not descricao:
                raise ValueError(
                    TranslatorApp.get("Descrição obrigatória")
                )

            valor_texto = self.valor_edit.text().strip()

            if not valor_texto:
                raise ValueError(
                    TranslatorApp.get("Valor obrigatório")
                )

            valor = float(
                valor_texto
                .replace(".", "")
                .replace(",", ".")
            )

            if valor <= 0:
                raise ValueError(
                    TranslatorApp.get("Valor deve ser maior que zero.")
                )

            tipo = self.tipo_combo.currentData()
            valor = -abs(valor) if tipo == "Despesa" else abs(valor)

            dados = {
                "Descricao": descricao,
                "Valor": valor,
                "Data": self.data_edit.date().toString("yyyy-MM-dd"),
                "ID_Conta": self.id_conta,
                "Tipo": tipo,
                "ID_Categoria": self.categoria_combo.currentData(),
                "ID_Favorecido": self.favorecido_combo.currentData(),
                "Notas": self.notas_edit.toPlainText(),
            }

            sucesso = self.main_controller.inserir_lancamento(dados)

            if not sucesso:
                raise RuntimeError(
                    TranslatorApp.get("Não foi possível salvar o lançamento.")
                )

            self.accept()

        except Exception as e:
            QMessageBox.warning(
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
