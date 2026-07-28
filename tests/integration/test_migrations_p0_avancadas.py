from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import os
import sqlite3

import pytest

from database.database import Database, DatabaseError


BASE_TRANSACOES = """
    CREATE TABLE transacoes (
        ID_Transacao INTEGER PRIMARY KEY AUTOINCREMENT,
        ID_Conta INTEGER NOT NULL,
        Tipo TEXT,
        Descricao TEXT NOT NULL,
        Valor REAL NOT NULL,
        Data TEXT NOT NULL,
        ID_Categoria INTEGER,
        ID_Favorecido INTEGER,
        Notas TEXT,
        ID_Usuario INTEGER NOT NULL
        {extra}
    )
"""


def criar_legado(path, com_coluna=False, com_indice=False, com_dados=False):
    connection = sqlite3.connect(path)
    connection.execute("""
        CREATE TABLE usuarios (
            ID_Usuario INTEGER PRIMARY KEY AUTOINCREMENT,
            Nome TEXT NOT NULL,
            Senha TEXT NOT NULL,
            Nivel_Acesso TEXT
        )
    """)
    connection.execute("""
        CREATE TABLE contas (
            ID_Conta INTEGER PRIMARY KEY AUTOINCREMENT,
            Nome_Conta TEXT NOT NULL,
            Saldo_Atual REAL DEFAULT 0,
            ID_Usuario INTEGER
        )
    """)
    extra = ", ID_Agendamento INTEGER" if com_coluna else ""
    connection.execute(BASE_TRANSACOES.format(extra=extra))
    if com_indice:
        connection.execute("""
            CREATE UNIQUE INDEX idx_transacao_agendamento
            ON transacoes(ID_Agendamento)
            WHERE ID_Agendamento IS NOT NULL
        """)
    if com_dados:
        connection.execute(
            "INSERT INTO usuarios (ID_Usuario, Nome, Senha, Nivel_Acesso) "
            "VALUES (1, 'Legado', 'x', 'usuario')"
        )
        connection.execute(
            "INSERT INTO contas (ID_Conta, Nome_Conta, Saldo_Atual, ID_Usuario) "
            "VALUES (1, 'Conta legado', 100, 1)"
        )
        columns = (
            "ID_Transacao, ID_Conta, Tipo, Descricao, Valor, Data, ID_Usuario"
            + (", ID_Agendamento" if com_coluna else "")
        )
        values = "1, 1, 'Despesa', 'Legada', -10, '2026-01-01', 1"
        values += ", NULL" if com_coluna else ""
        connection.execute(
            f"INSERT INTO transacoes ({columns}) VALUES ({values})"
        )
    connection.commit()
    connection.close()


def fk_agendamento(database):
    return any(
        row["from"] == "ID_Agendamento"
        and row["table"] == "agendamentos"
        for row in database.fetch_all("PRAGMA foreign_key_list(transacoes)")
    )


def versions(database):
    return database.fetch_all(
        "SELECT Versao, Nome FROM schema_migrations ORDER BY Versao"
    )


def test_banco_novo_tem_versoes_fks_indices_e_constraints(tmp_path):
    database = Database(str(tmp_path / "novo.db"))

    assert [row["Versao"] for row in versions(database)] == [1, 2, 3]
    assert fk_agendamento(database)
    assert database._schedule_index_valid()
    assert database._pagamentos_p0_valid()
    assert database.fetch_all("PRAGMA foreign_key_check") == []


@pytest.mark.parametrize(
    "com_coluna,com_indice",
    [(False, False), (True, False), (True, True)]
)
def test_legado_sem_fk_e_reconstruido_com_dados_preservados(
    tmp_path,
    com_coluna,
    com_indice
):
    path = str(tmp_path / f"legado_{com_coluna}_{com_indice}.db")
    criar_legado(path, com_coluna, com_indice, com_dados=True)

    database = Database(path)

    assert fk_agendamento(database)
    assert database._schedule_index_valid()
    assert database.fetch_one(
        "SELECT COUNT(*) AS total FROM transacoes"
    )["total"] == 1
    assert database.fetch_one(
        "SELECT ID_Transacao, Descricao FROM transacoes"
    ) == {"ID_Transacao": 1, "Descricao": "Legada"}
    assert database.fetch_all("PRAGMA foreign_key_check") == []


def test_indice_incorreto_e_recriado(tmp_path):
    path = str(tmp_path / "indice_incorreto.db")
    criar_legado(path, com_coluna=True, com_dados=True)
    connection = sqlite3.connect(path)
    connection.execute("""
        CREATE INDEX idx_transacao_agendamento
        ON transacoes(ID_Agendamento)
    """)
    connection.commit()
    connection.close()

    database = Database(path)
    assert database._schedule_index_valid()
    assert fk_agendamento(database)


def test_pagamentos_completa_sem_constraints_e_reconstruida(tmp_path):
    path = str(tmp_path / "pagamentos_completa.db")
    criar_legado(path)
    connection = sqlite3.connect(path)
    connection.execute("""
        CREATE TABLE pagamentos_fatura (
            ID_Pagamento INTEGER PRIMARY KEY AUTOINCREMENT,
            Chave_Idempotencia TEXT NOT NULL,
            ID_Cartao INTEGER NOT NULL,
            Competencia_Mes INTEGER NOT NULL,
            Competencia_Ano INTEGER NOT NULL,
            ID_Conta INTEGER NOT NULL,
            ID_Transacao INTEGER NOT NULL,
            ID_Usuario INTEGER NOT NULL,
            Valor REAL NOT NULL,
            Criado_Em TEXT
        )
    """)
    connection.execute("""
        CREATE TABLE credito (
            ID_Cartao INTEGER PRIMARY KEY,
            Nome TEXT NOT NULL,
            Limite REAL NOT NULL,
            Dia_Fechamento INTEGER NOT NULL,
            Dia_Vencimento INTEGER NOT NULL,
            ID_Usuario INTEGER
        )
    """)
    connection.execute(
        "INSERT INTO usuarios VALUES (1, 'U', 'x', 'usuario')"
    )
    connection.execute(
        "INSERT INTO contas VALUES (1, 'C', 100, 1)"
    )
    connection.execute(
        "INSERT INTO credito VALUES (1, 'Card', 100, 10, 20, 1)"
    )
    connection.execute("""
        INSERT INTO transacoes (
            ID_Transacao, ID_Conta, Tipo, Descricao, Valor, Data, ID_Usuario
        ) VALUES (1, 1, 'Despesa', 'Pagamento legado', -10, '2026-01-01', 1)
    """)
    connection.execute("""
        INSERT INTO pagamentos_fatura (
            ID_Pagamento, Chave_Idempotencia, ID_Cartao,
            Competencia_Mes, Competencia_Ano, ID_Conta,
            ID_Transacao, ID_Usuario, Valor, Criado_Em
        ) VALUES (5, 'legada', 1, 1, 2026, 1, 1, 1, 10, '2026-01-01')
    """)
    connection.commit()
    connection.close()

    database = Database(path)
    assert database._pagamentos_p0_valid()
    assert database.fetch_one("""
        SELECT ID_Pagamento, Chave_Idempotencia
        FROM pagamentos_fatura
    """) == {"ID_Pagamento": 5, "Chave_Idempotencia": "legada"}
    assert database.fetch_all("PRAGMA foreign_key_check") == []


def test_pagamentos_incompleta_vazia_e_recuperada(tmp_path):
    path = str(tmp_path / "pagamentos_incompleta.db")
    connection = sqlite3.connect(path)
    connection.execute("""
        CREATE TABLE pagamentos_fatura (
            ID_Pagamento INTEGER PRIMARY KEY
        )
    """)
    connection.commit()
    connection.close()

    database = Database(path)
    assert database._pagamentos_p0_valid()
    assert [row["Versao"] for row in versions(database)] == [1, 2, 3]


def test_pagamentos_incompleta_com_dados_falha_sem_perda(tmp_path):
    path = str(tmp_path / "pagamentos_incompleta_dados.db")
    connection = sqlite3.connect(path)
    connection.execute("""
        CREATE TABLE pagamentos_fatura (
            ID_Pagamento INTEGER PRIMARY KEY,
            Chave_Idempotencia TEXT
        )
    """)
    connection.execute(
        "INSERT INTO pagamentos_fatura VALUES (7, 'preservar')"
    )
    connection.commit()
    connection.close()

    with pytest.raises(DatabaseError, match="sem perda"):
        Database(path)

    connection = sqlite3.connect(path)
    assert connection.execute(
        "SELECT * FROM pagamentos_fatura"
    ).fetchall() == [(7, "preservar")]
    assert connection.execute(
        "SELECT COUNT(*) FROM schema_migrations WHERE Versao = 3"
    ).fetchone()[0] == 0
    connection.close()


def test_migracao_interrompida_simulada_e_execucao_repetida(tmp_path):
    path = str(tmp_path / "interrompida.db")
    criar_legado(path, com_coluna=True)
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE transacoes__p0_new (ID INTEGER)")
    connection.commit()
    connection.close()

    database = Database(path)
    primeiras_versoes = versions(database)
    database._run_migrations()

    assert versions(database) == primeiras_versoes
    assert database._transacoes_p0_valid()
    assert database._pagamentos_p0_valid()
    assert database.fetch_all("PRAGMA foreign_key_check") == []


def test_constraints_unique_estao_ativas(tmp_path):
    database = Database(str(tmp_path / "unique.db"))
    database.execute_query(
        "INSERT INTO usuarios (ID_Usuario, Nome, Senha, Nivel_Acesso) "
        "VALUES (1, 'U', 'x', 'usuario')"
    )
    database.execute_query(
        "INSERT INTO contas (ID_Conta, Nome_Conta, Saldo_Atual, ID_Usuario) "
        "VALUES (1, 'C', 100, 1)"
    )
    database.execute_query("""
        INSERT INTO credito (
            ID_Cartao, Nome, Limite, Dia_Fechamento, Dia_Vencimento,
            Ativo, ID_Usuario
        ) VALUES (1, 'Card', 100, 10, 20, 1, 1)
    """)
    database.execute_query("""
        INSERT INTO transacoes (
            ID_Transacao, ID_Conta, Tipo, Descricao, Valor, Data, ID_Usuario
        ) VALUES (1, 1, 'Despesa', 'P', -10, '2026-01-01', 1)
    """)
    database.execute_query("""
        INSERT INTO transacoes (
            ID_Transacao, ID_Conta, Tipo, Descricao, Valor, Data, ID_Usuario
        ) VALUES (2, 1, 'Despesa', 'P2', -10, '2026-01-02', 1)
    """)
    database.execute_query("""
        INSERT INTO pagamentos_fatura (
            Chave_Idempotencia, ID_Cartao, Competencia_Mes,
            Competencia_Ano, ID_Conta, ID_Transacao, ID_Usuario, Valor
        ) VALUES ('chave', 1, 1, 2026, 1, 1, 1, 10)
    """)

    with pytest.raises(DatabaseError):
        database.execute_query("""
            INSERT INTO pagamentos_fatura (
                Chave_Idempotencia, ID_Cartao, Competencia_Mes,
                Competencia_Ano, ID_Conta, ID_Transacao, ID_Usuario, Valor
            ) VALUES ('chave', 1, 2, 2026, 1, 2, 1, 10)
        """)


def test_inicializacao_concorrente_do_mesmo_banco(tmp_path):
    path = str(tmp_path / "concorrente.db")
    key = os.path.abspath(path)
    with Database._initialization_lock:
        Database._initialized_paths.discard(key)
    barrier = Barrier(2)

    def initialize(_):
        barrier.wait()
        database = Database(path)
        return (
            database.fetch_one("SELECT COUNT(*) AS total FROM schema_migrations")[
                "total"
            ],
            database.fetch_one("SELECT 1 AS valor")["valor"],
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(initialize, range(2)))

    assert results == [(3, 1), (3, 1)]
    database = Database(path)
    assert database.fetch_all("PRAGMA foreign_key_check") == []
