# services/backup_service.py

import logging
import os
from typing import List, Dict

from core.config import DB_PATH
from core.operation_result import operation_result
from models.backup_model import BackupModel



logger = logging.getLogger(__name__)


class BackupService:
    """
    Camada de serviço responsável por:
    - validações de negócio
    - orquestração entre View e Model
    - regras de segurança
    """

    def __init__(self, db_path=None):
        self.model = BackupModel(db_path or DB_PATH)

    # =====================================================
    # BACKUP
    # =====================================================
    def _ensure_admin_permission(self, usuario_logado: dict):
        nivel = (usuario_logado or {}).get("Nivel_Acesso", "")

        if str(nivel).lower() != "admin":
            logger.warning(
                "Tentativa não autorizada de operação global de backup. "
                "Usuario=%s",
                (usuario_logado or {}).get("ID_Usuario")
            )
            raise PermissionError(
                "Apenas administradores podem acessar backup e restauração."
            )

    def criar_backup(
        self,
        destino: str,
        senha: str,
        usuario_logado: dict = None
    ) -> dict:

        try:
            self._ensure_admin_permission(usuario_logado)

        except PermissionError as exc:
            return operation_result(False, "NAO_AUTORIZADO", str(exc))

        if not senha or len(senha) < 4:
            return operation_result(
                False,
                "DADOS_INVALIDOS",
                "A senha deve ter pelo menos 4 caracteres."
            )

        if not destino or not os.path.isdir(destino):
            return operation_result(False, "DADOS_INVALIDOS", "Destino inválido.")

        try:
            caminho = self.model.criar_backup(destino, senha)

            logger.info(f"[BACKUP] Criado com sucesso: {caminho}")

            return operation_result(
                True,
                "OK",
                "Backup gerado com sucesso.",
                {"arquivo": caminho}
            )

        except Exception:
            logger.exception("[BACKUP] Erro ao criar")
            return operation_result(
                False,
                "ERRO_INTERNO",
                "Falha ao criar backup."
            )

    # =====================================================
    # RESTAURAÇÃO
    # =====================================================
    def restaurar_backup(
        self,
        arquivo: str,
        senha: str,
        usuario_logado: dict = None
    ):

        try:
            self._ensure_admin_permission(usuario_logado)

        except PermissionError as exc:
            return operation_result(False, "NAO_AUTORIZADO", str(exc))

        if not os.path.exists(arquivo):
            return operation_result(
                False,
                "NAO_ENCONTRADO",
                "Arquivo de backup não encontrado."
            )

        if not senha:
            return operation_result(False, "DADOS_INVALIDOS", "Senha obrigatória.")

        # 🔥 valida antes
        if not self.model.validar_backup(arquivo, senha):
            return operation_result(
                False,
                "DADOS_INVALIDOS",
                "Senha inválida ou backup corrompido."
            )

        pasta_backup = os.path.dirname(arquivo)
        backup_preventivo = None

        try:
            logger.info("[RESTORE] Criando backup preventivo...")

            backup_preventivo = self.model.criar_backup(
                pasta_backup,
                senha,
                prefixo="backup_pre_restore"
            )
            if os.path.abspath(backup_preventivo) == os.path.abspath(arquivo):
                raise RuntimeError(
                    "Backup preventivo colidiu com o arquivo de origem."
                )

        except Exception:
            logger.exception("[RESTORE] Falha no backup preventivo")
            return operation_result(
                False,
                "ERRO_BACKUP_PREVENTIVO",
                "A restauração foi cancelada porque o backup preventivo falhou."
            )

        # 🔥 restauração real
        try:
            self.model.restaurar_backup(arquivo, senha)

            logger.info(f"[RESTORE] Sucesso: {arquivo}")

            return operation_result(
                True,
                "OK",
                "Backup restaurado com sucesso.",
                {"backup_preventivo": backup_preventivo}
            )

        except Exception:
            logger.exception("[RESTORE] Erro ao restaurar")
            return operation_result(
                False,
                "ERRO_INTERNO",
                "Falha ao restaurar backup; o banco foi preservado.",
                {"backup_preventivo": backup_preventivo}
            )

    # =====================================================
    # VALIDAÇÃO
    # =====================================================
    def validar_backup(
        self,
        arquivo: str,
        senha: str,
        usuario_logado: dict = None
    ) -> bool:

        try:
            self._ensure_admin_permission(usuario_logado)
        except PermissionError:
            return False

        if not os.path.exists(arquivo):
            return False

        try:
            return self.model.validar_backup(arquivo, senha)

        except Exception:
            logger.exception("[VALIDAR] Erro")
            return False

    # =====================================================
    # LISTAGEM
    # =====================================================
    def listar_backups(
        self,
        diretorio: str,
        usuario_logado: dict = None
    ) -> List[Dict]:

        try:
            self._ensure_admin_permission(usuario_logado)
        except PermissionError:
            return []

        if not os.path.isdir(diretorio):
            return []

        try:
            return self.model.listar_backups(diretorio)

        except Exception:
            logger.exception("[LISTAR] Erro")
            return []

    # =====================================================
    # EXCLUSÃO
    # =====================================================
    def excluir_backup(self, arquivo: str, usuario_logado: dict = None):

        self._ensure_admin_permission(usuario_logado)

        if not os.path.exists(arquivo):
            raise FileNotFoundError("Arquivo não encontrado.")

        try:
            self.model.excluir_backup(arquivo)

            logger.info(f"[DELETE] Backup removido: {arquivo}")

            return True

        except Exception as e:
            logger.exception("[DELETE] Erro")
            raise Exception(f"Falha ao excluir backup: {str(e)}")
