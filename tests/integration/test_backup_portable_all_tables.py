"""Backups portáveis preservam todo o estado financeiro entre bancos isolados."""
import json
from pathlib import Path

import pytest

from database.database import Database
from models.backup_model import BackupModel
from utilitarios.crypto_util import decrypt_bytes
from test_database_all_tables import populated_database, TABLES


def test_portable_encrypted_backup_restores_all_business_tables(populated_database, tmp_path):
    source = BackupModel(populated_database)
    destination = BackupModel(str(tmp_path / 'outra_maquina.db'))
    from services.account_service import AccountService
    account = source.db.fetch_one('SELECT * FROM contas ORDER BY ID_Conta LIMIT 1')
    AccountService(populated_database).ajustar_saldo(
        account['ID_Conta'], account['Saldo_Atual'] + 1, account['ID_Usuario']
    )
    assert set(source.BACKUP_TABLES) == set(TABLES) - {'schema_migrations','recuperacao_senha'}
    before = {table: source.db.fetch_all(f'SELECT * FROM {table} ORDER BY 1')
              for table in source.BACKUP_TABLES}
    filename = source.criar_backup(str(tmp_path), 'senha-portavel-compartilhada')
    assert not list(tmp_path.glob('*.partial'))
    payload = json.loads(decrypt_bytes(json.loads(Path(filename).read_text())['payload'], 'senha-portavel-compartilhada'))
    assert 'recuperacao_senha' not in payload
    assert 'schema_migrations' not in payload
    assert destination.restaurar_backup(filename, 'senha-portavel-compartilhada')
    for table, rows in before.items():
        assert destination.db.fetch_all(f'SELECT * FROM {table} ORDER BY 1') == rows, table
    assert destination.db.fetch_all('PRAGMA foreign_key_check') == []
    assert destination.db.fetch_one('PRAGMA integrity_check')['integrity_check'] == 'ok'


def test_interrupted_publication_does_not_leave_complete_backup(populated_database, tmp_path, monkeypatch):
    source = BackupModel(populated_database)
    def fail(*args):
        raise OSError('destino indisponível')
    monkeypatch.setattr('models.backup_model.os.replace', fail)
    with pytest.raises(OSError, match='destino indisponível'):
        source.criar_backup(str(tmp_path), 'senha-portavel')
    assert not list(tmp_path.glob('*.kp'))
    assert not list(tmp_path.glob('*.partial'))
