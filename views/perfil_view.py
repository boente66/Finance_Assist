# -*- coding: utf-8 -*-
"""Perfil responsivo do usuário autenticado."""

import os
from datetime import datetime

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QBoxLayout,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from controllers.configuracoes_controller import ConfiguracoesController
from controllers.user_controller import UserController
from core.session import Session
from core.theme_manager import ThemeManager
from core.translator_app import TranslatorApp
from core.version import APP_VERSION
from utilitarios.ion_path import IonPath
from views.perfil_dialogs import AlterarSenhaDialog, EditarPerfilDialog


class PerfilView(QWidget):
    logout_requested = pyqtSignal()
    profile_updated = pyqtSignal(dict)

    LANGUAGES = (("Português (Brasil)", "pt"), ("English", "en"), ("Español", "es"))

    def __init__(self, parent=None, user_controller=None, config_controller=None):
        super().__init__(parent)
        self.user_controller = user_controller or UserController()
        self.config_controller = config_controller or ConfiguracoesController()
        self.usuario = dict(Session.get_usuario() or {})
        if not self.usuario:
            raise RuntimeError("Usuário não autenticado.")
        self._compact = False
        self._init_ui()
        self._load_preferences()
        self._update_user_info()
        TranslatorApp.bind(self._on_translate, self)
        self._on_translate()

    def _icon(self, name):
        path = IonPath.icon(name)
        return QIcon(path) if os.path.exists(path) else QIcon()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setObjectName("profileScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root.addWidget(self.scroll)

        self.page = QWidget()
        self.page.setObjectName("profilePage")
        self.scroll.setWidget(self.page)
        self.page_layout = QVBoxLayout(self.page)
        self.page_layout.setContentsMargins(4, 2, 4, 2)
        self.page_layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(14)
        header_icon = QLabel("♙")
        header_icon.setObjectName("profileHeaderIcon")
        header_icon.setAlignment(Qt.AlignCenter)
        title_copy = QVBoxLayout()
        title_copy.setSpacing(2)
        self.title = QLabel()
        self.title.setObjectName("pageTitle")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("pageSubtitle")
        title_copy.addWidget(self.title)
        title_copy.addWidget(self.subtitle)
        header.addWidget(header_icon)
        header.addLayout(title_copy, 1)
        self.page_layout.addLayout(header)

        self.identity_card = QFrame()
        self.identity_card.setObjectName("profileHero")
        self.identity_layout = QHBoxLayout(self.identity_card)
        self.identity_layout.setContentsMargins(30, 24, 30, 24)
        self.identity_layout.setSpacing(28)
        self.avatar = QLabel()
        self.avatar.setObjectName("profileAvatar")
        self.avatar.setAlignment(Qt.AlignCenter)
        identity_copy = QVBoxLayout()
        identity_copy.setSpacing(8)
        self.name_label = QLabel()
        self.name_label.setObjectName("profileName")
        self.login_label = QLabel()
        self.email_label = QLabel()
        self.role_label = QLabel()
        self.role_label.setObjectName("profileRole")
        identity_copy.addWidget(self.name_label)
        identity_copy.addWidget(self.login_label)
        identity_copy.addWidget(self.email_label)
        identity_copy.addWidget(self.role_label)
        identity_copy.addStretch()
        self.identity_layout.addWidget(self.avatar, 0, Qt.AlignVCenter)
        self.identity_layout.addLayout(identity_copy, 1)
        self.page_layout.addWidget(self.identity_card)

        self.content_grid = QGridLayout()
        self.content_grid.setSpacing(16)
        self.personal_card = self._build_personal_card()
        self.preferences_card = self._build_preferences_card()
        self.security_card = self._build_security_card()
        self.page_layout.addLayout(self.content_grid)
        self._arrange_content(False)

        footer = QFrame()
        footer.setObjectName("profileFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 8, 12, 8)
        self.last_access = QLabel()
        self.last_backup = QLabel()
        self.version = QLabel(f"{TranslatorApp.get('Versão')} {APP_VERSION}")
        footer_layout.addWidget(self.last_access)
        footer_layout.addWidget(self.last_backup)
        footer_layout.addStretch()
        footer_layout.addWidget(self.version)
        self.page_layout.addWidget(footer)

    def _panel(self, title):
        card = QFrame()
        card.setObjectName("profilePanel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)
        label = QLabel(title)
        label.setObjectName("panelTitle")
        layout.addWidget(label)
        card.title_label = label
        return card, layout

    def _build_personal_card(self):
        card, layout = self._panel(TranslatorApp.get("Dados pessoais"))
        top = QHBoxLayout()
        top.addStretch()
        self.edit_button = QPushButton(TranslatorApp.get("Editar"))
        self.edit_button.setObjectName("secondaryButton")
        self.edit_button.setIcon(self._icon("edit"))
        self.edit_button.clicked.connect(self._edit_profile)
        top.addWidget(self.edit_button)
        layout.insertLayout(1, top)
        self.detail_labels = {}
        for key in ("Nome", "Data de nascimento", "Sexo", "CPF", "Telefone", "Celular", "E-mail", "Login"):
            row = QFrame()
            row.setObjectName("profileDetailRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(4, 7, 4, 7)
            name = QLabel(TranslatorApp.get(key))
            name.setObjectName("profileDetailName")
            value = QLabel("—")
            value.setObjectName("profileDetailValue")
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            value.setWordWrap(True)
            row_layout.addWidget(name, 2)
            row_layout.addWidget(value, 3)
            layout.addWidget(row)
            self.detail_labels[key] = (name, value)
        hint = QLabel("ⓘ  " + TranslatorApp.get("Para alterar seus dados pessoais, clique em Editar."))
        hint.setObjectName("profileHint")
        hint.setWordWrap(True)
        layout.addStretch()
        layout.addWidget(hint)
        return card

    def _build_preferences_card(self):
        card, layout = self._panel(TranslatorApp.get("Preferências do sistema"))
        form = QGridLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(14)
        self.theme_label = QLabel(TranslatorApp.get("Tema"))
        self.language_label = QLabel(TranslatorApp.get("Idioma"))
        self.theme_combo = QComboBox()
        for theme in ThemeManager.temas_disponiveis():
            self.theme_combo.addItem(TranslatorApp.get(theme), theme)
        self.language_combo = QComboBox()
        for label, code in self.LANGUAGES:
            self.language_combo.addItem(label, code)
        form.addWidget(self.theme_label, 0, 0)
        form.addWidget(self.theme_combo, 0, 1)
        form.addWidget(self.language_label, 1, 0)
        form.addWidget(self.language_combo, 1, 1)
        form.setColumnStretch(1, 1)
        layout.addLayout(form)
        layout.addStretch()
        self.save_preferences_button = QPushButton(TranslatorApp.get("Salvar preferências"))
        self.save_preferences_button.setIcon(self._icon("save"))
        self.save_preferences_button.clicked.connect(self._save_preferences)
        layout.addWidget(self.save_preferences_button, 0, Qt.AlignRight)
        return card

    def _build_security_card(self):
        card, layout = self._panel(TranslatorApp.get("Segurança"))
        row = QHBoxLayout()
        lock = QLabel("▣")
        lock.setObjectName("profileSecurityIcon")
        lock.setAlignment(Qt.AlignCenter)
        copy = QVBoxLayout()
        self.security_title = QLabel(TranslatorApp.get("Sua senha é protegida pelo sistema."))
        self.security_title.setObjectName("profileSecurityTitle")
        self.security_detail = QLabel(TranslatorApp.get("Use uma senha forte e altere-a periodicamente."))
        self.security_detail.setObjectName("muted")
        self.security_detail.setWordWrap(True)
        copy.addWidget(self.security_title)
        copy.addWidget(self.security_detail)
        row.addWidget(lock)
        row.addLayout(copy, 1)
        layout.addLayout(row)
        layout.addStretch()
        self.password_button = QPushButton(TranslatorApp.get("Alterar senha"))
        self.password_button.setObjectName("secondaryButton")
        self.password_button.setIcon(self._icon("lock"))
        self.password_button.clicked.connect(self._change_password)
        layout.addWidget(self.password_button, 0, Qt.AlignRight)
        return card

    def _arrange_content(self, compact):
        for card in (self.personal_card, self.preferences_card, self.security_card):
            self.content_grid.removeWidget(card)
        if compact:
            self.content_grid.addWidget(self.personal_card, 0, 0)
            self.content_grid.addWidget(self.preferences_card, 1, 0)
            self.content_grid.addWidget(self.security_card, 2, 0)
        else:
            self.content_grid.addWidget(self.personal_card, 0, 0, 2, 1)
            self.content_grid.addWidget(self.preferences_card, 0, 1)
            self.content_grid.addWidget(self.security_card, 1, 1)
        self.content_grid.setColumnStretch(0, 1)
        self.content_grid.setColumnStretch(1, 1 if not compact else 0)

    def set_compact_mode(self, sidebar_compact=False, available_width=None):
        width = available_width or self.width()
        compact = width < 900
        if compact != self._compact:
            self._compact = compact
            self._arrange_content(compact)
        self.identity_layout.setDirection(
            QBoxLayout.TopToBottom if width < 650 else QBoxLayout.LeftToRight
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.set_compact_mode(available_width=self.width())

    def _load_preferences(self):
        try:
            preferences = self.user_controller.get_preferences() or {}
        except Exception:
            preferences = {}
        theme = ThemeManager._normalizar(preferences.get("Tema") or self.usuario.get("Tema") or Session.get_config("tema"))
        language = preferences.get("Idioma") or self.usuario.get("Idioma") or Session.get_config("idioma", "pt")
        theme_index = self.theme_combo.findData(theme)
        language_index = self.language_combo.findData(Session._normalize_idioma(language))
        self.theme_combo.setCurrentIndex(max(0, theme_index))
        self.language_combo.setCurrentIndex(max(0, language_index))

    @staticmethod
    def _display_date(value):
        try:
            return datetime.strptime(value or "", "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return "Não informado"

    @staticmethod
    def _display(value):
        return str(value).strip() if value is not None and str(value).strip() else "Não informado"

    def _update_user_info(self):
        name = self._display(self.usuario.get("Nome"))
        initials = "".join(part[0] for part in name.split()[:2]).upper() if name != "Não informado" else "U"
        role = "Administrador" if str(self.usuario.get("Nivel_Acesso", "")).lower() == "admin" else "Usuário"
        self.avatar.setText(initials)
        self.name_label.setText(name)
        self.login_label.setText(f"{TranslatorApp.get('Login')}: {self._display(self.usuario.get('Login'))}")
        self.email_label.setText("✉  " + self._display(self.usuario.get("Email")))
        self.role_label.setText("◇  " + TranslatorApp.get(role))
        values = {
            "Nome": name,
            "Data de nascimento": self._display_date(self.usuario.get("DataNascimento")),
            "Sexo": self._display(self.usuario.get("Sexo")),
            "CPF": self._display(self.usuario.get("CPF")),
            "Telefone": self._display(self.usuario.get("Telefone")),
            "Celular": self._display(self.usuario.get("Celular")),
            "E-mail": self._display(self.usuario.get("Email")),
            "Login": self._display(self.usuario.get("Login")),
        }
        for key, value in values.items():
            self.detail_labels[key][1].setText(value)
        self.last_access.setText("▣  " + datetime.now().strftime("%d/%m/%Y %H:%M"))
        self.last_backup.setText("☁  " + self._last_backup_text())

    @staticmethod
    def _last_backup_text():
        try:
            directory = IonPath.backup_dir()
            files = [os.path.join(directory, item) for item in os.listdir(directory)]
            files = [item for item in files if os.path.isfile(item)]
            if files:
                latest = max(files, key=os.path.getmtime)
                return TranslatorApp.get("Backup") + ": " + datetime.fromtimestamp(os.path.getmtime(latest)).strftime("%d/%m/%Y %H:%M")
        except OSError:
            pass
        return TranslatorApp.get("Backup ainda não realizado")

    def _edit_profile(self):
        dialog = EditarPerfilDialog(self.user_controller, self.usuario, self)
        if dialog.exec_() != dialog.Accepted:
            return
        updated = self.user_controller.get_user_by_id(self.usuario["ID_Usuario"])
        if not updated:
            QMessageBox.warning(self, TranslatorApp.get("Aviso"), TranslatorApp.get("Dados salvos; atualize a tela para recarregar o perfil."))
            return
        self.usuario = dict(updated)
        Session.set_usuario(self.usuario)
        self._update_user_info()
        self.profile_updated.emit(dict(self.usuario))

    def _change_password(self):
        AlterarSenhaDialog(self.user_controller, self.usuario, self).exec_()

    def _save_preferences(self):
        theme = self.theme_combo.currentData()
        language = self.language_combo.currentData()
        if not self.user_controller.update_preferences(theme, language):
            QMessageBox.critical(self, TranslatorApp.get("Erro"), TranslatorApp.get("Não foi possível salvar as preferências."))
            return
        self.usuario["Tema"] = theme
        self.usuario["Idioma"] = language
        session_user = Session.get_usuario()
        if session_user:
            session_user.update({"Tema": theme, "Idioma": language})
        self.config_controller.set_tema(theme)
        self.config_controller.set_idioma(language)
        QMessageBox.information(self, TranslatorApp.get("Sucesso"), TranslatorApp.get("Preferências salvas com sucesso."))

    def _on_translate(self, *_):
        self.title.setText(TranslatorApp.get("Meu perfil"))
        self.subtitle.setText(TranslatorApp.get("Gerencie seus dados pessoais e preferências do sistema."))
        self.personal_card.title_label.setText(TranslatorApp.get("Dados pessoais"))
        self.preferences_card.title_label.setText(TranslatorApp.get("Preferências do sistema"))
        self.security_card.title_label.setText(TranslatorApp.get("Segurança"))
        for key, (label, _) in self.detail_labels.items():
            label.setText(TranslatorApp.get(key))
        self.theme_label.setText(TranslatorApp.get("Tema"))
        self.language_label.setText(TranslatorApp.get("Idioma"))
        self.security_title.setText(TranslatorApp.get("Sua senha é protegida pelo sistema."))
        self.security_detail.setText(TranslatorApp.get("Use uma senha forte e altere-a periodicamente."))
        self.edit_button.setText(TranslatorApp.get("Editar"))
        self.save_preferences_button.setText(TranslatorApp.get("Salvar preferências"))
        self.password_button.setText(TranslatorApp.get("Alterar senha"))
        self.version.setText(f"{TranslatorApp.get('Versão')} {APP_VERSION}")
        self._update_user_info()

    def closeEvent(self, event):
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass
        super().closeEvent(event)
