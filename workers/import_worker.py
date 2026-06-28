# -*- coding: utf-8 -*-
import logging
from typing import Optional

from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class ImportWorker(QThread):
    """
    Worker responsável por executar a importação em segundo plano.

    Fluxo:
    PainelAccount
        ↓
    ImportWorker
        ↓
    IAImportController.importar_arquivo()
        ↓
    ImportacaoService

    Observação:
    - Este worker NÃO salva no banco.
    - Ele apenas retorna os lançamentos reconhecidos.
    - A gravação só deve acontecer após confirmação na tela temporária.
    """

    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(
        self,
        controller,
        caminho_arquivo: str,
        id_conta: int,
        parent: Optional[object] = None
    ):
        super().__init__(parent)

        self.controller = controller
        self.caminho_arquivo = caminho_arquivo
        self.id_conta = id_conta
        self._cancelado = False

    def run(self):
        try:
            if self._cancelado:
                return

            self.progress.emit(0, "Iniciando importação...")

            lancamentos = self.controller.importar_arquivo(
                caminho_arquivo=self.caminho_arquivo,
                id_conta=self.id_conta,
                progress_callback=self._emit_progress
            )

            if self._cancelado:
                return

            self.progress.emit(100, "Importação finalizada.")

            self.finished.emit(
                lancamentos if isinstance(lancamentos, list) else []
            )

        except Exception as e:
            logger.exception("Erro no ImportWorker")
            self.error.emit(str(e))

    def cancel(self):
        self._cancelado = True
        self.progress.emit(0, "Importação cancelada.")

    def _emit_progress(self, progresso, mensagem=None):
        if self._cancelado:
            return

        try:
            progresso = int(progresso)
        except Exception:
            progresso = 0

        mensagem = mensagem or "Importando..."

        self.progress.emit(progresso, mensagem)