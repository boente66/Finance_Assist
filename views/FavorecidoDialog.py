# -*- coding: utf-8 -*-
import logging

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QMessageBox
)

from core.translator_app import TranslatorApp
from utilitarios.name_format import NameFormat
from form.favorecido_form import FavorecidoForm
from controllers.favorecido_controller import FavorecidoController

logger = logging.getLogger(__name__)


class FavorecidoDialog(QDialog):

    def __init__(self, parent=None, favorecido=None):
        super().__init__(parent)

        self.controller = FavorecidoController()
        self.favorecido = favorecido or {}
        self.dados = None

        self.setMinimumWidth(400)

        self._build_ui()
        self._carregar_dados()
        # A edição não converte silenciosamente PF em PJ (ou vice-versa).
        self.tipo_combo.setEnabled(not bool(self.favorecido))
        self._trocar_tipo()

        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

    # ==================================================
    # UI
    # ==================================================
    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.tipo_label = QLabel()
        layout.addWidget(self.tipo_label)

        self.tipo_combo = QComboBox()
        self.tipo_combo.addItem("Pessoa Física", "PF")
        self.tipo_combo.addItem("Pessoa Jurídica", "PJ")
        self.tipo_combo.currentIndexChanged.connect(self._trocar_tipo)
        layout.addWidget(self.tipo_combo)

        self.nome_label = QLabel()
        self.nome_edit = QLineEdit()
        layout.addWidget(self.nome_label)
        layout.addWidget(self.nome_edit)

        self.doc_label = QLabel()
        self.doc_edit = QLineEdit()
        layout.addWidget(self.doc_label)
        layout.addWidget(self.doc_edit)

        self.tel_label = QLabel()
        self.tel_edit = QLineEdit()
        layout.addWidget(self.tel_label)
        layout.addWidget(self.tel_edit)

        btns = QHBoxLayout()

        self.cancelar_btn = QPushButton()
        self.salvar_btn = QPushButton()

        self.cancelar_btn.clicked.connect(self.reject)
        self.salvar_btn.clicked.connect(self.salvar)

        btns.addStretch()
        btns.addWidget(self.cancelar_btn)
        btns.addWidget(self.salvar_btn)

        layout.addLayout(btns)

        self.doc_edit.editingFinished.connect(self._formatar_documento)
        self.tel_edit.editingFinished.connect(self._formatar_telefone)

    # ==================================================
    # TRADUÇÃO
    # ==================================================
    def _atualizar_textos(self):
        titulo = "Editar Favorecido" if self.favorecido else "Novo Favorecido"
        self.setWindowTitle(TranslatorApp.get(titulo))

        self.tipo_label.setText(TranslatorApp.get("Tipo"))
        self.tel_label.setText(TranslatorApp.get("Telefone"))

        self.cancelar_btn.setText(TranslatorApp.get("Cancelar"))
        self.salvar_btn.setText(TranslatorApp.get("Salvar"))

        self._trocar_tipo()

    # ==================================================
    # DADOS
    # ==================================================
    def _carregar_dados(self):
        if not self.favorecido:
            return

        id_fav = self.favorecido.get("ID_Favorecido")

        if id_fav:
            try:
                dados = self.controller.obter_favorecido(id_fav)
                if dados:
                    self.favorecido = dados
            except Exception:
                logger.exception("Erro ao carregar favorecido")

        tipo = self.favorecido.get("Tipo", "PF")

        index = self.tipo_combo.findData(tipo)
        if index >= 0:
            self.tipo_combo.setCurrentIndex(index)

        self.nome_edit.setText(
            self.favorecido.get("Nome")
            or self.favorecido.get("Razao_Social")
            or ""
        )

        documento = (
            self.favorecido.get("CPF")
            or self.favorecido.get("CNPJ")
            or self.favorecido.get("Documento")
            or ""
        )

        telefone = (
            self.favorecido.get("Telefone")
            or self.favorecido.get("Telefone_PF")
            or self.favorecido.get("Telefone_PJ")
            or ""
        )

        self.doc_edit.setText(NameFormat.format_documento(documento))
        self.tel_edit.setText(NameFormat.formatTelefone(telefone))

    # ==================================================
    # EVENTOS
    # ==================================================
    def _trocar_tipo(self):
        tipo = self.tipo_combo.currentData()

        if tipo == "PF":
            self.nome_label.setText(TranslatorApp.get("Nome"))
            self.doc_label.setText(TranslatorApp.get("CPF"))
        else:
            self.nome_label.setText(TranslatorApp.get("Razão Social"))
            self.doc_label.setText(TranslatorApp.get("CNPJ"))

    def _formatar_documento(self):
        tipo = self.tipo_combo.currentData()
        texto = self.doc_edit.text()

        if tipo == "PF":
            self.doc_edit.setText(NameFormat.formatCPF(texto))
        else:
            self.doc_edit.setText(NameFormat.formatCNPJ(texto))

    def _formatar_telefone(self):
        self.tel_edit.setText(
            NameFormat.formatTelefone(self.tel_edit.text())
        )

    # ==================================================
    # FORM
    # ==================================================
    def get_dados(self):
        form = FavorecidoForm(
            tipo=self.tipo_combo.currentData(),
            nome=self.nome_edit.text(),
            documento=self.doc_edit.text(),
            telefone=self.tel_edit.text()
        )

        form.validar()
        return form.to_dict()

    # ==================================================
    # SALVAR
    # ==================================================
    def salvar(self):
        try:
            self.dados = self.get_dados()

            id_fav = self.favorecido.get("ID_Favorecido")

            if id_fav:
                self.controller.atualizar_favorecido(id_fav, self.dados)
            else:
                id_fav = self.controller.adicionar_favorecido(self.dados)
                if not id_fav:
                    raise ValueError('Não foi possível cadastrar o favorecido.')
                self.dados['ID_Favorecido'] = id_fav

            self.accept()

        except Exception as e:
            logger.exception("Erro ao salvar favorecido")

            QMessageBox.warning(
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
