# -*- coding: utf-8 -*-
"""Diálogos autocontidos da tela de perfil."""

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from core.translator_app import TranslatorApp


class EditarPerfilDialog(QDialog):
    def __init__(self, controller, usuario, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.usuario = dict(usuario or {})
        self.setObjectName("profileDialog")
        self.setWindowTitle(TranslatorApp.get("Editar dados pessoais"))
        self.setMinimumSize(520, 560)
        self._init_ui()
        self._load_user()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

        title = QLabel(TranslatorApp.get("Editar dados pessoais"))
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)

        self.nome_input = QLineEdit()
        self.nascimento_input = QDateEdit()
        self.nascimento_input.setCalendarPopup(True)
        self.nascimento_input.setDisplayFormat("dd/MM/yyyy")
        self.sexo_input = QComboBox()
        for label, value in (("Masculino", "Masculino"), ("Feminino", "Feminino"), ("Outro", "Outro"), ("Não informar", "")):
            self.sexo_input.addItem(TranslatorApp.get(label), value)
        self.cpf_input = QLineEdit()
        self.cpf_input.setInputMask("000.000.000-00;_")
        self.telefone_input = QLineEdit()
        self.telefone_input.setInputMask("(00) 0000-0000;_")
        self.celular_input = QLineEdit()
        self.celular_input.setInputMask("(00) 00000-0000;_")
        self.email_input = QLineEdit()
        self.login_input = QLineEdit()

        rows = (
            ("Nome", self.nome_input),
            ("Data de nascimento", self.nascimento_input),
            ("Sexo", self.sexo_input),
            ("CPF", self.cpf_input),
            ("Telefone", self.telefone_input),
            ("Celular", self.celular_input),
            ("E-mail", self.email_input),
            ("Login", self.login_input),
        )
        for label, field in rows:
            form.addRow(TranslatorApp.get(label) + ":", field)
        layout.addLayout(form)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Save).setText(TranslatorApp.get("Salvar"))
        self.buttons.button(QDialogButtonBox.Cancel).setText(TranslatorApp.get("Cancelar"))
        self.buttons.accepted.connect(self._save)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def _load_user(self):
        self.nome_input.setText(self.usuario.get("Nome") or "")
        date = QDate.fromString(self.usuario.get("DataNascimento") or "", "yyyy-MM-dd")
        self.nascimento_input.setDate(date if date.isValid() else QDate(1990, 1, 1))
        index = self.sexo_input.findData(self.usuario.get("Sexo") or "")
        self.sexo_input.setCurrentIndex(max(0, index))
        self.cpf_input.setText(self.usuario.get("CPF") or "")
        self.telefone_input.setText(self.usuario.get("Telefone") or "")
        self.celular_input.setText(self.usuario.get("Celular") or "")
        self.email_input.setText(self.usuario.get("Email") or "")
        self.login_input.setText(self.usuario.get("Login") or "")

    @staticmethod
    def _clean_mask(field):
        return field.text().replace("_", "").strip()

    def _save(self):
        nome = self.nome_input.text().strip()
        email = self.email_input.text().strip()
        login = self.login_input.text().strip()
        if not nome or not email or not login:
            QMessageBox.warning(self, TranslatorApp.get("Erro"), TranslatorApp.get("Preencha os campos obrigatórios"))
            return
        if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            QMessageBox.warning(self, TranslatorApp.get("Erro"), TranslatorApp.get("E-mail inválido"))
            return

        dados = {
            "Nome": nome,
            "DataNascimento": self.nascimento_input.date().toString("yyyy-MM-dd"),
            "Sexo": self.sexo_input.currentData(),
            "CPF": self._clean_mask(self.cpf_input),
            "Telefone": self._clean_mask(self.telefone_input),
            "Celular": self._clean_mask(self.celular_input),
            "Email": email,
            "Login": login,
        }
        if not self.controller.update_own_profile(dados):
            QMessageBox.warning(
                self,
                TranslatorApp.get("Não foi possível salvar"),
                TranslatorApp.get("O login ou e-mail já está em uso, ou os dados são inválidos."),
            )
            return
        self.accept()


class AlterarSenhaDialog(QDialog):
    def __init__(self, controller, usuario, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.usuario = dict(usuario or {})
        self.setObjectName("profileDialog")
        self.setWindowTitle(TranslatorApp.get("Alterar senha"))
        self.setMinimumSize(460, 330)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)
        title = QLabel(TranslatorApp.get("Alterar senha"))
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        self.current_input = QLineEdit()
        self.new_input = QLineEdit()
        self.confirm_input = QLineEdit()
        for field in (self.current_input, self.new_input, self.confirm_input):
            field.setEchoMode(QLineEdit.Password)
        form.addRow(TranslatorApp.get("Senha atual") + ":", self.current_input)
        form.addRow(TranslatorApp.get("Nova senha") + ":", self.new_input)
        form.addRow(TranslatorApp.get("Confirmar nova senha") + ":", self.confirm_input)
        layout.addLayout(form)

        hint = QLabel(TranslatorApp.get("Use pelo menos 8 caracteres."))
        hint.setObjectName("muted")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText(TranslatorApp.get("Alterar senha"))
        buttons.button(QDialogButtonBox.Cancel).setText(TranslatorApp.get("Cancelar"))
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        current = self.current_input.text()
        new = self.new_input.text()
        if len(new) < 8:
            QMessageBox.warning(self, TranslatorApp.get("Senha inválida"), TranslatorApp.get("A nova senha deve possuir pelo menos 8 caracteres."))
            return
        if new != self.confirm_input.text():
            QMessageBox.warning(self, TranslatorApp.get("Senha inválida"), TranslatorApp.get("A confirmação da senha não confere."))
            return
        login = self.usuario.get("Login") or ""
        if not self.controller.authenticate_user(login, current):
            QMessageBox.warning(self, TranslatorApp.get("Senha inválida"), TranslatorApp.get("A senha atual está incorreta."))
            return
        if not self.controller.change_password(new):
            QMessageBox.critical(self, TranslatorApp.get("Erro"), TranslatorApp.get("Não foi possível alterar a senha."))
            return
        QMessageBox.information(self, TranslatorApp.get("Sucesso"), TranslatorApp.get("Senha alterada com sucesso."))
        self.accept()
