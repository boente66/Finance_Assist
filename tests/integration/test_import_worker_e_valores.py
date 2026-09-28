import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt5.QtTest import QSignalSpy
from PyQt5.QtWidgets import QApplication

from services.importacao_service import ImportacaoService
from workers.import_worker import ImportWorker


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class ControllerLento:
    def __init__(self):
        self.senha = None

    def importar_arquivo(self, *, progress_callback, senha_pdf, **_kwargs):
        self.senha = senha_pdf
        for etapa in range(100):
            time.sleep(0.005)
            progress_callback(etapa, "Processando")
        return [{"Descricao": "não deve chegar após cancelamento"}]


def test_worker_propaga_senha_e_cancela_sem_resultado(app):
    controller = ControllerLento()
    worker = ImportWorker(controller, "protegido.pdf", 1, senha_pdf="12345")
    resultados = QSignalSpy(worker.finished)
    erros = QSignalSpy(worker.error)
    parou = QSignalSpy(worker.stopped)
    progresso = QSignalSpy(worker.progress)
    worker.start()
    assert progresso.wait(500)
    worker.cancel()
    assert worker.wait(2000)
    app.processEvents()

    assert controller.senha == "12345"
    assert len(resultados) == 0
    assert len(erros) == 0
    assert len(parou) == 1


@pytest.mark.parametrize("texto, esperado", [
    ("1.234,56", 1234.56),
    ("1234,56", 1234.56),
    ("1,234.56", 1234.56),
    ("1234.56", 1234.56),
    ("- R$ 1.234,56", -1234.56),
    ("(1234.56)", -1234.56),
])
def test_parse_valor_aceita_formatos_brasileiro_e_internacional(texto, esperado):
    assert ImportacaoService()._parse_valor(texto) == esperado


@pytest.mark.parametrize("texto", ["1.234", "1,234", "12.34.56", "1,23,4"])
def test_parse_valor_recusa_formatos_ambiguos(texto):
    assert ImportacaoService()._parse_valor(texto) is None
