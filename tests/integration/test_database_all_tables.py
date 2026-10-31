"""Inserção real, persistência e rollback de todas as tabelas do schema ativo."""
import shutil
import sqlite3

import pytest

from database.database import Database, DatabaseError
from models.account_model import AccountModel
from models.category_model import CategoryModel
from models.credito_model import CreditoModel
from models.meta_model import MetaModel
from models.password_reset_model import PasswordResetModel
from models.user_model import UserModel
from services.divida_service import DividaService
from services.fatura_service import FaturaService
from services.favorecido_service import FavorecidoService
from services.relatorio_service import RelatorioService

TABLES = (
    'usuarios', 'recuperacao_senha', 'categorias', 'contas', 'credito',
    'favorecido', 'pessoa_fisica', 'pessoa_juridica', 'transacoes',
    'agendamentos', 'lancamentos', 'faturas_cartao', 'pagamentos_fatura',
    'dividas', 'divida_parcelas', 'pagamentos_divida', 'informes_fiscais',
    'metas', 'schema_migrations',
)


@pytest.fixture(scope='module')
def populated_database(tmp_path_factory, db_template_path):
    path = str(tmp_path_factory.mktemp('all-tables') / 'audit.db')
    shutil.copy2(db_template_path, path)
    Database._initialized_paths.add(path)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr('database.database.get_db_path', lambda: path)
        # Cada escrita passa pelo mesmo Model/Service usado pelo aplicativo.
        user = UserModel()
        user.add_user({'Nome': 'Auditoria', 'Email': 'audit@example.com',
                       'Login': 'audit', 'Senha': 'audit-test-password'})
        uid = user.get_user_by_login('audit')['ID_Usuario']
        PasswordResetModel(path).create_token(uid)
        category = CategoryModel(path).add_category('Teste', 'Despesa', uid)
        accounts = AccountModel(path)
        accounts.add_account('Principal', 'Teste', 'Corrente', 1000, uid)
        account = accounts.get_accounts_by_user(uid)[0]['ID_Conta']
        card = CreditoModel(path).add_cartao({'Nome': 'Teste', 'Limite': 1000,
                  'Dia_Fechamento': 10, 'Dia_Vencimento': 20, 'ID_Usuario': uid})['ID_Cartao']
        payees = FavorecidoService()
        pf = payees.criar({'Nome': 'Pessoa teste', 'CPF': '52998224725'}, uid)
        payees.criar({'Nome': 'Empresa teste', 'CNPJ': '11222333000181'}, uid)
        debts = DividaService(path)
        debt = debts.criar({'Descricao': 'Contrato teste', 'Tipo_Divida': 'Empréstimo bancário',
             'Tipo_Parcelamento': 'FIXO', 'Valor_Emprestado': 90, 'Valor_Total_Contrato': 100,
             'Quantidade_Parcelas': 2, 'ID_Favorecido': pf,
             'Data_Contratacao': '2026-10-01', 'Primeiro_Vencimento': '2026-11-10'}, uid)
        debts.registrar_pagamento({'ID_Divida': debt, 'ID_Conta': account,
             'Valor_Pago': 20, 'Data_Pagamento': '2026-10-31'}, uid)
        invoices = FaturaService(path)
        invoices.registrar_despesa_cartao({'ID_Cartao': card, 'ID_Usuario': uid,
             'ID_Categoria': category, 'ID_Favorecido': pf,
             'Data': '2026-10-01', 'Descricao': 'Compra teste', 'Valor': 100})
        result = invoices.pagar_fatura(card, 10, 2026, account, uid, valor=40)
        assert result['codigo'] == 'OK', result
        MetaModel(path).add_meta('Objetivo teste', 'Categoria', 200, uid, category,
                                '2026-10-01', '2026-12-31')
        RelatorioService().salvar_informe_fiscal({'Ano_Calendario': 2026,
             'Fonte_Nome': 'Empresa teste', 'Fonte_Documento': '11222333000181',
             'Natureza_Rendimento': 'Trabalho', 'Rendimentos_Tributaveis': 1000}, uid)
        yield path


def test_table_inventory_has_no_uncovered_tables(populated_database):
    with sqlite3.connect(populated_database) as connection:
        actual = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        # sqlite_sequence é mantida automaticamente pelo SQLite, nunca por INSERT manual.
        assert actual == set(TABLES) | {'sqlite_sequence'}
        assert connection.execute('SELECT COUNT(*) FROM sqlite_sequence').fetchone()[0] > 0
        assert connection.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
        assert connection.execute('PRAGMA foreign_key_check').fetchall() == []


@pytest.mark.parametrize('table', TABLES)
def test_inserted_rows_survive_reopening(populated_database, table):
    db = Database(populated_database)
    before = db.fetch_all(f'SELECT * FROM "{table}" ORDER BY 1')
    db.close()
    assert before, f'{table}: nenhuma inserção foi persistida'
    # Conexão independente: confere COMMIT e conteúdo, não apenas o cursor de escrita.
    with sqlite3.connect(populated_database) as reopened:
        reopened.row_factory = sqlite3.Row
        after = [dict(row) for row in reopened.execute(f'SELECT * FROM "{table}" ORDER BY 1')]
    assert after == before


def clone_for_insert(db, table):
    row = dict(db.fetch_one(f'SELECT * FROM "{table}" ORDER BY 1'))
    pk = [col['name'] for col in db.fetch_all(f'PRAGMA table_info("{table}")') if col['pk']]
    for key in pk:
        row.pop(key)
    if table == 'schema_migrations':
        row['Versao'] = 999999
    if table == 'usuarios':
        row.update(Login='rollback-user', Email='rollback@example.com')
    if table == 'recuperacao_senha':
        row['Token'] = 'rollback-token'
    if table in ('pessoa_fisica', 'pessoa_juridica'):
        row['ID_Favorecido'] = db.execute_insert(
            'INSERT INTO favorecido (Nome, Tipo, ID_Usuario) VALUES (?, ?, ?)',
            ('Rollback', 'PF' if table == 'pessoa_fisica' else 'PJ', 1))
        row['CPF' if table == 'pessoa_fisica' else 'CNPJ'] = None
    if table in ('pagamentos_fatura', 'pagamentos_divida'):
        row['Chave_Idempotencia'] = 'rollback-' + table
        row['ID_Transacao'] = insert_row(db, 'transacoes')
    if table == 'faturas_cartao':
        row['Competencia_Mes'] = 12
    if table == 'divida_parcelas':
        row['Numero_Parcela'] = 100
    if table == 'informes_fiscais':
        row['Ano_Calendario'] = 2027
    if table == 'agendamentos':
        row['ID_Parcela_Divida'] = None
    if table == 'transacoes':
        row['ID_Agendamento'] = None
    return row


def insert_row(db, table):
    row = clone_for_insert(db, table)
    columns = ', '.join(f'"{key}"' for key in row)
    return db.execute_insert(f'INSERT INTO "{table}" ({columns}) VALUES ({", ".join("?" for _ in row)})', tuple(row.values()))


@pytest.mark.parametrize('table', TABLES)
def test_insert_is_rolled_back_on_intermediate_failure(populated_database, table):
    db = Database(populated_database)
    before = {name: db.fetch_all(f'SELECT * FROM "{name}" ORDER BY 1') for name in TABLES}
    with pytest.raises(RuntimeError, match='falha intermediária'):
        with db.unit_of_work():
            insert_row(db, table)
            assert len(db.fetch_all(f'SELECT * FROM "{table}"')) > len(before[table])
            raise RuntimeError('falha intermediária')
    for name in TABLES:
        assert db.fetch_all(f'SELECT * FROM "{name}" ORDER BY 1') == before[name]
    assert db.fetch_all('PRAGMA foreign_key_check') == []
    db.close()


def test_every_foreign_key_rejects_orphan_inserts(populated_database):
    db = Database(populated_database)
    checked = []
    for table in TABLES:
        for fk in db.fetch_all(f'PRAGMA foreign_key_list("{table}")'):
            before = db.fetch_all(f'SELECT * FROM "{table}" ORDER BY 1')
            with pytest.raises(DatabaseError):
                with db.unit_of_work():
                    row = clone_for_insert(db, table)
                    row[fk['from']] = -999999
                    columns = ', '.join(f'"{key}"' for key in row)
                    db.execute_insert(f'INSERT INTO "{table}" ({columns}) VALUES ({", ".join("?" for _ in row)})', tuple(row.values()))
            assert db.fetch_all(f'SELECT * FROM "{table}" ORDER BY 1') == before
            checked.append((table, fk['from']))
    assert len(checked) >= 30, checked
    assert db.fetch_all('PRAGMA foreign_key_check') == []
    db.close()
