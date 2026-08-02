# -*- coding: utf-8 -*-
"""Geometria responsiva e persistência de janelas, sem usar o banco financeiro."""

from PyQt5.QtCore import QByteArray, QEvent, QObject, QPoint, QRect, QSize, Qt
from PyQt5.QtWidgets import QApplication, QDialog, QMainWindow, QWidget

from core.theme_manager import ThemeManager


class WindowManager:
    """Centraliza regras de tela, geometria e QSettings por usuário."""

    DEFAULT_SCREEN_RATIO = 0.86
    DIALOG_SCREEN_RATIO = 0.90
    MIN_VISIBLE_SIZE = 80

    @staticmethod
    def settings():
        return ThemeManager._settings()

    @staticmethod
    def key(name):
        return ThemeManager._user_key(f"janela/{name}")

    @staticmethod
    def screen_for(widget=None, parent=None):
        app = QApplication.instance()
        if app is None:
            return None
        reference = parent or (widget.parentWidget() if isinstance(widget, QWidget) else None)
        if reference is not None:
            handle = reference.windowHandle()
            if handle is not None and handle.screen() is not None:
                return handle.screen()
            center = reference.frameGeometry().center()
            screen = app.screenAt(center)
            if screen is not None:
                return screen
        if widget is not None:
            handle = widget.windowHandle()
            if handle is not None and handle.screen() is not None:
                return handle.screen()
        return app.primaryScreen()

    @staticmethod
    def available_geometries():
        app = QApplication.instance()
        return [screen.availableGeometry() for screen in app.screens()] if app else []

    @classmethod
    def default_geometry(cls, widget=None, parent=None):
        screen = cls.screen_for(widget, parent)
        available = screen.availableGeometry() if screen else QRect(0, 0, 1280, 720)
        width = max(720, int(available.width() * cls.DEFAULT_SCREEN_RATIO))
        height = max(560, int(available.height() * cls.DEFAULT_SCREEN_RATIO))
        width = min(width, available.width())
        height = min(height, available.height())
        x = available.x() + (available.width() - width) // 2
        y = available.y() + (available.height() - height) // 2
        return QRect(x, y, width, height)

    @classmethod
    def is_visible_geometry(cls, rect):
        if not isinstance(rect, QRect) or not rect.isValid():
            return False
        for available in cls.available_geometries():
            intersection = rect.intersected(available)
            if (intersection.width() >= cls.MIN_VISIBLE_SIZE and
                    intersection.height() >= cls.MIN_VISIBLE_SIZE):
                return True
        return False

    @classmethod
    def keep_visible(cls, widget, parent=None):
        if cls.is_visible_geometry(widget.frameGeometry()):
            return True
        geometry = cls.default_geometry(widget, parent)
        widget.setGeometry(geometry)
        return False

    @classmethod
    def restore_main_window(cls, window):
        settings = cls.settings()
        geometry = settings.value(cls.key("geometry"))
        restored = False
        if isinstance(geometry, (QByteArray, bytes, bytearray)) and geometry:
            restored = window.restoreGeometry(QByteArray(geometry))
        if not restored or not cls.is_visible_geometry(window.frameGeometry()):
            window.setGeometry(cls.default_geometry(window))
            restored = False
        maximized = settings.value(cls.key("maximized"), False, type=bool)
        if maximized:
            window.setWindowState((window.windowState() & ~Qt.WindowMinimized) | Qt.WindowMaximized)
        else:
            window.setWindowState(window.windowState() & ~(Qt.WindowMinimized | Qt.WindowMaximized))
        return restored

    @classmethod
    def save_main_window(cls, window, menu_compact=False, sidebar_width=None):
        settings = cls.settings()
        state = window.windowState()
        settings.setValue(cls.key("geometry"), window.saveGeometry())
        settings.setValue(cls.key("maximized"), bool(state & Qt.WindowMaximized))
        settings.setValue(cls.key("menu_compact"), bool(menu_compact))
        if sidebar_width is not None:
            settings.setValue(cls.key("sidebar_width"), int(sidebar_width))
        settings.sync()

    @classmethod
    def menu_preferences(cls, default_width=250):
        settings = cls.settings()
        compact = settings.value(cls.key("menu_compact"), False, type=bool)
        try:
            width = int(settings.value(cls.key("sidebar_width"), default_width))
        except (TypeError, ValueError):
            width = default_width
        return compact, max(210, min(width, 380))

    @classmethod
    def fit_dialog(cls, dialog, parent=None, center=True):
        screen = cls.screen_for(dialog, parent or dialog.parentWidget())
        if screen is None:
            return
        available = screen.availableGeometry()
        max_size = QSize(
            max(320, int(available.width() * cls.DIALOG_SCREEN_RATIO)),
            max(240, int(available.height() * cls.DIALOG_SCREEN_RATIO)),
        )
        dialog.setMaximumSize(max_size)
        minimum = dialog.minimumSize()
        if minimum.width() > max_size.width() or minimum.height() > max_size.height():
            dialog.setMinimumSize(
                min(minimum.width(), max_size.width()),
                min(minimum.height(), max_size.height()),
            )
        hint = dialog.sizeHint().boundedTo(max_size)
        current = dialog.size().boundedTo(max_size)
        target = QSize(max(current.width(), hint.width()), max(current.height(), hint.height()))
        dialog.resize(target.boundedTo(max_size))
        if center:
            rect = dialog.frameGeometry()
            rect.moveCenter(available.center())
            dialog.move(rect.topLeft())
        cls.keep_visible(dialog, parent)


class DialogGeometryFilter(QObject):
    """Aplica limites e centralização a QDialogs quando são exibidos."""

    def eventFilter(self, watched, event):
        if isinstance(watched, QDialog) and event.type() == QEvent.Show:
            WindowManager.fit_dialog(watched, watched.parentWidget())
        return super().eventFilter(watched, event)


def install_dialog_geometry_filter(app):
    manager = DialogGeometryFilter(app)
    app.installEventFilter(manager)
    app._dialog_geometry_filter = manager
    return manager
