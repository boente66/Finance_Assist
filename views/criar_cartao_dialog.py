from core.regional_format import RegionalFormat
# -*- coding: utf-8 -*-
import logging

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QDoubleSpinBox,
    QSpinBox,
    QCheckBox,
    QMessageBox,
)

from controllers.fatura_controller import FaturaController
from core.translator_app import TranslatorApp

logger = logging.getLogger(__name__)


# ==========================================================
# CRIAR CARTÃO
# ==========================================================
class CriarCartaoDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.controller = FaturaController()

        self.setMinimumWidth(360)

        self._init_ui()

        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

    # ======================================================
    # UI
    # ======================================================
    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.lbl_nome = QLabel()
        layout.addWidget(self.lbl_nome)

        self.nome_edit = QLineEdit()
        layout.addWidget(self.nome_edit)

        self.lbl_limite = QLabel()
        layout.addWidget(self.lbl_limite)

        self.limite_edit = QDoubleSpinBox()
        self.limite_edit.setPrefix("R$ "); RegionalFormat.configure_widget(self.limite_edit)
        self.limite_edit.setRange(0.01, 1_000_000.00)
        self.limite_edit.setDecimals(2)
        layout.addWidget(self.limite_edit)

        self.lbl_fechamento = QLabel()
        layout.addWidget(self.lbl_fechamento)

        self.fechamento_edit = QSpinBox()
        self.fechamento_edit.setRange(1, 31)
        layout.addWidget(self.fechamento_edit)

        self.lbl_vencimento = QLabel()
        layout.addWidget(self.lbl_vencimento)

        self.vencimento_edit = QSpinBox()
        self.vencimento_edit.setRange(1, 31)
        layout.addWidget(self.vencimento_edit)

        self.ativo_checkbox = QCheckBox()
        self.ativo_checkbox.setChecked(True)
        layout.addWidget(self.ativo_checkbox)

        btns = QHBoxLayout()

        self.salvar_btn = QPushButton()
        self.cancelar_btn = QPushButton()

        self.salvar_btn.clicked.connect(self._salvar)
        self.cancelar_btn.clicked.connect(self.reject)

        btns.addWidget(self.salvar_btn)
        btns.addWidget(self.cancelar_btn)

        layout.addLayout(btns)

    # ======================================================
    # TRADUÇÃO
    # ======================================================
    def _atualizar_textos(self):
        self.setWindowTitle(
            TranslatorApp.get("Cadastrar Cartão")
        )

        self.lbl_nome.setText(
            TranslatorApp.get("Nome do cartão")
        )

        self.nome_edit.setPlaceholderText(
            TranslatorApp.get("Ex: Nubank, Itaú")
        )

        self.lbl_limite.setText(
            TranslatorApp.get("Limite do cartão")
        )

        self.lbl_fechamento.setText(
            TranslatorApp.get("Dia de fechamento da fatura")
        )

        self.lbl_vencimento.setText(
            TranslatorApp.get("Dia de vencimento da fatura")
        )

        self.ativo_checkbox.setText(
            TranslatorApp.get("Cartão ativo")
        )

        self.salvar_btn.setText(
            TranslatorApp.get("Salvar")
        )

        self.cancelar_btn.setText(
            TranslatorApp.get("Cancelar")
        )

    # ======================================================
    # VALIDAÇÃO
    # ======================================================
    def _validar(self):
        nome = self.nome_edit.text().strip()

        if not nome:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Atenção"),
                TranslatorApp.get("Nome do cartão é obrigatório.")
            )
            return False

        if self.fechamento_edit.value() == self.vencimento_edit.value():
            QMessageBox.warning(
                self,
                TranslatorApp.get("Atenção"),
                TranslatorApp.get(
                    "Dia de fechamento não pode ser igual ao dia de vencimento."
                )
            )
            return False

        return True

    # ======================================================
    # SALVAR
    # ======================================================
    def _salvar(self):
        if not self._validar():
            return

        dados = {
            "nome": self.nome_edit.text().strip(),
            "limite": round(self.limite_edit.value(), 2),
            "dia_fechamento": self.fechamento_edit.value(),
            "dia_vencimento": self.vencimento_edit.value(),
            "ativo": 1 if self.ativo_checkbox.isChecked() else 0,
        }

        try:
            self.controller.criar_cartao(dados)

            QMessageBox.information(
                self,
                TranslatorApp.get("Sucesso"),
                TranslatorApp.get("Cartão criado com sucesso.")
            )

            self.accept()

        except Exception:
            logger.exception("Erro ao criar cartão")

            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Erro ao salvar cartão.")
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


# ==========================================================
# EDITAR CARTÃO
# ==========================================================
class EditCartaoDialog(QDialog):

    def __init__(self, parent=None, cartao=None):
        super().__init__(parent)

        self.cartao = cartao or {}
        self.controller = FaturaController()

        self.setMinimumWidth(360)

        self._init_ui()
        self._preencher_campos()

        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

    # ======================================================
    # UI
    # ======================================================
    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.lbl_nome = QLabel()
        layout.addWidget(self.lbl_nome)

        self.nome_edit = QLineEdit()
        layout.addWidget(self.nome_edit)

        self.lbl_limite = QLabel()
        layout.addWidget(self.lbl_limite)

        self.limite_edit = QDoubleSpinBox()
        self.limite_edit.setPrefix("R$ "); RegionalFormat.configure_widget(self.limite_edit)
        self.limite_edit.setRange(0.01, 1_000_000.00)
        self.limite_edit.setDecimals(2)
        layout.addWidget(self.limite_edit)

        self.lbl_fechamento = QLabel()
        layout.addWidget(self.lbl_fechamento)

        self.fechamento_edit = QSpinBox()
        self.fechamento_edit.setRange(1, 31)
        layout.addWidget(self.fechamento_edit)

        self.lbl_vencimento = QLabel()
        layout.addWidget(self.lbl_vencimento)

        self.vencimento_edit = QSpinBox()
        self.vencimento_edit.setRange(1, 31)
        layout.addWidget(self.vencimento_edit)

        self.ativo_checkbox = QCheckBox()
        layout.addWidget(self.ativo_checkbox)

        btns = QHBoxLayout()

        self.salvar_btn = QPushButton()
        self.cancelar_btn = QPushButton()

        self.salvar_btn.clicked.connect(self._salvar)
        self.cancelar_btn.clicked.connect(self.reject)

        btns.addWidget(self.salvar_btn)
        btns.addWidget(self.cancelar_btn)

        layout.addLayout(btns)

    # ======================================================
    # TRADUÇÃO
    # ======================================================
    def _atualizar_textos(self):
        self.setWindowTitle(
            TranslatorApp.get("Editar Cartão")
        )

        self.lbl_nome.setText(
            TranslatorApp.get("Nome do cartão")
        )

        self.nome_edit.setPlaceholderText(
            TranslatorApp.get("Ex: Nubank, Itaú")
        )

        self.lbl_limite.setText(
            TranslatorApp.get("Limite do cartão")
        )

        self.lbl_fechamento.setText(
            TranslatorApp.get("Dia de fechamento da fatura")
        )

        self.lbl_vencimento.setText(
            TranslatorApp.get("Dia de vencimento da fatura")
        )

        self.ativo_checkbox.setText(
            TranslatorApp.get("Cartão ativo")
        )

        self.salvar_btn.setText(
            TranslatorApp.get("Salvar")
        )

        self.cancelar_btn.setText(
            TranslatorApp.get("Cancelar")
        )

    # ======================================================
    # DADOS
    # ======================================================
    def _preencher_campos(self):
        self.nome_edit.setText(
            self.cartao.get("Nome")
            or self.cartao.get("nome", "")
        )

        self.limite_edit.setValue(
            float(
                self.cartao.get("Limite")
                or self.cartao.get("limite", 0)
            )
        )

        self.fechamento_edit.setValue(
            int(
                self.cartao.get("Dia_Fechamento")
                or self.cartao.get("dia_fechamento", 1)
            )
        )

        self.vencimento_edit.setValue(
            int(
                self.cartao.get("Dia_Vencimento")
                or self.cartao.get("dia_vencimento", 1)
            )
        )

        ativo = self.cartao.get("Ativo")

        if ativo is None:
            ativo = self.cartao.get("ativo", 1)

        self.ativo_checkbox.setChecked(
            bool(ativo)
        )

    # ======================================================
    # VALIDAÇÃO
    # ======================================================
    def _validar(self):
        nome = self.nome_edit.text().strip()

        if not nome:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Atenção"),
                TranslatorApp.get("Nome do cartão é obrigatório.")
            )
            return False

        if self.fechamento_edit.value() == self.vencimento_edit.value():
            QMessageBox.warning(
                self,
                TranslatorApp.get("Atenção"),
                TranslatorApp.get(
                    "Dia de fechamento não pode ser igual ao dia de vencimento."
                )
            )
            return False

        return True

    # ======================================================
    # SALVAR
    # ======================================================
    def _salvar(self):
        if not self._validar():
            return

        dados = {
            "nome": self.nome_edit.text().strip(),
            "limite": round(self.limite_edit.value(), 2),
            "dia_fechamento": self.fechamento_edit.value(),
            "dia_vencimento": self.vencimento_edit.value(),
            "ativo": 1 if self.ativo_checkbox.isChecked() else 0,
        }

        try:
            self.controller.editar_cartao(
                self.cartao["ID_Cartao"],
                dados
            )

            QMessageBox.information(
                self,
                TranslatorApp.get("Sucesso"),
                TranslatorApp.get("Cartão atualizado com sucesso.")
            )

            self.accept()

        except Exception:
            logger.exception("Erro ao editar cartão")

            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Erro ao salvar cartão.")
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
