import logging
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QDialogButtonBox,
    QMessageBox,
    QComboBox,
    QLabel,
)

from controllers.account_controller import AccountController
from core.session import Session
from core.translator_app import TranslatorApp
from core.window_manager import WindowManager

logger = logging.getLogger(__name__)


class CriarContaDialog(QDialog):
    """
    Dialog responsável APENAS por coletar dados da UI
    e chamar o Controller.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.controller = AccountController()

        # 🔥 título base (auto traduzido)
        self.setWindowTitle("Criar Conta")

        self.setMinimumSize(340, 260)
        self.resize(420, 300)

        self._init_ui()

        # 🔥 tradução automática global
        TranslatorApp.bind(self._on_translate, self)
        self._on_translate()
    
    # ==================================================
    # REATIVIDADE
    # ==================================================
    def _on_translate(self, *_):
        self.setWindowTitle(TranslatorApp.get("Criar Conta"))
        self.lbl_nome.setText(TranslatorApp.get("Nome da Conta") + ":")
        self.lbl_instituicao.setText(TranslatorApp.get("Instituição") + ":")
        self.lbl_tipo.setText(TranslatorApp.get("Tipo") + ":")
        self.lbl_saldo.setText(TranslatorApp.get("Saldo Inicial") + ":")
        self.buttons.button(QDialogButtonBox.Ok).setText(TranslatorApp.get("Salvar"))
        self.buttons.button(QDialogButtonBox.Cancel).setText(
            TranslatorApp.get("Cancelar")
        )
    # --------------------------------------------------
    # UI
    # --------------------------------------------------
    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Nome
        self.lbl_nome = QLabel("Nome da Conta:")
        self.nome_input = QLineEdit()
        self.nome_input.setPlaceholderText("Ex: Conta Principal")

        form.addRow(self.lbl_nome, self.nome_input)

        # Instituição
        self.lbl_instituicao = QLabel("Instituição:")
        self.instituicao_input = QLineEdit()
        self.instituicao_input.setPlaceholderText("Ex: Nubank, Itaú")

        form.addRow(self.lbl_instituicao, self.instituicao_input)

        # Tipo
        self.lbl_tipo = QLabel("Tipo:")
        self.tipo_combo = QComboBox()

        tipos = [
            ("Corrente", "Corrente"),
            ("Poupança", "Poupança"),
            ("Investimento", "Investimento"),
        ]

        for texto, valor in tipos:
            self.tipo_combo.addItem(texto, valor)

        form.addRow(self.lbl_tipo, self.tipo_combo)

        # Saldo
        self.lbl_saldo = QLabel("Saldo Inicial:")
        self.saldo_input = QLineEdit()
        self.saldo_input.setPlaceholderText("0,00")

        form.addRow(self.lbl_saldo, self.saldo_input)

        layout.addLayout(form)

        # Botões
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )

        self.buttons.accepted.connect(self._salvar)
        self.buttons.rejected.connect(self.reject)

        layout.addWidget(self.buttons)

        # texto base (auto traduzido depois)
        self.buttons.button(QDialogButtonBox.Ok).setText("Salvar")
        self.buttons.button(QDialogButtonBox.Cancel).setText("Cancelar")

    # --------------------------------------------------
    # SALVAR
    # --------------------------------------------------
    def _salvar(self):
        usuario = Session.get_usuario()

        if not usuario:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Usuário não autenticado."),
            )
            return

        nome = self.nome_input.text().strip()

        if not nome:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Atenção"),
                TranslatorApp.get("Nome da conta é obrigatório."),
            )
            return

        dados = {
            "Nome_Conta": nome,
            "Instituicao": self.instituicao_input.text().strip(),
            "Tipo": self.tipo_combo.currentData(),
            "Saldo_Atual": self.saldo_input.text().strip() or "0",
            "ID_Usuario": usuario["ID_Usuario"],
        }

        try:
            self.controller.create_account(dados)

            QMessageBox.information(
                self,
                TranslatorApp.get("Sucesso"),
                TranslatorApp.get("Conta criada com sucesso."),
            )
            self.accept()

        except ValueError as e:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Atenção"),
                str(e)
            )

        except Exception:
            logger.exception("Erro ao criar conta")
            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Não foi possível criar a conta."),
            )

    def showEvent(self, event):
        super().showEvent(event)
        WindowManager.fit_dialog(self, self.parentWidget())
    # ======================================================
    # CICLO DE VIDA
    # ======================================================
    def closeEvent(self, event):
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass

        super().closeEvent(event)
