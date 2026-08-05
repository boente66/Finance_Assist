import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt5.QtWidgets import QApplication, QDialog, QLineEdit, QMessageBox, QScrollArea

from core.themes import get_theme
from views.cadastro_usuario_dialog import CadastroUsuarioDialog


USUARIO = {
    "ID_Usuario": 42,
    "Nome": "Usuário de Teste",
    "DataNascimento": "1990-05-15",
    "Sexo": "Masculino",
    "CPF": "123.456.789-10",
    "Telefone": "(41) 3333-4444",
    "Celular": "(41) 99999-9999",
    "Email": "usuario@example.com",
    "Login": "usuario",
    "Nivel_Acesso": "usuario",
}


class UserControllerStub:
    def __init__(self):
        self.registros = []
        self.edicoes = []

    def register_user(self, dados):
        self.registros.append(dict(dados))
        return True

    def update_user(self, user_id, dados):
        self.edicoes.append((user_id, dict(dados)))
        return True


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def controller():
    return UserControllerStub()


@pytest.fixture(autouse=True)
def mensagens_sem_bloqueio(monkeypatch):
    monkeypatch.setattr(
        QMessageBox, "information", lambda *args, **kwargs: QMessageBox.Ok
    )
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.Ok
    )
    monkeypatch.setattr(
        QMessageBox, "critical", lambda *args, **kwargs: QMessageBox.Ok
    )


def _preencher_cadastro(dialog):
    dialog.nome_input.setText("Novo Usuário")
    dialog.email_input.setText("novo@example.com")
    dialog.login_input.setText("novo.usuario")
    dialog.senha_input.setText("senha-segura")
    dialog.confirmar_senha_input.setText("senha-segura")


def test_cadastro_exibe_confirmacao_e_textos_do_modo(app, controller):
    dialog = CadastroUsuarioDialog(controller=controller)
    assert dialog.lbl_titulo.text() == "Novo usuário"
    assert dialog.btn_salvar.text() == "Cadastrar usuário"
    assert dialog.confirmar_senha_input.isHidden() is False
    assert dialog.confirmar_senha_input.echoMode() == QLineEdit.Password
    assert "*" in dialog.lbl_senha.text()
    assert "*" in dialog.lbl_confirmar_senha.text()
    dialog.close()


def test_edicao_mantem_senha_opcional_e_estado_apos_traducao(app, controller):
    dialog = CadastroUsuarioDialog(controller=controller)
    dialog.preencher_dados(dict(USUARIO))
    dialog._atualizar_textos()
    assert dialog.lbl_titulo.text() == "Editar usuário"
    assert dialog.windowTitle() == "Editar usuário"
    assert dialog.btn_salvar.text() == "Salvar alterações"
    assert "manter a senha atual" in dialog.senha_input.placeholderText()
    assert "*" not in dialog.lbl_senha.text()
    assert "*" not in dialog.lbl_confirmar_senha.text()

    dialog.salvar_usuario()
    assert controller.edicoes[0][0] == USUARIO["ID_Usuario"]
    assert controller.edicoes[0][1]["Senha"] == ""
    assert dialog.result() == QDialog.Accepted


def test_senhas_diferentes_impedem_salvamento_e_mostram_erro(app, controller):
    dialog = CadastroUsuarioDialog(controller=controller)
    _preencher_cadastro(dialog)
    dialog.confirmar_senha_input.setText("outra-senha")
    dialog.show()
    app.processEvents()

    dialog.salvar_usuario()
    app.processEvents()

    assert controller.registros == []
    assert dialog._error_labels["confirmar_senha"].isVisible()
    assert "não coincidem" in dialog._error_labels["confirmar_senha"].text()
    assert dialog.confirmar_senha_input.hasFocus()
    dialog.close()


def test_primeiro_campo_invalido_recebe_foco(app, controller):
    dialog = CadastroUsuarioDialog(controller=controller)
    dialog.show()
    app.processEvents()
    dialog.salvar_usuario()
    app.processEvents()
    assert dialog.nome_input.hasFocus()
    assert dialog._error_labels["nome"].isVisible()
    assert controller.registros == []
    dialog.close()


def test_cancelar_rejeita_dialogo(app, controller):
    dialog = CadastroUsuarioDialog(controller=controller)
    dialog.btn_cancelar.click()
    assert dialog.result() == QDialog.Rejected
    dialog.close()


def test_layout_tem_scroll_e_reorganiza_em_largura_compacta(app, controller):
    dialog = CadastroUsuarioDialog(controller=controller)
    dialog.show()
    app.processEvents()
    assert isinstance(dialog.scroll_area, QScrollArea)
    assert dialog.scroll_area.widgetResizable()

    dialog.resize(600, 520)
    app.processEvents()
    dialog._aplicar_layout_responsivo(force=True)
    pos_nome = dialog.grid_pessoais.getItemPosition(
        dialog.grid_pessoais.indexOf(dialog._field_containers["nome"])
    )
    pos_nascimento = dialog.grid_pessoais.getItemPosition(
        dialog.grid_pessoais.indexOf(dialog._field_containers["nascimento"])
    )
    assert dialog._layout_compacto is True
    assert pos_nome[:2] == (0, 0)
    assert pos_nascimento[:2] == (1, 0)
    assert dialog.width() >= 600 and dialog.height() >= 520
    dialog.close()


def test_layout_amplo_usa_duas_colunas(app, controller):
    dialog = CadastroUsuarioDialog(controller=controller)
    dialog.resize(800, 620)
    dialog.show()
    app.processEvents()
    dialog.resize(800, 620)
    app.processEvents()
    dialog._aplicar_layout_responsivo(force=True)
    pos_nascimento = dialog.grid_pessoais.getItemPosition(
        dialog.grid_pessoais.indexOf(dialog._field_containers["nascimento"])
    )
    assert dialog._layout_compacto is False
    assert pos_nascimento[:2] == (0, 1)
    dialog.close()


def test_cadastro_e_edicao_usam_metodos_atuais_do_controller(app, controller):
    cadastro = CadastroUsuarioDialog(controller=controller)
    _preencher_cadastro(cadastro)
    cadastro.salvar_usuario()
    assert len(controller.registros) == 1
    assert controller.registros[0]["Login"] == "novo.usuario"

    edicao = CadastroUsuarioDialog(controller=controller)
    edicao.preencher_dados(dict(USUARIO))
    edicao.nome_input.setText("Usuário Atualizado")
    edicao.senha_input.setText("nova-senha")
    edicao.confirmar_senha_input.setText("nova-senha")
    edicao.salvar_usuario()
    assert len(controller.edicoes) == 1
    assert controller.edicoes[0][1]["Nome"] == "Usuário Atualizado"
    assert controller.edicoes[0][1]["Senha"] == "nova-senha"


def test_botoes_de_visibilidade_preservam_senhas(app, controller):
    dialog = CadastroUsuarioDialog(controller=controller)
    dialog.senha_input.setText("segredo")
    dialog.confirmar_senha_input.setText("segredo")
    dialog.senha_toggle_action.trigger()
    dialog.confirmar_senha_toggle_action.trigger()
    assert dialog.senha_input.echoMode() == QLineEdit.Normal
    assert dialog.confirmar_senha_input.echoMode() == QLineEdit.Normal
    assert dialog.senha_input.text() == "segredo"
    assert dialog.confirmar_senha_input.text() == "segredo"
    dialog.close()


@pytest.mark.parametrize(
    "tema", ["Primavera", "Noite Intensa", "Prosperidade", "Verão Quente"]
)
def test_dialogo_usa_tema_global_sem_cores_inline(app, controller, tema):
    app.setStyleSheet(get_theme(tema))
    dialog = CadastroUsuarioDialog(controller=controller)
    assert dialog.styleSheet() == ""
    assert dialog.nome_input.styleSheet() == ""
    assert dialog.btn_salvar.styleSheet() == ""
    dialog.close()


def test_testes_de_fluxo_nao_instanciam_controller_real(app, controller):
    dialog = CadastroUsuarioDialog(controller=controller)
    assert dialog.controller is controller
    assert not hasattr(controller, "user_model")
    dialog.close()
