"""Invoice presentation keeps official values and user-adjusted column widths."""
import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QHeaderView
from core.translator_app import TranslatorApp
from core.session import Session
from views.painel_fatura import PainelFatura


@pytest.mark.parametrize('language', ['pt', 'en', 'es'])
@pytest.mark.parametrize('screen', [(1280, 720), (1366, 768), (1920, 1080)])
def test_context_and_flexible_table(monkeypatch, language, screen):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(TranslatorApp, '_current_lang', language)
    monkeypatch.setattr(Session, 'configuracoes', {**Session.configuracoes, 'idioma': language})
    def no_fallback(*args, **kwargs):
        raise AssertionError(f"Missing offline translation: {args}")
    monkeypatch.setattr('services.argos_service.ArgosService.traduzir', no_fallback)
    panel = PainelFatura()
    panel.cartao = {'Nome': 'Cartão com nome longo para compras do dia', 'Bandeira': 'Mastercard', 'Ativo': 0}
    panel._render_header({'limite': 15000, 'saldo_devedor': 2095.2, 'disponivel': 12904.8}, 12, 2099)
    panel._render_resumo({'status': 'ABERTA', 'compras': 2095.2, 'saldo_a_pagar': 2095.2,
                          'data_fechamento': '2099-12-25', 'data_vencimento': '2100-01-05'})
    panel._render_tabela([{'ID_Lancamento': 9, 'Descricao': 'Descrição extensa ' * 30,
                           'Favorecido': 'Comércio com nome longo ' * 10, 'Valor': 123.45}])
    panel.resize(screen[0] - 500, screen[1] - 110)
    panel.show()
    app.processEvents()
    assert panel.table.columnCount() == 7
    assert panel.table.item(0, 0).data(Qt.UserRole) == 9
    assert panel.table.item(0, 1).toolTip() == panel.table.item(0, 1).text()
    assert panel.table.item(0, 2).toolTip() == panel.table.item(0, 2).text()
    assert panel.table.horizontalHeader().sectionResizeMode(2) == QHeaderView.Interactive
    assert panel.table.horizontalHeader().sectionResizeMode(6) == QHeaderView.Interactive
    assert panel.table.columnWidth(2) == max(200, panel.table.viewport().width() - 610)
    panel.table.setColumnWidth(2, 245)
    panel.resize(panel.width() + 30, panel.height())
    app.processEvents()
    assert panel.table.columnWidth(2) == 245
    assert panel.table.height() >= 210
    assert panel.table.geometry().bottom() < panel.height()
    assert panel.quitacao_label.geometry().bottom() < panel.height()
    assert 'Mastercard' in panel.card_context_label.text()
    assert '2099' in panel.invoice_context_label.text()
    assert {'pt': 'Dezembro', 'en': 'December', 'es': 'Diciembre'}[language] in panel.invoice_context_label.text()
    assert panel.btn_pagar.isEnabled()
    panel.close()
