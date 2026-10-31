import ast
from pathlib import Path

import pytest
from PyQt5.QtWidgets import QApplication, QLabel

from core import i18n
from core.translator_app import TranslatorApp
from services.argos_service import ArgosService


@pytest.fixture(autouse=True)
def restore_translator_language(monkeypatch):
    """Restaura o idioma global mesmo quando um teste o altera diretamente."""
    monkeypatch.setattr(TranslatorApp, "_current_lang", TranslatorApp._current_lang)


def _fixed_ui_keys():
    root = Path(__file__).resolve().parents[2]
    keys = set()
    sources = ("core", "controllers", "database", "form", "models", "services", "utilitarios", "views", "workers")
    for path in (path for source in sources for path in (root / source).rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "get"
                and isinstance(func.value, ast.Name)
                and func.value.id == "TranslatorApp"
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                keys.add(node.args[0].value)
    return keys


def test_all_fixed_ui_text_has_versioned_offline_catalog_entry():
    missing = i18n.missing_keys(_fixed_ui_keys())
    assert missing == {}


@pytest.mark.parametrize("language,expected", [
    ("pt", "Salvar"), ("en", "Save"), ("es", "Guardar"),
])
def test_fixed_text_is_available_without_argos(monkeypatch, language, expected):
    monkeypatch.setattr(
        ArgosService, "traduzir",
        classmethod(lambda cls, *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Argos não deve traduzir texto fixo")
        )),
    )
    TranslatorApp._current_lang = language
    assert TranslatorApp.get("Salvar") == expected


def test_open_component_updates_when_language_changes():
    app = QApplication.instance() or QApplication([])
    label = QLabel("Salvar")
    TranslatorApp.enable_auto_translation(label)
    TranslatorApp.set_language("en")
    app.processEvents()
    assert label.text() == "Save"
    TranslatorApp.set_language("es")
    app.processEvents()
    assert label.text() == "Guardar"
    TranslatorApp.set_language("pt")
    app.processEvents()
    assert label.text() == "Salvar"
    TranslatorApp.unbind(label)


def test_argos_ready_reapplies_dynamic_content(monkeypatch):
    calls = []
    monkeypatch.setattr(TranslatorApp, "translate_all", lambda: calls.append(True))
    TranslatorApp._current_lang = "en"
    TranslatorApp._on_argos_ready("pt", "en")
    assert calls == [True]
