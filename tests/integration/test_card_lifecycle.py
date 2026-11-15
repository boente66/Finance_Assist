"""Ativação, consultas históricas, barreiras financeiras e exclusão sem cascatas."""
from datetime import date

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox

from test_card_networks import controller, app, payload
from conftest import criar_usuario, criar_conta, criar_lancamento
from core.session import Session
from core.translator_app import TranslatorApp
from services.fatura_service import FaturaService
from services.schedule_service import ScheduleService
from models.backup_model import BackupModel
from views.transacao_view import TransacaoView


def test_toggle_reactivate_and_default_filter(controller, db):
    card = controller.criar_cartao(payload(bandeira='Mastercard'))
    before = dict(card)
    assert controller.excluir_cartao(card['ID_Cartao'])  # API legada é inativação.
    assert controller.listar_cartoes() == []
    inactive = controller.listar_cartoes(incluir_inativos=True)[0]
    assert inactive == {**before, 'Ativo': 0}
    assert controller.reativar_cartao(card['ID_Cartao'])
    assert controller.listar_cartoes()[0] == before
    assert db.fetch_all('PRAGMA foreign_key_check') == []


@pytest.mark.parametrize('state', [-1, 2, None, '1', 'inativo', 0.5])
def test_invalid_state_rejected_without_write(controller, db, state):
    card = controller.criar_cartao(payload())
    before = db.fetch_all('SELECT * FROM credito')
    with pytest.raises(ValueError, match='Estado'):
        controller.criar_cartao(payload(ativo=state))
    with pytest.raises(ValueError, match='Estado'):
        controller.editar_cartao(card['ID_Cartao'], {'ativo': state})
    assert db.fetch_all('SELECT * FROM credito') == before


def test_permanent_delete_only_without_dependencies(controller, db):
    card = controller.criar_cartao(payload())
    assert not any(d['total'] for d in controller.dependencias_cartao(card['ID_Cartao']))
    assert controller.excluir_cartao_definitivamente(card['ID_Cartao'])
    assert controller.buscar_cartao_por_id(card['ID_Cartao']) is None
    assert db.fetch_all('PRAGMA foreign_key_check') == []
    assert list(db.fetch_one('PRAGMA integrity_check').values()) == ['ok']


@pytest.mark.parametrize('dependency', ['purchase', 'empty_invoice', 'future_fk'])
def test_delete_detects_all_real_fks_including_cascade_and_future_table(controller, db, db_path, dependency):
    card = controller.criar_cartao(payload(bandeira='Visa'))
    key, user = card['ID_Cartao'], card['ID_Usuario']
    if dependency == 'purchase':
        criar_lancamento(db, user, key)
    elif dependency == 'empty_invoice':
        FaturaService(db_path).sincronizar_ciclo(key, 12, 2099, user)
    else:
        db.execute_query('CREATE TABLE future_link (id INTEGER PRIMARY KEY, card INTEGER REFERENCES credito(ID_Cartao) ON DELETE CASCADE)')
        db.execute_query('INSERT INTO future_link VALUES (1,?)', (key,))
    tables = [r['name'] for r in db.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    before = {t: db.fetch_all(f'SELECT * FROM "{t}" ORDER BY 1') for t in tables}
    with pytest.raises(ValueError, match='histórico'):
        controller.excluir_cartao_definitivamente(key)
    assert {t: db.fetch_all(f'SELECT * FROM "{t}" ORDER BY 1') for t in tables} == before
    assert controller.excluir_cartao(key)
    assert controller.buscar_cartao_por_id(key)['Ativo'] == 0


def test_permanent_delete_rejects_other_owner(controller, db, db_path):
    card = controller.criar_cartao(payload())
    other = criar_usuario(db, 'not_owner')
    with pytest.raises(ValueError):
        FaturaService(db_path).excluir_cartao_definitivamente(card['ID_Cartao'], other)
    assert controller.buscar_cartao_por_id(card['ID_Cartao'])


@pytest.mark.parametrize('operation', ['purchase', 'credit', 'import', 'schedule'])
def test_inactive_cannot_receive_new_operations(controller, db, db_path, operation):
    card = controller.criar_cartao(payload(ativo=0))
    user, key = card['ID_Usuario'], card['ID_Cartao']
    service = FaturaService(db_path)
    data = {'ID_Cartao': key, 'ID_Usuario': user, 'Descricao': 'Compra',
            'Valor': 50, 'Data': '2099-12-01', 'Competencia_Mes': 12, 'Competencia_Ano': 2099}
    if operation == 'schedule':
        assert not ScheduleService(db_path).add_schedule({**data, 'Tipo': 'Cartão'})
        assert db.fetch_all('SELECT * FROM agendamentos') == []
    else:
        with pytest.raises(ValueError, match='inativo'):
            if operation == 'purchase':
                service.registrar_despesa_cartao(data)
            elif operation == 'credit':
                service.adicionar_credito_fatura({**data, 'Tipo_Credito': 'Cashback'})
            else:
                service.salvar_lote_importado([data], user)
    assert db.fetch_all('SELECT * FROM lancamentos') == []
    assert db.fetch_all('SELECT * FROM faturas_cartao') == []


def test_inactive_preserves_debt_projection_and_allows_settling_existing_invoice(controller, db, db_path):
    card = controller.criar_cartao(payload())
    key, user = card['ID_Cartao'], card['ID_Usuario']
    account = criar_conta(db, user, 'Conta de pagamento', 1000)
    criar_lancamento(db, user, key, valor=100)
    controller.excluir_cartao(key)
    service = FaturaService(db_path)
    assert service.listar_faturas_projetadas(user, data_referencia=date(2026, 7, 1))
    result = service.pagar_fatura(key, 7, 2026, account, user)
    assert result['sucesso']
    assert db.fetch_one('SELECT Ativo FROM credito')['Ativo'] == 0
    assert db.fetch_all('PRAGMA foreign_key_check') == []


@pytest.mark.parametrize('state', [0, 1])
def test_backup_preserves_network_and_state(controller, db_path, tmp_path, state):
    card = controller.criar_cartao(payload(bandeira='Mastercard', ativo=state))
    filename = BackupModel(db_path).criar_backup(str(tmp_path), 'state-backup-test')
    restored = BackupModel(str(tmp_path / 'restored.db'))
    assert restored.restaurar_backup(filename, 'state-backup-test')
    assert restored.db.fetch_one('SELECT Bandeira,Ativo FROM credito') == {'Bandeira': 'Mastercard', 'Ativo': state}


def test_visual_hide_is_read_only_and_reactivation_is_contextual(app, controller, db, monkeypatch):
    active = controller.criar_cartao(payload(nome='Ativo', bandeira='Visa'))
    inactive = controller.criar_cartao(payload(nome='Histórico', ativo=0, bandeira='Elo'))
    view = TransacaoView()
    before = db.fetch_all('SELECT * FROM credito ORDER BY 1')
    assert view.lista_cartoes.count() == 1
    view.show_inactive_cards.setChecked(True)
    assert view.lista_cartoes.count() == 2
    assert db.fetch_all('SELECT * FROM credito ORDER BY 1') == before
    for i in range(view.lista_cartoes.count()):
        item = view.lista_cartoes.item(i)
        if item.data(Qt.UserRole) == inactive['ID_Cartao']:
            view.lista_cartoes.setCurrentItem(item)
            view.selecionar_cartao(item)
            break
    assert not view.painel_ativo.btn_lancar.isEnabled()
    assert not view.painel_ativo.btn_credito.isEnabled()
    assert not view.painel_ativo.btn_importar.isEnabled()
    monkeypatch.setattr(QMessageBox, 'question', lambda *a: QMessageBox.Yes)
    view._alternar_estado_cartao()
    assert controller.buscar_cartao_por_id(inactive['ID_Cartao'])['Ativo'] == 1
    assert view.painel_ativo.btn_lancar.isEnabled()
    view.close()


@pytest.mark.parametrize('language,expected', [('pt','Mostrar cartões inativos'), ('en','Show inactive cards'), ('es','Mostrar tarjetas inactivas')])
def test_lifecycle_controls_translate_without_translating_brand(app, controller, monkeypatch, language, expected):
    controller.criar_cartao(payload(bandeira='Mastercard'))
    monkeypatch.setattr(TranslatorApp, '_current_lang', language)
    view = TransacaoView()
    assert view.show_inactive_cards.text() == expected
    assert 'Mastercard' in view.lista_cartoes.item(0).text()
    view.close()
