from datetime import date

from services.fatura_service import FaturaService

from conftest import criar_cartao, criar_conta, criar_lancamento, criar_usuario, saldo


class DataAntesFechamento(date):
    @classmethod
    def today(cls):
        return cls(2026, 7, 5)


class DataDepoisFechamento(date):
    @classmethod
    def today(cls):
        return cls(2026, 7, 15)


def preparar(db, db_path):
    usuario = criar_usuario(db, "pagamento_flexivel")
    conta = criar_conta(db, usuario, "Conta principal", 1000)
    cartao = criar_cartao(db, usuario)
    criar_lancamento(db, usuario, cartao, valor=100, mes=7, ano=2026)
    return FaturaService(db_path), usuario, conta, cartao


def test_antecipacao_em_fatura_aberta_reduz_saldo_e_mantem_ciclo(
    db, db_path, monkeypatch
):
    monkeypatch.setattr("services.fatura_service.date", DataAntesFechamento)
    service, usuario, conta, cartao = preparar(db, db_path)

    resultado = service.pagar_fatura(
        cartao, 7, 2026, conta, usuario, valor=40
    )

    assert resultado["codigo"] == "OK"
    assert resultado["dados"]["Modalidade"] == "ANTECIPADO"
    assert resultado["dados"]["Saldo_Restante"] == 60
    resumo = service.get_painel_cartao(cartao, 7, 2026, usuario)["fatura"]
    assert resumo["status"] == "ABERTA"
    assert resumo["pagamentos"] == 40
    assert resumo["saldo_a_pagar"] == 60
    assert saldo(db, conta) == 960
    assert service.calcular_limite_disponivel(cartao, usuario) == 4940

    criar_lancamento(
        db, usuario, cartao, valor=50, mes=7, ano=2026,
        descricao="Compra após antecipação",
    )
    atualizado = service.get_painel_cartao(
        cartao, 7, 2026, usuario
    )["fatura"]
    assert atualizado["status"] == "ABERTA"
    assert atualizado["saldo_a_pagar"] == 110

    quitacao_antecipada = service.pagar_fatura(
        cartao, 7, 2026, conta, usuario, valor=110
    )
    assert quitacao_antecipada["dados"]["Modalidade"] == "ANTECIPADO"
    ainda_aberta = service.get_painel_cartao(
        cartao, 7, 2026, usuario
    )["fatura"]
    assert ainda_aberta["status"] == "ABERTA"
    assert ainda_aberta["saldo_a_pagar"] == 0

    monkeypatch.setattr("services.fatura_service.date", DataDepoisFechamento)
    fechada_quitada = service.get_painel_cartao(
        cartao, 7, 2026, usuario
    )["fatura"]
    assert fechada_quitada["status"] == "PAGA"
    assert fechada_quitada["pagamentos"] == 150
    assert service.calcular_limite_disponivel(cartao, usuario) == 5000


def test_pagamento_parcial_e_quitacao_total_em_fatura_fechada(
    db, db_path, monkeypatch
):
    monkeypatch.setattr("services.fatura_service.date", DataDepoisFechamento)
    service, usuario, conta, cartao = preparar(db, db_path)

    parcial = service.pagar_fatura(
        cartao, 7, 2026, conta, usuario, valor=40
    )
    assert parcial["dados"]["Modalidade"] == "PARCIAL"
    assert parcial["dados"]["Saldo_Restante"] == 60
    resumo = service.get_painel_cartao(cartao, 7, 2026, usuario)["fatura"]
    assert resumo["status"] == "FECHADA"
    assert resumo["saldo_a_pagar"] == 60
    assert db.fetch_one(
        "SELECT Paga FROM lancamentos WHERE ID_Cartao = ?", (cartao,)
    )["Paga"] == 0

    total = service.pagar_fatura(
        cartao, 7, 2026, conta, usuario, valor=60
    )
    assert total["dados"]["Modalidade"] == "TOTAL"
    assert total["dados"]["Saldo_Restante"] == 0
    resumo = service.get_painel_cartao(cartao, 7, 2026, usuario)["fatura"]
    assert resumo["status"] == "PAGA"
    assert resumo["pagamentos"] == 100
    assert resumo["saldo_a_pagar"] == 0
    assert saldo(db, conta) == 900
    assert db.fetch_one(
        "SELECT COUNT(*) AS n FROM pagamentos_fatura"
    )["n"] == 2
    assert db.fetch_one(
        "SELECT Paga FROM lancamentos WHERE ID_Cartao = ?", (cartao,)
    )["Paga"] == 1


def test_pagamento_acima_do_saldo_e_rejeitado(db, db_path, monkeypatch):
    monkeypatch.setattr("services.fatura_service.date", DataDepoisFechamento)
    service, usuario, conta, cartao = preparar(db, db_path)

    resultado = service.pagar_fatura(
        cartao, 7, 2026, conta, usuario, valor=100.01
    )

    assert resultado["codigo"] == "DADOS_INVALIDOS"
    assert saldo(db, conta) == 1000
    assert db.fetch_one(
        "SELECT COUNT(*) AS n FROM pagamentos_fatura"
    )["n"] == 0
