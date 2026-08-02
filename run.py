# -*- coding: utf-8 -*-
import sys
import logging
import traceback

from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox

from core.config import carregar_config
from core.session import Session
from core.themes import get_theme
from core.translator_app import TranslatorApp
from core.window_manager import install_dialog_geometry_filter

from views.login_dialog import LoginDialog
from views.main_view import MainView


logging.basicConfig(
    level=logging.DEBUG,
    filename="finance-assist.log",
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger(__name__)


def excecao_global(exctype, value, tb):
    erro = "".join(traceback.format_exception(exctype, value, tb))
    logger.critical("ERRO GLOBAL:\n%s", erro)

    app = QApplication.instance()
    if app:
        QMessageBox.critical(
            None,
            "Erro",
            f"Ocorreu um erro inesperado:\n\n{value}"
        )


sys.excepthook = excecao_global


def aplicar_tema(tema, app=None):
    try:
        app = app or QApplication.instance()

        if not isinstance(app, QApplication):
            logger.error("App inválido: %s", type(app))
            return

        style = get_theme(tema)

        if isinstance(style, str) and style.strip():
            app.setStyleSheet(style)
        else:
            logger.warning("Tema inválido: %s", tema)
            app.setStyleSheet("")

    except Exception:
        logger.exception("Erro ao aplicar tema")

        if isinstance(app, QApplication):
            app.setStyleSheet("")


def main():
    app = QApplication(sys.argv)
    install_dialog_geometry_filter(app)

    try:
        config = carregar_config()
        Session.load_config(config)

        TranslatorApp.initialize()

        Session.on_idioma_change(TranslatorApp.set_language)
        TranslatorApp.set_language(
            Session.get_config("idioma", "pt")
        )

        tema = Session.get_config("tema", "Claro")
        aplicar_tema(tema, app)

        Session.on_tema_change(
            lambda novo_tema: aplicar_tema(novo_tema, app)
        )

        login = LoginDialog()

        if login.exec_() == QDialog.Accepted:
            usuario = login.usuario_logado

            if not usuario:
                raise ValueError("Login sem usuário")

            Session.set_usuario(usuario)

            main_window = MainView(usuario)
            main_window.show()

            return app.exec_()

        return 0

    except Exception as e:
        logger.exception("Erro no main")

        QMessageBox.critical(
            None,
            "Erro",
            f"Erro ao iniciar o Finance Assist:\n\n{e}"
        )

        return 1


if __name__ == "__main__":
    sys.exit(main())
