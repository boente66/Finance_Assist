from pathlib import Path

from core.config import (
    CONFIG_PATH,
    DATA_DIR,
    DB_PATH,
    RUNTIME_ENVIRONMENT,
    clone_database_if_missing,
    get_app_data_dir,
)
from database.database import Database
from services.backup_service import BackupService


def test_suite_usa_diretorio_temporario_exclusivo():
    data_dir = Path(DATA_DIR).resolve()
    project_db = Path(__file__).resolve().parents[2] / "financeiro.db"

    assert RUNTIME_ENVIRONMENT == "test"
    assert Path(CONFIG_PATH).resolve().is_relative_to(data_dir)
    assert Path(DB_PATH).resolve().is_relative_to(data_dir)
    assert Path(DB_PATH).resolve() != project_db.resolve()


def test_desenvolvimento_e_producao_nao_compartilham_diretorio(tmp_path):
    production = get_app_data_dir("production", environ={}, home=tmp_path)
    development = get_app_data_dir(
        "development",
        environ={},
        home=tmp_path,
        base_dir=tmp_path,
    )

    assert Path(production) == (tmp_path / ".financeassist").resolve()
    assert Path(development) == (tmp_path / ".financeassist-development").resolve()
    assert production != development


def test_session_preserva_caminho_configurado(tmp_path):
    from core.session import Session

    custom_path = str(tmp_path / "dados-existentes.db")
    Session.load_config({"db_path": custom_path})
    assert Session.get_config("db_path") == custom_path


def test_copia_legado_uma_vez_sem_sobrescrever_destino(tmp_path):
    import sqlite3

    source = tmp_path / "financeiro.db"
    destination = tmp_path / "development" / "financeiro.db"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE marcador (valor TEXT NOT NULL)")
        connection.execute("INSERT INTO marcador VALUES ('legado')")

    assert clone_database_if_missing(source, destination) is True
    with sqlite3.connect(destination) as connection:
        assert connection.execute("SELECT valor FROM marcador").fetchone()[0] == "legado"
        connection.execute("UPDATE marcador SET valor = 'desenvolvimento'")

    assert clone_database_if_missing(source, destination) is False
    with sqlite3.connect(destination) as connection:
        assert connection.execute("SELECT valor FROM marcador").fetchone()[0] == "desenvolvimento"


def test_inicializacao_padrao_e_backup_usam_banco_de_teste():
    database = Database()
    backup = BackupService()
    try:
        assert Path(database.db_name).resolve() == Path(DB_PATH).resolve()
        assert Path(backup.model.database_path).resolve() == Path(DB_PATH).resolve()
    finally:
        backup.model.db.close()
        database.close()


def test_reabertura_atualiza_schema_sem_apagar_dados(tmp_path):
    path = str(tmp_path / "banco-existente.db")
    database = Database(path)
    user_id = database.execute_insert(
        """
        INSERT INTO usuarios (Nome, Email, Login, Senha, Nivel_Acesso)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("Usuário preservado", "preservado@example.com", "preservado", "hash", "usuario"),
    )
    database.close()

    reopened = Database(path)
    try:
        row = reopened.fetch_one(
            "SELECT Nome FROM usuarios WHERE ID_Usuario = ?", (user_id,)
        )
        migrations = reopened.fetch_one(
            "SELECT COUNT(*) AS total FROM schema_migrations"
        )
        assert row["Nome"] == "Usuário preservado"
        assert migrations["total"] >= 3
    finally:
        reopened.close()
