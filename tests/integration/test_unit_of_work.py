import pytest

from database.database import Database


def test_participante_e_vinculado_e_restaurado(db_path):
    owner = Database(db_path)
    participant = Database(db_path)
    owner_connection = owner.connection
    participant_connection = participant.connection

    with owner.unit_of_work(participant):
        assert participant.connection is owner_connection
        assert participant._in_transaction() is True
        with pytest.raises(RuntimeError, match="proprietário"):
            participant.close()
        with pytest.raises(RuntimeError, match="Participante"):
            participant.commit()
        with pytest.raises(RuntimeError, match="Participante"):
            participant.rollback()

    assert owner.connection is owner_connection
    assert participant.connection is participant_connection
    assert participant._in_transaction() is False


def test_fechar_participante_nao_fecha_proprietario(db_path):
    owner = Database(db_path)
    participant = Database(db_path)

    with owner.unit_of_work(participant):
        owner.execute_query(
            "INSERT INTO usuarios (Nome, Login, Senha, Nivel_Acesso) "
            "VALUES ('Owner', 'owner-uow', 'x', 'usuario')"
        )

    participant.close()
    assert owner.fetch_one(
        "SELECT COUNT(*) AS total FROM usuarios"
    )["total"] == 1


def test_participante_continua_utilizavel_depois_da_unidade(db_path):
    owner = Database(db_path)
    participant = Database(db_path)

    with owner.unit_of_work(participant):
        owner.execute_query(
            "INSERT INTO usuarios (Nome, Login, Senha, Nivel_Acesso) "
            "VALUES ('Participante', 'participant-uow', 'x', 'usuario')"
        )

    assert participant.fetch_one(
        "SELECT Nome FROM usuarios WHERE Login = 'participant-uow'"
    )["Nome"] == "Participante"


def test_excecao_restaura_conexoes_e_estados(db_path):
    owner = Database(db_path)
    participant = Database(db_path)
    owner_connection = owner.connection
    participant_connection = participant.connection

    with pytest.raises(RuntimeError, match="falha controlada"):
        with owner.unit_of_work(participant):
            owner.execute_query(
                "INSERT INTO usuarios (Nome, Login, Senha, Nivel_Acesso) "
                "VALUES ('Rollback', 'rollback-uow', 'x', 'usuario')"
            )
            raise RuntimeError("falha controlada")

    assert owner.connection is owner_connection
    assert participant.connection is participant_connection
    assert owner._in_transaction() is False
    assert participant._in_transaction() is False
    assert owner.fetch_one(
        "SELECT COUNT(*) AS total FROM usuarios"
    )["total"] == 0


def test_participante_em_transacao_e_recusado_sem_dano(db_path):
    owner = Database(db_path)
    participant = Database(db_path)
    participant_connection = participant.connection
    participant.begin()

    with pytest.raises(RuntimeError, match="Participante já possui"):
        with owner.unit_of_work(participant):
            pass

    assert participant.connection is participant_connection
    assert participant._in_transaction() is True
    assert owner._in_transaction() is False
    participant.rollback()
    assert participant.fetch_one("SELECT 1 AS valor")["valor"] == 1


def test_unidade_aninhada_e_recusada_com_erro_claro(db_path):
    owner = Database(db_path)
    participant = Database(db_path)

    with owner.unit_of_work(participant):
        with pytest.raises(RuntimeError, match="aninhada não é suportada"):
            with owner.unit_of_work(participant):
                pass

        with pytest.raises(RuntimeError, match="aninhada não é suportada"):
            with participant.unit_of_work(owner):
                pass


def test_unico_commit_no_sucesso(db_path):
    owner = Database(db_path)
    participant = Database(db_path)
    events = []
    owner.connection.set_trace_callback(events.append)

    with owner.unit_of_work(participant):
        participant.execute_query(
            "INSERT INTO usuarios (Nome, Login, Senha, Nivel_Acesso) "
            "VALUES ('Commit', 'commit-uow', 'x', 'usuario')"
        )

    assert sum(event.strip().upper() == "COMMIT" for event in events) == 1


def test_unico_rollback_na_falha(db_path):
    owner = Database(db_path)
    participant = Database(db_path)
    events = []
    owner.connection.set_trace_callback(events.append)

    with pytest.raises(RuntimeError):
        with owner.unit_of_work(participant):
            participant.execute_query(
                "INSERT INTO usuarios (Nome, Login, Senha, Nivel_Acesso) "
                "VALUES ('Rollback', 'rollback-trace', 'x', 'usuario')"
            )
            raise RuntimeError("falha")

    assert sum(event.strip().upper() == "ROLLBACK" for event in events) == 1
