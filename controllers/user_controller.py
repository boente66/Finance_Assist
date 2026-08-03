import re
from core.session import Session
from services.user_services import UserService


class UserController:
    def __init__(self):
        self.service = UserService()

    def _get_usuario_id(self):
        usuario = Session.get_usuario()
        if not usuario:
            raise RuntimeError("Usuário não autenticado.")
        return usuario["ID_Usuario"]
        

    # =============================
    # AUTENTICAÇÃO
    # =============================
    def authenticate_user(self, login, senha):
        return self.service.authenticate_user(login, senha)
    # =============================
    # REGISTRO
    # =============================
    def register_user(self, user_data: dict) -> bool:
        return self.service.register_user(
            user_data,
            Session.get_usuario()
        )
    # =============================
    # CONSULTAS
    # =============================
    def get_user_details(self, login):
        return self.service.get_user_details(login)

    # ============================
    # BUSCA POR ID
    # ============================
    def get_user_by_id(self, id_usuario):
        return self.service.get_user_by_id(id_usuario)

    def get_all_users(self):
        return self.service.get_all_users()
    # =============================
    # ATUALIZAÇÃO / EXCLUSÃO
    # =============================
    def update_user(self, id_usuario, user_data: dict) -> bool:
        return self.service.update_user(
            id_usuario,
            user_data,
            Session.get_usuario()
        )

    def update_own_profile(self, user_data: dict) -> bool:
        """Atualiza somente os dados do usuário autenticado."""
        id_usuario = self._get_usuario_id()
        return self.service.update_own_profile(
            id_usuario,
            user_data,
            Session.get_usuario(),
        )

    def delete_user(self, id_usuario) -> bool:
        return self.service.delete_user(
            id_usuario,
            Session.get_usuario()
        )
    # =============================
    # SENHA (DIRETA – ADMIN)
    # =============================
    def change_password(self, nova_senha) -> bool:
        id_usuario = self._get_usuario_id()
        return self.service.change_password(id_usuario, nova_senha)
    # =============================
    # RECUPERAÇÃO DE SENHA (TOKEN)
    # =============================
    def reset_password_with_token(self, token, nova_senha) -> bool:
        return self.service.reset_password_with_token(token, nova_senha)
    # =============================
    # EXISTÊNCIA
    # =============================
    def user_exists(self, login, email=None) -> bool:
        return self.service.user_exists(login, email)
    # =============================
    # PERMISSÕES
    # =============================
    def allow_editor_access(self, login) -> bool:
        return self.service.allow_editor_access(login)
    # =============================
    # PREFERÊNCIAS
    # =============================
    def get_preferences(self):
        id_usuario = self._get_usuario_id()
        return self.service.get_preferences(id_usuario)

    def update_preferences(self, tema, idioma) -> bool:
        id_usuario = self._get_usuario_id()
        return self.service.update_preferences(id_usuario, tema, idioma)
    def request_password_reset(self, login_ou_email):
        return self.service.request_password_reset(login_ou_email)


   # =============================
   # EXCLUIR USUÁRIO (AUTODESTRUIÇÃO)
   # =============================
    def delete_own_account(self, senha) -> bool:
        id_usuario = self._get_usuario_id()
        return self.service.delete_own_account(id_usuario, senha)
