"""A correção de saldo deve afetar o patrimônio, sem fabricar renda/gasto."""
from datetime import date

import pytest

from models.relatorio_model import RelatorioModel
from models.transaction_model import TransactionModel
from services.account_service import AccountService
from services.transaction_service import TransactionService
from conftest import criar_conta, criar_usuario


def seed(db, db_path):
    user = criar_usuario(db, 'neutral_adjustment')
    account = criar_conta(db, user, 'Conta', 100)
    service = TransactionService(db_path)
    for kind, value in [('Receita', 20), ('Despesa', -10)]:
        service.criar_transacao({
            'ID_Usuario': user, 'ID_Conta': account, 'Tipo': kind,
            'Descricao': kind, 'Valor': value, 'Data': date.today().isoformat(),
        })
    return user, account, service


@pytest.mark.parametrize('target', [250, 25, 0, 110])
def test_adjustments_preserve_financial_totals_and_reopening(db, db_path, target):
    user, account, service = seed(db, db_path)
    model = TransactionModel(db_path)
    before_rows = db.fetch_all("SELECT * FROM transacoes ORDER BY ID_Transacao")
    before = model.get_resumo_financeiro(user)
    report = RelatorioModel(db_path)
    before_report = report.get_relatorio_diario(None, user)
    AccountService(db_path).ajustar_saldo(account, target, user)
    assert db.fetch_all("SELECT * FROM transacoes ORDER BY ID_Transacao") == before_rows
    assert model.get_resumo_financeiro(user) == before
    assert model.somar_receitas_periodo(user) == 20
    assert model.calcular_economia_periodo(user) == 10
    assert report.get_relatorio_diario(None, user) == before_report
    assert all(t['Tipo'] != 'Ajuste' for t in report.get_transacoes_ano(date.today().year, user))
    rows = model.get_transactions_by_account(account, user)
    assert rows[0]['Saldo'] == target
    assert rows[-1]['Saldo'] == target + 10
    assert model.get_saldo_antes_periodo(account, '1900-01-01', user) == target - 10
    reopened = AccountService(db_path)
    assert reopened.obter_saldo(account, user) == target
    assert len(rows) == 2


def test_account_panel_balance_survives_pagination_filter_and_reopen(db, db_path, monkeypatch):
    from PyQt5.QtWidgets import QApplication
    from core.session import Session
    from views.painel_account import PainelAccount
    from utilitarios.currency_formatter import CurrencyFormatter

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr('database.database.get_db_path', lambda: db_path)
    user, account, _ = seed(db, db_path)
    Session.set_usuario({'ID_Usuario': user, 'Nome': 'Teste'})
    AccountService(db_path).ajustar_saldo(account, 250, user)
    for _ in range(2):
        panel = PainelAccount()
        panel.itens_por_pagina = 1
        panel.set_conta({'ID_Conta': account})
        assert panel.table.item(0, 7).text() == CurrencyFormatter.format(250)
        panel._next()
        assert panel.table.item(0, 7).text() == CurrencyFormatter.format(260)
        panel.input_busca.setText('Receita')
        panel._filtrar()
        assert panel.table.item(0, 7).text() == CurrencyFormatter.format(260)
        panel.close()
        app.processEvents()


def test_balance_change_through_real_dialog_refreshes_account_panel(db, db_path, monkeypatch):
    from PyQt5.QtCore import Qt, QTimer
    from PyQt5.QtTest import QTest
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from core.session import Session
    from views.ajustar_saldo_dialog import AjustarSaldoDialog
    from views.transacao_view import TransacaoView
    from utilitarios.currency_formatter import CurrencyFormatter

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr('database.database.get_db_path', lambda: db_path)
    monkeypatch.setattr(QMessageBox, 'information', lambda *a: QMessageBox.Ok)
    user, account, _ = seed(db, db_path)
    Session.set_usuario({'ID_Usuario': user, 'Nome': 'Teste'})
    view = TransacaoView()
    item = view.lista_contas.item(0)
    view.lista_contas.setCurrentItem(item)
    view.selecionar_conta(item)
    view.show()
    app.processEvents()

    def save():
        dialog = app.activeModalWidget()
        assert isinstance(dialog, AjustarSaldoDialog)
        QTest.keyClicks(dialog.saldo_edit, '250,00')
        QTest.mouseClick(dialog.btn_salvar, Qt.LeftButton)

    QTimer.singleShot(0, save)
    view._ajustar_saldo_conta()
    assert CurrencyFormatter.format(250) in view.lista_contas.item(0).text()
    assert view.painel_ativo.table.item(0, 7).text() == CurrencyFormatter.format(250)

    def cancel():
        dialog = app.activeModalWidget()
        QTest.keyClicks(dialog.saldo_edit, '999,00')
        QTest.mouseClick(dialog.btn_cancelar, Qt.LeftButton)

    QTimer.singleShot(0, cancel)
    view._ajustar_saldo_conta()
    assert AccountService(db_path).obter_saldo(account, user) == 250
    assert db.fetch_one("SELECT COUNT(*) n FROM transacoes WHERE Tipo='Ajuste'")['n'] == 0
    view.close()
    app.processEvents()
    reopened = TransacaoView()
    reopened.selecionar_conta(reopened.lista_contas.item(0))
    assert reopened.painel_ativo.table.item(0, 7).text() == CurrencyFormatter.format(250)
    reopened.close()
    app.processEvents()


def test_statement_preserves_initial_balance_and_outside_period_movements(db, db_path):
    user = criar_usuario(db, 'statement_dates')
    account = criar_conta(db, user, 'Conta', 100)
    model = TransactionModel(db_path)
    for day, value in [('2026-01-01', 20), ('2026-02-01', -10), ('2026-03-01', 50)]:
        model.add_transaction({'ID_Usuario': user, 'ID_Conta': account,
                               'Tipo': 'Receita' if value > 0 else 'Despesa',
                               'Descricao': day, 'Valor': value, 'Data': day})
    db.execute_query('UPDATE contas SET Saldo_Atual=160 WHERE ID_Conta=?', (account,))
    rows = model.get_transactions_by_account_periodo(account, '2026-02-01', '2026-02-28', user)
    assert len(rows) == 1 and rows[0]['Saldo'] == 110
    assert model.get_saldo_antes_periodo(account, '2026-02-01', user) == 120


def test_editing_account_balance_creates_no_history(db, db_path):
    user, account, _ = seed(db, db_path)
    service = AccountService(db_path)
    service.atualizar_conta(account, {'Saldo_Atual': 250}, user)
    service.atualizar_conta(account, {'Nome_Conta': 'Renomeada'}, user)
    rows = db.fetch_all("SELECT Tipo, Valor FROM transacoes WHERE Descricao='Ajuste de saldo'")
    assert rows == []
    assert service.obter_saldo(account, user) == 250


def test_empty_account_panel_shows_corrected_balance(db, db_path, monkeypatch):
    from PyQt5.QtWidgets import QApplication
    from core.session import Session
    from views.painel_account import PainelAccount
    from utilitarios.currency_formatter import CurrencyFormatter

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr('database.database.get_db_path', lambda: db_path)
    user = criar_usuario(db, 'empty_adjustment')
    account = criar_conta(db, user, 'Vazia', 100)
    Session.set_usuario({'ID_Usuario': user, 'Nome': 'Teste'})
    panel = PainelAccount()
    panel.set_conta({'ID_Conta': account})
    AccountService(db_path).ajustar_saldo(account, 250, user)
    panel.carregar_historico()
    assert CurrencyFormatter.format(250) in panel.lbl_saldo_atual.text()
    assert panel.table.rowCount() == 0
    assert db.fetch_all('SELECT * FROM transacoes') == []
    panel.close()
    app.processEvents()


def test_no_special_type_or_reclassification_migration(db, db_path):
    user = criar_usuario(db, 'legacy_unchanged')
    account = criar_conta(db, user, 'Legado', 250)
    db.execute_insert("""INSERT INTO transacoes
        (ID_Conta, Tipo, Descricao, Valor, Data, Notas, ID_Usuario)
        VALUES (?, 'Receita', 'Ajuste de saldo', 150, '2026-10-01',
                'Saldo ajustado de 100.00 para 250.00.', ?)""", (account, user))
    before = db.fetch_all('SELECT * FROM transacoes')
    db._run_migrations()
    assert db.fetch_all('SELECT * FROM transacoes') == before
    assert db.fetch_one('SELECT MAX(Versao) AS n FROM schema_migrations')['n'] == 8
    sql = db.fetch_one("SELECT sql FROM sqlite_master WHERE name='transacoes'")['sql']
    assert "'Ajuste'" not in sql
