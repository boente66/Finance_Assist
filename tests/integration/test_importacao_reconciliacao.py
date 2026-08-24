from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from services.fatura_service import FaturaService
from services.reconciliacao_importacao_service import (
    ReconciliacaoImportacaoService,
)
from services.transaction_service import TransactionService

from conftest import criar_cartao, criar_conta, criar_usuario, saldo, total


def item_conta(usuario, conta, data, descricao, valor):
    return {
        "ID_Usuario": usuario,
        "ID_Conta": conta,
        "Data": data,
        "Descricao": descricao,
        "Valor": valor,
        "Tipo": "Despesa" if valor < 0 else "Receita",
    }


def item_cartao(
    usuario,
    cartao,
    data,
    descricao,
    valor,
    mes=8,
    ano=2026,
    parcela=1,
    parcelas=1,
):
    return {
        "ID_Usuario": usuario,
        "ID_Cartao": cartao,
        "Data": data,
        "Descricao": descricao,
        "Valor": valor,
        "Competencia_Mes": mes,
        "Competencia_Ano": ano,
        "Parcela_Atual": parcela,
        "Num_Parcelas": parcelas,
    }


def test_importacao_incremental_e_reimportacao_nao_alteram_saldo(db, db_path):
    usuario = criar_usuario(db, "incremental")
    conta = criar_conta(db, usuario, "Conta", 1000)
    service = TransactionService(db_path)
    primeiro = item_conta(usuario, conta, "2026-08-01", "Mercado", -40)
    segundo = item_conta(usuario, conta, "2026-08-02", "Salário", 200)

    assert service.salvar_lote_importado([primeiro], usuario) == 1
    assert service.salvar_lote_importado([primeiro, segundo], usuario) == 1
    saldo_apos_incremental = saldo(db, conta)
    assert saldo_apos_incremental == 1160

    assert service.salvar_lote_importado([primeiro, segundo], usuario) == 0
    assert saldo(db, conta) == saldo_apos_incremental
    assert total(db, "transacoes") == 2


def test_mesma_data_valor_descricao_diferente_nao_e_duplicado(db, db_path):
    usuario = criar_usuario(db, "descricao")
    conta = criar_conta(db, usuario, "Conta", 100)
    service = TransactionService(db_path)
    a = item_conta(usuario, conta, "2026-08-03", "Loja Alfa", -20)
    b = item_conta(usuario, conta, "2026-08-03", "Posto Beta", -20)

    assert service.salvar_lote_importado([a], usuario) == 1
    assert service.salvar_lote_importado([b], usuario) == 1
    assert total(db, "transacoes") == 2


def test_descricao_semelhante_e_apenas_possivel_duplicado():
    service = ReconciliacaoImportacaoService()
    existente = item_conta(1, 2, "2026-08-03", "MERCADO CENTRAL", -20)
    existente["ID_Transacao"] = 9
    importado = item_conta(1, 2, "2026-08-03", "MERCADO CENTRA", -20)

    resultado = service.reconciliar(
        [importado], [existente], service.DOMINIO_CONTA
    )[0]
    assert resultado["StatusImportacao"] == service.POSSIVEL_DUPLICADO
    assert resultado["Importar"] is False


def test_ocorrencias_identicas_sao_consumidas_como_multiconjunto(db, db_path):
    usuario = criar_usuario(db, "ocorrencias")
    conta = criar_conta(db, usuario, "Conta", 100)
    service = TransactionService(db_path)
    item = item_conta(usuario, conta, "2026-08-04", "Tarifa", -5)

    assert service.salvar_lote_importado([item], usuario) == 1
    assert service.salvar_lote_importado([deepcopy(item), deepcopy(item)], usuario) == 1
    assert total(db, "transacoes") == 2
    assert saldo(db, conta) == 90


def test_contas_diferentes_nao_compartilham_identidade(db, db_path):
    usuario = criar_usuario(db, "contas")
    conta_a = criar_conta(db, usuario, "A", 0)
    conta_b = criar_conta(db, usuario, "B", 0)
    service = TransactionService(db_path)
    a = item_conta(usuario, conta_a, "2026-08-05", "PIX", 50)
    b = item_conta(usuario, conta_b, "2026-08-05", "PIX", 50)

    assert service.salvar_lote_importado([a], usuario) == 1
    assert service.salvar_lote_importado([b], usuario) == 1
    assert saldo(db, conta_a) == 50
    assert saldo(db, conta_b) == 50


def test_duas_importacoes_concorrentes_gravam_uma_unica_ocorrencia(db, db_path):
    usuario = criar_usuario(db, "corrida_importacao")
    conta = criar_conta(db, usuario, "Conta", 0)
    item = item_conta(usuario, conta, "2026-08-20", "Crédito", 75)
    barreira = Barrier(2)

    def importar():
        service = TransactionService(db_path)
        barreira.wait()
        return service.salvar_lote_importado([dict(item)], usuario)

    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(executor.map(lambda _indice: importar(), range(2)))

    assert sorted(resultados) == [0, 1]
    assert total(db, "transacoes") == 1
    assert saldo(db, conta) == 75


def test_fatura_parcial_completa_e_item_pago_nao_recriam_compra(db, db_path):
    usuario = criar_usuario(db, "fatura_importada")
    cartao = criar_cartao(db, usuario)
    service = FaturaService(db_path)
    compra_a = item_cartao(
        usuario, cartao, "2026-08-06", "Mercado", 30
    )
    compra_b = item_cartao(
        usuario, cartao, "2026-08-07", "Farmácia", 45
    )

    assert service.salvar_lote_importado([compra_a], usuario) == 1
    assert service.salvar_lote_importado([compra_a, compra_b], usuario) == 1
    assert service.salvar_lote_importado([compra_a, compra_b], usuario) == 0

    db.execute_query(
        "UPDATE lancamentos SET Paga = 1 WHERE Descricao = 'Mercado'"
    )
    assert service.salvar_lote_importado([compra_a], usuario) == 0
    assert total(db, "lancamentos") == 2


def test_cartoes_competencias_e_parcelas_diferentes_nao_colidem(db, db_path):
    usuario = criar_usuario(db, "cartoes")
    cartao_a = criar_cartao(db, usuario, "A")
    cartao_b = criar_cartao(db, usuario, "B")
    service = FaturaService(db_path)
    base = item_cartao(
        usuario, cartao_a, "2026-08-08", "Compra", 25,
        mes=8, parcela=1, parcelas=3,
    )
    outro_cartao = dict(base, ID_Cartao=cartao_b)
    outra_competencia = dict(base, Competencia_Mes=9)
    outra_parcela = dict(base, Parcela_Atual=2)

    assert service.salvar_lote_importado([base], usuario) == 1
    assert service.salvar_lote_importado([outro_cartao], usuario) == 1
    assert service.salvar_lote_importado([outra_competencia], usuario) == 1
    assert service.salvar_lote_importado([outra_parcela], usuario) == 1
    assert total(db, "lancamentos") == 4


def test_falha_no_lote_importado_reverte_lancamentos_e_saldo(
    db, db_path, monkeypatch
):
    usuario = criar_usuario(db, "rollback_importacao")
    conta = criar_conta(db, usuario, "Conta", 100)
    service = TransactionService(db_path)
    original = service._criar_transacao_base
    chamadas = {"total": 0}

    def falhar_no_segundo(dados, validar_saldo):
        chamadas["total"] += 1
        if chamadas["total"] == 2:
            raise RuntimeError("falha simulada")
        return original(dados, validar_saldo)

    monkeypatch.setattr(service, "_criar_transacao_base", falhar_no_segundo)
    itens = [
        item_conta(usuario, conta, "2026-08-10", "A", 10),
        item_conta(usuario, conta, "2026-08-11", "B", 20),
    ]
    with pytest.raises(RuntimeError):
        service.salvar_lote_importado(itens, usuario)
    assert total(db, "transacoes") == 0
    assert saldo(db, conta) == 100


def test_falha_no_lote_de_fatura_reverte_todas_as_compras(
    db, db_path, monkeypatch
):
    usuario = criar_usuario(db, "rollback_fatura_importada")
    cartao = criar_cartao(db, usuario)
    service = FaturaService(db_path)
    original = service.lancamento_model.add_lancamento
    chamadas = {"total": 0}

    def falhar_no_segundo(dados):
        chamadas["total"] += 1
        if chamadas["total"] == 2:
            raise RuntimeError("falha simulada")
        return original(dados)

    monkeypatch.setattr(service.lancamento_model, "add_lancamento", falhar_no_segundo)
    itens = [
        item_cartao(usuario, cartao, "2026-08-12", "A", 10),
        item_cartao(usuario, cartao, "2026-08-13", "B", 20),
    ]
    with pytest.raises(RuntimeError):
        service.salvar_lote_importado(itens, usuario)
    assert total(db, "lancamentos") == 0


@pytest.mark.parametrize(
    "datas_existentes,datas_importadas,esperados",
    [
        (["2026-01-10"], ["2026-01-10"], 0),
        (["2026-01-10"], ["2026-01-09", "2026-01-10"], 1),
        (["2026-01-10", "2026-01-20"], ["2026-01-10"], 0),
        (["2026-01-10"], ["2026-01-10", "2026-01-20"], 1),
        (["2026-01-10"], ["2026-02-10"], 1),
    ],
)
def test_periodos_variaveis_sem_datas_especiais_na_logica(
    db, db_path, datas_existentes, datas_importadas, esperados
):
    usuario = criar_usuario(db, f"periodo_{len(datas_importadas)}_{esperados}_{datas_importadas[-1]}")
    conta = criar_conta(db, usuario, "Conta", 0)
    service = TransactionService(db_path)
    existentes = [
        item_conta(usuario, conta, data, f"Item {data}", 10)
        for data in datas_existentes
    ]
    importados = [
        item_conta(usuario, conta, data, f"Item {data}", 10)
        for data in datas_importadas
    ]
    service.salvar_lote_importado(existentes, usuario)
    assert service.salvar_lote_importado(importados, usuario) == esperados
