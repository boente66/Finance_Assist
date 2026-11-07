from datetime import date

import pytest
from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QApplication

from core.translator_app import TranslatorApp
from utilitarios.currency_formatter import CurrencyFormatter
from utilitarios.date_formatter import DateFormatter


@pytest.fixture(autouse=True)
def restore_language():
    old = TranslatorApp._current_lang
    yield
    TranslatorApp.set_language(old)


@pytest.mark.parametrize('language,symbol,amount,day', [
    ('pt', 'R$', '1.234,56', '07/11/2026'),
    ('es', '€', '1.234,56', '07/11/2026'),
    ('en', '$', '1,234.56', '11/07/2026'),
])
def test_localized_presentation_and_input_preserve_values(language, symbol, amount, day):
    TranslatorApp.set_language(language)
    formatted = CurrencyFormatter.format(1234.56)
    assert symbol in formatted and amount in formatted
    assert CurrencyFormatter.to_float(formatted) == 1234.56
    assert CurrencyFormatter.to_float(amount) == 1234.56
    assert CurrencyFormatter.to_float(CurrencyFormatter.format(-1234.56)) == -1234.56
    assert DateFormatter.iso_to_display('2026-11-07') == day
    assert DateFormatter.iso_to_display(date(2026,11,7)) == day
    # Storage/import contracts remain explicitly Brazilian/ISO.
    assert DateFormatter.br_to_iso('07/11/2026') == '2026-11-07'
    assert DateFormatter.iso_to_br('2026-11-07') == '07/11/2026'


def test_open_debt_dialog_changes_locale_without_changing_entered_values(monkeypatch):
    from views.divida_dialog import DividaDialog
    monkeypatch.setattr('controllers.favorecido_controller.FavorecidoController.listar_favorecidos', lambda self: [])
    app = QApplication.instance() or QApplication([])
    TranslatorApp.set_language('pt')
    dialog = DividaDialog()
    dialog.emprestado.setValue(1234.56)
    dialog.juros.setValue(12.5)
    dialog.contratacao.setDate(QDate(2026,11,7))
    for language, symbol, pattern in [('en', '$', 'MM/dd/yyyy'), ('es', '€', 'dd/MM/yyyy'), ('pt', 'R$', 'dd/MM/yyyy')]:
        TranslatorApp.set_language(language)
        assert dialog.emprestado.value() == 1234.56
        assert symbol in dialog.emprestado.text()
        assert not any(x in dialog.juros.text() for x in ['R$', '$', '€'])
        assert dialog.juros.value() == 12.5
        assert dialog.contratacao.date() == QDate(2026,11,7)
        assert dialog.contratacao.displayFormat() == pattern
    dialog.close(); app.processEvents()
