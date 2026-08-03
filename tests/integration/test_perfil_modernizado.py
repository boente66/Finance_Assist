import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QMessageBox

from core.session import Session
from core.version import APP_VERSION, DEBIAN_VERSION
from services.user_services import UserService
from views.perfil_dialogs import AlterarSenhaDialog, EditarPerfilDialog
from views.perfil_view import PerfilView


USER = {
    "ID_Usuario": 42,
    "Nome": "Leonardo Gabriel Boente",
    "DataNascimento": "1990-05-15",
    "Sexo": "Masculino",
    "CPF": "123.456.789-10",
    "Telefone": "(41) 3333-4444",
    "Celular": "(41) 99999-9999",
    "Email": "leonardo@example.com",
    "Login": "leonardo",
    "Nivel_Acesso": "admin",
    "Tema": "Primavera",
    "Idioma": "pt",
}


class UserControllerStub:
    def __init__(self):
        self.preferences = []
        self.profile_updates = []
        self.passwords = []

    def get_preferences(self):
        return {"Tema": "Primavera", "Idioma": "pt"}

    def update_preferences(self, theme, language):
        self.preferences.append((theme, language))
        return True

    def update_own_profile(self, data):
        self.profile_updates.append(data)
        return True

    def get_user_by_id(self, _user_id):
        return dict(USER)

    def authenticate_user(self, login, password):
        return dict(USER) if login == USER["Login"] and password == "senha-atual" else None

    def change_password(self, password):
        self.passwords.append(password)
        return True


class ConfigControllerStub:
    def __init__(self):
        self.themes = []
        self.languages = []

    def set_tema(self, value):
        self.themes.append(value)
        Session.set_config("tema", value)
        return True

    def set_idioma(self, value):
        self.languages.append(value)
        Session.set_config("idioma", value)
        return True


_APP = None


def _app():
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def _view():
    _app()
    Session.set_usuario(dict(USER))
    return PerfilView(
        user_controller=UserControllerStub(),
        config_controller=ConfigControllerStub(),
    )


def test_perfil_exibe_modelo_com_dados_reais_da_sessao():
    view = _view()
    assert view.title.text() == "Meu perfil"
    assert view.name_label.text() == USER["Nome"]
    assert view.avatar.text() == "LG"
    assert view.detail_labels["Data de nascimento"][1].text() == "15/05/1990"
    assert view.detail_labels["CPF"][1].text() == USER["CPF"]
    assert view.role_label.text().endswith("Administrador")
    assert APP_VERSION in view.version.text()
    assert "test" in APP_VERSION and "test" in DEBIAN_VERSION
    view.close()


def test_perfil_reorganiza_paineis_e_mantem_rolagem():
    view = _view()
    view.set_compact_mode(available_width=760)
    assert view._compact is True
    assert view.content_grid.getItemPosition(view.content_grid.indexOf(view.personal_card))[:2] == (0, 0)
    assert view.content_grid.getItemPosition(view.content_grid.indexOf(view.preferences_card))[:2] == (1, 0)
    assert view.scroll.widgetResizable() is True
    view.set_compact_mode(available_width=1200)
    assert view._compact is False
    view.close()


def test_salvar_preferencias_reutiliza_controller_e_atualiza_sessao(monkeypatch):
    view = _view()
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.Ok)
    view.theme_combo.setCurrentIndex(view.theme_combo.findData("Prosperidade"))
    view.language_combo.setCurrentIndex(view.language_combo.findData("es"))
    view._save_preferences()
    assert view.user_controller.preferences == [("Prosperidade", "es")]
    assert view.config_controller.themes == ["Prosperidade"]
    assert view.config_controller.languages == ["es"]
    assert Session.get_usuario()["Tema"] == "Prosperidade"
    view.close()


def test_dialogo_edicao_envia_apenas_dados_pessoais(monkeypatch):
    _app()
    controller = UserControllerStub()
    dialog = EditarPerfilDialog(controller, USER)
    dialog.nome_input.setText("Leonardo Atualizado")
    dialog._save()
    assert controller.profile_updates[0]["Nome"] == "Leonardo Atualizado"
    assert "Nivel_Acesso" not in controller.profile_updates[0]
    assert dialog.result() == dialog.Accepted


def test_dialogo_senha_confirma_senha_atual(monkeypatch):
    _app()
    controller = UserControllerStub()
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.Ok)
    dialog = AlterarSenhaDialog(controller, USER)
    dialog.current_input.setText("senha-atual")
    dialog.new_input.setText("nova-senha-segura")
    dialog.confirm_input.setText("nova-senha-segura")
    dialog._save()
    assert controller.passwords == ["nova-senha-segura"]
    assert dialog.result() == dialog.Accepted


class UserModelStub:
    def __init__(self):
        self.updated = None

    def fetch_one(self, *_args):
        return None

    def update_user(self, user_id, data):
        self.updated = (user_id, data)


def test_autoedicao_preserva_nivel_de_acesso_no_service():
    service = UserService.__new__(UserService)
    service.user_model = UserModelStub()
    service.get_user_by_id = lambda _user_id: dict(USER)
    malicious = dict(USER, Nome="Novo Nome", Nivel_Acesso="usuario")
    assert service.update_own_profile(USER["ID_Usuario"], malicious, dict(USER)) is True
    assert service.user_model.updated[1]["Nivel_Acesso"] == "admin"


def test_autoedicao_rejeita_outro_usuario():
    service = UserService.__new__(UserService)
    service.user_model = UserModelStub()
    service.get_user_by_id = lambda _user_id: dict(USER)
    other = dict(USER, ID_Usuario=99)
    assert service.update_own_profile(USER["ID_Usuario"], dict(USER), other) is False
    assert service.user_model.updated is None
