import base64
import hashlib
import hmac
import logging
import os
from database.database import Database


class UserModel(Database):

    PASSWORD_ALGORITHM = "pbkdf2_sha256"
    PASSWORD_ITERATIONS = 600_000
    PASSWORD_SALT_BYTES = 16
    PASSWORD_DIGEST_BYTES = 32

    def __init__(self):
        super().__init__()

    # ==================================================
    # UTILITÁRIOS
    # ==================================================

    def hash_senha(self, senha: str) -> str:
        """Gera hash adaptativo com salt único, sem alterar o schema."""
        if not isinstance(senha, str):
            raise TypeError("A senha deve ser texto.")

        salt = os.urandom(self.PASSWORD_SALT_BYTES)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            senha.encode("utf-8"),
            salt,
            self.PASSWORD_ITERATIONS,
            dklen=self.PASSWORD_DIGEST_BYTES,
        )
        return "$".join((
            self.PASSWORD_ALGORITHM,
            str(self.PASSWORD_ITERATIONS),
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(digest).decode("ascii"),
        ))

    @staticmethod
    def _is_legacy_sha256(encoded: str) -> bool:
        if not isinstance(encoded, str) or len(encoded) != 64:
            return False
        try:
            int(encoded, 16)
            return True
        except ValueError:
            return False

    def verificar_senha(self, senha: str, encoded: str) -> bool:
        """Valida hashes atuais e SHA-256 legado em tempo constante."""
        if not isinstance(senha, str) or not isinstance(encoded, str):
            return False

        if self._is_legacy_sha256(encoded):
            legacy = hashlib.sha256(senha.encode("utf-8")).hexdigest()
            return hmac.compare_digest(legacy, encoded.lower())

        try:
            algoritmo, iteracoes_texto, salt_b64, digest_b64 = encoded.split("$", 3)
            iteracoes = int(iteracoes_texto)
            if algoritmo != self.PASSWORD_ALGORITHM:
                return False
            if iteracoes < 1 or iteracoes > 2_000_000:
                return False
            salt = base64.b64decode(salt_b64, validate=True)
            esperado = base64.b64decode(digest_b64, validate=True)
            if not salt or len(esperado) != self.PASSWORD_DIGEST_BYTES:
                return False
        except (TypeError, ValueError):
            return False

        calculado = hashlib.pbkdf2_hmac(
            "sha256",
            senha.encode("utf-8"),
            salt,
            iteracoes,
            dklen=len(esperado),
        )
        return hmac.compare_digest(calculado, esperado)

    def _precisa_atualizar_hash(self, encoded: str) -> bool:
        if self._is_legacy_sha256(encoded):
            return True
        try:
            algoritmo, iteracoes, _, _ = encoded.split("$", 3)
            return (
                algoritmo != self.PASSWORD_ALGORITHM
                or int(iteracoes) < self.PASSWORD_ITERATIONS
            )
        except (AttributeError, TypeError, ValueError):
            return False

    def _simular_verificacao_inexistente(self, senha: str):
        """Reduz diferença temporal entre usuário ausente e senha incorreta."""
        calculado = hashlib.pbkdf2_hmac(
            "sha256",
            (senha or "").encode("utf-8"),
            bytes(self.PASSWORD_SALT_BYTES),
            self.PASSWORD_ITERATIONS,
            dklen=self.PASSWORD_DIGEST_BYTES,
        )
        hmac.compare_digest(calculado, bytes(self.PASSWORD_DIGEST_BYTES))

    # ==================================================
    # CRIAÇÃO / AUTENTICAÇÃO
    # ==================================================

    def add_user(self, user_data: dict):

        query = """
        INSERT INTO usuarios (
            Nome, DataNascimento, Sexo, CPF, Telefone, Celular,
            Email, Login, Senha, Nivel_Acesso,
            Tema, Idioma
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        senha_hash = self.hash_senha(user_data["Senha"])

        self.execute_query(query, (
            user_data["Nome"],
            user_data.get("DataNascimento"),
            user_data.get("Sexo"),
            user_data.get("CPF"),
            user_data.get("Telefone"),
            user_data.get("Celular"),
            user_data["Email"],
            user_data["Login"],
            senha_hash,
            user_data.get("Nivel_Acesso", "usuario"),
            user_data.get("Tema", "Claro"),
            user_data.get("Idioma", "pt_BR"),
        ))

    def get_user_by_login(self, login: str):
        query = """
        SELECT ID_Usuario, Nome, DataNascimento, Sexo, CPF, Email, Login,
               Telefone, Celular, Nivel_Acesso, Tema, Idioma
        FROM usuarios
        WHERE Login = ?
        """
        return self.fetch_one(query, (login,))

    def _get_user_credentials_by_login(self, login: str):
        query = "SELECT * FROM usuarios WHERE Login = ?"
        return self.fetch_one(query, (login,))

    def authenticate_user(self, login: str, senha_digitada: str):

        usuario = self._get_user_credentials_by_login(login)
        if not usuario:
            self._simular_verificacao_inexistente(senha_digitada)
            return None

        senha_armazenada = usuario["Senha"]
        if self.verificar_senha(senha_digitada, senha_armazenada):
            if self._precisa_atualizar_hash(senha_armazenada):
                self.change_password(usuario["ID_Usuario"], senha_digitada)
            dados_publicos = dict(usuario)
            dados_publicos.pop("Senha", None)
            return dados_publicos

        return None

    # ==================================================
    # CONSULTAS
    # ==================================================

    def get_all_users(self):
        query = """
        SELECT ID_Usuario, Nome, Email, Login, Nivel_Acesso
        FROM usuarios
        """
        return self.fetch_all(query)

    def get_user_by_id(self, id_usuario: int):
        query = """
        SELECT ID_Usuario, Nome, DataNascimento, Sexo, CPF, Email, Login,
               Telefone, Celular, Nivel_Acesso, Tema, Idioma
        FROM usuarios
        WHERE ID_Usuario = ?
        """
        return self.fetch_one(query, (id_usuario,))

    def count_admins(self):
        """
        Retorna quantidade de usuários com nível admin.
        """
        query = """
        SELECT COUNT(*) as total
        FROM usuarios
        WHERE LOWER(Nivel_Acesso) = 'admin'
        """
        resultado = self.fetch_one(query)
        return resultado["total"] if resultado else 0

    # ==================================================
    # ATUALIZAÇÕES
    # ==================================================

    def update_user(self, id_usuario: int, user_data: dict):
        assignments = [
            "Nome = ?", "DataNascimento = ?", "Sexo = ?", "CPF = ?",
            "Telefone = ?", "Celular = ?", "Email = ?", "Login = ?",
            "Nivel_Acesso = ?",
        ]
        params = [
            user_data["Nome"],
            user_data.get("DataNascimento"),
            user_data.get("Sexo"),
            user_data.get("CPF"),
            user_data.get("Telefone"),
            user_data.get("Celular"),
            user_data["Email"],
            user_data["Login"],
            user_data.get("Nivel_Acesso", "usuario"),
        ]

        nova_senha = user_data.get("Senha")
        if nova_senha:
            assignments.append("Senha = ?")
            params.append(self.hash_senha(nova_senha))

        params.append(id_usuario)
        query = f"""
        UPDATE usuarios
        SET {', '.join(assignments)}
        WHERE ID_Usuario = ?
        """
        self.execute_query(query, tuple(params))

    def update_access_level(self, id_usuario: int, novo_nivel: str):
        """
        Atualiza apenas nível de acesso.
        """
        query = """
        UPDATE usuarios
        SET Nivel_Acesso = ?
        WHERE ID_Usuario = ?
        """
        self.execute_query(query, (novo_nivel, id_usuario))

    def change_password(self, id_usuario: int, nova_senha: str):

        query = "UPDATE usuarios SET Senha = ? WHERE ID_Usuario = ?"

        nova_senha_hash = self.hash_senha(nova_senha)

        self.execute_query(query, (nova_senha_hash, id_usuario))

    def delete_user(self, id_usuario: int):
        """
        Exclusão física do usuário.
        (Recomendado futuramente usar exclusão lógica)
        """
        query = "DELETE FROM usuarios WHERE ID_Usuario = ?"
        self.execute_query(query, (id_usuario,))

    # ==================================================
    # PREFERÊNCIAS
    # ==================================================

    def update_preferences(self, id_usuario: int, tema: str, idioma: str):

        query = """
        UPDATE usuarios
        SET Tema = ?, Idioma = ?
        WHERE ID_Usuario = ?
        """

        self.execute_query(query, (tema, idioma, id_usuario))

    def get_preferences(self, id_usuario: int):

        query = """
        SELECT Tema, Idioma
        FROM usuarios
        WHERE ID_Usuario = ?
        """

        return self.fetch_one(query, (id_usuario,))

    # ==================================================
    # VALIDAÇÃO
    # ==================================================

    def user_exists(self, login=None, email=None) -> bool:

        try:
            if not login and not email:
                raise ValueError("Login ou email devem ser fornecidos")

            query = """
            SELECT ID_Usuario
            FROM usuarios
            WHERE Login = ? OR Email = ?
            """

            resultado = self.fetch_one(query, (login, email))

            return resultado is not None

        except ValueError:
            raise
        except Exception as exc:
            logging.exception(
                "Erro ao verificar existência de usuário: %s", exc
            )
            return False
