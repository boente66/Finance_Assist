# -*- coding: utf-8 -*-
import logging
import threading
from typing import Optional

from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class ImportCancelledError(Exception):
    """Interrompe cooperativamente uma importação entre suas etapas."""


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
    stopped = pyqtSignal()

    def __init__(
        self,
        controller,
        caminho_arquivo: str,
        id_conta: int,
        parent: Optional[object] = None,
        tipo_destino: str = "conta",
        senha_pdf: str | None = None,
    ):
        super().__init__(parent)

        self.controller = controller
        self.caminho_arquivo = caminho_arquivo
        self.id_conta = id_conta
        self.tipo_destino = tipo_destino
        self.senha_pdf = senha_pdf
        self._cancel_event = threading.Event()

    def run(self):
        try:
            self._check_cancelled()
            self._emit_progress(0, "Iniciando importação...")

            if self.tipo_destino == "cartao":
                lancamentos = self.controller.importar_arquivo_fatura(
                    caminho_arquivo=self.caminho_arquivo,
                    id_cartao=self.id_conta,
                    progress_callback=self._emit_progress,
                    senha_pdf=self.senha_pdf,
                )
            else:
                lancamentos = self.controller.importar_arquivo(
                    caminho_arquivo=self.caminho_arquivo,
                    id_conta=self.id_conta,
                    progress_callback=self._emit_progress,
                    senha_pdf=self.senha_pdf,
                )

            self._check_cancelled()
            self._emit_progress(100, "Importação finalizada.")

            self.finished.emit(
                lancamentos if isinstance(lancamentos, list) else []
            )

        except ImportCancelledError:
            logger.info("Importação cancelada: %s", self.caminho_arquivo)
        except Exception as e:
            logger.exception("Erro no ImportWorker")
            if not self.is_cancelled():
                self.error.emit(str(e))
        finally:
            self.stopped.emit()

    def cancel(self):
        self._cancel_event.set()
        self.requestInterruption()

    def is_cancelled(self):
        return self._cancel_event.is_set() or self.isInterruptionRequested()

    def _check_cancelled(self):
        if self.is_cancelled():
            raise ImportCancelledError("Importação cancelada.")

    def _emit_progress(self, progresso, mensagem=None):
        self._check_cancelled()

        try:
            progresso = int(progresso)
        except Exception:
            progresso = 0

        mensagem = mensagem or "Importando..."

        self.progress.emit(progresso, mensagem)
