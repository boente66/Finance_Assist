import logging
from database.database import DatabaseError
from models.user_model import UserModel
from models.password_reset_model import PasswordResetModel
from services.email_service import EmailService


logger = logging.getLogger(__name__)


class UserService:
    """
    Serviço responsável pelas regras de negócio relacionadas a usuários.
    """

    MAX_ADMINS = 3

    def __init__(self):
        self.user_model = UserModel()
        self.password_reset_model = PasswordResetModel()

    # ======================================================
    # UTILITÁRIOS INTERNOS
    # ======================================================

    def _count_admins(self) -> int:
        return self.user_model.count_admins()

    def _normalize_access_level(self, nivel: str) -> str:
        return (nivel or "usuario").lower()

    def _ensure_admin_permission(self, usuario_logado: dict):
        if not usuario_logado or usuario_logado.get("Nivel_Acesso", "").lower() != "admin":
            raise PermissionError("Apenas administradores podem executar esta ação.")

    # ======================================================
    # AUTENTICAÇÃO
    # ======================================================

    def authenticate_user(self, login: str, senha: str):
        try:
            return self.user_model.authenticate_user(login, senha)
        except DatabaseError:
            logger.exception("Erro ao autenticar usuário")
            return None

    # ======================================================
    # REGISTRO
    # ======================================================

    def register_user(self, user_data: dict, usuario_logado: dict = None) -> bool:
        try:
            if not user_data.get("Login") or not user_data.get("Email") or not user_data.get("Senha"):
                raise ValueError("Dados obrigatórios ausentes.")

            if self.user_model.user_exists(
                user_data.get("Login"),
                user_data.get("Email")
            ):
                return False

            total_admins = self._count_admins()
            nivel = self._normalize_access_level(user_data.get("Nivel_Acesso"))

            # Primeiro usuário vira admin automaticamente
            if total_admins == 0:
                user_data["Nivel_Acesso"] = "admin"

            else:
                # Se já existe admin → somente admin pode registrar
                self._ensure_admin_permission(usuario_logado)

                if nivel == "admin":
                    if total_admins >= self.MAX_ADMINS:
                        raise ValueError("Limite máximo de administradores atingido.")
                    user_data["Nivel_Acesso"] = "admin"
                else:
                    user_data["Nivel_Acesso"] = "usuario"

            self.user_model.add_user(user_data)
            return True

        except (DatabaseError, PermissionError, ValueError):
            logger.exception("Erro ao registrar usuário")
            return False

    # ======================================================
    # CONSULTAS
    # ======================================================

    def get_user_details(self, login: str):
        try:
            return self.user_model.get_user_by_login(login)
        except DatabaseError:
            logger.exception("Erro ao obter detalhes do usuário")
            return None

    def get_user_by_id(self, id_usuario: int):
        try:
            return self.user_model.get_user_by_id(id_usuario)
        except DatabaseError:
            logger.exception("Erro ao buscar usuário por ID")
            return None

    def get_all_users(self):
        try:
            return self.user_model.get_all_users()
        except DatabaseError:
            logger.exception("Erro ao listar usuários")
            return []

    def update_user(
        self,
        id_usuario_alvo: int,
        user_data: dict,
        usuario_logado: dict
    ) -> bool:
        try:
            self._ensure_admin_permission(usuario_logado)

            usuario_alvo = self.get_user_by_id(id_usuario_alvo)
            if not usuario_alvo:
                return False

            if not user_data.get("Nome") or not user_data.get("Login") or not user_data.get("Email"):
                raise ValueError("Dados obrigatórios ausentes.")

            existente = self.user_model.fetch_one(
                """
                SELECT ID_Usuario
                FROM usuarios
                WHERE (Login = ? OR Email = ?)
                  AND ID_Usuario <> ?
                """,
                (
                    user_data.get("Login"),
                    user_data.get("Email"),
                    id_usuario_alvo
                )
            )

            if existente:
                return False

            novo_nivel = self._normalize_access_level(
                user_data.get("Nivel_Acesso")
            )
            total_admins = self._count_admins()

            if novo_nivel == "admin" and usuario_alvo.get("Nivel_Acesso", "").lower() != "admin":
                if total_admins >= self.MAX_ADMINS:
                    raise ValueError("Limite máximo de administradores atingido.")

            if usuario_alvo.get("Nivel_Acesso", "").lower() == "admin" and novo_nivel != "admin":
                if total_admins <= 1:
                    raise ValueError("O sistema deve possuir pelo menos um administrador.")

            user_data["Nivel_Acesso"] = novo_nivel
            self.user_model.update_user(id_usuario_alvo, user_data)
            return True

        except (DatabaseError, PermissionError, ValueError):
            logger.exception("Erro ao atualizar usuário")
            return False

    # ======================================================
    # ALTERAÇÃO DE NÍVEL
    # ======================================================

    def update_access_level(self, id_usuario_alvo: int, novo_nivel: str, usuario_logado: dict) -> bool:
        try:
            self._ensure_admin_permission(usuario_logado)

            usuario_alvo = self.get_user_by_id(id_usuario_alvo)
            if not usuario_alvo:
                return False

            novo_nivel = self._normalize_access_level(novo_nivel)
            total_admins = self._count_admins()

            if novo_nivel == "admin":
                if total_admins >= self.MAX_ADMINS:
                    raise ValueError("Limite máximo de administradores atingido.")

            if usuario_alvo.get("Nivel_Acesso", "").lower() == "admin" and novo_nivel != "admin":
                if total_admins <= 1:
                    raise ValueError("O sistema deve possuir pelo menos um administrador.")

            self.user_model.update_access_level(id_usuario_alvo, novo_nivel)
            return True

        except (DatabaseError, PermissionError, ValueError):
            logger.exception("Erro ao atualizar nível de acesso")
            return False

    def allow_editor_access(self, login: str) -> bool:
        usuario = self.get_user_details(login)
        return bool(usuario)

    # ======================================================
    # EXCLUSÃO
    # ======================================================

    def delete_user(self, id_usuario_alvo: int, usuario_logado: dict) -> bool:
        try:
            self._ensure_admin_permission(usuario_logado)

            usuario_alvo = self.get_user_by_id(id_usuario_alvo)
            if not usuario_alvo:
                return False

            total_admins = self._count_admins()

            if usuario_alvo.get("Nivel_Acesso", "").lower() == "admin" and total_admins <= 1:
                raise ValueError("Não é possível excluir o único administrador.")

            if usuario_logado.get("ID_Usuario") == id_usuario_alvo and total_admins <= 1:
                raise ValueError("Não é possível remover o único administrador.")

            self.user_model.delete_user(id_usuario_alvo)
            return True

        except (DatabaseError, PermissionError, ValueError):
            logger.exception("Erro ao excluir usuário")
            return False

            

    def delete_own_account(self, id_usuario: int, usuario_logado: dict) -> bool:
        """
        Permite que um usuário exclua sua própria conta a qualquer momento.
        """
        try:
            if not usuario_logado or usuario_logado.get("ID_Usuario") != id_usuario:
                raise PermissionError("Somente o próprio usuário pode excluir sua conta.")

            usuario_alvo = self.get_user_by_id(id_usuario)
            if not usuario_alvo:
                return False

            self.user_model.delete_user(id_usuario)
            return True

        except (DatabaseError, PermissionError):
            logger.exception("Erro ao excluir conta do usuário")
            return False

    # ======================================================
    # SENHA
    # ======================================================

    def change_password(self, id_usuario: int, nova_senha: str) -> bool:
        try:
            if not nova_senha:
                raise ValueError("Senha inválida.")

            self.user_model.change_password(id_usuario, nova_senha)
            return True

        except (DatabaseError, ValueError):
            logger.exception("Erro ao alterar senha")
            return False

    def reset_password_with_token(self, token: str, nova_senha: str) -> bool:
        try:
            registro = self.password_reset_model.get_valid_token(token)

            if not registro:
                return False

            id_usuario = registro["ID_Usuario"]

            self.user_model.change_password(id_usuario, nova_senha)

            # Marca token como usado
            self.password_reset_model.mark_token_used(token)

            return True

        except DatabaseError:
            logger.exception("Erro ao redefinir senha via token")
            return False

    # ======================================================
    # EXISTÊNCIA
    # ======================================================

    def user_exists(self, login: str, email: str = None) -> bool:
        try:
            return self.user_model.user_exists(login, email or login)
        except DatabaseError:
            logger.exception("Erro ao verificar existência do usuário")
            return False

    # ======================================================
    # PREFERÊNCIAS
    # ======================================================

    def get_preferences(self, id_usuario: int):
        try:
            return self.user_model.get_preferences(id_usuario)
        except DatabaseError:
            logger.exception("Erro ao obter preferências")
            return None

    def update_preferences(self, id_usuario: int, tema: str, idioma: str) -> bool:
        try:
            self.user_model.update_preferences(id_usuario, tema, idioma)
            return True
        except DatabaseError:
            logger.exception("Erro ao atualizar preferências")
            return False

    # ======================================================
    # SOLICITAÇÃO DE RECUPERAÇÃO
    # ======================================================

    def request_password_reset(self, login_ou_email: str) -> bool:
        """
        Solicita recuperação de senha.
        Não revela se usuário existe (boa prática de segurança).
        """

        try:
            usuario = self.user_model.get_user_by_login(login_ou_email)

            # Segurança: nunca revelar existência
            if not usuario:
                logger.info("Solicitação de reset para login inexistente.")
                return True

            # Limpa tokens expirados antes de gerar novo
            self.password_reset_model.cleanup_expired_tokens()

            token = self.password_reset_model.create_token(usuario["ID_Usuario"])

            corpo = f"""
Olá, {usuario['Nome']}

Você solicitou a recuperação de senha.

Código de recuperação:
{token}

Esse código expira em 30 minutos.

Se você não solicitou, ignore este e-mail.
"""

            enviado = EmailService.enviar_email(
                destinatario=usuario["Email"],
                assunto="Recuperação de Senha - Controle Financeiro",
                corpo=corpo
            )

            if not enviado:
                logger.error("Falha ao enviar e-mail de recuperação.")
                return False

            return True

        except Exception:
            logger.exception("Erro ao solicitar recuperação de senha")
            return False

    

    def encerrar_usuario(self, id_usuario: int, usuario_logado: dict) -> bool:
        """
        Marca um usuário como inativo (encerrado).
        Apenas administradores podem encerrar usuários.
        """
        try:
            self._ensure_admin_permission(usuario_logado)

            usuario_alvo = self.get_user_by_id(id_usuario)
            if not usuario_alvo:
                return False

            total_admins = self._count_admins()

            if usuario_alvo.get("Nivel_Acesso", "").lower() == "admin" and total_admins <= 1:
                raise ValueError("Não é possível encerrar o único administrador.")

            self.user_model.delete_user(id_usuario)
            return True

        except (DatabaseError, PermissionError, ValueError):
            logger.exception("Erro ao encerrar usuário")
            return False