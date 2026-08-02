# -*- coding: utf-8 -*-
import logging

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QMessageBox, QLineEdit, QFileDialog
)

from core.session import Session
from core.theme_manager import ThemeManager
from views.responsive_layout import FlowLayout
from core.translator_app import TranslatorApp
from controllers.configuracoes_controller import ConfiguracoesController
from controllers.user_controller import UserController

logger = logging.getLogger(__name__)


class ConfiguracoesView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.config_controller = ConfiguracoesController()
        self.user_controller = UserController()
        self.eh_admin = self._is_admin()

        self._init_ui()
        self._load_config()
        self._connect_events()

        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

    def _is_admin(self):
        usuario = Session.get_usuario()
        return bool(usuario and usuario.get("Nivel_Acesso") == "admin")

    def _init_ui(self):
        self.layout = QVBoxLayout(self)

        self.titulo_label = QLabel()
        self.titulo_label.setObjectName("pageTitle")
        self.layout.addWidget(self.titulo_label)

        self.idioma_label = QLabel()
        self.layout.addWidget(self.idioma_label)

        self.idioma_combo = QComboBox()
        self.layout.addWidget(self.idioma_combo)

        for label, code in [
            ("Português", "pt"),
            ("Inglês", "en"),
            ("Espanhol", "es"),
        ]:
            self.idioma_combo.addItem(label, code)

        self.tema_label = QLabel()
        self.layout.addWidget(self.tema_label)

        self.tema_combo = QComboBox()
        for tema in ThemeManager.temas_disponiveis():
            self.tema_combo.addItem(TranslatorApp.get(tema), tema)
        self.layout.addWidget(self.tema_combo)

        self.design_mode_btn = QPushButton()
        self.design_mode_btn.setObjectName("secondaryButton")
        self.layout.addWidget(self.design_mode_btn)

        self.moeda_label = QLabel()
        self.layout.addWidget(self.moeda_label)

        self.moeda_combo = QComboBox()
        for moeda in ["BRL", "USD", "EUR"]:
            self.moeda_combo.addItem(moeda, moeda)
        self.layout.addWidget(self.moeda_combo)

        # Banco: somente admin
        self.db_label = QLabel()
        self.db_edit = QLineEdit()
        self.db_btn = QPushButton()

        if self.eh_admin:
            self.layout.addWidget(self.db_label)

            db_layout = FlowLayout(horizontal_spacing=8, vertical_spacing=8)
            self.db_edit.setMinimumWidth(260)
            db_layout.addWidget(self.db_edit)
            db_layout.addWidget(self.db_btn)
            self.layout.addLayout(db_layout)
        else:
            self.db_label.hide()
            self.db_edit.hide()
            self.db_btn.hide()

        self.buttons_layout = FlowLayout(horizontal_spacing=8, vertical_spacing=8)

        self.aplicar_btn = QPushButton()
        self.aplicar_btn.setObjectName("primaryButton")
        self.buttons_layout.addWidget(self.aplicar_btn)

        self.aplicar_todos_btn = QPushButton()
        self.aplicar_todos_btn.setObjectName("secondaryButton")

        if self.eh_admin:
            self.buttons_layout.addWidget(self.aplicar_todos_btn)
        else:
            self.aplicar_todos_btn.hide()

        self.layout.addLayout(self.buttons_layout)
        self.layout.addStretch()

    def _connect_events(self):
        self.aplicar_btn.clicked.connect(self.aplicar_usuario)
        self.design_mode_btn.clicked.connect(self.abrir_modo_design)

        if self.eh_admin:
            self.aplicar_todos_btn.clicked.connect(self.aplicar_global)
            self.db_btn.clicked.connect(self.selecionar_banco)

    def _atualizar_textos(self):
        self.setWindowTitle(TranslatorApp.get("Configurações"))

        self.titulo_label.setText(TranslatorApp.get("Configurações"))
        self.idioma_label.setText(TranslatorApp.get("Idioma"))
        self.tema_label.setText(TranslatorApp.get("Tema"))
        self.design_mode_btn.setText(TranslatorApp.get("Abrir Modo Design"))
        self.moeda_label.setText(TranslatorApp.get("Moeda"))
        self.aplicar_btn.setText(TranslatorApp.get("Aplicar"))
        self.aplicar_todos_btn.setText(
            TranslatorApp.get("Aplicar para todos")
        )

        self.db_label.setText(
            TranslatorApp.get("Localização do banco de dados")
        )
        self.db_btn.setText(
            TranslatorApp.get("Selecionar")
        )
        selected_theme = self.tema_combo.currentData()
        self.tema_combo.blockSignals(True)
        self.tema_combo.clear()
        for theme in ThemeManager.temas_disponiveis():
            self.tema_combo.addItem(TranslatorApp.get(theme), theme)
        index = self.tema_combo.findData(selected_theme)
        self.tema_combo.setCurrentIndex(max(0, index))
        self.tema_combo.blockSignals(False)

    def _load_config(self):
        config = self.config_controller.obter_configuracoes()

        try:
            user_pref = self.user_controller.get_preferences() or {}
        except Exception:
            user_pref = {}

        idioma = (
            user_pref.get("Idioma")
            or user_pref.get("idioma")
            or config.get("idioma")
        )

        tema = (
            user_pref.get("Tema")
            or user_pref.get("tema")
            or config.get("tema")
        )

        moeda = config.get("moeda")
        db_path = config.get("db_path")

        self.idioma_combo.blockSignals(True)
        self.tema_combo.blockSignals(True)
        self.moeda_combo.blockSignals(True)

        self._set_combo_by_data(self.idioma_combo, idioma)

        if tema:
            tema = ThemeManager._normalizar(tema)
            index = self.tema_combo.findData(tema)
            if index >= 0:
                self.tema_combo.setCurrentIndex(index)

        self._set_combo_by_data(self.moeda_combo, moeda)

        if self.eh_admin and db_path:
            self.db_edit.setText(db_path)

        self.idioma_combo.blockSignals(False)
        self.tema_combo.blockSignals(False)
        self.moeda_combo.blockSignals(False)

    def _get_dados_config(self):
        return {
            "idioma": self.idioma_combo.currentData(),
            "tema": self.tema_combo.currentData(),
            "moeda": self.moeda_combo.currentData(),
            "db_path": self.db_edit.text().strip()
            if self.eh_admin else None,
        }

    def _set_combo_by_data(self, combo, value):
        index = combo.findData(value)

        if index >= 0:
            combo.setCurrentIndex(index)

    def selecionar_banco(self):
        caminho, _ = QFileDialog.getSaveFileName(
            self,
            TranslatorApp.get("Selecionar banco de dados"),
            self.db_edit.text().strip() or "",
            "SQLite Database (*.db);;Todos os arquivos (*)"
        )

        if caminho:
            self.db_edit.setText(caminho)

    def abrir_modo_design(self):
        from views.design_mode_dialog import DesignModeDialog

        dialog = DesignModeDialog(self)
        if dialog.exec_():
            index = self.tema_combo.findData("Personalizado")
            if index >= 0:
                self.tema_combo.setCurrentIndex(index)

    def aplicar_usuario(self):
        dados = self._get_dados_config()

        try:
            ok = self.user_controller.update_preferences(
                tema=dados["tema"],
                idioma=dados["idioma"]
            )

            if not ok:
                raise RuntimeError(
                    "Não foi possível salvar as preferências do usuário."
                )

            self.config_controller.set_tema(dados["tema"])
            self.config_controller.set_idioma(dados["idioma"])

            QMessageBox.information(
                self,
                TranslatorApp.get("Configurações"),
                TranslatorApp.get("Configurações aplicadas ao usuário.")
            )

        except Exception:
            logger.exception("Erro ao aplicar configurações do usuário")

            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Erro ao aplicar configurações.")
            )

    def aplicar_global(self):
        if not self.eh_admin:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Permissão negada"),
                TranslatorApp.get(
                    "Apenas administradores podem alterar configurações globais."
                )
            )
            return

        dados = self._get_dados_config()
        db_antigo = self.config_controller.get_db_path()

        try:
            ok = self.config_controller.set_configuracoes_globais(
                idioma=dados["idioma"],
                tema=dados["tema"],
                moeda=dados["moeda"],
                db_path=dados["db_path"],
            )

            if not ok:
                raise RuntimeError(
                    "Não foi possível salvar as configurações globais."
                )

            mensagem = TranslatorApp.get(
                "Configurações aplicadas para todos."
            )

            if dados["db_path"] and dados["db_path"] != db_antigo:
                mensagem += "\n\n" + TranslatorApp.get(
                    "A nova localização do banco será usada após reiniciar o sistema."
                )

            QMessageBox.information(
                self,
                TranslatorApp.get("Configurações"),
                mensagem
            )

        except Exception:
            logger.exception("Erro ao aplicar configurações globais")

            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Erro ao aplicar configurações globais.")
            )

    def closeEvent(self, event):
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass

        super().closeEvent(event)
