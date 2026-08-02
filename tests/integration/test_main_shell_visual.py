import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from core.theme_manager import ThemeManager
from views.main_view import MainView


def test_shell_principal_mantem_navegacao_e_expoe_configuracoes(monkeypatch):
    app = QApplication.instance() or QApplication([])
    ThemeManager.aplicar_tema("Primavera", app)
    monkeypatch.setattr(MainView, "_abrir_primeira_view", lambda self: None)
    view = MainView({
        "ID_Usuario": 77,
        "Nome": "Leonardo Gabriel Boente",
        "Email": "leonardo@example.com",
        "Nivel_Acesso": "admin",
    })
    assert view.brand_title.text() == "Finance\nAssist"
    assert view.btn_configuracoes in [button for button, _ in view._menu_buttons]
    assert view.btn_logout.text()
    assert view.user_card.objectName() == "sidebarUserCard"
    assert len(view._menu_buttons) == 8
    view.close()
