import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

import views.criar_conta_dialog as account_dialog_module
from core.themes import build_stylesheet, get_theme_config
from views.date_range_dialog import DateRangeDialog
from views.design_mode_dialog import DesignModeDialog
from views.login_dialog import LoginDialog


class ControllerStub:
    def authenticate_user(self, login, password):
        return None

    def create_account(self, data):
        return True


def _app():
    return QApplication.instance() or QApplication([])


def test_escala_padrao_permanece_legivel_sem_exagero():
    config = get_theme_config("Primavera")
    assert config["fontes"] == {
        "family": "DejaVu Sans", "base_size": 9, "title_size": 18,
        "subtitle_size": 10, "table_size": 9, "weight": 400,
        "line_spacing": 1.15,
    }
    assert config["layout"]["button_height"] == 34
    assert config["layout"]["field_height"] == 34
    assert config["layout"]["table_row_height"] == 34


def test_stylesheet_limita_metricas_exageradas_de_tema_importado():
    config = get_theme_config("Primavera")
    config["fontes"].update({
        "base_size": 36, "title_size": 36,
        "subtitle_size": 36, "table_size": 36,
    })
    config["layout"].update({
        "radius": 24, "button_height": 64,
        "field_height": 64, "table_row_height": 72,
    })
    stylesheet = build_stylesheet(config)
    assert 'font-size: 12pt' in stylesheet
    assert 'font-size: 20pt' in stylesheet
    assert 'min-height: 42px' in stylesheet
    assert 'min-height: 44px' in stylesheet
    assert 'font-size: 36pt' not in stylesheet
    assert 'min-height: 64px' not in stylesheet


def test_editor_expoe_apenas_intervalos_visuais_seguros():
    app = _app()
    dialog = DesignModeDialog()
    assert dialog.spin_controls["base_size"].maximum() == 12
    assert dialog.spin_controls["title_size"].maximum() == 20
    assert dialog.spin_controls["button_height"].maximum() == 42
    assert dialog.spin_controls["table_row_height"].maximum() == 44
    dialog.close()
    app.processEvents()


def test_login_reorganiza_conteudo_em_resolucao_compacta():
    app = _app()
    dialog = LoginDialog(controller=ControllerStub())
    dialog.resize(600, 500)
    dialog.show()
    app.processEvents()
    assert not dialog.hero.isVisibleTo(dialog)
    assert not dialog.footer.isVisibleTo(dialog)
    assert dialog.card.minimumWidth() == 360
    dialog.close()


def test_calendarios_empilham_sem_estilo_inline():
    app = _app()
    dialog = DateRangeDialog()
    dialog.resize(420, 600)
    dialog.show()
    app.processEvents()
    start = dialog.cal_layout.getItemPosition(
        dialog.cal_layout.indexOf(dialog.calendar_start)
    )[:2]
    end = dialog.cal_layout.getItemPosition(
        dialog.cal_layout.indexOf(dialog.calendar_end)
    )[:2]
    assert start == (0, 0)
    assert end == (1, 0)
    assert dialog.findChild(type(dialog.calendar_start)).styleSheet() == ""
    dialog.close()


def test_criar_conta_deixa_de_ser_dialogo_fixado(monkeypatch):
    app = _app()
    monkeypatch.setattr(account_dialog_module, "AccountController", ControllerStub)
    dialog = account_dialog_module.CriarContaDialog()
    assert dialog.minimumWidth() == 340
    assert dialog.maximumWidth() > dialog.minimumWidth()
    assert dialog.maximumHeight() > dialog.minimumHeight()
    dialog.close()
    app.processEvents()
