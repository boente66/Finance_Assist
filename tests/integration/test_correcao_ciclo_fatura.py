import sqlite3
from pathlib import Path

import pytest

from database.database import Database, DatabaseError
from services.fatura_service import FaturaService
from conftest import criar_cartao, criar_conta, criar_usuario


def registrar(service, usuario, cartao, data, valor, parcelas=1):
    service.registrar_despesa_cartao({
        "ID_Usuario": usuario,
        "ID_Cartao": cartao,
        "Data": data,
        "Descricao": "Compra",
        "Valor": valor,
        "Num_Parcelas": parcelas,
    })


def test_parcelamento_decimal_preserva_total(db, db_path):
    usuario = criar_usuario(db, "parcelas_decimal")
    cartao = criar_cartao(db, usuario)
    service = FaturaService(db_path)

    registrar(service, usuario, cartao, "2026-09-01", "100.00", 3)

    valores = [row["Valor"] for row in db.fetch_all(
        "SELECT Valor FROM lancamentos WHERE ID_Cartao=? ORDER BY Parcela_Atual",
        (cartao,),
    )]
    assert valores == [33.33, 33.33, 33.34]
    assert round(sum(valores), 2) == 100.00


def test_id_fatura_usa_mesma_validacao_logica_em_banco_novo(db):
    for tabela in ("lancamentos", "pagamentos_fatura"):
        fks = db.fetch_all(f"PRAGMA foreign_key_list({tabela})")
        assert not any(row["from"] == "ID_Fatura" for row in fks)
        for evento in ("insert", "update"):
            assert db.fetch_one(
                "SELECT 1 AS ok FROM sqlite_master "
                "WHERE type='trigger' AND name=?",
                (f"validar_fatura_{tabela}_{evento}",),
            )["ok"] == 1


@pytest.mark.parametrize(
    "mes,ano,fecha,vence,esperado_fecha,esperado_vence",
    [
        (2, 2028, 31, 5, "2028-02-29", "2028-03-05"),
        (4, 2026, 31, 5, "2026-04-30", "2026-05-05"),
        (12, 2026, 25, 5, "2026-12-25", "2027-01-05"),
        (1, 2027, 25, 28, "2027-01-25", "2027-01-28"),
    ],
)
def test_datas_do_ciclo_respeitam_mes_e_virada_de_ano(
    db, db_path, mes, ano, fecha, vence, esperado_fecha, esperado_vence
):
    usuario = criar_usuario(db, f"datas_{mes}_{ano}")
    cartao = criar_cartao(db, usuario)
    db.execute_query(
        "UPDATE credito SET Dia_Fechamento=?, Dia_Vencimento=? WHERE ID_Cartao=?",
        (fecha, vence, cartao),
    )
    ciclo = FaturaService(db_path).sincronizar_ciclo(
        cartao, mes, ano, usuario, esperado_fecha
    )
    assert ciclo["Data_Fechamento"] == esperado_fecha
    assert ciclo["Data_Vencimento"] == esperado_vence


def test_importacao_redireciona_competencia_fechada(db, db_path):
    usuario = criar_usuario(db, "importacao_fechada")
    cartao = criar_cartao(db, usuario)
    db.execute_query(
        "UPDATE credito SET Dia_Fechamento=10 WHERE ID_Cartao=?", (cartao,)
    )
    service = FaturaService(db_path)
    quantidade = service.salvar_lote_importado([{
        "ID_Cartao": cartao,
        "Data": "2026-08-20",
        "Descricao": "Compra importada",
        "Valor": 90,
        "Competencia_Mes": 8,
        "Competencia_Ano": 2026,
    }], usuario)
    item = db.fetch_one(
        "SELECT Competencia_Mes, Competencia_Ano, ID_Fatura FROM lancamentos "
        "WHERE ID_Cartao=?", (cartao,)
    )
    assert quantidade == 1
    assert (item["Competencia_Mes"], item["Competencia_Ano"]) == (9, 2026)
    assert item["ID_Fatura"] is not None


def test_importacao_ignora_pagamento_textual(db, db_path):
    usuario = criar_usuario(db, "ignora_pagamento")
    cartao = criar_cartao(db, usuario)
    service = FaturaService(db_path)
    quantidade = service.salvar_lote_importado([{
        "ID_Cartao": cartao,
        "Data": "2026-09-01",
        "Descricao": "Pagamento de fatura",
        "Valor": -100,
        "Competencia_Mes": 9,
        "Competencia_Ano": 2026,
        "Tipo_Movimento": "PAGAMENTO",
    }], usuario)
    assert quantidade == 0
    assert db.fetch_one("SELECT COUNT(*) AS n FROM lancamentos")["n"] == 0


def test_edicao_move_vinculo_para_fatura_de_destino_sem_duplicar(db, db_path):
    usuario = criar_usuario(db, "edicao_competencia")
    cartao = criar_cartao(db, usuario)
    service = FaturaService(db_path)
    registrar(service, usuario, cartao, "2026-11-01", 75)
    item = db.fetch_one("SELECT * FROM lancamentos WHERE ID_Cartao=?", (cartao,))
    fatura_origem = item["ID_Fatura"]

    service.atualizar_lancamento(item["ID_Lancamento"], {
        **dict(item),
        "Data": "2026-12-01",
        "Competencia_Mes": 12,
        "Competencia_Ano": 2026,
    }, usuario)

    movido = db.fetch_one(
        "SELECT * FROM lancamentos WHERE ID_Lancamento=?",
        (item["ID_Lancamento"],),
    )
    assert movido["ID_Fatura"] != fatura_origem
    assert (movido["Competencia_Mes"], movido["Competencia_Ano"]) == (12, 2026)
    assert service.obter_fatura(cartao, 11, 2026, usuario) == []
    assert len(service.obter_fatura(cartao, 12, 2026, usuario)) == 1
    assert db.fetch_one(
        "SELECT COUNT(*) AS n FROM lancamentos WHERE ID_Lancamento=?",
        (item["ID_Lancamento"],),
    )["n"] == 1


def test_ajuste_pode_reduzir_ou_aumentar_fatura(db, db_path):
    usuario = criar_usuario(db, "ajustes")
    cartao = criar_cartao(db, usuario)
    service = FaturaService(db_path)
    for natureza in ("Reduzir", "Aumentar"):
        service.adicionar_credito_fatura({
            "ID_Usuario": usuario,
            "ID_Cartao": cartao,
            "Data": "2026-09-01",
            "Tipo_Credito": "Ajuste",
            "Natureza_Ajuste": natureza,
            "Valor": 10,
        })
    valores = [row["Valor"] for row in db.fetch_all(
        "SELECT Valor FROM lancamentos ORDER BY ID_Lancamento"
    )]
    assert valores == [-10, 10]


def test_migration_7_remove_pagamento_test9_inequivoco(db, db_path):
    usuario = criar_usuario(db, "upgrade_test9")
    conta = criar_conta(db, usuario, "Conta", 500)
    cartao = criar_cartao(db, usuario)
    service = FaturaService(db_path)
    registrar(service, usuario, cartao, "2026-08-01", 100)
    ciclo = service.sincronizar_ciclo(cartao, 8, 2026, usuario, "2026-08-20")
    transacao = db.execute_insert("""
        INSERT INTO transacoes (ID_Conta, Tipo, Descricao, Valor, Data, ID_Usuario)
        VALUES (?, 'Despesa', 'Pagamento', -100, '2026-08-20', ?)
    """, (conta, usuario))
    db.execute_query("""
        INSERT INTO pagamentos_fatura (
          Chave_Idempotencia, ID_Cartao, ID_Fatura, Competencia_Mes,
          Competencia_Ano, ID_Conta, ID_Transacao, ID_Usuario, Valor
        ) VALUES ('test9', ?, ?, 8, 2026, ?, ?, ?, 100)
    """, (cartao, ciclo["ID_Fatura"], conta, transacao, usuario))
    db.execute_query("""
        INSERT INTO lancamentos (
          ID_Cartao, ID_Fatura, Data, Competencia_Mes, Competencia_Ano,
          Descricao, Valor, Paga, ID_Usuario, ID_Conta, ID_Transacao,
          Tipo_Movimento
        ) VALUES (?, ?, '2026-08-20', 8, 2026, 'Pagamento da fatura',
                  -100, 1, ?, ?, ?, 'PAGAMENTO')
    """, (cartao, ciclo["ID_Fatura"], usuario, conta, transacao))

    db._migration_007_invoice_cycle_correction()

    assert db.fetch_one(
        "SELECT COUNT(*) AS n FROM lancamentos WHERE Tipo_Movimento='PAGAMENTO'"
    )["n"] == 0
    assert db.fetch_one("SELECT COUNT(*) AS n FROM pagamentos_fatura")["n"] == 1
    assert db.fetch_one("SELECT COUNT(*) AS n FROM transacoes")["n"] == 1
    assert db.fetch_one(
        "SELECT Status FROM faturas_cartao WHERE ID_Fatura=?",
        (ciclo["ID_Fatura"],),
    )["Status"] == "PAGA"


def test_backup_obrigatorio_antes_da_migration_7(tmp_path):
    path = tmp_path / "legado_test9.db"
    database = Database(str(path))
    database.execute_query("DELETE FROM schema_migrations WHERE Versao=7")
    database.close()
    Database._initialized_paths.discard(str(path.resolve()))

    migrated = Database(str(path))
    backups = list(tmp_path.glob("legado_test9.db.pre-migration-v7-*.bak"))
    assert len(backups) == 1
    copy = sqlite3.connect(backups[0])
    assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    copy.close()
    assert migrated.fetch_one(
        "SELECT COUNT(*) AS n FROM schema_migrations WHERE Versao=7"
    )["n"] == 1


def test_migration_rollback_integral_quando_validador_falha(db):
    db.execute_query("DELETE FROM schema_migrations WHERE Versao=7")
    before = db.fetch_one(
        "SELECT COUNT(*) AS n FROM schema_migrations"
    )["n"]
    with pytest.raises(DatabaseError):
        db._run_migration(
            7, "falha_controlada",
            lambda: db.connection.execute(
                "UPDATE faturas_cartao SET Atualizado_Em='nao_confirmar'"
            ),
            lambda: False,
            False,
        )
    assert db.fetch_one(
        "SELECT COUNT(*) AS n FROM schema_migrations"
    )["n"] == before
    assert db.fetch_one(
        "SELECT COUNT(*) AS n FROM faturas_cartao "
        "WHERE Atualizado_Em='nao_confirmar'"
    )["n"] == 0
