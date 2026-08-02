# -*- coding: utf-8 -*-
"""Gerenciamento, persistência e validação dos temas visuais."""

import json
import logging
import os
from copy import deepcopy

from PyQt5.QtGui import QColor, QFontDatabase
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QApplication

from core.session import Session
from core.themes import (
    DEFAULT_THEME,
    THEME_CONFIGS,
    available_themes,
    build_stylesheet,
    get_theme_config,
    normalize_theme_name,
    validate_theme_config,
)

logger = logging.getLogger(__name__)


class ThemeManager:
    DEFAULT = DEFAULT_THEME
    SAFE_FONTS = (
        "DejaVu Sans", "Liberation Sans", "Ubuntu", "Noto Sans",
        "Arial", "Sans Serif",
    )
    _preview_config = None
    _settings_override_path = None

    @staticmethod
    def _settings():
        if ThemeManager._settings_override_path:
            return QSettings(
                ThemeManager._settings_override_path,
                QSettings.IniFormat,
            )
        return QSettings("ControleFinanceiro", "ControleFinanceiro")

    @staticmethod
    def _user_key(suffix):
        usuario = Session.get_usuario() or {}
        return f"usuarios/{usuario.get('ID_Usuario', 'anonimo')}/{suffix}"

    @staticmethod
    def _normalizar(nome):
        nome = normalize_theme_name(nome)
        return nome if nome in available_themes() else ThemeManager.DEFAULT

    @staticmethod
    def tema_atual():
        usuario = Session.get_usuario() or {}
        # A Session é a fonte do estado visual em execução; set_usuario já
        # carrega nela a preferência persistida do usuário.
        nome = Session.get_config("tema", None) or usuario.get("Tema")
        return ThemeManager._normalizar(nome)

    @staticmethod
    def temas_disponiveis():
        return available_themes()

    @staticmethod
    def get_theme_config(nome=None):
        nome = ThemeManager._normalizar(nome or ThemeManager.tema_atual())
        custom = ThemeManager.load_custom_theme() if nome == "Personalizado" else None
        if nome == "Personalizado" and not custom:
            return get_theme_config(ThemeManager.DEFAULT)
        return get_theme_config(nome, custom)

    @staticmethod
    def aplicar_tema(nome_tema=None, app=None):
        try:
            nome = ThemeManager._normalizar(nome_tema or ThemeManager.tema_atual())
            target = app or QApplication.instance()
            if target is None or not hasattr(target, "setStyleSheet"):
                raise TypeError(f"Aplicação inválida: {type(target)}")
            target.setStyleSheet(build_stylesheet(ThemeManager.get_theme_config(nome)))
            logger.info("[Theme] Tema aplicado: %s", nome)
            return True
        except Exception:
            logger.exception("[Theme] Falha ao aplicar tema '%s'", nome_tema)
            return False

    apply_theme = aplicar_tema

    @staticmethod
    def definir_tema(nome_tema, app=None):
        nome = ThemeManager._normalizar(nome_tema)
        usuario = Session.get_usuario()
        if usuario:
            usuario["Tema"] = nome
        Session.set_config("tema", nome)
        settings = ThemeManager._settings()
        settings.setValue(ThemeManager._user_key("tema"), nome)
        settings.sync()
        return ThemeManager.aplicar_tema(nome, app)

    @staticmethod
    def load_user_theme():
        settings = ThemeManager._settings()
        settings.sync()
        persisted = settings.value(ThemeManager._user_key("tema"))
        nome = ThemeManager._normalizar(persisted or ThemeManager.tema_atual())
        Session.set_config("tema", nome, notify=False)
        return nome

    @staticmethod
    def is_dark():
        return ThemeManager.tema_atual() == "Noite Intensa"

    @staticmethod
    def is_light():
        return not ThemeManager.is_dark()

    @staticmethod
    def is_green():
        return ThemeManager.tema_atual() == "Prosperidade"

    @staticmethod
    def alternar_tema(app=None):
        ordem = ["Primavera", "Noite Intensa", "Prosperidade", "Verão Quente"]
        atual = ThemeManager.tema_atual()
        novo = ordem[(ordem.index(atual) + 1) % len(ordem)] if atual in ordem else ThemeManager.DEFAULT
        ThemeManager.definir_tema(novo, app)
        return novo

    @staticmethod
    def get_color(token):
        cores = ThemeManager.get_theme_config().get("cores", {})
        aliases = {
            "primary_blue": "primary", "green": "success",
            "text_normal": "text_primary", "text_strong": "text_primary",
            "text_soft": "text_secondary", "card": "surface",
            "panel": "surface", "bg": "background",
        }
        cor = cores.get(aliases.get(token, token))
        if cor:
            return cor
        logger.warning("[Theme] Token não encontrado: %s", token)
        return cores.get("text_primary", "#000000")

    @staticmethod
    def get_finance_color(tipo):
        tipo = (tipo or "").lower()
        if tipo in ("receita", "entrada", "ganho"):
            return ThemeManager.get_color("success")
        if tipo in ("despesa", "saida", "saída", "gasto"):
            return ThemeManager.get_color("danger")
        return ThemeManager.get_color("info")

    @staticmethod
    def get_chart_colors():
        return {
            "receita": ThemeManager.get_color("success"),
            "despesa": ThemeManager.get_color("danger"),
            "saldo": ThemeManager.get_color("info"),
            "grid": ThemeManager.get_color("border"),
            "text": ThemeManager.get_color("text_primary"),
        }

    @staticmethod
    def _luminance(color):
        rgb = QColor(color)
        if not rgb.isValid():
            raise ValueError(f"Cor inválida: {color}")
        values = [rgb.redF(), rgb.greenF(), rgb.blueF()]
        values = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in values]
        return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2]

    @staticmethod
    def contrast_ratio(foreground, background):
        a, b = ThemeManager._luminance(foreground), ThemeManager._luminance(background)
        return (max(a, b) + 0.05) / (min(a, b) + 0.05)

    @staticmethod
    def validate_custom_theme(config):
        validate_theme_config(config)
        c = config["cores"]
        for key, value in c.items():
            if not isinstance(value, str) or not QColor(value).isValid():
                raise ValueError(f"Cor inválida no token {key}.")
        checks = (
            ("text_primary", "background", 4.5),
            ("text_primary", "surface", 4.5),
            ("text_primary", "table_header", 4.5),
            ("disabled_text", "disabled_background", 3.0),
        )
        for fg, bg, minimum in checks:
            if ThemeManager.contrast_ratio(c[fg], c[bg]) < minimum:
                raise ValueError(f"Contraste insuficiente entre {fg} e {bg}.")
        for key in ("base_size", "title_size", "subtitle_size", "table_size"):
            if not 8 <= int(config["fontes"][key]) <= 36:
                raise ValueError(f"Tamanho de fonte inválido: {key}.")
        for key in ("radius", "padding", "button_height", "field_height", "table_row_height", "sidebar_width"):
            if int(config["layout"][key]) < 0:
                raise ValueError(f"Valor de layout inválido: {key}.")
        return True

    @staticmethod
    def resolve_font(family):
        if QApplication.instance() is None:
            return family if family in ThemeManager.SAFE_FONTS else "Sans Serif"
        try:
            installed = set(QFontDatabase().families())
        except Exception:
            installed = set()
        if family in installed:
            return family
        for fallback in ThemeManager.SAFE_FONTS:
            if fallback in installed:
                return fallback
        return "Sans Serif"

    @staticmethod
    def preview_theme(config):
        preview = deepcopy(config)
        preview["fontes"]["family"] = ThemeManager.resolve_font(preview["fontes"]["family"])
        ThemeManager.validate_custom_theme(preview)
        ThemeManager._preview_config = preview
        return build_stylesheet(preview)

    @staticmethod
    def cancel_preview():
        ThemeManager._preview_config = None

    @staticmethod
    def save_custom_theme(config):
        saved = deepcopy(config)
        validate_theme_config(saved)
        saved["nome"] = str(saved.get("nome") or "Meu Tema").strip() or "Meu Tema"
        saved["base"] = "PERSONALIZADO"
        saved["fontes"]["family"] = ThemeManager.resolve_font(saved["fontes"]["family"])
        ThemeManager.validate_custom_theme(saved)
        raw = json.dumps(saved, ensure_ascii=False, sort_keys=True)
        settings = ThemeManager._settings()
        settings.setValue(ThemeManager._user_key("tema_personalizado"), raw)
        settings.sync()
        return deepcopy(saved)

    @staticmethod
    def load_custom_theme():
        raw = ThemeManager._settings().value(ThemeManager._user_key("tema_personalizado"))
        if not raw:
            return None
        try:
            config = json.loads(raw)
            ThemeManager.validate_custom_theme(config)
            return config
        except (TypeError, ValueError, json.JSONDecodeError):
            logger.exception("Tema personalizado persistido é inválido; usando fallback.")
            return None

    @staticmethod
    def export_theme(path):
        config = ThemeManager.load_custom_theme()
        if not config:
            raise ValueError("Nenhum tema personalizado foi salvo.")
        if not path or os.path.isdir(path):
            raise ValueError("Caminho de exportação inválido.")
        with open(path, "w", encoding="utf-8") as stream:
            json.dump(config, stream, ensure_ascii=False, indent=2, sort_keys=True)
        return True

    @staticmethod
    def import_theme(path):
        if not path or not os.path.isfile(path):
            raise ValueError("Arquivo de tema não encontrado.")
        if os.path.getsize(path) > 256 * 1024:
            raise ValueError("Arquivo de tema excede o limite permitido.")
        with open(path, "r", encoding="utf-8") as stream:
            config = json.load(stream)
        return ThemeManager.save_custom_theme(config)

    @staticmethod
    def restore_default(app=None):
        ThemeManager._settings().remove(ThemeManager._user_key("tema_personalizado"))
        ThemeManager.cancel_preview()
        ThemeManager.definir_tema(ThemeManager.DEFAULT, app)
        return get_theme_config(ThemeManager.DEFAULT)
