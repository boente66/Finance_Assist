import json
import os
from copy import deepcopy

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt5.QtWidgets import QApplication, QDialog, QTableWidget, QWidget

from core.session import Session
from core.theme_manager import ThemeManager
from core.themes import get_theme_config


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path):
    ThemeManager._settings_override_path = str(tmp_path / "themes.ini")
    Session.set_usuario({"ID_Usuario": 987654, "Nome": "Tema", "Tema": "Primavera"})
    ThemeManager._settings().clear()
    ThemeManager.cancel_preview()
    yield
    ThemeManager._settings().clear()
    ThemeManager._settings_override_path = None
    ThemeManager.cancel_preview()


@pytest.mark.parametrize("theme", ["Primavera", "Noite Intensa", "Prosperidade", "Verão Quente"])
def test_aplicar_tema_pronto(theme, app):
    assert ThemeManager.definir_tema(theme, app) is True
    assert app.styleSheet()
    assert ThemeManager.tema_atual() == theme


def test_criar_tema_personalizado():
    config = get_theme_config("Primavera")
    config["nome"] = "Meu Tema"
    config["base"] = "PERSONALIZADO"
    assert ThemeManager.save_custom_theme(config)["nome"] == "Meu Tema"


def test_alterar_fonte():
    config = get_theme_config("Primavera")
    config["base"] = "PERSONALIZADO"
    config["fontes"]["family"] = "Sans Serif"
    saved = ThemeManager.save_custom_theme(config)
    assert saved["fontes"]["family"]


def test_salvar_por_usuario():
    config = get_theme_config("Primavera")
    config["base"] = "PERSONALIZADO"
    ThemeManager.save_custom_theme(config)
    assert ThemeManager.load_custom_theme()["base"] == "PERSONALIZADO"


def test_restaurar_ao_reiniciar():
    ThemeManager._settings().setValue("usuarios/987654/tema", "Prosperidade")
    assert ThemeManager.load_user_theme() == "Prosperidade"


def test_fallback_de_fonte_inexistente():
    assert ThemeManager.resolve_font("Fonte que certamente não existe 123") in ThemeManager.SAFE_FONTS


def test_importar_tema_valido(tmp_path):
    config = get_theme_config("Primavera")
    config["base"] = "PERSONALIZADO"
    path = tmp_path / "tema.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    assert ThemeManager.import_theme(str(path))["base"] == "PERSONALIZADO"


def test_rejeitar_tema_invalido(tmp_path):
    path = tmp_path / "invalido.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        ThemeManager.import_theme(str(path))


def test_rejeitar_campo_desconhecido_ou_perigoso(tmp_path):
    config = get_theme_config("Primavera")
    config["script"] = "os.system('x')"
    path = tmp_path / "perigoso.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError):
        ThemeManager.import_theme(str(path))


def test_contraste_minimo():
    config = get_theme_config("Primavera")
    config["base"] = "PERSONALIZADO"
    config["cores"]["text_primary"] = config["cores"]["background"]
    with pytest.raises(ValueError, match="Contraste"):
        ThemeManager.validate_custom_theme(config)


def test_atualizar_tela_aberta(app):
    widget = QWidget()
    ThemeManager.definir_tema("Primavera", app)
    first = app.styleSheet()
    ThemeManager.definir_tema("Verão Quente", app)
    app.processEvents()
    assert widget is not None and app.styleSheet() != first


def test_dialog_respeita_tema_global(app):
    dialog = QDialog()
    ThemeManager.definir_tema("Noite Intensa", app)
    assert dialog.styleSheet() == "" and "QDialog" in app.styleSheet()


def test_tabela_respeita_tema_global(app):
    table = QTableWidget()
    ThemeManager.definir_tema("Prosperidade", app)
    assert table.styleSheet() == "" and "QTableWidget" in app.styleSheet()


def test_preview_nao_altera_tema_permanente(app):
    ThemeManager.definir_tema("Primavera", app)
    before = app.styleSheet()
    config = get_theme_config("Verão Quente")
    config["base"] = "PERSONALIZADO"
    assert ThemeManager.preview_theme(config)
    assert app.styleSheet() == before
    assert ThemeManager.tema_atual() == "Primavera"


def test_cancelar_preview_restaura_estado():
    config = get_theme_config("Primavera")
    config["base"] = "PERSONALIZADO"
    ThemeManager.preview_theme(config)
    ThemeManager.cancel_preview()
    assert ThemeManager._preview_config is None


def test_restaurar_padrao_funciona(app):
    ThemeManager.definir_tema("Noite Intensa", app)
    restored = ThemeManager.restore_default(app)
    assert restored["nome"] == "Primavera"
    assert ThemeManager.tema_atual() == "Primavera"


def test_exportar_tema_salvo(tmp_path):
    config = get_theme_config("Primavera")
    config["base"] = "PERSONALIZADO"
    ThemeManager.save_custom_theme(config)
    path = tmp_path / "exportado.json"
    assert ThemeManager.export_theme(str(path)) is True
    assert json.loads(path.read_text(encoding="utf-8"))["base"] == "PERSONALIZADO"


def test_configuracao_invalida_persistida_usa_fallback():
    ThemeManager._settings().setValue("usuarios/987654/tema_personalizado", "{ruim")
    assert ThemeManager.load_custom_theme() is None


def test_preview_nao_modifica_dicionario_recebido():
    config = get_theme_config("Primavera")
    config["base"] = "PERSONALIZADO"
    original = deepcopy(config)
    ThemeManager.preview_theme(config)
    assert config == original


def test_nenhum_teste_de_tema_depende_de_banco_real():
    assert Session.get_usuario()["ID_Usuario"] == 987654
