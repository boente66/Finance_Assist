from datetime import date

from PyPDF2 import PdfReader
from PyQt5.QtWidgets import QApplication, QMessageBox

from core.session import Session
from controllers.fatura_controller import FaturaController
from database.database import Database
from services.fatura_service import FaturaService
from services.ia_export_service import IAExportService
from views.painel_fatura import PainelFatura


def _texto_pdf(path):
    return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)


def _cenario(tmp_path, monkeypatch):
    path = str(tmp_path / "fatura.db")
    monkeypatch.setattr("database.database.get_db_path", lambda: path)
    db = Database(path)
    uid = db.execute_insert(
        "INSERT INTO usuarios (Nome, Login, Senha) VALUES ('Teste','teste','hash')"
    )
    card = db.execute_insert(
        """INSERT INTO credito (Nome, Limite, Dia_Fechamento, Dia_Vencimento, ID_Usuario)
           VALUES ('Cartão Azul', 2000, 20, 27, ?)""", (uid,)
    )
    account = db.execute_insert(
        "INSERT INTO contas (Nome_Conta, Tipo, Saldo_Atual, ID_Usuario) VALUES ('Principal','Corrente',1000,?)",
        (uid,),
    )
    Session.set_usuario({"ID_Usuario": uid, "Nome": "Teste", "Nivel_Acesso": "usuario"})
    return db, card, account


def test_crud_copy_paste_and_paid_protection(tmp_path, monkeypatch):
    db, card, _ = _cenario(tmp_path, monkeypatch)
    controller = FaturaController()
    payload = {"ID_Cartao": card, "Descricao": "Compra original", "Valor": 25,
               "Data": "2026-08-05", "Competencia_Mes": 8, "Competencia_Ano": 2026,
               "Num_Parcelas": 1}
    assert controller.registrar_despesa_cartao(payload)
    item = controller.listar_lancamentos_fatura(card, 8, 2026)[0]
    controller.atualizar_lancamento(item["ID_Lancamento"], {**item, "Descricao": "Compra editada"})
    assert controller.obter_lancamento(item["ID_Lancamento"])["Descricao"] == "Compra editada"

    app = QApplication.instance() or QApplication([])
    view = PainelFatura(); view.set_cartao(controller.buscar_cartao_por_id(card)); view.set_competencia(8, 2026); view._carregar()
    view.table.selectRow(0)
    assert view.copiar_lancamento()
    assert view.colar_lancamento()
    assert len(controller.listar_lancamentos_fatura(card, 8, 2026)) == 2
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Yes)
    view.table.selectRow(0)
    assert view.excluir_lancamento()
    assert len(controller.listar_lancamentos_fatura(card, 8, 2026)) == 1
    remaining = controller.listar_lancamentos_fatura(card, 8, 2026)[0]
    db.execute_query("UPDATE lancamentos SET Paga=1 WHERE ID_Lancamento=?", (remaining["ID_Lancamento"],))
    try:
        controller.excluir_lancamento(remaining["ID_Lancamento"])
    except ValueError:
        pass
    else:
        raise AssertionError("Lançamento pago foi excluído")
    view.close(); app.processEvents(); db.close()


def test_exportacoes_pdf_possuem_titulo_tabela_total_e_multiplas_paginas(tmp_path, monkeypatch):
    db, card, account = _cenario(tmp_path, monkeypatch)
    service = FaturaService(str(tmp_path / "fatura.db"))
    lancamentos = []
    transacoes = []
    for index in range(75):
        lancamentos.append({"Data": "2026-08-05", "Descricao": f"Compra {index}",
                            "Categoria": "Compras", "Valor": 10, "Paga": 0,
                            "Parcela_Atual": 1, "Num_Parcelas": 1})
        transacoes.append({"Data": "2026-08-05", "Descricao": f"Movimento {index}",
                           "Favorecido": "Loja", "Categoria": "Compras", "Valor": -10})
    invoice = tmp_path / "fatura.pdf"
    statement = tmp_path / "extrato.pdf"
    assert service.exportar_fatura_pdf({"Nome": "Cartão Azul"}, lancamentos, str(invoice), 8, 2026)
    assert IAExportService().exportar_extrato_conta(
        transacoes, {"ID_Conta": account, "Nome_Conta": "Principal"},
        "2026-08-01", "2026-08-31", "PDF", str(statement)
    )
    invoice_reader = PdfReader(invoice); statement_reader = PdfReader(statement)
    assert len(invoice_reader.pages) > 1 and len(statement_reader.pages) > 1
    assert "Fatura do Cartão Azul" in _texto_pdf(invoice)
    assert "Total da fatura" in _texto_pdf(invoice) and "Compra 74" in _texto_pdf(invoice)
    assert "Extrato da Principal" in _texto_pdf(statement)
    assert "Resultado do período" in _texto_pdf(statement) and "Movimento 74" in _texto_pdf(statement)
    service.lancamento_model.close(); db.close()
