# -*- coding: utf-8 -*-
import logging

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QLineEdit,
    QMessageBox,
    QApplication,
)
from PyQt5.QtCore import Qt

from controllers.backup_controller import BackupController
from core.session import Session
from core.translator_app import TranslatorApp

logger = logging.getLogger(__name__)


class BackupView(QWidget):
    """
    Tela de Backup e Restauração do Sistema.
    """

    def __init__(self, parent=None, usuario=None, *args, **kwargs):
        super().__init__(parent)

        self.usuario = (
            usuario
            or Session.get_usuario()
            or getattr(parent, "usuario", None)
            or {}
        )

        self.controller = BackupController()

        self.setMinimumWidth(420)
        self.setWindowTitle("Backup e Restauração")

        self._init_ui()
        self._connect_events()

        autorizado = (
            str(self.usuario.get("Nivel_Acesso", "")).lower()
            == "admin"
        )
        self.btn_backup.setVisible(autorizado)
        self.btn_restaurar.setVisible(autorizado)
        self.senha_input.setEnabled(autorizado)

        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

    # -------------------------------------------------
    # UI
    # -------------------------------------------------
    def _init_ui(self):
        self.layout = QVBoxLayout(self)

        self.titulo = QLabel()
        self.titulo.setObjectName("pageTitle")
        self.titulo.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.titulo)

        self.label_senha = QLabel()

        self.senha_input = QLineEdit()
        self.senha_input.setEchoMode(QLineEdit.Password)

        self.layout.addWidget(self.label_senha)
        self.layout.addWidget(self.senha_input)

        botoes = QHBoxLayout()

        self.btn_backup = QPushButton()
        self.btn_backup.setObjectName("primaryButton")

        self.btn_restaurar = QPushButton()
        self.btn_restaurar.setObjectName("secondaryButton")

        botoes.addWidget(self.btn_backup)
        botoes.addWidget(self.btn_restaurar)

        self.layout.addLayout(botoes)
        self.layout.addStretch()

    # -------------------------------------------------
    # EVENTOS
    # -------------------------------------------------
    def _connect_events(self):
        self.btn_backup.clicked.connect(self.gerar_backup)
        self.btn_restaurar.clicked.connect(self.restaurar_backup)

    # -------------------------------------------------
    # TRADUÇÃO
    # -------------------------------------------------
    def _atualizar_textos(self, *_):
        self.setWindowTitle(
            TranslatorApp.get("Backup e Restauração")
        )

        self.titulo.setText(
            TranslatorApp.get("Backup e Restauração")
        )

        self.label_senha.setText(
            TranslatorApp.get("Senha do Backup") + ":"
        )

        self.senha_input.setPlaceholderText(
            TranslatorApp.get("Digite a senha")
        )

        self.btn_backup.setText(
            TranslatorApp.get("Gerar Backup")
        )

        self.btn_restaurar.setText(
            TranslatorApp.get("Restaurar Backup")
        )

    # -------------------------------------------------
    # UTIL
    # -------------------------------------------------
    def _bloquear_ui(self, estado=True):
        self.setEnabled(not estado)

        QApplication.setOverrideCursor(
            Qt.WaitCursor if estado else Qt.ArrowCursor
        )

    def _desbloquear_ui(self):
        self.setEnabled(True)
        QApplication.restoreOverrideCursor()

    def _limpar_senha(self):
        self.senha_input.clear()

    # -------------------------------------------------
    # BACKUP
    # -------------------------------------------------
    def gerar_backup(self):
        senha = self.senha_input.text().strip()

        if not senha:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Aviso"),
                TranslatorApp.get("Informe uma senha para o backup."),
            )
            return

        destino = QFileDialog.getExistingDirectory(
            self,
            TranslatorApp.get("Selecionar pasta para salvar o backup"),
        )

        if not destino:
            return

        self._bloquear_ui(True)

        try:
            resultado = self.controller.criar_backup(
                destino,
                senha
            )

            if not resultado.get("sucesso"):
                QMessageBox.warning(
                    self,
                    TranslatorApp.get("Aviso"),
                    TranslatorApp.get(resultado.get("mensagem", "Operação recusada."))
                )
                return

            arquivo = (resultado.get("dados") or {}).get("arquivo", "")

            QMessageBox.information(
                self,
                TranslatorApp.get("Sucesso"),
                (
                    TranslatorApp.get("Backup gerado com sucesso")
                    + f":\n{arquivo}"
                ),
            )

        except Exception as e:
            logger.exception("Erro ao gerar backup")

            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                str(e)
            )

        finally:
            self._desbloquear_ui()
            self._limpar_senha()

    # -------------------------------------------------
    # RESTAURAÇÃO
    # -------------------------------------------------
    def restaurar_backup(self):
        senha = self.senha_input.text().strip()

        if not senha:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Aviso"),
                TranslatorApp.get("Informe a senha do backup."),
            )
            return

        arquivo, _ = QFileDialog.getOpenFileName(
            self,
            TranslatorApp.get("Selecionar arquivo de backup"),
            "",
            (
                f"{TranslatorApp.get('Backup')} (*.kp);;"
                f"{TranslatorApp.get('Todos os arquivos')} (*)"
            ),
        )

        if not arquivo:
            return

        confirm = QMessageBox.question(
            self,
            TranslatorApp.get("Confirmação"),
            TranslatorApp.get(
                "Restaurar um backup irá substituir os dados atuais.\nDeseja continuar?"
            ),
            QMessageBox.Yes | QMessageBox.No,
        )

        if confirm != QMessageBox.Yes:
            return

        self._bloquear_ui(True)

        try:
            resultado = self.controller.restaurar_backup(
                arquivo,
                senha
            )

            if not resultado.get("sucesso"):
                QMessageBox.warning(
                    self,
                    TranslatorApp.get("Aviso"),
                    TranslatorApp.get(resultado.get("mensagem", "Operação recusada."))
                )
                return

            QMessageBox.information(
                self,
                TranslatorApp.get("Sucesso"),
                TranslatorApp.get(
                    "Backup restaurado com sucesso.\nReinicie o sistema."
                ),
            )

        except Exception as e:
            logger.exception("Erro ao restaurar backup")

            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                str(e)
            )

        finally:
            self._desbloquear_ui()
            self._limpar_senha()

    # -------------------------------------------------
    # CICLO DE VIDA
    # -------------------------------------------------
    def closeEvent(self, event):
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass

        super().closeEvent(event)
