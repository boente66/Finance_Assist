from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import date

import pytest
from PyQt5.QtWidgets import QApplication, QDialog

from core.session import Session
from database.database import Database, DatabaseError
from controllers.favorecido_controller import FavorecidoController
from controllers.relatorio_controller import RelatorioController
from models.favorecido_model import FavorecidoModel
from views.FavorecidoDialog import FavorecidoDialog


@pytest.fixture
def payees(tmp_path, monkeypatch):
    path = str(tmp_path / 'payees.db')
    monkeypatch.setattr('database.database.get_db_path', lambda: path)
    db = Database(path)
    for uid in (1, 2):
        db.execute_query("INSERT INTO usuarios (ID_Usuario,Nome,Senha) VALUES (?, 'Teste', 'hash')", (uid,))
    previous = Session.get_usuario()
    Session.set_usuario({'ID_Usuario': 1})
    yield db
    Session.set_usuario(previous)
    db.close()


@pytest.mark.parametrize('tipo,documento', [('PF', '123.456.789-10'), ('PJ', '12.345.678/0001-90')])
def test_dialog_inserts_and_report_uses_real_payee(payees, tipo, documento):
    app = QApplication.instance() or QApplication([])
    dialog = FavorecidoDialog()
    dialog.tipo_combo.setCurrentIndex(dialog.tipo_combo.findData(tipo))
    dialog.nome_edit.setText('Favorecido teste')
    dialog.doc_edit.setText(documento)
    dialog.tel_edit.setText('(11) 99999-9999')
    dialog.salvar_btn.click()
    assert dialog.result() == QDialog.Accepted
    uid = dialog.dados['ID_Favorecido']
    saved = FavorecidoController().obter_favorecido(uid)
    assert saved['Nome'] == 'Favorecido teste'
    assert saved['Telefone'] == '11999999999'
    assert saved['Documento'] == ''.join(c for c in documento if c.isdigit())
    payees.execute_query("INSERT INTO contas (ID_Conta,Nome_Conta,ID_Usuario) VALUES (1,'Conta',1)")
    payees.execute_query("""INSERT INTO transacoes
        (ID_Conta,ID_Usuario,Tipo,Descricao,Valor,Data,ID_Favorecido)
        VALUES (1,1,'Receita','Teste',123,?,?)""", (date.today().isoformat(), uid))
    text = RelatorioController().gerar_texto_informe(date.today().year)
    assert 'Favorecido teste' in text and '123,00' in text
    edit = FavorecidoDialog(favorecido=saved)
    assert not edit.tipo_combo.isEnabled()
    edit.nome_edit.setText('Nome atualizado')
    edit.salvar()
    assert FavorecidoController().obter_favorecido(uid)['Nome'] == 'Nome atualizado'
    app.processEvents()
    edit.close()
    dialog.close()


def test_partial_insert_rolls_back(payees):
    payees.execute_query("""CREATE TRIGGER fail_pf BEFORE INSERT ON pessoa_fisica
        BEGIN SELECT RAISE(ABORT, 'falha injetada'); END""")
    with pytest.raises(DatabaseError):
        FavorecidoController().adicionar_favorecido({'Nome': 'Teste', 'CPF': '12345678910'})
    assert payees.fetch_all('SELECT * FROM favorecido') == []


def test_duplicate_concurrent_insert_is_one_record(payees):
    barrier = Barrier(2)
    def create(_):
        model = FavorecidoModel()
        barrier.wait()
        try:
            return model.add_favorecido({'Nome': 'Teste', 'CPF': '12345678910'}, 1)
        finally:
            model.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(create, range(2)))
    assert ids[0] == ids[1]
    assert len(payees.fetch_all('SELECT * FROM favorecido')) == 1


def test_documents_are_scoped_by_user_and_invalid_data_is_rejected(payees):
    controller = FavorecidoController()
    first = controller.adicionar_favorecido({'Nome': 'Um', 'CPF': '12345678910'})
    Session.set_usuario({'ID_Usuario': 2})
    second = controller.adicionar_favorecido({'Nome': 'Dois', 'CPF': '12345678910'})
    assert first != second
    assert [row['ID_Favorecido'] for row in controller.listar_favorecidos()] == [second]
    with pytest.raises(ValueError):
        controller.adicionar_favorecido({'Nome': '', 'CPF': '12345678910'})
    with pytest.raises(ValueError):
        controller.adicionar_favorecido({'Nome': 'Inválido', 'CPF': '123'})
    with pytest.raises(ValueError):
        controller.adicionar_favorecido({'Nome': 'Ambíguo', 'CPF': '12345678910', 'CNPJ': '12345678000190'})


@pytest.mark.parametrize('documento,alteracao', [
    ({'CPF': '12345678910'}, {'CPF': '123'}),
    ({'CPF': '12345678910'}, {'CPF': ''}),
    ({'CNPJ': '12345678000190'}, {'CNPJ': '123'}),
    ({'CNPJ': '12345678000190'}, {'CNPJ': ''}),
    ({'CPF': '12345678910'}, {'CNPJ': '12345678000190'}),
    ({'CPF': '12345678910'}, {'Nome': ' '}),
])
def test_invalid_edit_preserves_existing_payee(payees, documento, alteracao):
    controller = FavorecidoController()
    fid = controller.adicionar_favorecido({'Nome': 'Preservar', **documento})
    before = controller.obter_favorecido(fid)
    with pytest.raises(ValueError):
        controller.atualizar_favorecido(fid, alteracao)
    assert controller.obter_favorecido(fid) == before


@pytest.mark.parametrize('table,document', [('pessoa_fisica', 'CPF'), ('pessoa_juridica', 'CNPJ')])
def test_legacy_document_index_migrates_without_deleting_records(payees, table, document):
    number = '12345678910' if document == 'CPF' else '12345678000190'
    controller = FavorecidoController()
    fid = controller.adicionar_favorecido({'Nome': 'Preservar', document: number})
    before = controller.obter_favorecido(fid)
    # Reproduz o índice global das versões anteriores em banco descartável.
    index = 'idx_' + document.lower()
    payees.execute_query(f'DROP INDEX {index}')
    payees.execute_query(f'CREATE UNIQUE INDEX {index} ON {table}({document}) WHERE {document} IS NOT NULL')
    payees.execute_query('DELETE FROM schema_migrations WHERE Versao = 5')
    payees._run_migrations()
    assert controller.obter_favorecido(fid) == before
    Session.set_usuario({'ID_Usuario': 2})
    other = controller.adicionar_favorecido({'Nome': 'Outro usuário', document: number})
    assert other != fid
    # Mesmo usuário continua protegido, inclusive em escrita direta no banco.
    other_number = '98765432100' if document == 'CPF' else '98765432000100'
    third = controller.adicionar_favorecido({'Nome': 'Terceiro', document: other_number})
    with pytest.raises(DatabaseError):
        payees.execute_query(f'UPDATE {table} SET {document} = ? WHERE ID_Favorecido = ?', (number, third))
    assert controller.obter_favorecido(third)['Documento'] == other_number
    assert payees.fetch_one('PRAGMA integrity_check')['integrity_check'] == 'ok'
    assert payees.fetch_all('PRAGMA foreign_key_check') == []
