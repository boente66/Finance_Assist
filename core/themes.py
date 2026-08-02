# -*- coding: utf-8 -*-
"""Temas visuais centralizados e orientados a tokens.

As views identificam a função visual dos widgets por ``objectName`` ou por
propriedades Qt. Nenhuma regra de negócio deve depender das cores daqui.
"""

from copy import deepcopy

from core.session import Session


REQUIRED_COLORS = {
    "background", "surface", "surface_alt", "sidebar", "sidebar_active",
    "primary", "primary_hover", "secondary", "text_primary",
    "text_secondary", "border", "success", "danger", "warning", "info",
    "table_header", "table_alternate", "input_background",
    "disabled_background", "disabled_text", "button_background", "focus",
    "selection",
}
REQUIRED_FONTS = {
    "family", "base_size", "title_size", "subtitle_size", "table_size",
    "weight", "line_spacing",
}
REQUIRED_LAYOUT = {
    "radius", "shadow", "padding", "density", "button_height",
    "field_height", "table_row_height", "sidebar_width", "divider_contrast",
}


_BASE_FONTS = {
    "family": "DejaVu Sans",
    "base_size": 10,
    "title_size": 22,
    "subtitle_size": 11,
    "table_size": 10,
    "weight": 400,
    "line_spacing": 1.25,
}

_BASE_LAYOUT = {
    "radius": 10,
    "shadow": 1,
    "padding": 12,
    "density": "confortavel",
    "button_height": 36,
    "field_height": 36,
    "table_row_height": 38,
    "sidebar_width": 250,
    "divider_contrast": 35,
}


THEME_CONFIGS = {
    "Primavera": {
        "nome": "Primavera",
        "base": "PRIMAVERA",
        "cores": {
            "background": "#F5F8FB", "surface": "#FFFFFF",
            "surface_alt": "#F0F7F5", "sidebar": "#07243F",
            "sidebar_active": "#12A8E0", "primary": "#148BC2",
            "primary_hover": "#0C74A6", "secondary": "#62B9AC",
            "text_primary": "#10233F", "text_secondary": "#66748B",
            "border": "#DCE4EC", "success": "#159447",
            "danger": "#DC3545", "warning": "#D9820B", "info": "#1976D2",
            "table_header": "#F3F6FA", "table_alternate": "#F8FAFC",
            "input_background": "#FFFFFF", "disabled_background": "#E9EEF3",
            "disabled_text": "#657386", "button_background": "#148BC2",
            "focus": "#12A8E0", "selection": "#DDF3FC",
        },
        "fontes": deepcopy(_BASE_FONTS),
        "layout": deepcopy(_BASE_LAYOUT),
    },
    "Noite Intensa": {
        "nome": "Noite Intensa",
        "base": "NOITE_INTENSA",
        "cores": {
            "background": "#0D1524", "surface": "#151F30",
            "surface_alt": "#1B283C", "sidebar": "#07101F",
            "sidebar_active": "#245DFF", "primary": "#4D82FF",
            "primary_hover": "#3269ED", "secondary": "#8A63F6",
            "text_primary": "#F4F7FC", "text_secondary": "#AEBBD0",
            "border": "#2B3A51", "success": "#3BCB79",
            "danger": "#FF6673", "warning": "#F7B84B", "info": "#63A7FF",
            "table_header": "#1A2638", "table_alternate": "#182437",
            "input_background": "#111B2B", "disabled_background": "#273348",
            "disabled_text": "#A5B2C7", "button_background": "#4D82FF",
            "focus": "#8A63F6", "selection": "#233F75",
        },
        "fontes": deepcopy(_BASE_FONTS),
        "layout": deepcopy(_BASE_LAYOUT),
    },
    "Prosperidade": {
        "nome": "Prosperidade",
        "base": "PROSPERIDADE",
        "cores": {
            "background": "#F7F8F2", "surface": "#FFFFFF",
            "surface_alt": "#F0F4E8", "sidebar": "#123B32",
            "sidebar_active": "#168B68", "primary": "#167A5A",
            "primary_hover": "#105E45", "secondary": "#B28A32",
            "text_primary": "#183129", "text_secondary": "#66766F",
            "border": "#DDE4D9", "success": "#168B52",
            "danger": "#C83C3C", "warning": "#C77A12", "info": "#3578B8",
            "table_header": "#F1F5ED", "table_alternate": "#FAFBF7",
            "input_background": "#FFFFFF", "disabled_background": "#E9ECE4",
            "disabled_text": "#66736A", "button_background": "#167A5A",
            "focus": "#B28A32", "selection": "#DCEFE7",
        },
        "fontes": deepcopy(_BASE_FONTS),
        "layout": deepcopy(_BASE_LAYOUT),
    },
    "Verão Quente": {
        "nome": "Verão Quente",
        "base": "VERAO_QUENTE",
        "cores": {
            "background": "#FFF8F3", "surface": "#FFFFFF",
            "surface_alt": "#FFF0E5", "sidebar": "#40201E",
            "sidebar_active": "#F26A2E", "primary": "#E85D24",
            "primary_hover": "#C94818", "secondary": "#D63F63",
            "text_primary": "#3B2522", "text_secondary": "#796560",
            "border": "#ECDDD5", "success": "#178B4E",
            "danger": "#D73737", "warning": "#B96A00", "info": "#3479B8",
            "table_header": "#FFF1E7", "table_alternate": "#FFFAF6",
            "input_background": "#FFFFFF", "disabled_background": "#F2E8E2",
            "disabled_text": "#796A63", "button_background": "#E85D24",
            "focus": "#D63F63", "selection": "#FFE2D1",
        },
        "fontes": deepcopy(_BASE_FONTS),
        "layout": deepcopy(_BASE_LAYOUT),
    },
}

# Compatibilidade com preferências persistidas pelas versões anteriores.
THEME_ALIASES = {
    "Claro": "Primavera", "Escuro": "Noite Intensa", "Verde": "Prosperidade",
    "PRIMAVERA": "Primavera", "NOITE_INTENSA": "Noite Intensa",
    "PROSPERIDADE": "Prosperidade", "VERAO_QUENTE": "Verão Quente",
    "PERSONALIZADO": "Personalizado",
}

DEFAULT_THEME = "Primavera"


def normalize_theme_name(nome):
    if not isinstance(nome, str):
        return DEFAULT_THEME
    nome = nome.strip()
    return THEME_ALIASES.get(nome, nome)


def validate_theme_config(config):
    if not isinstance(config, dict) or set(config) != {"nome", "base", "cores", "fontes", "layout"}:
        raise ValueError("Estrutura de tema inválida.")
    if set(config["cores"]) != REQUIRED_COLORS:
        raise ValueError("Tokens de cores inválidos.")
    if set(config["fontes"]) != REQUIRED_FONTS:
        raise ValueError("Tokens de fontes inválidos.")
    if set(config["layout"]) != REQUIRED_LAYOUT:
        raise ValueError("Tokens de layout inválidos.")
    return True


def build_stylesheet(config):
    validate_theme_config(config)
    c, f, l = config["cores"], config["fontes"], config["layout"]
    radius = int(l["radius"])
    density_factor = {"compacta": 0.8, "confortavel": 1.0, "ampla": 1.2}.get(
        l["density"], 1.0
    )
    pad = max(3, int(int(l["padding"]) * density_factor))
    line_pad = max(4, int(6 * float(f["line_spacing"]) * density_factor))
    surface_border = 1 + min(1, int(l["shadow"]) // 5)
    divider_size = max(1, int(l["divider_contrast"]) // 25)
    return f"""
QWidget {{
    background-color: {c['background']}; color: {c['text_primary']};
    font-family: \"{f['family']}\"; font-size: {int(f['base_size'])}pt;
    font-weight: {int(f['weight'])};
}}
QLabel {{ background: transparent; border: 0; }}
QMainWindow, QDialog {{ background-color: {c['background']}; }}
QToolTip {{ color: white; background: #172033; border: 1px solid {c['border']}; padding: 6px; }}
QWidget#sidebarShell, QWidget#sidebar, QScrollArea#sidebarScroll {{ background-color: {c['sidebar']}; border: 0; }}
QWidget#sidebarSubmenu {{ background: transparent; border: 0; }}
QScrollArea#sidebarScroll QScrollBar:vertical {{ background: rgba(255,255,255,0.07); width: 12px; margin: 2px; }}
QScrollArea#sidebarScroll QScrollBar::handle:vertical {{ background: rgba(255,255,255,0.42); border-radius: 4px; min-height: 30px; }}
QScrollArea#sidebarScroll QScrollBar::handle:vertical:hover {{ background: rgba(255,255,255,0.68); }}
QWidget#sidebarBrand {{ background: transparent; border: 0; }}
QLabel#brandIcon {{ background: transparent; border: 0; min-width: 46px; min-height: 46px; }}
QLabel#brandTitle {{ color: white; font-size: 16pt; font-weight: 700; }}
QLabel#sidebarUser, QWidget#sidebar QLabel {{ color: #F4F7FC; }}
QFrame#sidebarUserCard {{ background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.12); border-radius: {radius}px; margin: 4px 10px; }}
QLabel#sidebarAvatar {{ background: {c['sidebar_active']}; color: white; border-radius: 18px; min-width: 36px; max-width: 36px; min-height: 36px; max-height: 36px; font-weight: 700; }}
QLabel#sidebarUser {{ color: white; font-weight: 700; }}
QLabel#sidebarUserDetail {{ color: #B8C7D9; font-size: 8pt; }}
QLabel#sidebarUserToggle {{ color: #D7E3F0; font-size: 13pt; }}
QPushButton#menuButton {{ background: transparent; color: #E9F0FA; border: 0; border-radius: {radius}px; text-align: left; padding: 10px 16px; min-height: 26px; }}
QPushButton#menuButton[compact="true"] {{ text-align: center; padding: 10px; min-width: 34px; }}
QPushButton#menuButton:hover {{ background: rgba(255,255,255,0.09); }}
QPushButton#menuButton[active=\"true\"] {{ background-color: {c['sidebar_active']}; color: white; font-weight: 600; }}
QPushButton#sidebarToggle {{ background: transparent; color: #DCE8F5; border: 1px solid rgba(255,255,255,0.16); border-radius: 12px; min-width: 26px; max-width: 26px; min-height: 26px; max-height: 26px; padding: 0; margin-right: 10px; }}
QPushButton#sidebarToggle:hover {{ background: rgba(255,255,255,0.10); }}
QFrame#card, QGroupBox, QWidget#surface {{ background-color: {c['surface']}; border: {surface_border}px solid {c['border']}; border-radius: {radius}px; }}
QGroupBox {{ margin-top: 12px; padding: {pad}px; font-weight: 600; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 5px; }}
QLabel#pageTitle {{ font-size: {int(f['title_size'])}pt; font-weight: 700; color: {c['text_primary']}; }}
QLabel#pageSubtitle, QLabel#secondary, QLabel#muted {{ color: {c['text_secondary']}; font-size: {int(f['subtitle_size'])}pt; }}
QLabel#cardTitle {{ color: {c['text_secondary']}; font-weight: 600; }}
QLabel#cardValue {{ color: {c['primary']}; font-size: 18pt; font-weight: 700; }}
QLabel#positivo {{ color: {c['success']}; font-weight: 700; }}
QLabel#negativo {{ color: {c['danger']}; font-weight: 700; }}
QLabel#warning {{ color: {c['warning']}; font-weight: 700; }}
QPushButton, QToolButton {{ background-color: {c['button_background']}; color: white; border: 1px solid {c['button_background']}; border-radius: {radius - 2}px; padding: 6px 14px; min-height: {int(l['button_height'])}px; }}
QPushButton:hover, QToolButton:hover {{ background-color: {c['primary_hover']}; border-color: {c['primary_hover']}; }}
QPushButton:disabled, QToolButton:disabled {{ background: {c['disabled_background']}; color: {c['disabled_text']}; border-color: {c['border']}; }}
QPushButton#secondaryButton, QToolButton#secondaryButton {{ background: {c['surface']}; color: {c['text_primary']}; border-color: {c['border']}; }}
QPushButton#dangerButton, QToolButton#dangerButton {{ background: transparent; color: {c['danger']}; border-color: {c['danger']}; }}
QPushButton#filterButton:checked {{ background: {c['primary']}; color: white; }}
QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QTextEdit {{ background: {c['input_background']}; color: {c['text_primary']}; border: 1px solid {c['border']}; border-radius: {radius - 3}px; padding: 5px 9px; min-height: {int(l['field_height'])}px; selection-background-color: {c['selection']}; }}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {{ border: 2px solid {c['focus']}; }}
QComboBox QAbstractItemView {{ background: {c['surface']}; color: {c['text_primary']}; selection-background-color: {c['selection']}; }}
QTableWidget, QTableView {{ background: {c['surface']}; alternate-background-color: {c['table_alternate']}; color: {c['text_primary']}; border: 1px solid {c['border']}; border-radius: {radius}px; gridline-color: {c['border']}; font-size: {int(f['table_size'])}pt; }}
QHeaderView::section {{ background: {c['table_header']}; color: {c['text_primary']}; border: 0; border-bottom: 1px solid {c['border']}; padding: 9px; font-weight: 600; min-height: {int(l['table_row_height'])}px; }}
QTableWidget::item, QTableView::item {{ padding: {line_pad}px; min-height: {int(l['table_row_height'])}px; }}
QTableWidget::item:selected, QTableView::item:selected {{ background: {c['selection']}; color: {c['text_primary']}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 5px; min-height: 24px; }}
QScrollArea#sidebarScroll QScrollBar:vertical {{ background: rgba(255,255,255,0.10); width: 14px; margin: 2px; }}
QScrollArea#sidebarScroll QScrollBar::handle:vertical {{ background: {c['sidebar_active']}; border-radius: 5px; min-height: 36px; }}
QScrollArea#sidebarScroll QScrollBar::handle:vertical:hover {{ background: {c['primary_hover']}; }}
QProgressBar {{ background: {c['surface_alt']}; border: 0; border-radius: 6px; text-align: center; }}
QProgressBar::chunk {{ background: {c['success']}; border-radius: 6px; }}
QSplitter::handle {{ background: {c['border']}; min-width: {divider_size}px; min-height: {divider_size}px; }}
QMenu {{ background: {c['surface']}; color: {c['text_primary']}; border: 1px solid {c['border']}; }}
QMenu::item:selected {{ background: {c['selection']}; }}

/* Login */
QDialog#loginRoot {{ background-color: {c['background']}; }}
QWidget#loginHero {{ background: transparent; }}
QWidget#loginFormArea {{ background-color: {c['background']}; }}
QFrame#loginCard {{
    background-color: {c['surface']}; border: 1px solid {c['border']};
    border-radius: {radius + 2}px;
}}
QLabel#loginDialogTitle {{
    background: transparent; color: {c['text_secondary']}; border: 0;
    min-height: 34px; font-size: 13pt; font-weight: 500;
}}
QWidget#loginContent {{ background-color: {c['surface']}; border: 0; }}
QWidget#loginContent QLabel {{ background: transparent; border: 0; }}
QLabel#loginLogo {{
    background-color: transparent; border: 0;
    min-width: 68px; min-height: 68px;
}}
QLabel#loginBrandTitle {{
    color: {c['text_primary']}; font-size: 25pt; font-weight: 700;
}}
QLabel#loginBrandSubtitle {{ color: {c['text_secondary']}; font-size: 12pt; }}
QFrame#loginAccent {{ background-color: {c['sidebar_active']}; border: 0; border-radius: 1px; }}
QLabel#loginFieldLabel {{ color: {c['text_primary']}; font-size: 11pt; font-weight: 700; }}
QWidget#loginField {{
    background-color: {c['input_background']}; border: 1px solid {c['border']};
    border-radius: {radius - 2}px; min-height: 52px;
}}
QWidget#loginField[invalid=\"true\"] {{ border: 2px solid {c['danger']}; }}
QLabel#loginFieldIcon {{ background: transparent; border: 0; min-width: 28px; }}
QLineEdit#loginInput {{
    background: transparent; color: {c['text_primary']}; border: 0;
    padding: 4px; min-height: 42px; font-size: 11pt;
}}
QLineEdit#loginInput:focus {{ background: {c['surface_alt']}; }}
QToolButton#loginIconButton {{
    background: transparent; color: {c['text_primary']}; border: 0;
    padding: 4px; min-width: 34px; min-height: 34px;
}}
QToolButton#loginIconButton:hover {{ background: {c['surface_alt']}; border: 0; }}
QPushButton#loginPrimary {{
    background-color: {c['sidebar_active']}; color: white;
    border: 1px solid {c['sidebar_active']}; border-radius: {radius - 2}px;
    min-height: 48px; font-size: 12pt; font-weight: 700;
}}
QPushButton#loginPrimary:hover {{ background-color: {c['primary_hover']}; border-color: {c['primary_hover']}; }}
QPushButton#loginSecondary {{
    background-color: {c['surface']}; color: {c['primary']};
    border: 1px solid {c['primary']}; border-radius: {radius - 2}px;
    min-height: 48px; font-size: 12pt; font-weight: 700;
}}
QPushButton#loginSecondary:hover {{ background-color: {c['surface_alt']}; color: {c['primary_hover']}; border-color: {c['primary_hover']}; }}
QPushButton#linkButton {{
    background: transparent; color: {c['info']}; border: 0;
    min-height: 34px; font-weight: 700;
}}
QPushButton#linkButton:hover {{ color: {c['primary_hover']}; text-decoration: underline; }}
QFrame#loginFooter {{ background-color: {c['surface']}; border-top: 1px solid {c['border']}; }}
QLabel#loginBenefitIcon {{ color: {c['primary']}; font-size: 20pt; font-weight: 700; min-width: 32px; }}
QLabel#loginBenefitTitle {{ color: {c['text_primary']}; font-size: 10pt; font-weight: 700; }}
QLabel#loginBenefitDetail {{ color: {c['text_secondary']}; font-size: 8pt; }}

/* Dashboard */
QFrame#metricCard {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: {radius}px; }}
QLabel#metricLabel {{ color: {c['text_secondary']}; font-size: 9pt; font-weight: 600; }}
QLabel#metricValue {{ color: {c['text_primary']}; font-size: 16pt; font-weight: 700; }}
QLabel#metricValuePositive {{ color: {c['success']}; font-size: 16pt; font-weight: 700; }}
QLabel#metricValueNegative {{ color: {c['danger']}; font-size: 16pt; font-weight: 700; }}
QLabel#metricValueWarning {{ color: {c['warning']}; font-size: 16pt; font-weight: 700; }}
QLabel#metricHint {{ color: {c['text_secondary']}; font-size: 8pt; }}
QLabel#metricIcon {{ background: {c['surface_alt']}; color: {c['primary']}; border-radius: 18px; min-width: 38px; min-height: 38px; font-size: 16pt; font-weight: 700; }}
QLabel#dashboardGreeting {{ color: {c['text_primary']}; font-size: {int(f['title_size'])}pt; font-weight: 700; }}
QFrame#dashboardPanel {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: {radius}px; }}
QLabel#panelTitle {{ color: {c['text_primary']}; font-size: 12pt; font-weight: 700; }}
QLabel#listAmountPositive {{ color: {c['success']}; font-weight: 700; }}
QLabel#listAmountNegative {{ color: {c['danger']}; font-weight: 700; }}
QFrame#dashboardRow {{ background: transparent; border-bottom: 1px solid {c['border']}; }}
QFrame#financeTip {{ background: {c['surface_alt']}; border: 1px solid {c['border']}; border-radius: {radius}px; }}
"""


def get_theme_config(nome=None, custom_config=None):
    nome = normalize_theme_name(nome or Session.get_config("tema", DEFAULT_THEME))
    if nome == "Personalizado" and custom_config:
        validate_theme_config(custom_config)
        return deepcopy(custom_config)
    return deepcopy(THEME_CONFIGS.get(nome, THEME_CONFIGS[DEFAULT_THEME]))


def get_theme(nome=None, custom_config=None):
    return build_stylesheet(get_theme_config(nome, custom_config))


def available_themes():
    return list(THEME_CONFIGS) + ["Personalizado"]


# API legada mantida para módulos externos.
THEMES = {nome: (lambda n=nome: get_theme(n)) for nome in THEME_CONFIGS}
THEMES.update({alias: (lambda n=target: get_theme(n)) for alias, target in THEME_ALIASES.items() if target != "Personalizado"})
V = {
    "success": THEME_CONFIGS[DEFAULT_THEME]["cores"]["success"],
    "danger": THEME_CONFIGS[DEFAULT_THEME]["cores"]["danger"],
    "warning": THEME_CONFIGS[DEFAULT_THEME]["cores"]["warning"],
    "primary": THEME_CONFIGS[DEFAULT_THEME]["cores"]["primary"],
}


def apply_theme(app, nome=None):
    app.setStyleSheet(get_theme(nome))


def current_theme():
    return normalize_theme_name(Session.get_config("tema", DEFAULT_THEME))


def register_theme(nome, builder):
    if nome and callable(builder):
        THEMES[nome] = builder
