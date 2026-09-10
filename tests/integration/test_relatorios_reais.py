from datetime import date

import pytest
from PyQt5.QtWidgets import QApplication

from core.session import Session
from database.database import Database, DatabaseError
from controllers.relatorio_controller import RelatorioController
from views.relatorio_view import RelatorioView
from utilitarios.currency_formatter import CurrencyFormatter


@pytest.fixture
def report_data(tmp_path, monkeypatch):
    path = str(tmp_path / 'reports.db')
    monkeypatch.setattr('database.database.get_db_path', lambda: path)
    db = Database(path)
    for uid in (1, 2):
        db.execute_query("INSERT INTO usuarios (ID_Usuario,Nome,Login,Senha) VALUES (?, ?, ?, 'hash')", (uid, f'U{uid}', f'u{uid}'))
        db.execute_query("INSERT INTO contas (ID_Conta,Nome_Conta,ID_Usuario) VALUES (?, 'Conta', ?)", (uid, uid))
    previous = Session.get_usuario()
    Session.set_usuario({'ID_Usuario': 1, 'Nome': 'U1', 'Nivel_Acesso': 'usuario'})
    yield db
    Session.set_usuario(previous)
    db.close()


def transaction(db, valor, data=None, uid=1, tipo=None, favorecido=None):
    db.execute_query('''INSERT INTO transacoes
        (ID_Conta, ID_Usuario, Tipo, Descricao, Valor, Data, ID_Favorecido)
        VALUES (?, ?, ?, 'Transação teste', ?, ?, ?)''',
        (uid, uid, tipo or ('Receita' if valor >= 0 else 'Despesa'), valor,
         data or date.today().isoformat(), favorecido))


def test_reports_include_no_payee_and_null_document_without_leaking_users(report_data):
    db = report_data
    db.execute_query("INSERT INTO favorecido (ID_Favorecido,Nome,Tipo,ID_Usuario) VALUES (1,'Sem documento','PF',1)")
    db.execute_query('INSERT INTO pessoa_fisica (ID_Favorecido,CPF) VALUES (1,NULL)')
    transaction(db, 1500)
    transaction(db, -200, favorecido=1)
    transaction(db, 9999, uid=2)
    transaction(db, 500, tipo='Transferência')
    controller = RelatorioController()
    diario = controller.relatorio_diario(7)
    assert sum(row['Receita'] for row in diario) == 1500
    assert sum(row['Despesa'] for row in diario) == 200
    texto = controller.gerar_texto_informe(date.today().year)
    assert texto and '1.500,00' in texto and '200,00' in texto
    assert '9.999,00' not in texto and 'IRRF: R$ 0,00' not in texto
    assert 'Não informado' in texto


def test_legacy_dates_and_old_year_are_available_without_rewriting(report_data):
    transaction(report_data, 50, '15/03/2012')
    controller = RelatorioController()
    assert 2012 in controller.anos_disponiveis()
    assert controller.relatorio_anual(2012)[0]['Receita'] == 50
    assert controller.relatorio_diario(None)[0]['Data'] == '2012-03-15'
    assert report_data.fetch_one('SELECT Data FROM transacoes')['Data'] == '15/03/2012'


def test_query_failure_is_not_empty_report(report_data):
    controller = RelatorioController()
    controller.service.model.close()
    controller.service.model.db_name = '/directory-that-does-not-exist/reports.db'
    with pytest.raises(DatabaseError):
        controller.service.model.get_relatorio_anual(date.today().year, 1)
    assert controller.relatorio_anual(date.today().year) is None


def test_daily_period_excludes_future_transactions(report_data):
    transaction(report_data, 10)
    transaction(report_data, 999, '2999-01-01')
    rows = RelatorioController().relatorio_diario(1)
    assert sum(row['Receita'] for row in rows) == 10


def test_exported_pdf_contains_real_transactions(report_data, tmp_path):
    from utilitarios.makepdf import MakePDF
    from PyPDF2 import PdfReader
    transaction(report_data, 1234.56)
    text = RelatorioController().gerar_texto_informe(date.today().year)
    output = tmp_path / 'informe.pdf'
    assert MakePDF.gerar_pdf(str(output), 'Informe auxiliar', text)
    extracted = '\n'.join(page.extract_text() for page in PdfReader(output).pages)
    assert '1.234,56' in extracted
    assert 'U1' in extracted


def test_view_recovers_columns_refreshes_annual_and_clears_stale_totals(report_data):
    app = QApplication.instance() or QApplication([])
    view = RelatorioView()
    assert view.table.columnCount() == 1
    transaction(report_data, 100)
    view.on_load()
    assert view.table.columnCount() == 5
    assert view.table.item(0, 2).text() == CurrencyFormatter.format(100)
    view.sections.setCurrentRow(1)
    app.processEvents()
    assert view.table_anual.columnCount() == 5
    assert view.table_anual.item(0, 2).text() == CurrencyFormatter.format(100)
    view.sections.setCurrentRow(2)
    assert '100,00' in view.text.toPlainText()
    report_data.execute_query('DELETE FROM transacoes')
    view.load_diario()
    assert view.lbl_receita.text() == CurrencyFormatter.format(0)
    view.close()


def test_zero_movement_does_not_prevent_table_rendering(report_data):
    app = QApplication.instance() or QApplication([])
    transaction(report_data, 0)
    view = RelatorioView()
    assert view.table.columnCount() == 5
    assert view.table.item(0, 2).text() == CurrencyFormatter.format(0)
    app.processEvents()
    view.close()


def test_period_query_error_clears_previous_report(report_data, monkeypatch):
    app = QApplication.instance() or QApplication([])
    transaction(report_data, 100)
    view = RelatorioView()
    view.sections.setCurrentRow(2)
    assert '100,00' in view.text.toPlainText()

    def fail():
        raise DatabaseError('falha injetada')

    monkeypatch.setattr(view.controller, 'anos_disponiveis', fail)
    view.on_load()
    assert view.lbl_receita.text() == CurrencyFormatter.format(0)
    assert '100,00' not in view.text.toPlainText()
    assert not view.btn_pdf.isEnabled()
    assert not view.btn_print.isEnabled()
    assert view.table_anual.columnCount() == 1
    app.processEvents()
    view.close()
