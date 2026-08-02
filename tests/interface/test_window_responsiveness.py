import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from PyQt5.QtCore import QByteArray, QRect, Qt
from PyQt5.QtWidgets import QApplication, QDialog, QTableWidget

import views.agendamento_view as schedule_module
import views.painel_fatura as invoice_module
import views.resumo_financeiro_view as dashboard_module
from core.session import Session
from core.theme_manager import ThemeManager
from core.window_manager import WindowManager
from views.login_dialog import LoginDialog
from views.main_view import MainView


class EmptyAccountController:
    def get_all_accounts(self):
        return []


class EmptyCardController:
    def get_all_cartoes(self):
        return []


class EmptyTransactionController:
    def get_resumo_financeiro(self):
        return {"Receitas": 0, "Despesas": 0}

    def get_analise_mensal(self):
        return {}


class EmptyGoalController:
    def listar_metas_ativas(self):
        return []


class EmptyScheduleController:
    def get_upcoming_schedules(self):
        return []

    def get_financial_projection(self, months):
        return {"itens": [], "totais": {}}


class LoginController:
    def authenticate_user(self, login, password):
        return None


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch, app):
    ThemeManager._settings_override_path = str(tmp_path / "window.ini")
    Session.set_usuario({"ID_Usuario": 424242, "Nome": "Teste", "Nivel_Acesso": "usuario"})
    ThemeManager._settings().clear()
    monkeypatch.setattr(MainView, "_abrir_primeira_view", lambda self: None)
    yield
    ThemeManager._settings().clear()
    ThemeManager._settings_override_path = None


def create_main(app):
    view = MainView({"ID_Usuario": 424242, "Nome": "Teste", "Nivel_Acesso": "usuario"})
    view.show()
    app.processEvents()
    return view


def configure_dashboard_stubs(monkeypatch):
    monkeypatch.setattr(dashboard_module, "AccountController", EmptyAccountController)
    monkeypatch.setattr(dashboard_module, "FaturaController", EmptyCardController)
    monkeypatch.setattr(dashboard_module, "TransactionController", EmptyTransactionController)
    monkeypatch.setattr(dashboard_module, "ScheduleController", EmptyScheduleController)
    monkeypatch.setattr(dashboard_module, "MetaController", EmptyGoalController)


def test_main_view_pode_ser_redimensionada(app):
    view = create_main(app)
    view.resize(980, 680)
    app.processEvents()
    assert view.size().width() == 980 and view.size().height() == 680
    view.close()


def test_main_view_pode_maximizar_e_restaurar(app):
    view = create_main(app)
    view.showMaximized()
    app.processEvents()
    assert view.isMaximized()
    view.toggle_maximized()
    app.processEvents()
    assert not view.isMaximized()
    view.close()


def test_estado_da_janela_e_salvo(app):
    view = create_main(app)
    view.resize(990, 690)
    WindowManager.save_main_window(view, True, 275)
    settings = ThemeManager._settings()
    assert settings.value(WindowManager.key("geometry"))
    assert settings.value(WindowManager.key("menu_compact"), type=bool) is True
    assert int(settings.value(WindowManager.key("sidebar_width"))) == 275
    view.close()


def test_estado_da_janela_e_restaurado(app):
    first = create_main(app)
    first.resize(1000, 700)
    first._sidebar_expanded_width = 268
    first.close()
    second = create_main(app)
    assert second.width() == 1000 and second.height() == 700
    assert second._sidebar_expanded_width == 268
    second.close()


def test_estado_minimizado_nao_e_restaurado(app):
    view = create_main(app)
    view.showMinimized()
    app.processEvents()
    WindowManager.save_main_window(view, False, 250)
    view.close()
    restored = create_main(app)
    assert not restored.isMinimized()
    restored.close()


def test_geometria_invalida_usa_fallback(app):
    ThemeManager._settings().setValue(WindowManager.key("geometry"), QByteArray(b"invalid"))
    view = create_main(app)
    assert WindowManager.is_visible_geometry(view.frameGeometry())
    view.close()


def test_janela_fora_da_tela_retorna_a_area_visivel(app):
    view = create_main(app)
    view.setGeometry(QRect(50000, 50000, 900, 650))
    assert WindowManager.keep_visible(view) is False
    assert WindowManager.is_visible_geometry(view.frameGeometry())
    view.close()


def test_menu_lateral_recolhe(app):
    view = create_main(app)
    view._apply_sidebar_mode(False)
    view.toggle_sidebar()
    assert view._sidebar_compact and view.sidebar.maximumWidth() == 72
    view.close()


def test_menu_lateral_expande(app):
    view = create_main(app)
    view._apply_sidebar_mode(True)
    view.toggle_sidebar()
    assert not view._sidebar_compact
    assert view.sidebar.maximumWidth() == view._sidebar_expanded_width
    view.close()


def test_preferencia_do_menu_e_persistida(app):
    view = create_main(app)
    view._menu_compact_preference = True
    view.close()
    compact, _ = WindowManager.menu_preferences()
    assert compact is True


def test_tooltips_existem_no_menu_compacto(app):
    view = create_main(app)
    view._apply_sidebar_mode(True)
    assert all(button.toolTip() for button, _ in view._menu_buttons)
    assert all(not button.text() for button, _ in view._menu_buttons)
    assert all(not button.icon().isNull() for button, _ in view._menu_buttons)
    view.close()


def test_opcoes_do_usuario_possuem_rolagem_quando_altura_e_reduzida(app):
    view = MainView({
        "ID_Usuario": 424242,
        "Nome": "Administrador",
        "Email": "admin@example.com",
        "Nivel_Acesso": "admin",
    })
    view.resize(900, 600)
    view._manual_compact_override = True
    view._apply_sidebar_mode(False)
    view.show()
    view._toggle_user_menu()
    app.processEvents()
    assert view.btn_gerenciar.isVisibleTo(view)
    assert view.btn_backup.isVisibleTo(view)
    assert view.sidebar_scroll.verticalScrollBar().maximum() > 0
    view.close()


def test_cards_reorganizam_em_largura_menor(monkeypatch, app):
    configure_dashboard_stubs(monkeypatch)
    view = dashboard_module.ResumoFinanceiroView()
    view.set_compact_mode(True, 700)
    positions = [view.metrics_layout.getItemPosition(view.metrics_layout.indexOf(card)) for card in view.metric_widgets]
    assert positions[0][:2] == (0, 0)
    assert positions[2][:2] == (1, 0)
    view.close()


def test_filtros_de_agendamento_continuam_acessiveis(monkeypatch, app):
    monkeypatch.setattr(schedule_module, "ScheduleController", EmptyScheduleController)
    view = schedule_module.AgendamentoView(schedule_controller=EmptyScheduleController())
    view.resize(700, 600)
    app.processEvents()
    assert view.search_input.isVisibleTo(view)
    assert all(combo.isVisibleTo(view) for combo in (
        view.combo_status, view.combo_conta, view.combo_categoria, view.combo_pessoa
    ))
    view.close()


def test_tabelas_mantem_rolagem(monkeypatch, app):
    monkeypatch.setattr(schedule_module, "ScheduleController", EmptyScheduleController)
    view = schedule_module.AgendamentoView(schedule_controller=EmptyScheduleController())
    assert isinstance(view.table, QTableWidget)
    assert view.table.horizontalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    view.close()


def test_dialogo_nao_ultrapassa_area_disponivel(app):
    dialog = QDialog()
    dialog.setMinimumSize(2000, 1400)
    dialog.resize(2200, 1600)
    WindowManager.fit_dialog(dialog)
    available = WindowManager.screen_for(dialog).availableGeometry()
    assert dialog.width() <= int(available.width() * .90)
    assert dialog.height() <= int(available.height() * .90)


def test_login_permanece_compacto_e_minimizavel(app):
    dialog = LoginDialog(controller=LoginController())
    WindowManager.fit_dialog(dialog)
    assert dialog.minimumWidth() == 720
    assert dialog.windowFlags() & Qt.WindowMinimizeButtonHint
    assert not dialog.windowFlags() & Qt.WindowMaximizeButtonHint
    dialog.close()


def test_painel_fatura_funciona_reduzido(monkeypatch, app):
    monkeypatch.setattr(invoice_module, "FaturaController", EmptyCardController)
    monkeypatch.setattr(invoice_module, "AccountController", EmptyAccountController)
    panel = invoice_module.PainelFatura()
    panel.set_compact_mode(True, 520)
    assert panel.indicators_layout.getItemPosition(
        panel.indicators_layout.indexOf(panel.indicator_widgets[2])
    )[:2] == (1, 0)
    assert panel.table.horizontalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    panel.close()


def test_agendamentos_funciona_reduzido(monkeypatch, app):
    monkeypatch.setattr(schedule_module, "ScheduleController", EmptyScheduleController)
    view = schedule_module.AgendamentoView(schedule_controller=EmptyScheduleController())
    view.set_compact_mode(True, 600)
    last = view.summary_widgets[-1]
    assert view.summary_layout.getItemPosition(view.summary_layout.indexOf(last))[0] >= 2
    view.close()


@pytest.mark.parametrize("theme", [
    "Primavera", "Noite Intensa", "Prosperidade", "Verão Quente", "Personalizado",
])
def test_temas_funcionam_no_modo_compacto(theme, app):
    if theme == "Personalizado":
        config = ThemeManager.get_theme_config("Primavera")
        config["base"] = "PERSONALIZADO"
        ThemeManager.save_custom_theme(config)
    assert ThemeManager.aplicar_tema(theme, app)
    view = create_main(app)
    view._apply_sidebar_mode(True)
    assert view._sidebar_compact and app.styleSheet()
    view.close()


def test_controles_nativos_da_janela_principal(app):
    view = create_main(app)
    flags = view.windowFlags()
    assert flags & Qt.WindowMinimizeButtonHint
    assert flags & Qt.WindowMaximizeButtonHint
    assert flags & Qt.WindowCloseButtonHint
    assert not flags & Qt.FramelessWindowHint
    view.close()


def test_suite_de_responsividade_nao_inicializa_database_real(monkeypatch):
    import database.database as database_module

    monkeypatch.setattr(
        database_module.Database,
        "__init__",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("banco real proibido")),
    )
    assert WindowManager.available_geometries()
