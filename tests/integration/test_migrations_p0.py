import sqlite3

from database.database import Database


def test_migration_adiciona_vinculos_em_banco_existente(tmp_path):
    db_path = str(tmp_path / "legado.db")
    connection = sqlite3.connect(db_path)
    connection.execute("""
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
        )
    """)
    connection.commit()
    connection.close()

    database = Database(db_path)

    assert "ID_Agendamento" in database._table_columns("transacoes")
    assert database.fetch_one("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'pagamentos_fatura'
    """) is not None
    assert database.fetch_one("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'index'
          AND name = 'idx_transacao_agendamento'
    """) is not None
