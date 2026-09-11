# -*- coding: utf-8 -*-
import re

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QPushButton,
    QTextEdit, QDateEdit, QSpinBox, QSpacerItem,
    QSizePolicy, QMessageBox
)
from PyQt5.QtCore import QDate
from PyQt5.QtGui import QIcon

from controllers.fatura_controller import FaturaController
from controllers.favorecido_controller import FavorecidoController
from controllers.category_controller import CategoryController

from views.FavorecidoDialog import FavorecidoDialog
from views.categoria_dialog import CategoriaDialog
from views.animated_add_button import AnimatedAddButton
from utilitarios.ion_path import IonPath


class FaturaDialog(QDialog):

    def __init__(self, parent=None, id_cartao=None):
        super().__init__(parent)

        if id_cartao is None:
            raise ValueError("Cartão inválido")

        self.id_cartao = id_cartao

        self.fatura_controller = FaturaController()
        self.favorecido_controller = FavorecidoController()
        self.category_controller = CategoryController()

        self.setup_ui()
        self._carregar_dados()
        self._conectar_eventos()

    # ======================================================
    # UI
    # ======================================================
    def setup_ui(self):
        self.setObjectName("FaturaDialog")
        self.setWindowTitle("Nova despesa no cartão")
        self.resize(594, 333)

        self.main_layout = QVBoxLayout(self)

        self.top_layout = QHBoxLayout()

        # ==================================================
        # ESQUERDA
        # ==================================================
        self.form_left = QFormLayout()

        self.descricao_edit = QLineEdit()
        self.form_left.addRow("Descrição:", self.descricao_edit)

        self.lbl_favorecido = QLabel("Estabelecimento:")
        self.fav_layout = QHBoxLayout()

        self.favorecido_combo = QComboBox()

        self.btn_add_fav = AnimatedAddButton(
            "Adicionar estabelecimento",
            QIcon(IonPath.icon("add")),
            self,
        )

        self.fav_layout.addWidget(self.favorecido_combo)
        self.fav_layout.addWidget(self.btn_add_fav)

        self.form_left.addRow(self.lbl_favorecido, self.fav_layout)

        self.lbl_categoria = QLabel("Categoria:")
        self.cat_layout = QHBoxLayout()

        self.categoria_combo = QComboBox()

        self.btn_add_cat = AnimatedAddButton(
            "Adicionar categoria",
            QIcon(IonPath.icon("add")),
            self,
        )

        self.cat_layout.addWidget(self.categoria_combo)
        self.cat_layout.addWidget(self.btn_add_cat)

        self.form_left.addRow(self.lbl_categoria, self.cat_layout)

        self.top_layout.addLayout(self.form_left)

        # ==================================================
        # DIREITA
        # ==================================================
        self.form_right = QFormLayout()

        self.data_edit = QDateEdit()
        self.data_edit.setCalendarPopup(True)
        self.form_right.addRow("Data:", self.data_edit)

        self.fatura_combo = QComboBox()
        self.form_right.addRow("Fatura:", self.fatura_combo)

        self.parcelas_spin = QSpinBox()
        self.parcelas_spin.setRange(1, 36)
        self.form_right.addRow("Parcelas:", self.parcelas_spin)

        self.top_layout.addLayout(self.form_right)

        self.main_layout.addLayout(self.top_layout)

        # ==================================================
        # VALOR
        # ==================================================
        self.valor_edit = QLineEdit()
        self.valor_edit.setPlaceholderText("0,00")

        valor_layout = QVBoxLayout()
        valor_layout.addWidget(QLabel("Valor:"))
        valor_layout.addWidget(self.valor_edit)

        self.main_layout.addLayout(valor_layout)

        # ==================================================
        # NOTAS
        # ==================================================
        self.notas_edit = QTextEdit()

        notas_layout = QVBoxLayout()
        notas_layout.addWidget(QLabel("Notas:"))
        notas_layout.addWidget(self.notas_edit)

        self.main_layout.addLayout(notas_layout)

        # ==================================================
        # BOTÕES
        # ==================================================
        self.buttons_layout = QHBoxLayout()

        self.buttons_layout.addItem(
            QSpacerItem(
                0,
                0,
                QSizePolicy.Expanding,
                QSizePolicy.Minimum
            )
        )

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_salvar = QPushButton("Salvar")

        self.buttons_layout.addWidget(self.btn_cancelar)
        self.buttons_layout.addWidget(self.btn_salvar)

        self.main_layout.addLayout(self.buttons_layout)

        self.data_edit.setDate(QDate.currentDate())

    # ======================================================
    # LOAD
    # ======================================================
    def _carregar_dados(self):
        self._carregar_categorias()
        self._carregar_favorecidos()
        self._carregar_ciclos()

    def _carregar_categorias(self, selecionar_id=None):
        self.categoria_combo.clear()
        self.categoria_combo.addItem("Nenhum", None)

        categorias = self.category_controller.get_all_categories() or []

        for categoria in categorias:
            self.categoria_combo.addItem(
                categoria["Nome"],
                categoria["ID_Categoria"]
            )

        if selecionar_id:
            index = self.categoria_combo.findData(selecionar_id)
            if index >= 0:
                self.categoria_combo.setCurrentIndex(index)

    def _carregar_favorecidos(self, selecionar_id=None):
        self.favorecido_combo.clear()
        self.favorecido_combo.addItem("Nenhum", None)

        favorecidos = self.favorecido_controller.listar_favorecidos() or []

        for favorecido in favorecidos:
            self.favorecido_combo.addItem(
                favorecido["Nome"],
                favorecido["ID_Favorecido"]
            )

        if selecionar_id:
            index = self.favorecido_combo.findData(selecionar_id)
            if index >= 0:
                self.favorecido_combo.setCurrentIndex(index)

    def _carregar_ciclos(self):
        self.fatura_combo.clear()

        ciclos = self.fatura_controller.listar_ciclos(self.id_cartao) or []

        for ciclo in ciclos:
            texto = f"{ciclo['Mes']:02d}/{ciclo['Ano']}"
            self.fatura_combo.addItem(texto, ciclo)

    # ======================================================
    # EVENTOS
    # ======================================================
    def _conectar_eventos(self):
        self.btn_salvar.clicked.connect(self.salvar)
        self.btn_cancelar.clicked.connect(self.reject)

        self.valor_edit.textChanged.connect(self._formatar_moeda)

        self.btn_add_cat.clicked.connect(self.adicionar_categoria)
        self.btn_add_fav.clicked.connect(self.adicionar_favorecido)

    # ======================================================
    # FORMATAÇÃO
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
    # ADICIONAR CATEGORIA
    # ======================================================
    def adicionar_categoria(self):
        try:
            dialog = CategoriaDialog(self)

            if dialog.exec_() == QDialog.Accepted:
                dados = dialog.get_data()
                nova_id = self.category_controller.add_category(
                        dados["Nome"],
                        dados["Tipo"]
                    )

                self._carregar_categorias(nova_id)

        except Exception as e:
            QMessageBox.warning(
                self,
                "Erro",
                f"Erro ao adicionar categoria:\n{e}"
            )
    # ======================================================
    # ADICIONAR FAVORECIDO
    # ======================================================
    def adicionar_favorecido(self):
        try:
            dialog = FavorecidoDialog(parent=self)

            if dialog.exec_() == QDialog.Accepted:
                id_favorecido = dialog.get_id()
                self._carregar_favorecidos(id_favorecido)

        except Exception as e:
            QMessageBox.warning(
                self,
                "Erro",
                f"Erro ao adicionar favorecido:\n{e}"
            )

    # ======================================================
    # SALVAR
    # ======================================================
    def dados_formulario(self):
        """Valida e retorna os campos; compartilhado com a tela de edição."""
        descricao = self.descricao_edit.text().strip()
        if not descricao:
            raise ValueError("Descrição obrigatória")
        valor_texto = self.valor_edit.text().replace(".", "").replace(",", ".").strip()
        if not valor_texto:
            raise ValueError("Valor obrigatório")
        valor = abs(float(valor_texto))
        if valor <= 0:
            raise ValueError("Valor deve ser maior que zero")
        ciclo = self.fatura_combo.currentData()
        if not ciclo:
            raise ValueError("Selecione a fatura")
        return {
            "ID_Cartao": self.id_cartao,
            "Descricao": descricao,
            "Valor": valor,
            "Data": self.data_edit.date().toString("yyyy-MM-dd"),
            "Competencia_Mes": ciclo["Mes"],
            "Competencia_Ano": ciclo["Ano"],
            "Num_Parcelas": int(self.parcelas_spin.value()),
            "ID_Categoria": self.categoria_combo.currentData(),
            "ID_Favorecido": self.favorecido_combo.currentData(),
            "Notas": self.notas_edit.toPlainText(),
            "Paga": 0,
            "Previsto": 0,
        }

    def salvar(self):
        try:
            self.fatura_controller.registrar_despesa_cartao(self.dados_formulario())

            self.accept()

        except Exception as e:
            QMessageBox.warning(
                self,
                "Erro",
                str(e)
            )
