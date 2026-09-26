import logging
from typing import List, Optional, Callable

from core.session import Session
from services.importacao_service import ImportacaoService
from services.transaction_service import TransactionService
from services.reconciliacao_importacao_service import ReconciliacaoImportacaoService


logger = logging.getLogger(__name__)


class IAImportController:
    STATUS_NOVO = ReconciliacaoImportacaoService.NOVO
    STATUS_DUPLICADO = ReconciliacaoImportacaoService.DUPLICADO
    STATUS_POSSIVEL_DUPLICADO = (
        ReconciliacaoImportacaoService.POSSIVEL_DUPLICADO
    )
    """
    Controller responsável por:

    - Receber arquivo da View
    - Chamar ImportacaoService
    - Retornar dados para tela temporária
    - Persistir lançamentos confirmados
    """

    def __init__(self):
        self.import_service = ImportacaoService()
        self.transaction_service = TransactionService()


    def get_id_usuario(self):
        usuario = Session.get_usuario()
        if not usuario:
            raise PermissionError("Usuário não autenticado.")
        return usuario["ID_Usuario"]

    # ==========================================================
    # IMPORTAR ARQUIVO (FASE 1 → Tela Temporária)
    # ==========================================================
    def importar_arquivo(
        self,
        caminho_arquivo: str,
        id_conta: int,
        progress_callback: Optional[Callable] = None
    ) -> List[dict]:
        id_usuario = self.get_id_usuario()

        if not caminho_arquivo:
            raise ValueError("Arquivo não informado.")

        if not id_usuario or not id_conta:
            raise ValueError("Usuário ou conta inválidos.")

        try:
            dados = self.import_service.importar(
                caminho_arquivo=caminho_arquivo,
                id_usuario=id_usuario,
                id_conta=id_conta,
                progress_callback=progress_callback
            )

            return dados if isinstance(dados, list) else []

        except Exception:
            logger.exception("Erro ao importar arquivo")
            raise

    # ==========================================================
    # SALVAR LANÇAMENTOS CONFIRMADOS (FASE 2 → Banco)
    # ==========================================================
    def salvar_lancamentos_confirmados(
        self,
        lista_lancamentos: List[dict]
    ) -> int:
        if not lista_lancamentos:
            return 0

        try:
            total = self.transaction_service.salvar_lote_importado(
                lista_lancamentos,
                self.get_id_usuario(),
            )

            return total

        except Exception:
            logger.exception("Erro ao salvar lançamentos importados")
            raise
    
    def importar_comprovante_pdf(self, caminho_arquivo: str, id_conta: int) -> Optional[bytes]:
        id_usuario = self.get_id_usuario()

        if not caminho_arquivo:
            raise ValueError("Arquivo não informado.")

        if not id_usuario or not id_conta:
            raise ValueError("Usuário ou conta inválidos.")

        try:
            comprovante = self.import_service.importar_comprovante_pdf(
                caminho_arquivo=caminho_arquivo
            )

            return comprovante

        except Exception:
            logger.exception("Erro ao importar comprovante PDF")
            raise
