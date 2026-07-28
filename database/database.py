# -*- coding: utf-8 -*-
import sqlite3
import logging
import os
import threading
from contextlib import contextmanager

from core.config import DB_PATH

logging.basicConfig(
    filename="database.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class Database:
    _initialized_paths = set()
    _initializing_paths = {}
    _initialization_lock = threading.Lock()

    def __init__(self, db_name=DB_PATH):
        self.db_name = db_name
        self._thread_local = threading.local()

        self._ensure_directory()
        self._ensure_connection()
        self._initialize_schema_once()

    def _initialization_key(self):
        if self.db_name == ":memory:":
            return f":memory:{id(self)}"
        return os.path.abspath(self.db_name)

    def _initialize_schema_once(self):
        """Serializa somente a primeira inicialização de cada arquivo."""
        key = self._initialization_key()

        while True:
            with Database._initialization_lock:
                if key in Database._initialized_paths:
                    return

                event = Database._initializing_paths.get(key)
                if event is None:
                    event = threading.Event()
                    Database._initializing_paths[key] = event
                    initializer = True
                else:
                    initializer = False

            if initializer:
                break

            event.wait()

        succeeded = False
        try:
            self.create_tables()
            succeeded = True
        finally:
            with Database._initialization_lock:
                if succeeded:
                    Database._initialized_paths.add(key)
                Database._initializing_paths.pop(key, None)
                event.set()

    # =====================================================
    # CONNECTION
    # =====================================================
    def _ensure_connection(self):
        if not getattr(self._thread_local, "connection", None):
            self._thread_local.connection = self.connect()
            self._thread_local.manual_transaction = False
            self._thread_local.shared_connection = False

    @property
    def connection(self):
        self._ensure_connection()
        return self._thread_local.connection

    @connection.setter
    def connection(self, value):
        self._thread_local.connection = value
        self._thread_local.shared_connection = False

    def connect(self):
        try:
            conn = sqlite3.connect(self.db_name)
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA busy_timeout = 5000;")
            conn.row_factory = sqlite3.Row
            return conn

        except sqlite3.Error as e:
            raise DatabaseError(
                f"Erro ao conectar: {str(e)}",
                original_exception=e
            )

    def close(self):
        if getattr(self._thread_local, "shared_connection", False):
            raise RuntimeError(
                "Este objeto não é proprietário da conexão compartilhada."
            )

        conn = getattr(self._thread_local, "connection", None)
        if conn:
            conn.close()
            self._thread_local.connection = None

    def _ensure_directory(self):
        directory = os.path.dirname(self.db_name)

        if directory and not os.path.exists(directory):
            os.makedirs(directory)

    # =====================================================
    # SCHEMA
    # =====================================================
    def create_tables(self):
        self.connection.executescript("""
-- =====================================================
-- USUÁRIOS
-- =====================================================
CREATE TABLE IF NOT EXISTS usuarios (
    ID_Usuario INTEGER PRIMARY KEY AUTOINCREMENT,
    Nome TEXT NOT NULL,
    DataNascimento TEXT,
    Sexo TEXT CHECK (
        Sexo IN ('Masculino','Feminino','Outro')
    ),
    CPF TEXT,
    Email TEXT UNIQUE,
    Login TEXT UNIQUE,
    Senha TEXT NOT NULL,
    Telefone TEXT,
    Celular TEXT,
    Nivel_Acesso TEXT CHECK (
        Nivel_Acesso IN ('admin','usuario')
    ),
    Tema TEXT DEFAULT 'Claro',
    Idioma TEXT DEFAULT 'pt_BR'
);

-- =====================================================
-- RECUPERAÇÃO DE SENHA
-- =====================================================
CREATE TABLE IF NOT EXISTS recuperacao_senha (
    ID_Recuperacao INTEGER PRIMARY KEY AUTOINCREMENT,
    ID_Usuario INTEGER NOT NULL,
    Token TEXT NOT NULL UNIQUE,
    Codigo TEXT,
    Expira_Em TEXT NOT NULL,
    Utilizado INTEGER DEFAULT 0,
    Criado_Em TEXT DEFAULT CURRENT_TIMESTAMP,
    IP TEXT,
    User_Agent TEXT,

    FOREIGN KEY(ID_Usuario)
        REFERENCES usuarios(ID_Usuario)
        ON DELETE CASCADE
);

-- =====================================================
-- CATEGORIAS
-- =====================================================
CREATE TABLE IF NOT EXISTS categorias (
    ID_Categoria INTEGER PRIMARY KEY AUTOINCREMENT,
    Nome TEXT NOT NULL,
    Tipo TEXT CHECK (
        Tipo IN ('Despesa','Receita')
    ),
    ID_Usuario INTEGER NOT NULL,
    ID_Categoria_Pai INTEGER,

    FOREIGN KEY(ID_Usuario)
        REFERENCES usuarios(ID_Usuario)
        ON DELETE CASCADE,

    FOREIGN KEY(ID_Categoria_Pai)
        REFERENCES categorias(ID_Categoria)
);

-- =====================================================
-- CONTAS
-- =====================================================
CREATE TABLE IF NOT EXISTS contas (
    ID_Conta INTEGER PRIMARY KEY AUTOINCREMENT,
    Nome_Conta TEXT NOT NULL,
    Instituicao TEXT,
    Tipo TEXT,
    Saldo_Atual REAL DEFAULT 0,
    ID_Usuario INTEGER,

    FOREIGN KEY(ID_Usuario)
        REFERENCES usuarios(ID_Usuario)
        ON DELETE CASCADE
);

-- =====================================================
-- CARTÕES
-- =====================================================
CREATE TABLE IF NOT EXISTS credito (
    ID_Cartao INTEGER PRIMARY KEY AUTOINCREMENT,
    Nome TEXT NOT NULL,
    Limite REAL NOT NULL DEFAULT 0,
    Dia_Fechamento INTEGER NOT NULL,
    Dia_Vencimento INTEGER NOT NULL,
    Ativo INTEGER DEFAULT 1,
    ID_Usuario INTEGER,

    FOREIGN KEY(ID_Usuario)
        REFERENCES usuarios(ID_Usuario)
        ON DELETE CASCADE
);

-- =====================================================
-- FAVORECIDOS
-- =====================================================
CREATE TABLE IF NOT EXISTS favorecido (
    ID_Favorecido INTEGER PRIMARY KEY AUTOINCREMENT,
    Nome TEXT NOT NULL,
    Tipo TEXT CHECK (
        Tipo IN ('PF','PJ')
    ),
    ID_Usuario INTEGER NOT NULL,
    Criado_Em TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(ID_Usuario)
        REFERENCES usuarios(ID_Usuario)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pessoa_fisica (
    ID_Favorecido INTEGER PRIMARY KEY,
    CPF TEXT ,
    Telefone TEXT,

    FOREIGN KEY(ID_Favorecido)
        REFERENCES favorecido(ID_Favorecido)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pessoa_juridica (
    ID_Favorecido INTEGER PRIMARY KEY,
    CNPJ TEXT ,
    Razao_Social TEXT,
    Telefone TEXT,

    FOREIGN KEY(ID_Favorecido)
        REFERENCES favorecido(ID_Favorecido)
        ON DELETE CASCADE
);

-- =====================================================
-- TRANSAÇÕES
-- =====================================================
CREATE TABLE IF NOT EXISTS transacoes (
    ID_Transacao INTEGER PRIMARY KEY AUTOINCREMENT,
    ID_Conta INTEGER NOT NULL,

    Tipo TEXT CHECK (
        Tipo IN ('Receita','Despesa','Transferência')
    ),

    Descricao TEXT NOT NULL,
    Valor REAL NOT NULL,
    Data TEXT NOT NULL,
    ID_Categoria INTEGER,
    ID_Favorecido INTEGER,
    Notas TEXT,
    ID_Usuario INTEGER NOT NULL,
    ID_Agendamento INTEGER,

    FOREIGN KEY(ID_Conta)
        REFERENCES contas(ID_Conta)
        ON DELETE CASCADE,

    FOREIGN KEY(ID_Categoria)
        REFERENCES categorias(ID_Categoria),

    FOREIGN KEY(ID_Favorecido)
        REFERENCES favorecido(ID_Favorecido),

    FOREIGN KEY(ID_Usuario)
        REFERENCES usuarios(ID_Usuario)
        ON DELETE CASCADE,

    FOREIGN KEY(ID_Agendamento)
        REFERENCES agendamentos(ID_Agendamento)
);

-- =====================================================
-- AGENDAMENTOS
-- =====================================================
CREATE TABLE IF NOT EXISTS agendamentos (
    ID_Agendamento INTEGER PRIMARY KEY AUTOINCREMENT,

    Tipo TEXT CHECK (
        Tipo IN (
            'Contas a Receber',
            'Contas a Pagar',
            'Transferências',
            'Cartao',
            'Cartão'
        )
    ),

    Data TEXT NOT NULL,
    Valor REAL NOT NULL,
    Descricao TEXT,

    Status TEXT CHECK (
        Status IN (
            'AGENDADO',
            'EXECUTADO',
            'CANCELADO',
            'ATRASADO',
            'INATIVO'
        )
    ),

    ID_Categoria INTEGER,
    ID_Favorecido INTEGER,
    ID_Conta INTEGER,
    ID_Cartao INTEGER,
    ID_Usuario INTEGER NOT NULL,

    Recorrente INTEGER DEFAULT 0,
    Periodicidade TEXT,
    Ativo INTEGER DEFAULT 1,
    ID_Pai INTEGER,
    Parcelas INTEGER DEFAULT 1,

    FOREIGN KEY(ID_Categoria)
        REFERENCES categorias(ID_Categoria),

    FOREIGN KEY(ID_Favorecido)
        REFERENCES favorecido(ID_Favorecido),

    FOREIGN KEY(ID_Conta)
        REFERENCES contas(ID_Conta),

    FOREIGN KEY(ID_Cartao)
        REFERENCES credito(ID_Cartao),

    FOREIGN KEY(ID_Usuario)
        REFERENCES usuarios(ID_Usuario)
        ON DELETE CASCADE
);

-- =====================================================
-- LANÇAMENTOS
-- =====================================================
CREATE TABLE IF NOT EXISTS lancamentos (
    ID_Lancamento INTEGER PRIMARY KEY AUTOINCREMENT,
    ID_Cartao INTEGER NOT NULL,
    Data TEXT NOT NULL,
    Competencia_Mes INTEGER NOT NULL,
    Competencia_Ano INTEGER NOT NULL,
    Descricao TEXT,
    Valor REAL NOT NULL,
    ID_Categoria INTEGER,
    ID_Favorecido INTEGER,
    Num_Parcelas INTEGER,
    Parcela_Atual INTEGER,
    Paga INTEGER DEFAULT 0,
    Notas TEXT,
    Previsto INTEGER DEFAULT 0,
    ID_Usuario INTEGER,
    ID_Conta INTEGER,
    ID_Transacao INTEGER,

    FOREIGN KEY(ID_Cartao)
        REFERENCES credito(ID_Cartao)
        ON DELETE CASCADE,

    FOREIGN KEY(ID_Categoria)
        REFERENCES categorias(ID_Categoria),

    FOREIGN KEY(ID_Favorecido)
        REFERENCES favorecido(ID_Favorecido),

    FOREIGN KEY(ID_Usuario)
        REFERENCES usuarios(ID_Usuario)
        ON DELETE CASCADE,

    FOREIGN KEY(ID_Conta)
        REFERENCES contas(ID_Conta),

    FOREIGN KEY(ID_Transacao)
        REFERENCES transacoes(ID_Transacao)
);

-- =====================================================
-- PAGAMENTOS DE FATURA / IDEMPOTÊNCIA
-- =====================================================
CREATE TABLE IF NOT EXISTS pagamentos_fatura (
    ID_Pagamento INTEGER PRIMARY KEY AUTOINCREMENT,
    Chave_Idempotencia TEXT NOT NULL UNIQUE,
    ID_Cartao INTEGER NOT NULL,
    Competencia_Mes INTEGER NOT NULL,
    Competencia_Ano INTEGER NOT NULL,
    ID_Conta INTEGER NOT NULL,
    ID_Transacao INTEGER NOT NULL UNIQUE,
    ID_Usuario INTEGER NOT NULL,
    Valor REAL NOT NULL,
    Criado_Em TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(ID_Cartao)
        REFERENCES credito(ID_Cartao),

    FOREIGN KEY(ID_Conta)
        REFERENCES contas(ID_Conta),

    FOREIGN KEY(ID_Transacao)
        REFERENCES transacoes(ID_Transacao),

    FOREIGN KEY(ID_Usuario)
        REFERENCES usuarios(ID_Usuario)
        ON DELETE CASCADE
);

-- =====================================================
-- METAS
-- =====================================================
CREATE TABLE IF NOT EXISTS metas (
    ID_Meta INTEGER PRIMARY KEY AUTOINCREMENT,
    Nome TEXT NOT NULL,

    Tipo TEXT CHECK (
        Tipo IN ('Categoria','Economia','Objetivo')
    ),

    Valor_Alvo REAL NOT NULL,
    Valor_Atual REAL DEFAULT 0,
    ID_Categoria INTEGER,
    Data_Inicio TEXT,
    Data_Fim TEXT,
    ID_Usuario INTEGER NOT NULL,
    Status TEXT DEFAULT 'ATIVA',
    Criado_Em TEXT DEFAULT CURRENT_TIMESTAMP,
    Atualizado_Em TEXT,
    Concluido_Em TEXT,

    FOREIGN KEY(ID_Usuario)
        REFERENCES usuarios(ID_Usuario)
        ON DELETE CASCADE,

    FOREIGN KEY(ID_Categoria)
        REFERENCES categorias(ID_Categoria)
);

-- =====================================================
-- ÍNDICES
-- =====================================================
CREATE UNIQUE INDEX IF NOT EXISTS idx_cpf
ON pessoa_fisica(CPF)
WHERE CPF IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_cnpj
ON pessoa_juridica(CNPJ)
WHERE CNPJ IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_recuperacao_token
ON recuperacao_senha(Token);

CREATE INDEX IF NOT EXISTS idx_recuperacao_usuario
ON recuperacao_senha(ID_Usuario);

""")

        self._run_migrations()
        self.connection.commit()

    # =====================================================
    # VERSIONED MIGRATIONS
    # =====================================================
    def _table_columns(self, table):
        rows = self.connection.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()

        return {row["name"] for row in rows}

    def _add_column_if_missing(self, table, column, definition):
        if column not in self._table_columns(table):
            self.connection.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
            )

    def _ensure_migration_table(self):
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                Versao INTEGER PRIMARY KEY,
                Nome TEXT NOT NULL,
                Aplicada_Em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.connection.commit()

    def _migration_applied(self, version):
        row = self.connection.execute(
            "SELECT 1 FROM schema_migrations WHERE Versao = ?",
            (version,)
        ).fetchone()
        return row is not None

    def _run_migration(
        self,
        version,
        name,
        migration,
        validator,
        disable_foreign_keys=False
    ):
        if self._migration_applied(version):
            if not validator():
                raise DatabaseError(
                    f"Migração {version} ({name}) consta como aplicada, "
                    "mas o schema está incompatível."
                )
            return

        connection = self.connection
        previous_foreign_keys = connection.execute(
            "PRAGMA foreign_keys"
        ).fetchone()[0]

        try:
            connection.commit()
            if disable_foreign_keys:
                connection.execute("PRAGMA foreign_keys = OFF")

            connection.execute("BEGIN IMMEDIATE")
            migration()

            if not validator():
                raise sqlite3.DatabaseError(
                    f"Validação da migração {version} falhou."
                )

            violations = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()
            if violations:
                raise sqlite3.IntegrityError(
                    f"Migração {version} produziu violações de foreign key: "
                    f"{[tuple(row) for row in violations]}"
                )

            connection.execute(
                "INSERT INTO schema_migrations (Versao, Nome) VALUES (?, ?)",
                (version, name)
            )
            connection.commit()

        except Exception as exc:
            connection.rollback()
            if isinstance(exc, DatabaseError):
                raise
            raise DatabaseError(
                f"Erro na migração {version} ({name}): {exc}",
                original_exception=exc
            ) from exc

        finally:
            if disable_foreign_keys:
                connection.execute(
                    f"PRAGMA foreign_keys = {1 if previous_foreign_keys else 0}"
                )

    def _migration_001_legacy_columns(self):
        additions = (
            ("recuperacao_senha", "Codigo", "TEXT"),
            ("recuperacao_senha", "Utilizado", "INTEGER DEFAULT 0"),
            ("recuperacao_senha", "Criado_Em", "TEXT"),
            ("recuperacao_senha", "IP", "TEXT"),
            ("recuperacao_senha", "User_Agent", "TEXT"),
            ("metas", "Concluido_Em", "TEXT"),
            ("agendamentos", "ID_Cartao", "INTEGER"),
            ("agendamentos", "Parcelas", "INTEGER DEFAULT 1"),
            ("agendamentos", "Recorrente", "INTEGER DEFAULT 0"),
            ("agendamentos", "Periodicidade", "TEXT"),
            ("agendamentos", "Ativo", "INTEGER DEFAULT 1"),
            ("agendamentos", "ID_Pai", "INTEGER"),
        )
        for table, column, definition in additions:
            self._add_column_if_missing(table, column, definition)

    def _legacy_columns_valid(self):
        expected = {
            "recuperacao_senha": {
                "Codigo", "Utilizado", "Criado_Em", "IP", "User_Agent"
            },
            "metas": {"Concluido_Em"},
            "agendamentos": {
                "ID_Cartao", "Parcelas", "Recorrente", "Periodicidade",
                "Ativo", "ID_Pai"
            },
        }
        return all(
            columns.issubset(self._table_columns(table))
            for table, columns in expected.items()
        )

    def _foreign_key_exists(self, table, column, parent, parent_column):
        rows = self.connection.execute(
            f"PRAGMA foreign_key_list({table})"
        ).fetchall()
        return any(
            row["from"] == column
            and row["table"] == parent
            and row["to"] == parent_column
            for row in rows
        )

    def _index_definition(self, name):
        return self.connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?",
            (name,)
        ).fetchone()

    def _schedule_index_valid(self):
        rows = self.connection.execute(
            "PRAGMA index_list(transacoes)"
        ).fetchall()
        index = next(
            (row for row in rows if row["name"] == "idx_transacao_agendamento"),
            None
        )
        if not index or not index["unique"] or not index["partial"]:
            return False

        columns = self.connection.execute(
            "PRAGMA index_info(idx_transacao_agendamento)"
        ).fetchall()
        definition = self._index_definition("idx_transacao_agendamento")
        return (
            [row["name"] for row in columns] == ["ID_Agendamento"]
            and definition is not None
            and "WHERE ID_Agendamento IS NOT NULL" in definition["sql"]
        )

    def _transacoes_p0_valid(self):
        return (
            "ID_Agendamento" in self._table_columns("transacoes")
            and self._foreign_key_exists(
                "transacoes",
                "ID_Agendamento",
                "agendamentos",
                "ID_Agendamento"
            )
            and self._schedule_index_valid()
        )

    def _dependent_objects(self, table, excluded_names=()):
        rows = self.connection.execute("""
            SELECT type, name, sql
            FROM sqlite_master
            WHERE tbl_name = ?
              AND type IN ('index', 'trigger')
              AND sql IS NOT NULL
        """, (table,)).fetchall()
        return [
            dict(row) for row in rows
            if row["name"] not in set(excluded_names)
        ]

    def _migration_002_transacoes_agendamento(self):
        required = [
            "ID_Transacao", "ID_Conta", "Tipo", "Descricao", "Valor",
            "Data", "ID_Categoria", "ID_Favorecido", "Notas", "ID_Usuario"
        ]
        existing = self._table_columns("transacoes")
        allowed = set(required) | {"ID_Agendamento"}
        missing = set(required) - existing
        extra = existing - allowed
        if missing or extra:
            raise DatabaseError(
                "Schema de transacoes incompatível; "
                f"colunas ausentes={sorted(missing)}, extras={sorted(extra)}."
            )

        needs_rebuild = not self._foreign_key_exists(
            "transacoes",
            "ID_Agendamento",
            "agendamentos",
            "ID_Agendamento"
        )

        if needs_rebuild:
            dangling = 0
            if "ID_Agendamento" in existing:
                dangling = self.connection.execute("""
                    SELECT COUNT(*) AS total
                    FROM transacoes t
                    LEFT JOIN agendamentos a
                      ON a.ID_Agendamento = t.ID_Agendamento
                    WHERE t.ID_Agendamento IS NOT NULL
                      AND a.ID_Agendamento IS NULL
                """).fetchone()["total"]
            if dangling:
                raise DatabaseError(
                    "Não é possível migrar transacoes: existem "
                    f"{dangling} vínculos de agendamento inválidos."
                )

            objects = self._dependent_objects(
                "transacoes",
                {"idx_transacao_agendamento"}
            )
            before = self.connection.execute(
                "SELECT COUNT(*) AS total FROM transacoes"
            ).fetchone()["total"]

            self.connection.execute("DROP TABLE IF EXISTS transacoes__p0_new")
            self.connection.execute("""
                CREATE TABLE transacoes__p0_new (
                    ID_Transacao INTEGER PRIMARY KEY AUTOINCREMENT,
                    ID_Conta INTEGER NOT NULL,
                    Tipo TEXT CHECK (
                        Tipo IN ('Receita','Despesa','Transferência')
                    ),
                    Descricao TEXT NOT NULL,
                    Valor REAL NOT NULL,
                    Data TEXT NOT NULL,
                    ID_Categoria INTEGER,
                    ID_Favorecido INTEGER,
                    Notas TEXT,
                    ID_Usuario INTEGER NOT NULL,
                    ID_Agendamento INTEGER,
                    FOREIGN KEY(ID_Conta) REFERENCES contas(ID_Conta)
                        ON DELETE CASCADE,
                    FOREIGN KEY(ID_Categoria) REFERENCES categorias(ID_Categoria),
                    FOREIGN KEY(ID_Favorecido) REFERENCES favorecido(ID_Favorecido),
                    FOREIGN KEY(ID_Usuario) REFERENCES usuarios(ID_Usuario)
                        ON DELETE CASCADE,
                    FOREIGN KEY(ID_Agendamento)
                        REFERENCES agendamentos(ID_Agendamento)
                )
            """)

            source_columns = required + (
                ["ID_Agendamento"] if "ID_Agendamento" in existing else []
            )
            target_columns = required + ["ID_Agendamento"]
            select_columns = source_columns + (
                [] if "ID_Agendamento" in existing else ["NULL"]
            )
            self.connection.execute(
                f"INSERT INTO transacoes__p0_new "
                f"({', '.join(target_columns)}) "
                f"SELECT {', '.join(select_columns)} FROM transacoes"
            )

            after = self.connection.execute(
                "SELECT COUNT(*) AS total FROM transacoes__p0_new"
            ).fetchone()["total"]
            if before != after:
                raise sqlite3.DatabaseError(
                    "Contagem de transacoes divergiu durante a migração."
                )

            self.connection.execute("DROP TABLE transacoes")
            self.connection.execute(
                "ALTER TABLE transacoes__p0_new RENAME TO transacoes"
            )
            for obj in objects:
                self.connection.execute(obj["sql"])

        if self._index_definition("idx_transacao_agendamento"):
            if not self._schedule_index_valid():
                self.connection.execute(
                    "DROP INDEX idx_transacao_agendamento"
                )

        self.connection.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_transacao_agendamento
            ON transacoes(ID_Agendamento)
            WHERE ID_Agendamento IS NOT NULL
        """)

    def _create_pagamentos_fatura_table(self, table="pagamentos_fatura"):
        self.connection.execute(f"""
            CREATE TABLE {table} (
                ID_Pagamento INTEGER PRIMARY KEY AUTOINCREMENT,
                Chave_Idempotencia TEXT NOT NULL UNIQUE,
                ID_Cartao INTEGER NOT NULL,
                Competencia_Mes INTEGER NOT NULL,
                Competencia_Ano INTEGER NOT NULL,
                ID_Conta INTEGER NOT NULL,
                ID_Transacao INTEGER NOT NULL UNIQUE,
                ID_Usuario INTEGER NOT NULL,
                Valor REAL NOT NULL,
                Criado_Em TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(ID_Cartao) REFERENCES credito(ID_Cartao),
                FOREIGN KEY(ID_Conta) REFERENCES contas(ID_Conta),
                FOREIGN KEY(ID_Transacao) REFERENCES transacoes(ID_Transacao),
                FOREIGN KEY(ID_Usuario) REFERENCES usuarios(ID_Usuario)
                    ON DELETE CASCADE
            )
        """)

    def _payment_uniques_valid(self):
        unique_columns = set()
        for index in self.connection.execute(
            "PRAGMA index_list(pagamentos_fatura)"
        ).fetchall():
            if index["unique"]:
                columns = self.connection.execute(
                    f"PRAGMA index_info({index['name']})"
                ).fetchall()
                unique_columns.add(tuple(row["name"] for row in columns))
        return {
            ("Chave_Idempotencia",),
            ("ID_Transacao",),
        }.issubset(unique_columns)

    def _payment_index_valid(self):
        rows = self.connection.execute(
            "PRAGMA index_info(idx_pagamento_fatura_competencia)"
        ).fetchall()
        return [row["name"] for row in rows] == [
            "ID_Cartao", "Competencia_Mes", "Competencia_Ano", "ID_Usuario"
        ]

    def _pagamentos_p0_valid(self):
        required = {
            "ID_Pagamento", "Chave_Idempotencia", "ID_Cartao",
            "Competencia_Mes", "Competencia_Ano", "ID_Conta",
            "ID_Transacao", "ID_Usuario", "Valor", "Criado_Em"
        }
        foreign_keys = (
            ("ID_Cartao", "credito", "ID_Cartao"),
            ("ID_Conta", "contas", "ID_Conta"),
            ("ID_Transacao", "transacoes", "ID_Transacao"),
            ("ID_Usuario", "usuarios", "ID_Usuario"),
        )
        return (
            self._table_columns("pagamentos_fatura") == required
            and all(
                self._foreign_key_exists(
                    "pagamentos_fatura", column, parent, parent_column
                )
                for column, parent, parent_column in foreign_keys
            )
            and self._payment_uniques_valid()
            and self._payment_index_valid()
        )

    def _migration_003_pagamentos_fatura(self):
        required_order = [
            "ID_Pagamento", "Chave_Idempotencia", "ID_Cartao",
            "Competencia_Mes", "Competencia_Ano", "ID_Conta",
            "ID_Transacao", "ID_Usuario", "Valor", "Criado_Em"
        ]
        existing = self._table_columns("pagamentos_fatura")
        row_count = self.connection.execute(
            "SELECT COUNT(*) AS total FROM pagamentos_fatura"
        ).fetchone()["total"]
        missing = set(required_order) - existing
        extra = existing - set(required_order)

        if row_count and (missing - {"Criado_Em"} or extra):
            raise DatabaseError(
                "Tabela pagamentos_fatura incompleta contém dados e não pode "
                "ser reconstruída sem perda; "
                f"colunas ausentes={sorted(missing)}, extras={sorted(extra)}."
            )

        if not self._pagamentos_p0_valid():
            objects = self._dependent_objects(
                "pagamentos_fatura",
                {"idx_pagamento_fatura_competencia"}
            )
            self.connection.execute(
                "DROP TABLE IF EXISTS pagamentos_fatura__p0_new"
            )
            self._create_pagamentos_fatura_table(
                "pagamentos_fatura__p0_new"
            )

            if row_count:
                copy_columns = [
                    column for column in required_order if column in existing
                ]
                self.connection.execute(
                    f"INSERT INTO pagamentos_fatura__p0_new "
                    f"({', '.join(copy_columns)}) "
                    f"SELECT {', '.join(copy_columns)} "
                    "FROM pagamentos_fatura"
                )

            copied = self.connection.execute(
                "SELECT COUNT(*) AS total FROM pagamentos_fatura__p0_new"
            ).fetchone()["total"]
            if copied != row_count:
                raise sqlite3.DatabaseError(
                    "Contagem de pagamentos divergiu durante a migração."
                )

            self.connection.execute("DROP TABLE pagamentos_fatura")
            self.connection.execute(
                "ALTER TABLE pagamentos_fatura__p0_new "
                "RENAME TO pagamentos_fatura"
            )
            for obj in objects:
                self.connection.execute(obj["sql"])

        if self._index_definition("idx_pagamento_fatura_competencia"):
            if not self._payment_index_valid():
                self.connection.execute(
                    "DROP INDEX idx_pagamento_fatura_competencia"
                )

        self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_pagamento_fatura_competencia
            ON pagamentos_fatura(
                ID_Cartao,
                Competencia_Mes,
                Competencia_Ano,
                ID_Usuario
            )
        """)

    def _run_migrations(self):
        self._ensure_migration_table()
        migrations = (
            (
                1,
                "legacy_columns",
                self._migration_001_legacy_columns,
                self._legacy_columns_valid,
                False,
            ),
            (
                2,
                "p0_transacoes_agendamento",
                self._migration_002_transacoes_agendamento,
                self._transacoes_p0_valid,
                True,
            ),
            (
                3,
                "p0_pagamentos_fatura",
                self._migration_003_pagamentos_fatura,
                self._pagamentos_p0_valid,
                True,
            ),
        )
        for migration in migrations:
            self._run_migration(*migration)

    # =====================================================
    # TRANSACTIONS
    # =====================================================
    def _in_transaction(self):
        return getattr(self._thread_local, "manual_transaction", False)

    def _set_transaction(self, value):
        self._thread_local.manual_transaction = value

    def begin(self, immediate=False):
        if self._in_transaction():
            raise RuntimeError("Já existe uma transação ativa nesta conexão.")

        self._set_transaction(True)
        try:
            self.connection.execute(
                "BEGIN IMMEDIATE" if immediate else "BEGIN"
            )
        except Exception:
            self._set_transaction(False)
            raise

    def commit(self):
        if getattr(self._thread_local, "shared_connection", False):
            raise RuntimeError(
                "Participante não pode confirmar a conexão compartilhada."
            )
        self.connection.commit()
        self._set_transaction(False)

    def rollback(self):
        if getattr(self._thread_local, "shared_connection", False):
            raise RuntimeError(
                "Participante não pode reverter a conexão compartilhada."
            )
        self.connection.rollback()
        self._set_transaction(False)

    def _bind_connection(self, connection):
        """Vincula temporariamente sem fechar a conexão pertencente ao model."""
        self._ensure_connection()
        if self._in_transaction():
            raise RuntimeError(
                "Participante já possui uma transação ativa."
            )

        previous = self._connection_state()
        self._thread_local.connection = connection
        self._thread_local.manual_transaction = True
        self._thread_local.shared_connection = True
        return previous

    def _connection_state(self):
        self._ensure_connection()
        return {
            "connection": self._thread_local.connection,
            "manual_transaction": self._in_transaction(),
            "shared_connection": getattr(
                self._thread_local,
                "shared_connection",
                False
            ),
        }

    def _restore_connection_state(self, state):
        self._thread_local.connection = state["connection"]
        self._thread_local.manual_transaction = state["manual_transaction"]
        self._thread_local.shared_connection = state["shared_connection"]

    @contextmanager
    def unit_of_work(self, *participants, immediate=True):
        """
        Executa vários models na mesma conexão e transação SQLite.

        Todos os participantes recebem o mesmo estado transacional, impedindo
        commits automáticos em execute_query/execute_insert até o commit final.
        """
        models = []
        for model in (self, *participants):
            if all(model is not existing for existing in models):
                models.append(model)

        if self._in_transaction():
            raise RuntimeError(
                "Unidade de trabalho aninhada não é suportada."
            )

        for model in models[1:]:
            if model._in_transaction():
                raise RuntimeError(
                    "Participante já possui uma transação ativa."
                )

        connection = self.connection
        owner_state = self._connection_state()
        participant_states = []

        try:
            self.begin(immediate=immediate)

            for model in models[1:]:
                state = model._bind_connection(connection)
                participant_states.append((model, state))

            yield connection

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            for model, state in reversed(participant_states):
                model._restore_connection_state(state)
            self._restore_connection_state(owner_state)

    # =====================================================
    # QUERY
    # =====================================================
    def execute_query(self, query, params=None):
        try:
            cur = self.connection.cursor()
            cur.execute(query, params or ())

            if not self._in_transaction():
                self.connection.commit()

            return cur

        except sqlite3.Error as e:
            logging.error(
                f"Erro Query: {query} | {str(e)}"
            )

            raise DatabaseError(
                str(e),
                query,
                params,
                e
            )

    def execute_insert(self, query, params=None):
        try:
            cur = self.connection.cursor()
            cur.execute(query, params or ())

            if not self._in_transaction():
                self.connection.commit()

            return cur.lastrowid

        except sqlite3.Error as e:
            logging.error(
                f"Erro Insert: {query} | {str(e)}"
            )

            raise DatabaseError(
                str(e),
                query,
                params,
                e
            )

    def fetch_all(self, query, params=None):
        try:
            cur = self.connection.cursor()
            cur.execute(query, params or ())

            return [
                dict(row)
                for row in cur.fetchall()
            ]

        except sqlite3.Error as e:
            logging.error(
                f"Erro FetchAll: {query} | {str(e)}"
            )

            raise DatabaseError(
                str(e),
                query,
                params,
                e
            )

    def fetch_one(self, query, params=None):
        try:
            cur = self.connection.cursor()
            cur.execute(query, params or ())

            row = cur.fetchone()

            return dict(row) if row else None

        except sqlite3.Error as e:
            logging.error(
                f"Erro FetchOne: {query} | {str(e)}"
            )

            raise DatabaseError(
                str(e),
                query,
                params,
                e
            )


class DatabaseError(Exception):
    """
    Exceção padrão da camada de persistência.
    Guarda query, parâmetros e erro original para facilitar debug.
    """

    def __init__(
        self,
        message,
        query=None,
        params=None,
        original_exception=None
    ):
        super().__init__(message)

        self.message = message
        self.query = query
        self.params = params
        self.original_exception = original_exception

        self.error_type = (
            type(original_exception).__name__
            if original_exception is not None
            else None
        )

    def __str__(self):
        return self.message

    def to_dict(self):
        return {
            "message": self.message,
            "query": self.query,
            "params": self.params,
            "error_type": self.error_type,
        }
