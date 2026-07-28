from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from services.payment_service import PaymentService

from conftest import (
    criar_agendamento,
    criar_conta,
    criar_usuario,
    dados_baixa,
    saldo,
    total,
)


def preparar(db, recorrente=0, status="AGENDADO"):
    user_id = criar_usuario(db, "usuario")
    conta = criar_conta(db, user_id, "Conta", 100)
    agendamento = criar_agendamento(
        db,
        user_id,
        conta,
        status=status,
        recorrente=recorrente
    )
    return user_id, conta, agendamento


def status_agendamento(db, id_agendamento):
    return db.fetch_one(
        "SELECT Status FROM agendamentos WHERE ID_Agendamento = ?",
        (id_agendamento,)
    )["Status"]


def test_baixa_normal_cria_vinculo(db, db_path):
    user_id, conta, agendamento = preparar(db)
    resultado = PaymentService(db_path).baixar_agendamento(
        dados_baixa(agendamento, conta),
        user_id
    )

    assert resultado["codigo"] == "OK"
    assert saldo(db, conta) == 80
    assert status_agendamento(db, agendamento) == "EXECUTADO"
    transacao = db.fetch_one(
        "SELECT * FROM transacoes WHERE ID_Agendamento = ?",
        (agendamento,)
    )
    assert transacao is not None
    assert transacao["Valor"] == -20


def test_falha_ao_atualizar_status_reverte_baixa(
    db,
    db_path,
    monkeypatch
):
    user_id, conta, agendamento = preparar(db)
    service = PaymentService(db_path)

    def falhar(*_):
        raise RuntimeError("falha simulada ao atualizar status")

    monkeypatch.setattr(service.schedule_service.schedule_model, "mark_executed", falhar)
    resultado = service.baixar_agendamento(
        dados_baixa(agendamento, conta),
        user_id
    )

    assert resultado["sucesso"] is False
    assert saldo(db, conta) == 100
    assert status_agendamento(db, agendamento) == "AGENDADO"
    assert total(db, "transacoes") == 0


def test_falha_na_recorrencia_reverte_baixa(db, db_path, monkeypatch):
    user_id, conta, agendamento = preparar(db, recorrente=1)
    service = PaymentService(db_path)

    def falhar(*_):
        raise RuntimeError("falha simulada na recorrência")

    monkeypatch.setattr(
        service.schedule_service,
        "_criar_proximo_agendamento",
        falhar
    )
    resultado = service.baixar_agendamento(
        dados_baixa(agendamento, conta),
        user_id
    )

    assert resultado["sucesso"] is False
    assert saldo(db, conta) == 100
    assert status_agendamento(db, agendamento) == "AGENDADO"
    assert total(db, "transacoes") == 0
    assert total(db, "agendamentos") == 1


def test_segunda_execucao_nao_cobra_novamente(db, db_path):
    user_id, conta, agendamento = preparar(db)
    service = PaymentService(db_path)
    dados = dados_baixa(agendamento, conta)

    primeiro = service.baixar_agendamento(dados, user_id)
    segundo = service.baixar_agendamento(dados, user_id)

    assert primeiro["codigo"] == "OK"
    assert segundo["codigo"] == "JA_PROCESSADO"
    assert saldo(db, conta) == 80
    assert total(db, "transacoes") == 1


def test_duas_tentativas_concorrentes_geram_uma_cobranca(db, db_path):
    user_id, conta, agendamento = preparar(db)
    barreira = Barrier(2)

    def executar():
        service = PaymentService(db_path)
        barreira.wait()
        return service.baixar_agendamento(
            dados_baixa(agendamento, conta),
            user_id
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(executor.map(lambda _: executar(), range(2)))

    codigos = sorted(resultado["codigo"] for resultado in resultados)
    assert codigos == ["JA_PROCESSADO", "OK"]
    assert saldo(db, conta) == 80
    assert total(db, "transacoes") == 1


def test_agendamento_de_outro_usuario_e_recusado(db, db_path):
    user_id, conta, agendamento = preparar(db)
    outro = criar_usuario(db, "outro")

    resultado = PaymentService(db_path).baixar_agendamento(
        dados_baixa(agendamento, conta),
        outro
    )

    assert resultado["codigo"] == "NAO_AUTORIZADO"
    assert saldo(db, conta) == 100
    assert total(db, "transacoes") == 0


def test_agendamento_cancelado_ou_executado_e_recusado(db, db_path):
    user_id = criar_usuario(db, "usuario")
    conta = criar_conta(db, user_id, "Conta", 100)
    service = PaymentService(db_path)

    for status in ("CANCELADO", "EXECUTADO"):
        agendamento = criar_agendamento(
            db,
            user_id,
            conta,
            status=status
        )
        resultado = service.baixar_agendamento(
            dados_baixa(agendamento, conta),
            user_id
        )
        assert resultado["codigo"] == "CONFLITO"

    assert saldo(db, conta) == 100
    assert total(db, "transacoes") == 0
