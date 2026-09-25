# -*- coding: utf-8 -*-
import sqlite3
import logging
import os
import threading
import calendar
from datetime import datetime
from contextlib import contextmanager

from core.config import get_db_path

logging.basicConfig(
    filename="database.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class Database:
    _initialized_paths = set()
    _initializing_paths = {}
    _initialization_lock = threading.Lock()

    def __init__(self, db_name=None):
        self.db_name = db_name or get_db_path()
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
            self._backup_before_invoice_cycle_correction()
            self.create_tables()
            succeeded = True
        finally:
            with Database._initialization_lock:
                if succeeded:
                    Database._initialized_paths.add(key)
                Database._initializing_paths.pop(key, None)
                event.set()

    def _backup_before_invoice_cycle_correction(self):
        """Cria e valida uma cópia antes da migração financeira v7."""
        if self.db_name == ":memory:" or not os.path.isfile(self.db_name):
            return
        tables = {
            row[0] for row in self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "schema_migrations" not in tables or "usuarios" not in tables:
            return
        if self.connection.execute(
            "SELECT 1 FROM schema_migrations WHERE Versao = 7"
        ).fetchone():
            return
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup_path = f"{self.db_name}.pre-migration-v7-{stamp}.bak"
        destination = sqlite3.connect(backup_path)
        try:
            self.connection.backup(destination)
            check = destination.execute("PRAGMA integrity_check").fetchone()[0]
            if check != "ok":
                raise sqlite3.DatabaseError(
                    f"Backup pré-migração inválido: {check}"
                )
        except Exception:
            destination.close()
            try:
                os.unlink(backup_path)
            except OSError:
                pass
            raise
        destination.close()

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
    Idioma TEXT DEFAULT 'pt_BR',
    Ativo INTEGER NOT NULL DEFAULT 1 CHECK (Ativo IN (0, 1))
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
    ID_Fatura INTEGER,
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
    Tipo_Movimento TEXT NOT NULL DEFAULT 'COMPRA'
        CHECK (Tipo_Movimento IN (
            'COMPRA','CREDITO','ESTORNO','AJUSTE','ENCARGO','PAGAMENTO'
        )),
    ID_Lancamento_Origem INTEGER,

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
-- CICLOS DE FATURA
-- =====================================================
CREATE TABLE IF NOT EXISTS faturas_cartao (
    ID_Fatura INTEGER PRIMARY KEY AUTOINCREMENT,
    ID_Cartao INTEGER NOT NULL,
    Competencia_Mes INTEGER NOT NULL,
    Competencia_Ano INTEGER NOT NULL,
    ID_Usuario INTEGER NOT NULL,
    Status TEXT NOT NULL DEFAULT 'ABERTA'
        CHECK (Status IN ('ABERTA','FECHADA','PAGA')),
    Data_Fechamento TEXT NOT NULL,
    Data_Vencimento TEXT,
    Fechada_Em TEXT,
    Paga_Em TEXT,
    Criado_Em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Atualizado_Em TEXT,
    UNIQUE(ID_Cartao, Competencia_Mes, Competencia_Ano, ID_Usuario),
    FOREIGN KEY(ID_Cartao) REFERENCES credito(ID_Cartao) ON DELETE CASCADE,
    FOREIGN KEY(ID_Usuario) REFERENCES usuarios(ID_Usuario) ON DELETE CASCADE
);

-- =====================================================
-- PAGAMENTOS DE FATURA / IDEMPOTÊNCIA
-- =====================================================
CREATE TABLE IF NOT EXISTS pagamentos_fatura (
    ID_Pagamento INTEGER PRIMARY KEY AUTOINCREMENT,
    Chave_Idempotencia TEXT NOT NULL UNIQUE,
    ID_Cartao INTEGER NOT NULL,
    ID_Fatura INTEGER,
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
-- DADOS FISCAIS INFORMADOS PELA FONTE PAGADORA
-- =====================================================
CREATE TABLE IF NOT EXISTS informes_fiscais (
    ID_Informe INTEGER PRIMARY KEY AUTOINCREMENT,
    ID_Usuario INTEGER NOT NULL,
    Ano_Calendario INTEGER NOT NULL CHECK (Ano_Calendario BETWEEN 1900 AND 9999),
    Fonte_Nome TEXT NOT NULL,
    Fonte_Documento TEXT NOT NULL,
    Natureza_Rendimento TEXT NOT NULL,
    Rendimentos_Tributaveis REAL NOT NULL DEFAULT 0 CHECK (Rendimentos_Tributaveis >= 0),
    Previdencia_Oficial REAL NOT NULL DEFAULT 0 CHECK (Previdencia_Oficial >= 0),
    Previdencia_Complementar REAL NOT NULL DEFAULT 0 CHECK (Previdencia_Complementar >= 0),
    Pensao_Alimenticia REAL NOT NULL DEFAULT 0 CHECK (Pensao_Alimenticia >= 0),
    IRRF REAL NOT NULL DEFAULT 0 CHECK (IRRF >= 0),
    Parcela_Isenta_65 REAL NOT NULL DEFAULT 0 CHECK (Parcela_Isenta_65 >= 0),
    Diarias_Ajudas_Custo REAL NOT NULL DEFAULT 0 CHECK (Diarias_Ajudas_Custo >= 0),
    Pensao_Molestia_Grave REAL NOT NULL DEFAULT 0 CHECK (Pensao_Molestia_Grave >= 0),
    Lucros_Dividendos REAL NOT NULL DEFAULT 0 CHECK (Lucros_Dividendos >= 0),
    Valores_Empresario REAL NOT NULL DEFAULT 0 CHECK (Valores_Empresario >= 0),
    Indenizacoes REAL NOT NULL DEFAULT 0 CHECK (Indenizacoes >= 0),
    Isentos_Outros REAL NOT NULL DEFAULT 0 CHECK (Isentos_Outros >= 0),
    Decimo_Terceiro REAL NOT NULL DEFAULT 0 CHECK (Decimo_Terceiro >= 0),
    IRRF_Decimo_Terceiro REAL NOT NULL DEFAULT 0 CHECK (IRRF_Decimo_Terceiro >= 0),
    Exclusivos_Outros REAL NOT NULL DEFAULT 0 CHECK (Exclusivos_Outros >= 0),
    RRA_Meses INTEGER NOT NULL DEFAULT 0 CHECK (RRA_Meses >= 0),
    RRA_Tributacao TEXT NOT NULL DEFAULT 'EXCLUSIVA'
        CHECK (RRA_Tributacao IN ('EXCLUSIVA','AJUSTE_ANUAL')),
    RRA_Rendimentos REAL NOT NULL DEFAULT 0 CHECK (RRA_Rendimentos >= 0),
    RRA_Previdencia_Oficial REAL NOT NULL DEFAULT 0 CHECK (RRA_Previdencia_Oficial >= 0),
    RRA_Pensao_Alimenticia REAL NOT NULL DEFAULT 0 CHECK (RRA_Pensao_Alimenticia >= 0),
    RRA_IRRF REAL NOT NULL DEFAULT 0 CHECK (RRA_IRRF >= 0),
    RRA_Despesas_Judiciais REAL NOT NULL DEFAULT 0 CHECK (RRA_Despesas_Judiciais >= 0),
    Informacoes_Complementares TEXT,
    Criado_Em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Atualizado_Em TEXT,
    UNIQUE(ID_Usuario, Ano_Calendario, Fonte_Documento),
    FOREIGN KEY(ID_Usuario) REFERENCES usuarios(ID_Usuario) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_informes_fiscais_usuario_ano
ON informes_fiscais(ID_Usuario, Ano_Calendario);

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
CREATE INDEX IF NOT EXISTS idx_cpf
ON pessoa_fisica(CPF)
WHERE CPF IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_cnpj
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
            required.issubset(self._table_columns("pagamentos_fatura"))
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

    def _migration_004_user_access(self):
        self._add_column_if_missing('usuarios', 'Ativo',
                                    'INTEGER NOT NULL DEFAULT 1 CHECK (Ativo IN (0, 1))')

    def _user_access_valid(self):
        if 'Ativo' not in self._table_columns('usuarios'):
            return False
        return self.connection.execute(
            'SELECT 1 FROM usuarios WHERE Ativo IS NULL OR Ativo NOT IN (0, 1) LIMIT 1'
        ).fetchone() is None

    def _migration_005_payee_documents(self):
        # Remove somente a restrição global antiga; nenhum registro é regravado.
        for table, document in (('pessoa_fisica', 'CPF'), ('pessoa_juridica', 'CNPJ')):
            index = 'idx_' + document.lower()
            self.connection.execute(f'DROP INDEX IF EXISTS {index}')
            self.connection.execute(
                f'CREATE INDEX {index} ON {table}({document}) WHERE {document} IS NOT NULL')
            for event in ('INSERT', 'UPDATE'):
                self.connection.execute(f"""
                    CREATE TRIGGER IF NOT EXISTS scoped_{document.lower()}_{event.lower()}
                    BEFORE {event} ON {table}
                    WHEN NEW.{document} IS NOT NULL AND EXISTS (
                        SELECT 1 FROM {table} d
                        JOIN favorecido f ON f.ID_Favorecido = d.ID_Favorecido
                        JOIN favorecido alvo ON alvo.ID_Favorecido = NEW.ID_Favorecido
                        WHERE d.{document} = NEW.{document}
                          AND d.ID_Favorecido <> NEW.ID_Favorecido
                          AND f.ID_Usuario = alvo.ID_Usuario
                    )
                    BEGIN SELECT RAISE(ABORT, 'Documento já cadastrado para este usuário'); END
                """)

    def _payee_documents_valid(self):
        for table, document in (('pessoa_fisica', 'CPF'), ('pessoa_juridica', 'CNPJ')):
            indexes = self.connection.execute(f'PRAGMA index_list({table})').fetchall()
            if not any(row['name'] == 'idx_' + document.lower() and not row['unique']
                       for row in indexes):
                return False
            for event in ('insert', 'update'):
                name = f'scoped_{document.lower()}_{event}'
                if not self.connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'trigger' AND name = ?", (name,)
                ).fetchone():
                    return False
        return True

    def _migration_006_invoice_cycles(self):
        self._add_column_if_missing(
            'lancamentos', 'Tipo_Movimento',
            "TEXT NOT NULL DEFAULT 'COMPRA'"
        )
        self._add_column_if_missing(
            'lancamentos', 'ID_Lancamento_Origem', 'INTEGER'
        )
        self._add_column_if_missing(
            'lancamentos', 'ID_Fatura', 'INTEGER'
        )
        self._add_column_if_missing(
            'pagamentos_fatura', 'ID_Fatura', 'INTEGER'
        )
        self.connection.execute("""
            UPDATE lancamentos
            SET Tipo_Movimento = CASE
                WHEN Tipo_Movimento = 'PAGAMENTO' THEN 'PAGAMENTO'
                WHEN Valor < 0 THEN 'CREDITO'
                WHEN Tipo_Movimento IN (
                    'COMPRA','CREDITO','ESTORNO','AJUSTE','ENCARGO','PAGAMENTO'
                )
                    THEN Tipo_Movimento
                ELSE 'COMPRA'
            END
        """)
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS faturas_cartao (
                ID_Fatura INTEGER PRIMARY KEY AUTOINCREMENT,
                ID_Cartao INTEGER NOT NULL,
                Competencia_Mes INTEGER NOT NULL,
                Competencia_Ano INTEGER NOT NULL,
                ID_Usuario INTEGER NOT NULL,
                Status TEXT NOT NULL DEFAULT 'ABERTA'
                    CHECK (Status IN ('ABERTA','FECHADA','PAGA')),
                Data_Fechamento TEXT NOT NULL,
                Fechada_Em TEXT,
                Paga_Em TEXT,
                Criado_Em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                Atualizado_Em TEXT,
                UNIQUE(ID_Cartao, Competencia_Mes, Competencia_Ano, ID_Usuario),
                FOREIGN KEY(ID_Cartao) REFERENCES credito(ID_Cartao)
                    ON DELETE CASCADE,
                FOREIGN KEY(ID_Usuario) REFERENCES usuarios(ID_Usuario)
                    ON DELETE CASCADE
            )
        """)
        self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_faturas_cartao_usuario_status
            ON faturas_cartao(ID_Usuario, ID_Cartao, Status)
        """)
        for tabela in ('lancamentos', 'pagamentos_fatura'):
            for evento in ('INSERT', 'UPDATE'):
                nome = f'validar_fatura_{tabela}_{evento.lower()}'
                self.connection.execute(f"""
                    CREATE TRIGGER IF NOT EXISTS {nome}
                    BEFORE {evento} ON {tabela}
                    WHEN NEW.ID_Fatura IS NOT NULL
                     AND NOT EXISTS (
                        SELECT 1
                        FROM faturas_cartao f
                        WHERE f.ID_Fatura = NEW.ID_Fatura
                          AND f.ID_Cartao = NEW.ID_Cartao
                          AND f.Competencia_Mes = NEW.Competencia_Mes
                          AND f.Competencia_Ano = NEW.Competencia_Ano
                          AND f.ID_Usuario = NEW.ID_Usuario
                     )
                    BEGIN
                        SELECT RAISE(
                            ABORT,
                            'Fatura incompatível com cartão e competência'
                        );
                    END
                """)
        self.connection.execute("""
            INSERT OR IGNORE INTO faturas_cartao (
                ID_Cartao, Competencia_Mes, Competencia_Ano, ID_Usuario,
                Status, Data_Fechamento, Fechada_Em, Paga_Em
            )
            SELECT
                base.ID_Cartao,
                base.Competencia_Mes,
                base.Competencia_Ano,
                base.ID_Usuario,
                CASE
                    WHEN EXISTS (
                        SELECT 1 FROM pagamentos_fatura p
                        WHERE p.ID_Cartao = base.ID_Cartao
                          AND p.Competencia_Mes = base.Competencia_Mes
                          AND p.Competencia_Ano = base.Competencia_Ano
                          AND p.ID_Usuario = base.ID_Usuario
                    ) THEN 'PAGA'
                    WHEN date(
                        printf(
                            '%04d-%02d-%02d',
                            base.Competencia_Ano,
                            base.Competencia_Mes,
                            MIN(
                                c.Dia_Fechamento,
                                CAST(strftime(
                                    '%d',
                                    date(
                                        printf(
                                            '%04d-%02d-01',
                                            base.Competencia_Ano,
                                            base.Competencia_Mes
                                        ),
                                        '+1 month', '-1 day'
                                    )
                                ) AS INTEGER)
                            )
                        )
                    ) < date('now') THEN 'FECHADA'
                    ELSE 'ABERTA'
                END,
                printf(
                    '%04d-%02d-%02d',
                    base.Competencia_Ano,
                    base.Competencia_Mes,
                    MIN(
                        c.Dia_Fechamento,
                        CAST(strftime(
                            '%d',
                            date(
                                printf(
                                    '%04d-%02d-01',
                                    base.Competencia_Ano,
                                    base.Competencia_Mes
                                ),
                                '+1 month', '-1 day'
                            )
                        ) AS INTEGER)
                    )
                ),
                CASE
                    WHEN date(
                        printf(
                            '%04d-%02d-%02d',
                            base.Competencia_Ano,
                            base.Competencia_Mes,
                            MIN(
                                c.Dia_Fechamento,
                                CAST(strftime(
                                    '%d',
                                    date(
                                        printf(
                                            '%04d-%02d-01',
                                            base.Competencia_Ano,
                                            base.Competencia_Mes
                                        ),
                                        '+1 month', '-1 day'
                                    )
                                ) AS INTEGER)
                            )
                        )
                    ) < date('now') THEN CURRENT_TIMESTAMP
                END,
                CASE WHEN EXISTS (
                    SELECT 1 FROM pagamentos_fatura p
                    WHERE p.ID_Cartao = base.ID_Cartao
                      AND p.Competencia_Mes = base.Competencia_Mes
                      AND p.Competencia_Ano = base.Competencia_Ano
                      AND p.ID_Usuario = base.ID_Usuario
                ) THEN CURRENT_TIMESTAMP END
            FROM (
                SELECT DISTINCT
                    ID_Cartao, Competencia_Mes, Competencia_Ano, ID_Usuario
                FROM lancamentos
                WHERE ID_Usuario IS NOT NULL
                UNION
                SELECT DISTINCT
                    ID_Cartao, Competencia_Mes, Competencia_Ano, ID_Usuario
                FROM pagamentos_fatura
            ) base
            JOIN credito c ON c.ID_Cartao = base.ID_Cartao
        """)
        self.connection.execute("""
            UPDATE lancamentos
            SET ID_Fatura = (
                SELECT f.ID_Fatura
                FROM faturas_cartao f
                WHERE f.ID_Cartao = lancamentos.ID_Cartao
                  AND f.Competencia_Mes = lancamentos.Competencia_Mes
                  AND f.Competencia_Ano = lancamentos.Competencia_Ano
                  AND f.ID_Usuario = lancamentos.ID_Usuario
            )
            WHERE ID_Fatura IS NULL
        """)
        self.connection.execute("""
            UPDATE pagamentos_fatura
            SET ID_Fatura = (
                SELECT f.ID_Fatura
                FROM faturas_cartao f
                WHERE f.ID_Cartao = pagamentos_fatura.ID_Cartao
                  AND f.Competencia_Mes = pagamentos_fatura.Competencia_Mes
                  AND f.Competencia_Ano = pagamentos_fatura.Competencia_Ano
                  AND f.ID_Usuario = pagamentos_fatura.ID_Usuario
            )
            WHERE ID_Fatura IS NULL
        """)

    def _invoice_cycles_valid(self):
        columns = self._table_columns('lancamentos')
        invoice_columns = self._table_columns('faturas_cartao')
        return (
            {
                'Tipo_Movimento', 'ID_Lancamento_Origem', 'ID_Fatura'
            }.issubset(columns)
            and 'ID_Fatura' in self._table_columns('pagamentos_fatura')
            and {
                'ID_Fatura', 'ID_Cartao', 'Competencia_Mes',
                'Competencia_Ano', 'ID_Usuario', 'Status',
                'Data_Fechamento', 'Fechada_Em', 'Paga_Em'
            }.issubset(invoice_columns)
            and self._index_definition('idx_faturas_cartao_usuario_status')
            is not None
            and all(
                self.connection.execute(
                    "SELECT 1 FROM sqlite_master "
                    "WHERE type = 'trigger' AND name = ?",
                    (f'validar_fatura_{tabela}_{evento}',),
                ).fetchone()
                for tabela in ('lancamentos', 'pagamentos_fatura')
                for evento in ('insert', 'update')
            )
        )

    @staticmethod
    def _cycle_dates(mes, ano, dia_fechamento, dia_vencimento):
        ultimo = calendar.monthrange(int(ano), int(mes))[1]
        fechamento = datetime(
            int(ano), int(mes), min(int(dia_fechamento), ultimo)
        ).date()
        venc_mes, venc_ano = int(mes), int(ano)
        if int(dia_vencimento) <= int(dia_fechamento):
            venc_mes += 1
            if venc_mes == 13:
                venc_mes, venc_ano = 1, venc_ano + 1
        ultimo_venc = calendar.monthrange(venc_ano, venc_mes)[1]
        vencimento = datetime(
            venc_ano, venc_mes, min(int(dia_vencimento), ultimo_venc)
        ).date()
        return fechamento.isoformat(), vencimento.isoformat()

    def _migration_007_invoice_cycle_correction(self):
        self._add_column_if_missing(
            'faturas_cartao', 'Data_Vencimento', 'TEXT'
        )
        ciclos = self.connection.execute("""
            SELECT f.ID_Fatura, f.Competencia_Mes, f.Competencia_Ano,
                   f.Status, c.Dia_Fechamento, c.Dia_Vencimento
            FROM faturas_cartao f
            JOIN credito c ON c.ID_Cartao = f.ID_Cartao
        """).fetchall()
        hoje = datetime.now().date().isoformat()
        for ciclo in ciclos:
            fechamento, vencimento = self._cycle_dates(
                ciclo['Competencia_Mes'], ciclo['Competencia_Ano'],
                ciclo['Dia_Fechamento'], ciclo['Dia_Vencimento'],
            )
            self.connection.execute("""
                UPDATE faturas_cartao
                SET Data_Fechamento = ?, Data_Vencimento = ?,
                    Fechada_Em = CASE
                        WHEN Status IN ('FECHADA','PAGA') THEN ?
                        ELSE NULL
                    END,
                    Atualizado_Em = CURRENT_TIMESTAMP
                WHERE ID_Fatura = ?
            """, (fechamento, vencimento, fechamento, ciclo['ID_Fatura']))

        # Remove somente a materialização duplicada da test.9 quando o
        # pagamento oficial correspondente é inequívoco.
        self.connection.execute("""
            DELETE FROM lancamentos
            WHERE Tipo_Movimento = 'PAGAMENTO'
              AND EXISTS (
                SELECT 1
                FROM pagamentos_fatura p
                WHERE p.ID_Transacao = lancamentos.ID_Transacao
                  AND p.ID_Usuario = lancamentos.ID_Usuario
                  AND p.ID_Cartao = lancamentos.ID_Cartao
                  AND p.Competencia_Mes = lancamentos.Competencia_Mes
                  AND p.Competencia_Ano = lancamentos.Competencia_Ano
                  AND ABS(p.Valor - ABS(lancamentos.Valor)) < 0.005
              )
        """)

        self.connection.execute("""
            UPDATE faturas_cartao AS f
            SET Status = CASE
                    WHEN COALESCE((
                        SELECT SUM(p.Valor) FROM pagamentos_fatura p
                        WHERE p.ID_Fatura = f.ID_Fatura
                    ), 0) > 0
                     AND COALESCE((
                        SELECT SUM(p.Valor) FROM pagamentos_fatura p
                        WHERE p.ID_Fatura = f.ID_Fatura
                    ), 0) + 0.005 >= MAX(COALESCE((
                        SELECT SUM(l.Valor) FROM lancamentos l
                        WHERE l.ID_Fatura = f.ID_Fatura
                          AND l.Tipo_Movimento <> 'PAGAMENTO'
                    ), 0), 0)
                    THEN 'PAGA'
                    WHEN date(f.Data_Fechamento) < date(?) THEN 'FECHADA'
                    ELSE 'ABERTA'
                END,
                Paga_Em = CASE
                    WHEN COALESCE((
                        SELECT SUM(p.Valor) FROM pagamentos_fatura p
                        WHERE p.ID_Fatura = f.ID_Fatura
                    ), 0) > 0
                    THEN COALESCE(Paga_Em, CURRENT_TIMESTAMP)
                    ELSE NULL
                END,
                Atualizado_Em = CURRENT_TIMESTAMP
        """, (hoje,))

    def _invoice_cycle_correction_valid(self):
        if 'Data_Vencimento' not in self._table_columns('faturas_cartao'):
            return False
        if self.connection.execute("""
            SELECT 1 FROM faturas_cartao
            WHERE Data_Vencimento IS NULL OR Data_Fechamento IS NULL
            LIMIT 1
        """).fetchone():
            return False
        if self.connection.execute("""
            SELECT 1
            FROM lancamentos l
            JOIN pagamentos_fatura p
              ON p.ID_Transacao = l.ID_Transacao
             AND p.ID_Usuario = l.ID_Usuario
             AND p.ID_Cartao = l.ID_Cartao
             AND p.Competencia_Mes = l.Competencia_Mes
             AND p.Competencia_Ano = l.Competencia_Ano
             AND ABS(p.Valor - ABS(l.Valor)) < 0.005
            WHERE l.Tipo_Movimento = 'PAGAMENTO'
            LIMIT 1
        """).fetchone():
            return False
        return self.connection.execute(
            'PRAGMA integrity_check'
        ).fetchone()[0] == 'ok'

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
            (4, 'user_access_status', self._migration_004_user_access, self._user_access_valid, False),
            (5, 'payee_documents_by_user', self._migration_005_payee_documents,
             self._payee_documents_valid, False),
            (6, 'invoice_cycles_and_movements', self._migration_006_invoice_cycles,
             self._invoice_cycles_valid, False),
            (7, 'invoice_cycle_correction',
             self._migration_007_invoice_cycle_correction,
             self._invoice_cycle_correction_valid, False),
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
