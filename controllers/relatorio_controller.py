import logging
from core.session import Session
from services.relatorio_service import RelatorioService

logger = logging.getLogger(__name__)


class RelatorioController:
    """Controlador responsável por gerar relatórios financeiros."""

    def __init__(self):
        self.service = RelatorioService()


    def _get_usuario_id(self):
        usuario = Session.get_usuario()
        if not usuario:
            raise RuntimeError("Usuário não autenticado.")
        return usuario["ID_Usuario"]

    def anos_disponiveis(self):
        return self.service.anos_disponiveis(self._get_usuario_id())

    # ---------------------------------------------------------
    # RELATÓRIO DIÁRIO
    # ---------------------------------------------------------
    def relatorio_diario(self, dias):
        id_usuario = self._get_usuario_id()
        try:
            return self.service.relatorio_diario(dias, id_usuario)
        except Exception as e:
            logger.error("Erro ao gerar relatório diário: %s", e, exc_info=True)
            return None

    # ---------------------------------------------------------
    # RELATÓRIO ANUAL
    # ---------------------------------------------------------
    def relatorio_anual(self, ano):
        id_usuario = self._get_usuario_id()
        try:
            return self.service.relatorio_anual(ano, id_usuario)
        except Exception as e:
            logger.error("Erro ao gerar relatório anual: %s", e, exc_info=True)
            return None

    # ---------------------------------------------------------
    # INFORME DE RENDIMENTOS (DADOS)
    # ---------------------------------------------------------
    def informe_rendimentos(self, ano):
        id_usuario = self._get_usuario_id()
        try:
            return self.service.informe_rendimentos(ano, id_usuario)
        except Exception as e:
            logger.error("Erro ao gerar informe de rendimentos: %s", e, exc_info=True)
            return None

    # ---------------------------------------------------------
    # INFORME DE RENDIMENTOS (TEXTO FORMATADO)
    # ---------------------------------------------------------
    def gerar_texto_informe(self, ano):
        id_usuario = self._get_usuario_id()
        try:
            return self.service.gerar_texto_informe(id_usuario, ano)
        except Exception as e:
            logger.error("Erro ao formatar texto do informe: %s", e, exc_info=True)
            return None
