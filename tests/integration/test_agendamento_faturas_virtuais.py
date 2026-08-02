import os
from datetime import date
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from dateutil.relativedelta import relativedelta
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from controllers.schedule_controller import ScheduleController
from core.session import Session
from services.fatura_service import FaturaService
from services.schedule_service import ScheduleService
from views.agendamento_view import AgendamentoView

from conftest import criar_cartao, criar_conta, criar_usuario


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def limpar_sessao():
    Session.set_usuario(None)
    yield
    Session.set_usuario(None)


def preparar(db, db_path, cartoes=1):
    user_id = criar_usuario(db, "projecao")
    conta_id = criar_conta(db, user_id, "Conta projeção", 5000)
    ids = [criar_cartao(db, user_id, f"Cartão {n + 1}") for n in range(cartoes)]
    Session.set_usuario({"ID_Usuario": user_id, "Nome": "Projeção", "Tema": "Primavera"})
    return user_id, conta_id, ids


def adicionar_compra(db, user_id, card_id, value, reference=None, paid=0, description="Compra"):
    reference = reference or date.today()
    return db.execute_insert(
        """
        INSERT INTO lancamentos (
            ID_Cartao, Data, Competencia_Mes, Competencia_Ano,
            Descricao, Valor, Paga, ID_Usuario
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            card_id, reference.isoformat(), reference.month, reference.year,
            description, value, paid, user_id,
        ),
    )


def adicionar_agendamento(db, user_id, value, schedule_type="Contas a Pagar", card_id=None):
    return db.execute_insert(
        """
        INSERT INTO agendamentos (
            Tipo, Data, Valor, Descricao, Status, ID_Cartao,
            ID_Usuario, Recorrente, Ativo, Parcelas
        ) VALUES (?, ?, ?, 'Compromisso', 'AGENDADO', ?, ?, 0, 1, 1)
        """,
        (schedule_type, date.today().isoformat(), value, card_id, user_id),
    )


def projection(db_path, user_id, months=12):
    return ScheduleService(db_path).get_financial_projection(user_id, months)


def invoice_items(result):
    return [i for i in result["itens"] if i["tipo_origem"] == "FATURA_CARTAO"]


def make_view(db_path, qt_app):
    view = AgendamentoView(schedule_controller=ScheduleController(db_path))
    qt_app.processEvents()
    return view


def select_invoice(view, qt_app):
    for row in range(view.table.rowCount()):
        cell = view.table.item(row, 0)
        item = cell.data(Qt.UserRole) if cell else None
        if item and item["tipo_origem"] == "FATURA_CARTAO":
            view.table.selectRow(row)
            qt_app.processEvents()
            return item
    raise AssertionError("Fatura virtual não encontrada na tabela")


def test_fatura_em_aberto_aparece_em_contas_a_pagar(db, db_path):
    user, _, cards = preparar(db, db_path)
    adicionar_compra(db, user, cards[0], 274.14)
    item = invoice_items(projection(db_path, user))[0]
    assert item["tipo"] == "Contas a Pagar"
    assert item["status"] == "A_PAGAR"


def test_valor_e_o_mesmo_da_fonte_oficial(db, db_path):
    user, _, cards = preparar(db, db_path)
    adicionar_compra(db, user, cards[0], 99.99)
    service = FaturaService(db_path)
    official = service.calcular_fatura_mes(cards[0], date.today().month, date.today().year, user)
    assert invoice_items(projection(db_path, user))[0]["valor"] == Decimal(str(official)).quantize(Decimal("0.01"))


def test_nova_compra_aumenta_valor_dinamico(db, db_path):
    user, _, cards = preparar(db, db_path)
    service = ScheduleService(db_path)
    adicionar_compra(db, user, cards[0], 10)
    before = invoice_items(service.get_financial_projection(user))[0]["valor"]
    service.fatura_service.registrar_despesa_cartao({
        "ID_Usuario": user, "ID_Cartao": cards[0], "Descricao": "Nova compra",
        "Valor": 15, "Data": date.today().replace(day=1).isoformat(), "Num_Parcelas": 1,
    })
    after = invoice_items(service.get_financial_projection(user))[0]["valor"]
    assert after == before + Decimal("15.00")


def test_exclusao_diminui_valor(db, db_path):
    user, _, cards = preparar(db, db_path)
    first = adicionar_compra(db, user, cards[0], 40)
    adicionar_compra(db, user, cards[0], 10)
    before = invoice_items(projection(db_path, user))[0]["valor"]
    FaturaService(db_path).lancamento_model.excluir_lancamento(first, user)
    after = invoice_items(projection(db_path, user))[0]["valor"]
    assert before - after == Decimal("40.00")


def test_pagamento_integral_remove_fatura_pendente(db, db_path):
    user, account, cards = preparar(db, db_path)
    adicionar_compra(db, user, cards[0], 80)
    result = FaturaService(db_path).pagar_fatura(
        cards[0], date.today().month, date.today().year, account, user
    )
    assert result["sucesso"] is True
    assert invoice_items(projection(db_path, user)) == []


def test_valor_zero_nao_entra_em_pendentes(db, db_path):
    user, _, cards = preparar(db, db_path)
    adicionar_compra(db, user, cards[0], 0)
    assert invoice_items(projection(db_path, user)) == []


def test_tres_cartoes_geram_tres_linhas(db, db_path):
    user, _, cards = preparar(db, db_path, cartoes=3)
    for index, card in enumerate(cards, 1):
        adicionar_compra(db, user, card, index * 10)
    assert {i["id_cartao"] for i in invoice_items(projection(db_path, user))} == set(cards)


def test_competencias_diferentes_nao_se_misturam(db, db_path):
    user, _, cards = preparar(db, db_path)
    current = date.today()
    following = current + relativedelta(months=1)
    adicionar_compra(db, user, cards[0], 10, current)
    adicionar_compra(db, user, cards[0], 20, following)
    items = invoice_items(projection(db_path, user, 2))
    assert {(i["competencia_mes"], i["valor"]) for i in items} == {
        (current.month, Decimal("10.00")), (following.month, Decimal("20.00"))
    }


def test_filtro_a_pagar_inclui_faturas(db, db_path, qt_app):
    user, _, cards = preparar(db, db_path)
    adicionar_compra(db, user, cards[0], 10)
    view = make_view(db_path, qt_app)
    view.apply_quick_filter(view.FILTER_PAY)
    assert any(i["tipo_origem"] == "FATURA_CARTAO" for i in view.filtered_data)
    view.close()


def test_filtro_a_receber_exclui_faturas(db, db_path, qt_app):
    user, _, cards = preparar(db, db_path)
    adicionar_compra(db, user, cards[0], 10)
    view = make_view(db_path, qt_app)
    view.apply_quick_filter(view.FILTER_RECEIVE)
    assert all(i["tipo_origem"] != "FATURA_CARTAO" for i in view.filtered_data)
    view.close()


def test_filtro_faturas_exibe_apenas_faturas(db, db_path, qt_app):
    user, _, cards = preparar(db, db_path)
    adicionar_compra(db, user, cards[0], 10)
    adicionar_agendamento(db, user, 30)
    view = make_view(db_path, qt_app)
    view.apply_quick_filter(view.FILTER_INVOICES)
    assert view.filtered_data and all(i["tipo_origem"] == "FATURA_CARTAO" for i in view.filtered_data)
    view.close()


def test_total_pagar_soma_agendamentos_e_faturas(db, db_path):
    user, _, cards = preparar(db, db_path)
    adicionar_compra(db, user, cards[0], 70)
    adicionar_agendamento(db, user, 30)
    totals = projection(db_path, user)["totais"]
    assert totals["agendamentos_pagar"] == Decimal("30.00")
    assert totals["faturas"] == Decimal("70.00")
    assert totals["pagar"] == Decimal("100.00")


def test_compra_individual_do_cartao_nao_duplica_total(db, db_path):
    user, _, cards = preparar(db, db_path)
    adicionar_compra(db, user, cards[0], 100)
    adicionar_agendamento(db, user, 100, "Cartão", cards[0])
    result = projection(db_path, user)
    assert result["totais"]["pagar"] == Decimal("100.00")
    card_schedules = [i for i in result["itens"] if i["tipo"] == "Cartão"]
    assert card_schedules and card_schedules[0]["incluir_totais"] is False


def test_fatura_virtual_nao_pode_ser_cancelada(db, db_path, qt_app):
    user, _, cards = preparar(db, db_path)
    adicionar_compra(db, user, cards[0], 10)
    view = make_view(db_path, qt_app)
    select_invoice(view, qt_app)
    assert view.btn_cancel.isEnabled() is False
    view.close()


def test_abertura_direciona_cartao_e_competencia(db, db_path, qt_app):
    user, _, cards = preparar(db, db_path)
    adicionar_compra(db, user, cards[0], 10)
    view = make_view(db_path, qt_app)
    selected = select_invoice(view, qt_app)
    emitted = []
    view.open_invoice_requested.connect(lambda *args: emitted.append(args))
    view.open_selected_item()
    assert emitted == [(cards[0], selected["competencia_mes"], selected["competencia_ano"])]
    view.close()


def test_usuario_nao_ve_fatura_de_outro_usuario(db, db_path):
    user, _, cards = preparar(db, db_path)
    other = criar_usuario(db, "outro")
    other_card = criar_cartao(db, other, "Privado")
    adicionar_compra(db, user, cards[0], 10)
    adicionar_compra(db, other, other_card, 999)
    assert {i["id_cartao"] for i in invoice_items(projection(db_path, user))} == {cards[0]}


def test_erro_de_fatura_nao_e_mostrado_como_lista_vazia(db, db_path, qt_app):
    user, _, cards = preparar(db, db_path)
    adicionar_compra(db, user, cards[0], 10)
    db.execute_query("DROP TABLE lancamentos")
    view = make_view(db_path, qt_app)
    assert view._loading_error is not None
    assert view.error_label.isHidden() is False
    view.close()


def test_atualizacao_apos_pagamento_reflete_valor(db, db_path):
    user, account, cards = preparar(db, db_path)
    adicionar_compra(db, user, cards[0], 35)
    service = ScheduleService(db_path)
    assert service.get_financial_projection(user)["totais"]["faturas"] == Decimal("35.00")
    FaturaService(db_path).pagar_fatura(
        cards[0], date.today().month, date.today().year, account, user
    )
    assert service.get_financial_projection(user)["totais"]["faturas"] == Decimal("0.00")


def test_agendamento_manual_de_fatura_vinculado_evitar_duplicidade(db, db_path):
    user, _, cards = preparar(db, db_path)
    adicionar_compra(db, user, cards[0], 50)
    db.execute_insert(
        """
        INSERT INTO agendamentos (
            Tipo, Data, Valor, Descricao, Status, ID_Cartao,
            ID_Usuario, Recorrente, Ativo, Parcelas
        ) VALUES ('Contas a Pagar', ?, 50, 'Pagamento da fatura', 'AGENDADO', ?, ?, 0, 1, 1)
        """,
        (date.today().isoformat(), cards[0], user),
    )
    result = projection(db_path, user)
    assert invoice_items(result) == []
    assert result["totais"]["pagar"] == Decimal("50.00")


def test_vencimento_usa_dia_de_vencimento_do_cartao(db, db_path):
    user, _, cards = preparar(db, db_path)
    adicionar_compra(db, user, cards[0], 10)
    item = invoice_items(projection(db_path, user))[0]
    assert int(item["data"].split("-")[2]) == 20


def test_fatura_antiga_em_aberto_aparece_como_atrasada(db, db_path):
    user, _, cards = preparar(db, db_path)
    previous = date.today() + relativedelta(months=-1)
    adicionar_compra(db, user, cards[0], 25, previous)
    items = invoice_items(projection(db_path, user))
    overdue = next(i for i in items if i["competencia_mes"] == previous.month)
    assert overdue["data"] < date.today().isoformat()


def test_suite_utiliza_somente_banco_temporario(db_path):
    assert "pytest-" in db_path
    assert db_path.endswith("financeiro_test.db")
