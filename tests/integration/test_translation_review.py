"""Regressão das correções manuais e dos fluxos financeiros em outros idiomas."""
import ast
import string
from pathlib import Path

import pytest
from PyQt5.QtWidgets import QApplication, QDialogButtonBox, QFormLayout, QMessageBox

from core import i18n
from core.session import Session
from core.translator_app import TranslatorApp
from services.argos_service import ArgosService
from services.divida_service import DividaService
from utilitarios.date_formatter import DateFormatter
from views.agendamento_divida_dialog import AgendamentoDividaDialog
from views.divida_dialog import DividaDialog
from views.divida_view import DividaView
from views.pagamento_divida_dialog import PagamentoDividaDialog
from views.parcelas_divida_view import ParcelasDividaView
from conftest import criar_conta, criar_usuario


@pytest.fixture
def translation_environment(db, db_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr('database.database.get_db_path', lambda: db_path)
    monkeypatch.setattr(TranslatorApp, '_current_lang', 'pt')
    monkeypatch.setattr(TranslatorApp, '_bindings', [])
    monkeypatch.setattr(TranslatorApp, '_translations', {})
    monkeypatch.setattr(Session, 'configuracoes', dict(Session.configuracoes, idioma='pt'))
    uid = criar_usuario(db, 'translation-review')
    criar_conta(db, uid, 'Minha conta', 1000)
    monkeypatch.setattr(Session, 'usuario', {'ID_Usuario': uid})
    missing = []
    monkeypatch.setattr(ArgosService, 'traduzir', classmethod(
        lambda cls, text, **kwargs: missing.append(text) or text))
    def unexpected_message(*args):
        pytest.fail(f'Diálogo de erro inesperado: {args[1:]}')
    monkeypatch.setattr(QMessageBox, 'warning', unexpected_message)
    yield app, uid, missing
    app.processEvents()
    assert missing == [], f'Textos fixos sem catálogo offline: {missing}'


@pytest.mark.parametrize('language,month', [('pt', 'Janeiro'), ('en', 'January'), ('es', 'Enero'), ('pt_BR', 'Janeiro')])
def test_month_lookup_does_not_change_language_or_notify(monkeypatch, language, month):
    monkeypatch.setattr(Session, 'configuracoes', dict(Session.configuracoes, idioma=language))
    notifications = []
    monkeypatch.setattr(Session, '_idioma_listeners', [notifications.append])
    assert DateFormatter.map_nome_mes(1) == month
    assert Session.get_config('idioma') == language
    assert notifications == []


@pytest.mark.parametrize('language,expected', [('en', 'Bank loan'), ('es', 'Préstamo bancario'), ('pt', 'Empréstimo bancário')])
def test_debt_form_translates_without_changing_inserted_type(translation_environment, db, language, expected):
    app, uid, missing = translation_environment
    TranslatorApp.set_language(language)
    dialog = DividaDialog()
    index = dialog.tipo.findData('Empréstimo bancário')
    dialog.tipo.setCurrentIndex(index)
    assert dialog.tipo.currentText() == expected
    assert dialog.windowTitle() == i18n.t('Cadastrar dívida', language)
    dialog.descricao.setText('Descrição pessoal intocada')
    dialog.modelo.setCurrentIndex(dialog.modelo.findData('LIVRE'))
    dialog.emprestado.setValue(100)
    dialog.total.setValue(100)
    dialog.salvar()
    assert dialog.result() == dialog.Accepted
    saved = db.fetch_one('SELECT * FROM dividas WHERE ID_Usuario=?', (uid,))
    assert saved['Tipo_Divida'] == 'Empréstimo bancário'
    assert saved['Tipo_Parcelamento'] == 'LIVRE'
    assert saved['Descricao'] == 'Descrição pessoal intocada'
    assert not any(ref() is dialog for _, ref in TranslatorApp._bindings)


def test_open_debt_screens_follow_language_changes(translation_environment, db_path):
    app, uid, missing = translation_environment
    service = DividaService(db_path)
    debt_id = service.criar({'Descricao': 'Contrato pessoal', 'Tipo_Divida': 'Empréstimo bancário',
        'Tipo_Parcelamento': 'FIXO', 'Valor_Emprestado': 100, 'Valor_Total_Contrato': 100,
        'Quantidade_Parcelas': 2, 'Data_Contratacao': '2026-10-01', 'Primeiro_Vencimento': '2026-11-01'}, uid)
    debt = service.obter(debt_id, uid)
    create = DividaDialog()
    view = DividaView()
    view.load_data()
    payment = PagamentoDividaDialog(debt)
    details = ParcelasDividaView(debt)
    schedule = AgendamentoDividaDialog(debt)
    for language in ('en', 'es', 'pt'):
        TranslatorApp.set_language(language)
        app.processEvents()
        assert create.windowTitle() == i18n.t('Cadastrar dívida', language)
        assert view.title.text() == i18n.t('Dívidas e empréstimos', language)
        assert payment.windowTitle() == i18n.t('Registrar pagamento da dívida', language)
        assert payment.form.itemAt(0, QFormLayout.LabelRole).widget().text() == i18n.t('Conta de pagamento', language)
        assert payment.buttons.button(QDialogButtonBox.Cancel).text() == i18n.t('Cancelar', language)
        assert details.tabs.tabText(0) == i18n.t('Parcelas', language)
        assert details.tabs.widget(0).horizontalHeaderItem(0).text() == i18n.t('Número', language)
        assert schedule.windowTitle() == i18n.t('Agendar pagamento livre', language)
        assert create.tipo.currentData() in service.TIPOS
        assert view.table.item(0, 2).text() == 'Contrato pessoal'
    for widget in (create, payment, details, schedule):
        widget.reject()
    view.close()


def test_excess_payment_message_is_offline_and_does_not_write(translation_environment, db, db_path, monkeypatch):
    app, uid, missing = translation_environment
    service = DividaService(db_path)
    debt_id = service.criar({'Descricao': 'Livre', 'Tipo_Divida': 'Outro',
        'Tipo_Parcelamento': 'LIVRE', 'Valor_Emprestado': 100, 'Valor_Total_Contrato': 100,
        'Data_Contratacao': '2026-10-01'}, uid)
    TranslatorApp.set_language('en')
    dialog = PagamentoDividaDialog(service.obter(debt_id, uid))
    dialog.valor.setValue(100.01)
    messages = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda parent, title, message: messages.append((title, message)))
    dialog.salvar()
    assert messages == [('Payment not recorded', 'The payment exceeds the maximum payable amount of R$ 100.00.')]
    assert db.fetch_one('SELECT COUNT(*) AS n FROM pagamentos_divida')['n'] == 0
    assert db.fetch_one('SELECT Saldo_Atual FROM contas')['Saldo_Atual'] == 1000
    dialog.reject()


def test_original_text_is_not_persisted_as_a_translation(monkeypatch):
    monkeypatch.setattr(TranslatorApp, '_current_lang', 'en')
    monkeypatch.setattr(TranslatorApp, '_translations', {})
    monkeypatch.setattr(ArgosService, 'traduzir', classmethod(lambda cls, text, **kwargs: text))
    monkeypatch.setattr(TranslatorApp, 'save_translations', lambda: pytest.fail('Cache incorreto'))
    assert TranslatorApp.get('Texto dinâmico de teste') == 'Texto dinâmico de teste'
    assert TranslatorApp._translations == {}


def test_offline_catalog_preserves_format_fields():
    def fields(value):
        return sorted(field for _, field, _, _ in string.Formatter().parse(value) if field)
    for language in ('en', 'es'):
        for key, translated in i18n.get_language_dict(language).items():
            assert fields(key) == fields(translated), (language, key, translated)


def test_debt_ui_does_not_call_nonexistent_translation_api():
    for name in ('divida_dialog.py', 'divida_view.py', 'pagamento_divida_dialog.py'):
        tree = ast.parse((Path(__file__).parents[2] / 'views' / name).read_text())
        assert not any(isinstance(node, ast.Attribute) and node.attr == 'translate'
            and isinstance(node.value, ast.Name) and node.value.id == 'TranslatorApp' for node in ast.walk(tree))


@pytest.mark.parametrize('language', ['en', 'es', 'pt'])
def test_invoice_credit_translation_keeps_type_and_direction(translation_environment, db, language):
    from conftest import criar_cartao
    from views.credito_fatura_dialog import CreditoFaturaDialog
    app, uid, missing = translation_environment
    card = criar_cartao(db, uid)
    dialog = CreditoFaturaDialog(card)
    dialog.tipo_combo.setCurrentIndex(dialog.tipo_combo.findData('Ajuste'))
    dialog.natureza_combo.setCurrentIndex(1)
    dialog.descricao_edit.setText('Ajuste pessoal')
    TranslatorApp.set_language(language)
    assert dialog.tipo_combo.currentData() == 'Ajuste'
    assert dialog.natureza_combo.currentIndex() == 1
    assert not dialog.natureza_combo.isHidden()
    dialog.valor_spin.setValue(25)
    dialog.salvar()
    assert dialog.result() == dialog.Accepted
    entry = db.fetch_one('SELECT * FROM lancamentos WHERE ID_Cartao=?', (card,))
    assert entry['Tipo_Movimento'] == 'AJUSTE'
    assert entry['Valor'] == 25
    assert entry['Descricao'] == 'Ajuste pessoal'


def test_invoice_and_date_dialogs_translate_while_open(translation_environment, db):
    from conftest import criar_cartao
    from views.fatura_dialog import FaturaDialog
    from views.date_range_dialog import DateRangeDialog
    app, uid, missing = translation_environment
    card = criar_cartao(db, uid)
    invoice = FaturaDialog(id_cartao=card)
    dates = DateRangeDialog()
    for language in ('en', 'es', 'pt'):
        TranslatorApp.set_language(language)
        app.processEvents()
        assert invoice.windowTitle() == i18n.t('Nova despesa no cartão', language)
        assert invoice.btn_salvar.text() == i18n.t('Salvar', language)
        assert dates.title.text() == i18n.t('Selecione a Data Inicial e Final', language)
        assert dates.calendar_start.locale().name().startswith(language)
    invoice.reject()
    dates.reject()


def test_translation_persistence_uses_data_directory_not_installation(tmp_path, monkeypatch):
    from models.translation_model import TranslationModel
    from utilitarios.translation_storage import TranslationStorage
    data = tmp_path / 'data'
    installation = tmp_path / 'installation'
    installation.mkdir()
    monkeypatch.chdir(installation)
    monkeypatch.setattr('utilitarios.translation_storage.DATA_DIR', str(data))
    monkeypatch.setattr('models.translation_model.DATA_DIR', str(data))
    storage = TranslationStorage()
    assert storage.set('en', 'Texto dinâmico', 'Dynamic text')
    assert TranslationModel().get_translation('en', 'Texto dinâmico') == 'Dynamic text'
    assert TranslationModel().set_translation('es', 'Texto dinâmico', 'Texto dinámico')
    assert TranslationStorage().get('es', 'Texto dinâmico') == 'Texto dinámico'
    assert list(installation.iterdir()) == []


def test_translation_json_failure_preserves_previous_content(tmp_path, monkeypatch):
    from utilitarios.translation_storage import TranslationStorage
    storage = TranslationStorage(tmp_path / 'translations.json')
    assert storage.set('en', 'Anterior', 'Previous')
    def fail_replace(*args):
        raise OSError('falha intermediária')
    monkeypatch.setattr('database.json_database.os.replace', fail_replace)
    assert storage.set('en', 'Nova', 'New') is False
    assert TranslationStorage(tmp_path / 'translations.json').load() == {'en': {'Anterior': 'Previous'}}
