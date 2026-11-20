"""IMP-003: context-bound authorization, real keyboard flow and financial history."""
from datetime import date
import gc
import subprocess
import sys

import pytest
from dateutil.relativedelta import relativedelta
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QListWidget

from conftest import criar_usuario, criar_conta, criar_cartao
from controllers.fatura_controller import FaturaController
from core.invoice_maintenance import InvoiceMaintenance
from core.session import Session
from core.translator_app import TranslatorApp
from services.fatura_service import FaturaService
from views.painel_fatura import PainelFatura
from views.editar_fatura_dialog import EditarFaturaDialog


class Owner:
    pass


def test_shortcut_from_card_sidebar_and_module_exit(scenario, app):
    _, service, uid, card, _, _, month, year, _, _, _ = scenario
    window = QWidget()
    layout = QHBoxLayout(window)
    sidebar = QListWidget()
    sidebar.addItem('Cartão selecionado')
    view = PainelFatura()
    layout.addWidget(sidebar)
    layout.addWidget(view)
    view.set_competencia(month, year)
    view.set_cartao(service.buscar_cartao_por_id(card, uid))
    window.show()
    window.activateWindow()
    sidebar.setFocus()
    app.processEvents()
    QTest.keyClick(sidebar, Qt.Key_D, Qt.ControlModifier)
    app.processEvents()
    assert view._maintenance_capability is not None
    view.hide()
    app.processEvents()
    QTest.keyClick(sidebar, Qt.Key_D, Qt.ControlModifier)
    app.processEvents()
    assert view._maintenance_capability is None
    window.close()


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def scenario(db, db_path, monkeypatch):
    monkeypatch.setattr('database.database.get_db_path', lambda: db_path)
    uid = criar_usuario(db, 'maintenance')
    account = criar_conta(db, uid, 'Conta', 1000)
    card = criar_cartao(db, uid)
    Session.set_usuario({'ID_Usuario': uid, 'Nome': 'Teste'})
    competence = date.today().replace(day=1) - relativedelta(months=1)
    service = FaturaService(db_path)
    service.registrar_despesa_cartao({
        'ID_Usuario': uid, 'ID_Cartao': card, 'Descricao': 'Compra original',
        'Valor': 80, 'Data': competence.replace(day=5).isoformat(), 'Num_Parcelas': 1,
    })
    month, year = competence.month, competence.year
    service.sincronizar_ciclo(card, month, year, uid)
    item = service.obter_fatura(card, month, year, uid)[0]
    owner = Owner()
    def activate():
        return service.ativar_manutencao(card, month, year, uid, owner)
    def pay():
        assert service.pagar_fatura(card, month, year, account, uid)['sucesso']
    def panel():
        return service.get_painel_cartao(card, month, year, uid)
    yield db, service, uid, card, account, item['ID_Lancamento'], month, year, activate, pay, panel
    InvoiceMaintenance.revoke_all()
    Session.set_usuario(None)


def history(db):
    return {table: db.fetch_all(f'SELECT * FROM {table} ORDER BY 1')
            for table in ('pagamentos_fatura', 'transacoes', 'contas')}


@pytest.mark.parametrize('paid', [False, True])
def test_normal_locked_and_explicit_authorization_reversible(scenario, paid):
    db, service, uid, card, _, item, month, year, activate, pay, panel = scenario
    if paid:
        pay()
    with pytest.raises(ValueError):
        service.atualizar_lancamento(item, {'Descricao': 'Bloqueada'}, uid)
    with pytest.raises(ValueError):
        service.excluir_lancamento(item, uid)
    before = history(db)
    token = activate()
    # Another controller and service instance must receive the actual capability.
    controller = FaturaController()
    assert controller.atualizar_lancamento(item, {'Descricao': 'Corrigida'}, capacidade=token)
    assert panel()['fatura']['status'] == ('PAGA' if paid else 'FECHADA')
    assert history(db) == before
    controller.desativar_manutencao(token)
    with pytest.raises(PermissionError):
        controller.atualizar_lancamento(item, {'Descricao': 'Token antigo'}, capacidade=token)
    with pytest.raises(ValueError):
        controller.atualizar_lancamento(item, {'Descricao': 'Sem token'})


@pytest.mark.parametrize('value,remaining,credit', [(120, 40, 0), (50, 0, 30)])
def test_paid_history_and_derived_values_are_honest(scenario, value, remaining, credit):
    db, service, uid, card, _, item, _, _, activate, pay, panel = scenario
    pay()
    before = history(db)
    paid_entry = service.obter_lancamento(item, uid)
    token = activate()
    service.atualizar_lancamento(item, {'Valor': value}, uid, capacidade=token)
    result = panel()
    assert result['fatura']['status'] == 'PAGA'
    assert result['fatura']['pagamentos'] == 80
    assert result['fatura']['saldo_a_pagar'] == remaining
    assert result['fatura']['saldo_credor'] == credit
    assert result['fatura']['diferenca_total_pago'] == value - 80
    assert result['resumo']['saldo_devedor'] == remaining
    assert history(db) == before
    edited = service.obter_lancamento(item, uid)
    assert edited['Paga'] == paid_entry['Paga']
    assert edited['ID_Transacao'] == paid_entry['ID_Transacao']
    pending = service.listar_faturas_projetadas(uid)
    assert any(row['valor'] == remaining for row in pending) if remaining else not pending


def test_paid_difference_can_be_settled_without_changing_old_payments(scenario):
    db, service, uid, card, account, item, month, year, activate, pay, panel = scenario
    pay()
    original = db.fetch_all('SELECT * FROM pagamentos_fatura')
    token = activate()
    service.atualizar_lancamento(item, {'Valor': 120}, uid, capacidade=token)
    service.desativar_manutencao(token)
    payment_result = service.pagar_fatura(card, month, year, account, uid, 40)
    assert payment_result['sucesso'], payment_result
    assert db.fetch_all('SELECT * FROM pagamentos_fatura ORDER BY ID_Pagamento')[0] == original[0]
    assert panel()['fatura']['saldo_a_pagar'] == 0
    assert panel()['fatura']['pagamentos'] == 120
    assert len(db.fetch_all('SELECT * FROM pagamentos_fatura')) == 2


@pytest.mark.parametrize('value', [0, -1, float('inf'), float('nan')])
def test_invalid_values_remain_blocked(scenario, value):
    _, service, uid, _, _, item, _, _, activate, _, _ = scenario
    original = service.obter_lancamento(item, uid)
    with pytest.raises(ValueError):
        service.atualizar_lancamento(item, {'Valor': value}, uid, capacidade=activate())
    assert service.obter_lancamento(item, uid) == original


@pytest.mark.parametrize('field,value', [('Competencia_Mes', 12), ('Tipo_Movimento', 'PAGAMENTO'),
                                        ('ID_Usuario', 999), ('ID_Cartao', 999), ('Paga', 1)])
def test_capability_does_not_authorize_structure_changes(scenario, field, value):
    _, service, uid, _, _, item, _, _, activate, _, _ = scenario
    original = service.obter_lancamento(item, uid)
    if original.get(field) == value:
        value = 11
    with pytest.raises(ValueError):
        service.atualizar_lancamento(item, {field: value}, uid, capacidade=activate())
    assert service.obter_lancamento(item, uid) == original


@pytest.mark.parametrize('forged', [True, {}, 'unlocked', object()])
def test_forged_capabilities_are_rejected(scenario, forged):
    _, service, uid, _, _, item, _, _, _, _, _ = scenario
    with pytest.raises(PermissionError):
        service.atualizar_lancamento(item, {'Descricao': 'Inválida'}, uid, capacidade=forged)


def test_cross_user_and_foreign_relationships_are_rejected(scenario):
    db, service, uid, card, _, item, month, year, activate, _, _ = scenario
    token = activate()
    other = criar_usuario(db, 'other-maintenance')
    category = db.execute_insert("INSERT INTO categorias (Nome, Tipo, ID_Usuario) VALUES ('Privada','Despesa',?)", (other,))
    payee = db.execute_insert("INSERT INTO favorecido (Nome, Tipo, ID_Usuario) VALUES ('Privado','PJ',?)", (other,))
    for field, value in [('ID_Categoria', category), ('ID_Favorecido', payee)]:
        with pytest.raises(ValueError):
            service.atualizar_lancamento(item, {field: value}, uid, capacidade=token)
    with pytest.raises(ValueError):
        service.atualizar_lancamento(item, {'Descricao': 'Outro usuário'}, other, capacidade=token)
    with pytest.raises(PermissionError):
        service.ativar_manutencao(card, month, year, other, Owner())
    Session.set_usuario({'ID_Usuario': other})
    with pytest.raises(PermissionError):
        service.atualizar_lancamento(item, {'Descricao': 'Sessão trocada'}, uid, capacidade=token)


def test_no_database_flag_and_no_restart_restore(scenario):
    db, service, uid, _, _, item, _, _, activate, _, _ = scenario
    schema = db.fetch_all('SELECT * FROM sqlite_master ORDER BY name')
    tables = [r['name'] for r in db.fetch_all("SELECT name FROM sqlite_master WHERE type='table'")]
    before = {name: db.fetch_all(f'SELECT * FROM "{name}"') for name in tables}
    token = activate()
    assert db.fetch_all('SELECT * FROM sqlite_master ORDER BY name') == schema
    assert {name: db.fetch_all(f'SELECT * FROM "{name}"') for name in tables} == before
    output = subprocess.check_output([sys.executable, '-c',
        'from core.invoice_maintenance import InvoiceMaintenance; print(len(InvoiceMaintenance._grants))'], text=True)
    assert output.strip() == '0'
    Session.set_usuario(None)
    Session.set_usuario({'ID_Usuario': uid})
    with pytest.raises(PermissionError):
        service.atualizar_lancamento(item, {'Descricao': 'Nova sessão'}, uid, capacidade=token)


@pytest.mark.parametrize('event', ['toggle', 'invoice', 'year', 'card', 'hide', 'logout', 'close'])
def test_real_shortcut_and_context_revocation(scenario, app, event):
    _, service, uid, card, _, item, month, year, _, _, _ = scenario
    view = PainelFatura()
    view.set_competencia(month, year)
    view.set_cartao(service.buscar_cartao_por_id(card, uid))
    view.show(); view.activateWindow(); view.table.setFocus(); app.processEvents()
    QTest.keyClick(view.table, Qt.Key_D, Qt.ControlModifier)
    app.processEvents()
    token = view._maintenance_capability
    assert token is not None
    assert view.maintenance_label.isVisible()
    view.controller.atualizar_lancamento(item, {'Descricao': 'Pelo atalho'}, capacidade=token)
    if event == 'toggle':
        QTest.keyClick(view.table, Qt.Key_D, Qt.ControlModifier)
    elif event == 'invoice':
        view.mes_combo.setCurrentIndex((month % 12))
    elif event == 'year':
        view.ano_combo.addItem(str(year + 1))
        view.ano_combo.setCurrentText(str(year + 1))
    elif event == 'card':
        other_card = criar_cartao(scenario[0], uid, 'Outro contexto')
        view.set_cartao(service.buscar_cartao_por_id(other_card, uid))
    elif event == 'hide':
        view.hide()
    elif event == 'logout':
        Session.set_usuario(None)
    else:
        view.close()
    app.processEvents()
    assert view._maintenance_capability is None
    assert not view.maintenance_label.isVisible()
    if event == 'logout':
        Session.set_usuario({'ID_Usuario': uid})
    with pytest.raises(PermissionError):
        service.atualizar_lancamento(item, {'Descricao': 'Contexto encerrado'}, uid, capacidade=token)
    view.close(); app.processEvents()


@pytest.mark.parametrize('language', ['pt', 'en', 'es'])
def test_indicator_translation_and_historical_edit_dialog(scenario, app, monkeypatch, language):
    _, service, uid, card, _, item, month, year, activate, _, _ = scenario
    monkeypatch.setattr(TranslatorApp, '_current_lang', language)
    view = PainelFatura()
    assert {'pt': 'Modo de ajuste temporário ativo', 'en': 'Temporary adjustment mode active',
            'es': 'Modo de ajuste temporal activo'}[language] in view.maintenance_label.text()
    token = activate()
    dialog = EditarFaturaDialog(service.obter_lancamento(item, uid), capacidade=token)
    assert dialog.fatura_combo.currentData() == {'Mes': month, 'Ano': year} or (
        dialog.fatura_combo.currentData()['Mes'], dialog.fatura_combo.currentData()['Ano']) == (month, year)
    assert not dialog.fatura_combo.isEnabled()
    assert not dialog.parcelas_spin.isEnabled()
    dialog.close(); view.close(); app.processEvents()


def test_authorized_delete_preserves_paid_history(scenario):
    db, service, uid, _, _, item, _, _, activate, pay, panel = scenario
    pay()
    before = history(db)
    assert service.excluir_lancamento(item, uid, capacidade=activate())
    assert history(db) == before
    result = panel()['fatura']
    assert result['status'] == 'PAGA'
    assert result['pagamentos'] == 80
    assert result['saldo_credor'] == 80


def test_payment_rows_cannot_be_edited_or_deleted(scenario):
    db, service, uid, card, _, item, month, year, activate, _, _ = scenario
    payment = db.execute_insert('''INSERT INTO lancamentos
        (ID_Cartao, ID_Usuario, Descricao, Valor, Data, Competencia_Mes,
         Competencia_Ano, ID_Fatura, Tipo_Movimento)
        SELECT ID_Cartao, ID_Usuario, 'Pagamento legado', -10, Data,
               Competencia_Mes, Competencia_Ano, ID_Fatura, 'PAGAMENTO'
        FROM lancamentos WHERE ID_Lancamento=?''', (item,))
    token = activate()
    original = service.obter_lancamento(payment, uid)
    with pytest.raises(ValueError):
        service.atualizar_lancamento(payment, {'Valor': 20}, uid, capacidade=token)
    with pytest.raises(ValueError):
        service.excluir_lancamento(payment, uid, capacidade=token)
    assert service.obter_lancamento(payment, uid) == original


def test_other_invoice_and_card_cannot_use_same_grant(scenario):
    db, service, uid, card, _, item, month, year, activate, _, _ = scenario
    token = activate()
    other_card = criar_cartao(db, uid, 'Outro cartão')
    source = service.obter_lancamento(item, uid)
    for target_card, target_month in ((other_card, month), (card, month % 12 + 1)):
        inserted = dict(source)
        inserted.pop('ID_Lancamento')
        inserted['ID_Cartao'] = target_card
        inserted['Competencia_Mes'] = target_month
        cycle = service.sincronizar_ciclo(target_card, target_month, year, uid)
        inserted['ID_Fatura'] = cycle['ID_Fatura']
        service.lancamento_model.add_lancamento(inserted)
        other = service.lancamento_model.get_lancamentos_por_fatura(target_card, target_month, year, uid)[0]
        with pytest.raises(PermissionError):
            service.atualizar_lancamento(other['ID_Lancamento'], {'Descricao': 'Fora do contexto'}, uid, capacidade=token)


def test_owner_collection_revokes_capability(scenario):
    _, service, uid, card, _, item, month, year, _, _, _ = scenario
    owner = Owner()
    token = service.ativar_manutencao(card, month, year, uid, owner)
    del owner
    gc.collect()
    with pytest.raises(PermissionError):
        service.atualizar_lancamento(item, {'Descricao': 'Dono destruído'}, uid, capacidade=token)


def test_dialog_propagates_grant_and_preserves_paid_fields(scenario, app, monkeypatch):
    _, service, uid, _, _, item, _, _, activate, pay, panel = scenario
    pay()
    dialog = EditarFaturaDialog(service.obter_lancamento(item, uid), capacidade=activate())
    errors = []
    monkeypatch.setattr('views.editar_fatura_dialog.QMessageBox.warning', lambda *args: errors.append(args))
    dialog.valor_edit.setText('125,00')
    dialog.salvar()
    assert errors == []
    assert panel()['fatura']['saldo_a_pagar'] == 45
    assert service.obter_lancamento(item, uid)['Paga'] == 1
    dialog.close(); app.processEvents()


def test_failed_maintenance_rolls_back_the_whole_write(scenario, monkeypatch):
    db, service, uid, _, _, item, _, _, activate, pay, _ = scenario
    pay()
    before = history(db)
    original = service.obter_lancamento(item, uid)
    update = service.lancamento_model.update_lancamento
    def fail_after_write(*args, **kwargs):
        update(*args, **kwargs)
        raise RuntimeError('Falha simulada após UPDATE')
    monkeypatch.setattr(service.lancamento_model, 'update_lancamento', fail_after_write)
    with pytest.raises(RuntimeError):
        service.atualizar_lancamento(item, {'Valor': 999}, uid, capacidade=activate())
    assert service.obter_lancamento(item, uid) == original
    assert history(db) == before


def test_linked_refund_blocks_parent_deletion(scenario):
    db, service, uid, _, _, item, _, _, activate, _, _ = scenario
    db.execute_insert('''INSERT INTO lancamentos
        (ID_Cartao, ID_Usuario, Descricao, Valor, Data, Competencia_Mes,
         Competencia_Ano, ID_Fatura, Tipo_Movimento, ID_Lancamento_Origem)
        SELECT ID_Cartao, ID_Usuario, 'Estorno vinculado', -10, Data,
               Competencia_Mes, Competencia_Ano, ID_Fatura, 'ESTORNO', ID_Lancamento
        FROM lancamentos WHERE ID_Lancamento=?''', (item,))
    before = db.fetch_all('SELECT * FROM lancamentos ORDER BY ID_Lancamento')
    with pytest.raises(ValueError, match='vinculados'):
        service.excluir_lancamento(item, uid, capacidade=activate())
    assert db.fetch_all('SELECT * FROM lancamentos ORDER BY ID_Lancamento') == before


def test_stale_edit_dialog_cannot_save_after_context_closes(scenario, app, monkeypatch):
    _, service, uid, _, _, item, _, _, activate, _, _ = scenario
    token = activate()
    dialog = EditarFaturaDialog(service.obter_lancamento(item, uid), capacidade=token)
    service.desativar_manutencao(token)
    before = service.obter_lancamento(item, uid)
    warnings = []
    monkeypatch.setattr('views.editar_fatura_dialog.QMessageBox.warning', lambda *args: warnings.append(args))
    dialog.valor_edit.setText('125,00')
    dialog.salvar()
    assert len(warnings) == 1
    assert service.obter_lancamento(item, uid) == before
    dialog.close(); app.processEvents()


@pytest.mark.parametrize('width,height', [(724, 587), (810, 635), (1364, 925)])
def test_active_mode_and_paid_difference_remain_visible(scenario, app, width, height):
    _, service, uid, card, _, item, month, year, _, pay, _ = scenario
    pay()
    view = PainelFatura()
    view.set_competencia(month, year)
    view.set_cartao(service.buscar_cartao_por_id(card, uid))
    view.resize(width, height); view.show(); app.processEvents()
    view._alternar_manutencao()
    view.controller.atualizar_lancamento(item, {'Valor': 120}, capacidade=view._maintenance_capability)
    view._carregar(); app.processEvents()
    assert view.maintenance_label.isVisible()
    assert view.payment_difference_label.isVisible()
    assert view.btn_pagar.isEnabled()
    assert view.table.height() >= 210
    assert view.quitacao_label.mapTo(view, view.quitacao_label.rect().bottomRight()).y() < view.height()
    view.close(); app.processEvents()
