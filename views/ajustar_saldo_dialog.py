import logging
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
)

from controllers.account_controller import AccountController
from core.translator_app import TranslatorApp

logger = logging.getLogger(__name__)


class AjustarSaldoDialog(QDialog):
    """
    Diálogo para ajuste manual de saldo da conta.
    """

    def __init__(self, parent=None, conta=None):
        super().__init__(parent)

        if not conta:
            raise ValueError("Conta não informada para ajuste de saldo.")

        self.conta = conta
        self.controller = AccountController()

        self.setMinimumWidth(300)

        self._init_ui()

        # 🔥 título base
        self.setWindowTitle("Ajustar Saldo da Conta")

        # 🔥 tradução automática global
        TranslatorApp.bind(self._atualizar_textos,self)
        self._atualizar_textos()

    def _atualizar_textos(self):
        self.setWindowTitle(TranslatorApp.get("Ajustar Saldo da Conta"))
        self.lbl_conta.setText(self._get_conta_text())
        self.lbl_saldo.setText(TranslatorApp.get("Novo saldo") + ":")
        self.btn_salvar.setText(TranslatorApp.get("Salvar Ajuste"))
        self.btn_cancelar.setText(TranslatorApp.get("Cancelar"))

    # --------------------------------------------------
    # UI
    # --------------------------------------------------
    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Conta (dinâmico)
        self.lbl_conta = QLabel()
        layout.addWidget(self.lbl_conta)

        # Label saldo
        self.lbl_saldo = QLabel("Novo saldo:")
        layout.addWidget(self.lbl_saldo)

        # Input
        self.saldo_edit = QLineEdit()
        self.saldo_edit.setPlaceholderText("Ex: 1500,00")
        layout.addWidget(self.saldo_edit)

        # Botão salvar
        self.btn_salvar = QPushButton("Salvar Ajuste")
        self.btn_salvar.clicked.connect(self.salvar)
        layout.addWidget(self.btn_salvar)

        # Botão cancelar
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.clicked.connect(self.reject)
        layout.addWidget(self.btn_cancelar)

    # --------------------------------------------------
    # TEXTO DINÂMICO (AGORA REATIVO)
    # --------------------------------------------------
    def _get_conta_text(self):
        return f"{TranslatorApp.get('Conta')}: {self.conta.get('Nome_Conta', '')}"

    # --------------------------------------------------
    # AÇÃO
    # --------------------------------------------------
    def salvar(self):
        texto = self.saldo_edit.text().strip().replace(".", "").replace(",", ".")

        try:
            novo_saldo = float(texto)
        except ValueError:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Saldo inválido."),
            )
            return

        try:
            self.controller.ajustar_saldo(
                id_conta=self.conta["ID_Conta"],
                novo_saldo=novo_saldo
            )

            QMessageBox.information(
                self,
                TranslatorApp.get("Sucesso"),
                TranslatorApp.get("Saldo ajustado com sucesso."),
            )
            self.accept()

        except Exception as e:
            logger.exception("Erro ao ajustar saldo")
            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                str(e)
            )

    #--------------------------------------------------
    # CICLO DE VIDA
    #--------------------------------------------------
    def closeEvent(self, event):
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass

        super().closeEvent(event)
