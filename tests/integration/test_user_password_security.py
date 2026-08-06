import hashlib
import os
from contextlib import contextmanager

from database.database import Database
from models.user_model import UserModel
from services.user_services import UserService


STRONG_PASSWORD = "frase-senha-segura"


def _model_without_database():
    return UserModel.__new__(UserModel)


def _temporary_user_model(path):
    model = UserModel.__new__(UserModel)
    Database.__init__(model, str(path))
    return model


def test_pbkdf2_usa_salt_unico_e_valida_em_tempo_constante():
    model = _model_without_database()
    first = model.hash_senha(STRONG_PASSWORD)
    second = model.hash_senha(STRONG_PASSWORD)

    assert first.startswith("pbkdf2_sha256$600000$")
    assert second.startswith("pbkdf2_sha256$600000$")
    assert first != second
    assert model.verificar_senha(STRONG_PASSWORD, first) is True
    assert model.verificar_senha("senha-incorreta", first) is False


def test_hash_legado_continua_valido_e_eh_migrado_no_login():
    model = _model_without_database()
    legacy = hashlib.sha256(STRONG_PASSWORD.encode("utf-8")).hexdigest()
    changed = []
    model._get_user_credentials_by_login = lambda _login: {
        "ID_Usuario": 7,
        "Nome": "Usuário",
        "Login": "usuario",
        "Senha": legacy,
    }
    model.change_password = lambda user_id, password: changed.append(
        (user_id, password)
    )

    result = model.authenticate_user("usuario", STRONG_PASSWORD)

    assert result["ID_Usuario"] == 7
    assert "Senha" not in result
    assert changed == [(7, STRONG_PASSWORD)]


def test_hash_invalido_falha_fechado_sem_excecao():
    model = _model_without_database()
    invalid_hashes = (
        "",
        "sha256$600000$salt$digest",
        "pbkdf2_sha256$invalido$salt$digest",
        "pbkdf2_sha256$999999999$c2FsdA==$ZGlnZXN0",
        "nao-e-um-hash",
    )
    assert all(
        model.verificar_senha(STRONG_PASSWORD, encoded) is False
        for encoded in invalid_hashes
    )


def test_consultas_publicas_nao_selecionam_hash_da_senha():
    model = _model_without_database()
    queries = []
    model.fetch_one = lambda query, _params: queries.append(query) or None

    model.get_user_by_login("usuario")
    model.get_user_by_id(7)

    assert len(queries) == 2
    assert all("Senha" not in query for query in queries)


def test_edicao_com_nova_senha_gera_um_unico_update_atomico():
    model = _model_without_database()
    calls = []
    model.execute_query = lambda query, params: calls.append((query, params))
    data = {
        "Nome": "Usuário",
        "DataNascimento": "1990-05-15",
        "Sexo": "Outro",
        "CPF": "",
        "Telefone": "",
        "Celular": "",
        "Email": "usuario@example.com",
        "Login": "usuario",
        "Nivel_Acesso": "usuario",
        "Senha": STRONG_PASSWORD,
    }

    model.update_user(7, data)

    assert len(calls) == 1
    query, params = calls[0]
    assert "Senha = ?" in query
    assert params[-1] == 7
    assert params[-2].startswith("pbkdf2_sha256$600000$")
    assert STRONG_PASSWORD not in params


def test_edicao_sem_nova_senha_preserva_hash_existente():
    model = _model_without_database()
    calls = []
    model.execute_query = lambda query, params: calls.append((query, params))
    data = {
        "Nome": "Usuário",
        "Email": "usuario@example.com",
        "Login": "usuario",
        "Nivel_Acesso": "usuario",
        "Senha": "",
    }

    model.update_user(7, data)

    assert "Senha = ?" not in calls[0][0]
    assert calls[0][1][-1] == 7


class UserModelStub:
    def __init__(self):
        self.added = []
        self.updated = []

    def user_exists(self, *_args):
        return False

    def count_admins(self):
        return 1

    def add_user(self, data):
        self.added.append(dict(data))

    def get_user_by_id(self, _user_id):
        return {"ID_Usuario": 7, "Nivel_Acesso": "usuario"}

    def fetch_one(self, *_args):
        return None

    def update_user(self, user_id, data):
        self.updated.append((user_id, dict(data)))


def _service_with_model(model):
    service = UserService.__new__(UserService)
    service.user_model = model
    return service


def test_service_rejeita_senha_fraca_antes_da_persistencia():
    model = UserModelStub()
    service = _service_with_model(model)
    data = {
        "Nome": "Usuário",
        "Email": "usuario@example.com",
        "Login": "usuario",
        "Senha": "curta",
        "Nivel_Acesso": "usuario",
    }

    assert service.register_user(data, {"Nivel_Acesso": "admin"}) is False
    assert model.added == []


def test_service_autoriza_e_encaminha_senha_segura_na_edicao():
    model = UserModelStub()
    service = _service_with_model(model)
    data = {
        "Nome": "Usuário",
        "Email": "usuario@example.com",
        "Login": "usuario",
        "Senha": STRONG_PASSWORD,
        "Nivel_Acesso": "usuario",
    }

    assert service.update_user(7, data, {"Nivel_Acesso": "admin"}) is True
    assert model.updated == [(7, data)]


class ResetModelStub:
    def __init__(self):
        self.used = []
        self.shared = False

    def get_valid_token(self, token):
        assert self.shared is True
        return {"ID_Usuario": 7} if token == "token-valido" else None

    def mark_token_used(self, token):
        assert self.shared is True
        self.used.append(token)


class PasswordModelStub:
    def __init__(self, reset_model):
        self.reset_model = reset_model
        self.changed = []

    @contextmanager
    def unit_of_work(self, participant):
        assert participant is self.reset_model
        self.reset_model.shared = True
        try:
            yield
        finally:
            self.reset_model.shared = False

    def change_password(self, user_id, password):
        assert self.reset_model.shared is True
        self.changed.append((user_id, password))


def test_reset_consumo_do_token_e_senha_ocorrem_na_mesma_unidade_de_trabalho():
    reset_model = ResetModelStub()
    password_model = PasswordModelStub(reset_model)
    service = _service_with_model(password_model)
    service.password_reset_model = reset_model

    assert service.reset_password_with_token("token-valido", STRONG_PASSWORD)
    assert password_model.changed == [(7, STRONG_PASSWORD)]
    assert reset_model.used == ["token-valido"]


def test_fluxo_real_em_sqlite_temporario_migra_legado_e_atualiza_senha(tmp_path):
    db_path = tmp_path / "security.sqlite"
    model = _temporary_user_model(db_path)
    data = {
        "Nome": "Usuário",
        "DataNascimento": "1990-05-15",
        "Sexo": "Outro",
        "CPF": "",
        "Telefone": "",
        "Celular": "",
        "Email": "usuario@example.com",
        "Login": "usuario",
        "Senha": STRONG_PASSWORD,
        "Nivel_Acesso": "admin",
    }

    model.add_user(data)
    stored = model.connection.execute(
        "SELECT ID_Usuario, Senha FROM usuarios WHERE Login = ?", ("usuario",)
    ).fetchone()
    user_id = stored["ID_Usuario"]
    assert stored["Senha"].startswith("pbkdf2_sha256$600000$")
    assert "Senha" not in model.authenticate_user("usuario", STRONG_PASSWORD)

    legacy = hashlib.sha256(STRONG_PASSWORD.encode("utf-8")).hexdigest()
    model.connection.execute(
        "UPDATE usuarios SET Senha = ? WHERE ID_Usuario = ?", (legacy, user_id)
    )
    model.connection.commit()
    assert model.authenticate_user("usuario", STRONG_PASSWORD)["ID_Usuario"] == user_id
    migrated = model.connection.execute(
        "SELECT Senha FROM usuarios WHERE ID_Usuario = ?", (user_id,)
    ).fetchone()["Senha"]
    assert migrated.startswith("pbkdf2_sha256$600000$")

    updated = dict(data, Senha="outra-frase-segura")
    model.update_user(user_id, updated)
    assert model.authenticate_user("usuario", STRONG_PASSWORD) is None
    assert model.authenticate_user("usuario", "outra-frase-segura")["ID_Usuario"] == user_id
    model.close()
    Database._initialized_paths.discard(os.path.abspath(str(db_path)))
