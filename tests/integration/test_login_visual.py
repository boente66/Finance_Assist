import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt5.QtWidgets import QApplication, QLineEdit

from core.theme_manager import ThemeManager
from views.login_dialog import LoginDialog


class LoginControllerStub:
    def __init__(self, user=None):
        self.user = user
        self.calls = []

    def authenticate_user(self, login, password):
        self.calls.append((login, password))
        return self.user


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication([])
    ThemeManager.aplicar_tema("Primavera", application)
    return application


def test_login_adota_composicao_lateral_e_componentes_do_modelo(app):
    dialog = LoginDialog(controller=LoginControllerStub())
    assert dialog.objectName() == "loginRoot"
    assert dialog.hero.objectName() == "loginHero"
    assert dialog.card.objectName() == "loginCard"
    assert dialog.brand_title.text() == "Finance Assist"
    assert dialog.btn_login.objectName() == "loginPrimary"
    assert dialog.btn_cadastrar.objectName() == "loginSecondary"
    assert dialog.btn_recuperar.objectName() == "linkButton"
    assert dialog.minimumWidth() == 600
    assert dialog.minimumHeight() == 500
    dialog.close()


def test_toggle_de_senha_preserva_conteudo(app):
    dialog = LoginDialog(controller=LoginControllerStub())
    dialog.senha_input.setText("segredo")
    assert dialog.senha_input.echoMode() == QLineEdit.Password
    dialog._toggle_password()
    assert dialog.senha_input.echoMode() == QLineEdit.Normal
    assert dialog.senha_input.text() == "segredo"
    dialog._toggle_password()
    assert dialog.senha_input.echoMode() == QLineEdit.Password
    dialog.close()


def test_autenticacao_continua_usando_controller_existente(app):
    user = {"ID_Usuario": 7, "Nome": "Usuário"}
    controller = LoginControllerStub(user)
    dialog = LoginDialog(controller=controller)
    dialog.login_input.setText("usuario@example.com")
    dialog.senha_input.setText("senha")
    dialog._autenticar()
    assert controller.calls == [("usuario@example.com", "senha")]
    assert dialog.usuario_logado == user
    assert dialog.result() == dialog.Accepted


def test_campos_possuem_rotulos_acessiveis(app):
    dialog = LoginDialog(controller=LoginControllerStub())
    assert dialog.login_input.accessibleName()
    assert dialog.senha_input.accessibleName()
    assert dialog.login_input.placeholderText()
    assert dialog.senha_input.placeholderText()
    dialog.close()
