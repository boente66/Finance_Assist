"""Metadado de cartão: migração aditiva, camadas, interface e compatibilidade."""
import ast
import json
import sqlite3
from pathlib import Path

import pytest
from PyQt5.QtWidgets import QApplication, QMessageBox

from conftest import criar_usuario, criar_cartao, criar_conta, criar_lancamento
from controllers.fatura_controller import FaturaController
from core.i18n_catalogs import CATALOGS
from core.session import Session
from core.translator_app import TranslatorApp
from database.database import Database
from models.backup_model import BackupModel
from models.credito_model import CreditoModel
from services.card_networks import CARD_NETWORKS, normalize_card_network
from services.fatura_service import FaturaService
from utilitarios.crypto_util import decrypt_bytes, encrypt_bytes
from views.criar_cartao_dialog import CriarCartaoDialog, EditCartaoDialog


@pytest.fixture
def controller(db, db_path, monkeypatch):
    monkeypatch.setattr('database.database.get_db_path', lambda: db_path)
    user = criar_usuario(db, 'card_network_user')
    previous = Session.get_usuario()
    Session.set_usuario({'ID_Usuario': user, 'Nome': 'Teste', 'Nivel_Acesso': 'admin'})
    value = FaturaController()
    yield value
    Session.set_usuario(previous)


def payload(**changes):
    result = dict(nome='Itaú Click', limite=5000, dia_fechamento=10,
                  dia_vencimento=20, ativo=1)
    result.update(changes)
    return result


@pytest.fixture(scope='module')
def app():
    application = QApplication.instance() or QApplication([])
    yield application


def test_new_database_and_idempotence(db):
    assert db._card_network_valid()
    column = next(r for r in db.fetch_all('PRAGMA table_info(credito)')
                  if r['name'] == 'Bandeira')
    assert column['type'] == 'TEXT' and column['notnull'] == 0
    assert column['dflt_value'] in (None, 'NULL')
    db._run_migrations()
    db._run_migrations()
    assert db.fetch_one('SELECT count(*) AS n FROM schema_migrations WHERE Versao=9')['n'] == 1


@pytest.mark.parametrize('column_already_exists', [False, True])
def test_legacy_preserves_financial_rows_relations_and_table_identity(
    db, db_path, column_already_exists
):
    user = criar_usuario(db, 'legacy_network')
    card = criar_cartao(db, user, 'Mastercard Nome legado')
    criar_lancamento(db, user, card)
    FaturaService(db_path).sincronizar_ciclo(card, 7, 2026, user)
    before_card = db.fetch_one('SELECT * FROM credito WHERE ID_Cartao=?', (card,))
    before_card.pop('Bandeira')
    before = {table: db.fetch_all(f'SELECT * FROM {table}')
              for table in ('lancamentos', 'faturas_cartao', 'pagamentos_fatura')}
    root = db.fetch_one("SELECT rootpage FROM sqlite_master WHERE name='credito'")
    db.connection.execute('DELETE FROM schema_migrations WHERE Versao=9')
    if not column_already_exists:
        db.connection.execute('ALTER TABLE credito DROP COLUMN Bandeira')
    db.connection.commit()
    db._run_migrations()
    db._run_migrations()
    after = db.fetch_one('SELECT * FROM credito WHERE ID_Cartao=?', (card,))
    assert after.pop('Bandeira') is None
    assert after == before_card  # Nome, IDs e todos os campos financeiros intactos.
    for table, rows in before.items():
        assert db.fetch_all(f'SELECT * FROM {table}') == rows
    assert db.fetch_one("SELECT rootpage FROM sqlite_master WHERE name='credito'") == root
    assert db.fetch_all('PRAGMA foreign_key_check') == []
    assert list(db.fetch_one('PRAGMA integrity_check').values()) == ['ok']


@pytest.mark.parametrize('network', CARD_NETWORKS)
def test_all_networks_through_controller_service_model_and_reopen(controller, db_path, network):
    card = controller.criar_cartao(payload(bandeira=network))
    key = card['ID_Cartao']
    assert card['Bandeira'] == network
    assert controller.buscar_cartao_por_id(key)['Bandeira'] == network
    assert any(r['ID_Cartao'] == key and r['Bandeira'] == network
               for r in controller.listar_cartoes())
    with sqlite3.connect(db_path) as connection:
        assert connection.execute('SELECT Bandeira FROM credito WHERE ID_Cartao=?',
                                  (key,)).fetchone() == (network,)
    assert controller.editar_cartao(key, {'nome': 'Novo nome'})
    assert controller.buscar_cartao_por_id(key)['Bandeira'] == network
    assert controller.editar_cartao(key, {'bandeira': None})
    assert controller.buscar_cartao_por_id(key)['Bandeira'] is None


@pytest.mark.parametrize('value', [None, '', '  ', 'Sem bandeira', ' sem bandeira '])
def test_neutral_network_is_sql_null(controller, db_path, value):
    card = controller.criar_cartao(payload(bandeira=value))
    with sqlite3.connect(db_path) as connection:
        assert connection.execute('SELECT Bandeira IS NULL FROM credito WHERE ID_Cartao=?',
                                  (card['ID_Cartao'],)).fetchone() == (1,)


@pytest.mark.parametrize('value', ['Outra', 'Desconhecida', 'No card network', 42, {}, 'Visa Mastercard'])
def test_invalid_network_cannot_create_or_update(controller, db, value):
    card = controller.criar_cartao(payload(bandeira='Visa'))
    before = db.fetch_all('SELECT * FROM credito')
    with pytest.raises(ValueError, match='Bandeira'):
        controller.criar_cartao(payload(bandeira=value))
    with pytest.raises(ValueError, match='Bandeira'):
        controller.editar_cartao(card['ID_Cartao'], {'bandeira': value})
    assert db.fetch_all('SELECT * FROM credito') == before


def test_service_normalizes_case_without_mutating_caller():
    assert normalize_card_network('  mAsTeRcArD  ') == 'Mastercard'


def test_update_network_only_preserves_finance_and_ownership(controller, db, db_path):
    card = controller.criar_cartao(payload(bandeira='Visa'))
    key, user = card['ID_Cartao'], card['ID_Usuario']
    criar_lancamento(db, user, key)
    FaturaService(db_path).sincronizar_ciclo(key, 7, 2026, user)
    before = {t: db.fetch_all(f'SELECT * FROM {t}') for t in
              ('lancamentos', 'faturas_cartao', 'pagamentos_fatura', 'contas')}
    assert controller.editar_cartao(key, {'bandeira': 'Mastercard'})
    actual = controller.buscar_cartao_por_id(key)
    assert {k: v for k, v in actual.items() if k != 'Bandeira'} == {
        k: v for k, v in card.items() if k != 'Bandeira'}
    for table, rows in before.items():
        assert db.fetch_all(f'SELECT * FROM {table}') == rows
    other = criar_usuario(db, 'other_card_user')
    with pytest.raises(ValueError):
        FaturaService(db_path).editar_cartao(key, {'Bandeira': 'Elo'}, other)


def test_soft_delete_preserves_existing_dependencies(controller, db, db_path):
    card = controller.criar_cartao(payload(bandeira='Mastercard'))
    key, user = card['ID_Cartao'], card['ID_Usuario']
    criar_lancamento(db, user, key)
    FaturaService(db_path).sincronizar_ciclo(key, 7, 2026, user)
    before = {t: db.fetch_all(f'SELECT * FROM {t}')
              for t in ('lancamentos', 'faturas_cartao')}
    assert controller.excluir_cartao(key)
    actual = controller.buscar_cartao_por_id(key)
    assert actual['Ativo'] == 0 and actual['Bandeira'] == 'Mastercard'
    assert not controller.listar_cartoes()
    for table, rows in before.items():
        assert db.fetch_all(f'SELECT * FROM {table}') == rows
    assert db.fetch_all('PRAGMA foreign_key_check') == []


def test_create_inactive_and_model_omitted_network_preserves_value(controller, db_path):
    card = controller.criar_cartao(payload(bandeira='Elo', ativo=0))
    assert card['Ativo'] == 0
    assert not controller.listar_cartoes()
    values = dict(card)
    values.pop('Bandeira')
    values['Nome'] = 'Nome alterado'
    model = CreditoModel(db_path)
    assert model.update_cartao(card['ID_Cartao'], values, card['ID_Usuario'])
    assert model.get_cartao_by_id(card['ID_Cartao'], card['ID_Usuario'])['Bandeira'] == 'Elo'


@pytest.mark.parametrize('limit', [0, 123.4567, 2000000])
def test_form_network_only_does_not_rewrite_legacy_financial_values(
    app, controller, db, monkeypatch, limit
):
    monkeypatch.setattr(QMessageBox, 'information', lambda *a: None)
    card = controller.criar_cartao(payload(bandeira='Visa'))
    db.execute_query('UPDATE credito SET Limite=? WHERE ID_Cartao=?',
                     (limit, card['ID_Cartao']))
    card = controller.buscar_cartao_por_id(card['ID_Cartao'])
    dialog = EditCartaoDialog(cartao=card)
    dialog.bandeira_combo.setCurrentIndex(dialog.bandeira_combo.findData('Mastercard'))
    dialog._salvar()
    assert dialog.result() == dialog.Accepted
    after = controller.buscar_cartao_por_id(card['ID_Cartao'])
    assert after['Limite'] == limit
    assert {k: v for k, v in after.items() if k != 'Bandeira'} == {
        k: v for k, v in card.items() if k != 'Bandeira'}
    dialog.close()


def test_backup_restore_new_and_old_payload(controller, db_path, tmp_path):
    card = controller.criar_cartao(payload(bandeira='Mastercard'))
    backup = BackupModel(db_path)
    filename = backup.criar_backup(str(tmp_path), 'network-test-secret')
    target = BackupModel(str(tmp_path / 'restore.db'))
    assert target.restaurar_backup(filename, 'network-test-secret')
    assert target.db.fetch_one('SELECT Bandeira FROM credito')['Bandeira'] == 'Mastercard'
    assert target.db.fetch_all('PRAGMA foreign_key_check') == []
    envelope = json.loads(Path(filename).read_text())
    old_data = json.loads(decrypt_bytes(envelope['payload'], 'network-test-secret'))
    for row in old_data['credito']:
        row.pop('Bandeira')
    envelope['payload'] = encrypt_bytes(json.dumps(old_data).encode(), 'network-test-secret')
    old_file = tmp_path / 'legacy.kp'
    old_file.write_text(json.dumps(envelope))
    assert target.restaurar_backup(str(old_file), 'network-test-secret')
    assert target.db.fetch_one('SELECT ID_Cartao, Bandeira FROM credito') == {
        'ID_Cartao': card['ID_Cartao'], 'Bandeira': None}


@pytest.mark.parametrize('language,label,neutral', [
    ('pt', 'Bandeira', 'Sem bandeira'),
    ('en', 'Card network', 'No card network'),
    ('es', 'Red de tarjeta', 'Sin red'),
])
def test_forms_translations_selection_and_no_write_on_open(
    app, controller, db, monkeypatch, language, label, neutral
):
    # Tradutor real offline; não acionar tradução automática/rede.
    monkeypatch.setattr(TranslatorApp, '_current_lang', language)
    monkeypatch.setattr('core.i18n._current_lang', language, raising=False)
    card = controller.criar_cartao(payload(bandeira='Mastercard'))
    before = db.fetch_all('SELECT * FROM credito')
    create = CriarCartaoDialog()
    edit = EditCartaoDialog(cartao=card)
    legacy = EditCartaoDialog(cartao={**card, 'Bandeira': None})
    assert create.bandeira_combo.count() == 15
    assert create.bandeira_combo.currentData() is None
    assert edit.bandeira_combo.currentData() == 'Mastercard'
    assert legacy.bandeira_combo.currentData() is None
    assert [create.bandeira_combo.itemText(i) for i in range(1, 15)] == list(CARD_NETWORKS)
    assert create.lbl_bandeira.text() == label
    assert create.bandeira_combo.itemText(0) == neutral
    for i in range(15):
        assert not create.bandeira_combo.itemIcon(i).isNull()
    for dialog in (create, edit, legacy):
        dialog.reject()
        dialog.close()
    assert db.fetch_all('SELECT * FROM credito') == before


def test_form_create_edit_persist_and_error_does_not_accept(app, controller, db, monkeypatch):
    monkeypatch.setattr(QMessageBox, 'information', lambda *a: None)
    monkeypatch.setattr(QMessageBox, 'critical', lambda *a: None)
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a: None)
    create = CriarCartaoDialog()
    create.nome_edit.setText('Cartão de teste')
    create.limite_edit.setValue(1200)
    create.fechamento_edit.setValue(10)
    create.vencimento_edit.setValue(20)
    create.bandeira_combo.setCurrentIndex(create.bandeira_combo.findData('Visa'))
    create._salvar()
    assert create.result() == create.Accepted
    card = controller.listar_cartoes()[0]
    assert card['Bandeira'] == 'Visa'
    edit = EditCartaoDialog(cartao=card)
    edit.bandeira_combo.setCurrentIndex(0)
    edit._salvar()
    assert edit.result() == edit.Accepted
    assert controller.buscar_cartao_por_id(card['ID_Cartao'])['Bandeira'] is None
    failed = EditCartaoDialog(cartao=card)
    monkeypatch.setattr(failed.controller, 'editar_cartao', lambda *a: False)
    failed._salvar()
    assert failed.result() != failed.Accepted
    for dialog in (create, edit, failed):
        dialog.close()


def test_missing_icon_keeps_text_and_generic_fallback(app, controller, monkeypatch, tmp_path):
    import views.card_network_selector as selector
    monkeypatch.setattr(selector, 'ICON_DIRECTORY', tmp_path)
    dialog = CriarCartaoDialog()
    assert dialog.bandeira_combo.itemText(1) == 'Visa'
    assert dialog.bandeira_combo.itemData(1) == 'Visa'
    dialog.close()


def test_no_persistence_access_from_form_or_controller():
    root = Path(__file__).resolve().parents[2]
    for relative in ('views/criar_cartao_dialog.py', 'controllers/fatura_controller.py'):
        tree = ast.parse((root / relative).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or '').startswith(('models', 'database', 'sqlite3'))
            if isinstance(node, ast.Import):
                assert not any(n.name.startswith(('models', 'database', 'sqlite3')) for n in node.names)
    for language in ('en', 'es'):
        assert CATALOGS[language]['Bandeira']
        assert CATALOGS[language]['Sem bandeira']
