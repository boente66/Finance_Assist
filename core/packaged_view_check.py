"""Executable view smoke test; run.py establishes disposable storage first."""
import importlib
import faulthandler
import inspect
import json
import logging
from pathlib import Path
import sys
import traceback


def run_check():
    from core.config import RUNTIME_ENVIRONMENT
    if RUNTIME_ENVIRONMENT != 'test':
        raise RuntimeError('A verificação exige armazenamento de teste isolado.')
    from PyQt5.QtWidgets import QApplication, QWidget
    from controllers.user_controller import UserController
    from core.session import Session
    from core.translator_app import TranslatorApp

    app = QApplication.instance() or QApplication([])
    TranslatorApp.initialize()
    errors = []
    checked = []
    target = None
    if '--self-test-report' in sys.argv:
        target = Path(sys.argv[sys.argv.index('--self-test-report') + 1])

    def checkpoint(stage):
        if target is not None:
            target.write_text(json.dumps({'checked': checked, 'errors': errors,
                                          'ok': False, 'stage': stage}, indent=2), encoding='utf-8')

    checkpoint('initialize')
    fault_log = None
    if target is not None:
        fault_log = target.with_name(target.name + '.fault.log').open('w', encoding='utf-8')
        faulthandler.enable(file=fault_log, all_threads=True)

    class ErrorCollector(logging.Handler):
        def emit(self, record):
            if record.levelno >= logging.ERROR:
                errors.append(self.format(record))

    collector = ErrorCollector()
    logging.getLogger().addHandler(collector)
    old_hook = sys.excepthook
    sys.excepthook = lambda *args: errors.append(''.join(traceback.format_exception(*args)))
    controller = UserController()
    user = {'Nome': 'Teste de empacotamento', 'Login': 'package-check',
            'Email': 'package-check@example.invalid', 'Senha': 'Package-check-2026!',
            'Nivel_Acesso': 'admin'}
    if not controller.register_user(user):
        raise RuntimeError('Falha ao criar usuário no banco temporário')
    user = controller.authenticate_user(user['Login'], user['Senha'])
    Session.set_usuario(user)
    if getattr(sys, 'frozen', False):
        modules = json.loads((Path(sys._MEIPASS) / 'view-manifest.json').read_text())
    else:
        modules = sorted('views.' + p.stem for p in (Path(__file__).resolve().parents[1] / 'views').glob('*.py') if p.stem != '__init__')
    fixtures = {'usuario_logado': user, 'usuario': user, 'controller': controller,
                'transacao': {}, 'lancamentos': [], 'tooltip': 'Adicionar',
                'symbol': '+', 'label': 'Teste'}
    widgets = []
    try:
        if getattr(sys, 'frozen', False):
            for dependency in ('typing_extensions', 'openpyxl', 'pandas', 'reportlab',
                               'pdfplumber', 'pdf2image', 'pytesseract', 'cryptography',
                               'matplotlib.backends.backend_qtagg', 'sentence_transformers',
                               'ctranslate2', 'onnxruntime', 'spacy', 'stanza',
                               'argostranslate.translate', 'sklearn'):
                try:
                    checkpoint('import:' + dependency)
                    importlib.import_module(dependency)
                    checked.append(dependency)
                except Exception:
                    errors.append(traceback.format_exc())
        if '--self-test-ocr' in sys.argv:
            try:
                from core.config import DATA_DIR
                from PIL import Image, ImageDraw, ImageFont
                from utilitarios.makepdf import MakePDF
                page = Image.new('RGB', (1000, 250), 'white')
                ImageDraw.Draw(page).text((40, 70), 'FINANCE ASSIST',
                                          font=ImageFont.load_default(size=60), fill='black')
                sample = Path(DATA_DIR) / 'ocr-check.pdf'
                page.save(sample, 'PDF', resolution=150)
                extracted = MakePDF.ler_pdf(str(sample))
                if not extracted or 'FINANCE' not in extracted.upper():
                    raise RuntimeError('O OCR do PDF de teste não retornou o texto esperado')
                checked.append('ocr.pdf-portugues')
            except Exception:
                errors.append(traceback.format_exc())
        for name in modules:
            try:
                checkpoint('import:' + name)
                module = importlib.import_module(name)
                checked.append(name)
                for _, cls in inspect.getmembers(module, inspect.isclass):
                    if cls.__module__ != name or not issubclass(cls, QWidget):
                        continue
                    checkpoint('construct:' + name + '.' + cls.__name__)
                    kwargs = {key: fixtures[key] for key, param in inspect.signature(cls.__init__).parameters.items()
                              if key != 'self' and param.default is inspect.Parameter.empty
                              and param.kind not in (param.VAR_POSITIONAL, param.VAR_KEYWORD)}
                    if cls.__name__ == 'ExecuteScheduleDialog':
                        kwargs['agendamento'] = {'Descricao': 'Teste', 'Valor': 1, 'Tipo': 'Contas a Pagar'}
                    if cls.__name__ in ('AjustarSaldoDialog', 'EditarContaDialog'):
                        kwargs['conta'] = {'ID_Conta': 1, 'Nome_Conta': 'Teste', 'Saldo': 0}
                    if cls.__name__ == 'FaturaDialog':
                        kwargs['id_cartao'] = 1
                    if cls.__name__ == 'TransactionDialogConta':
                        kwargs['id_conta'] = 1
                    if cls.__name__ == 'SubcategoriaDialog':
                        from controllers.category_controller import CategoryController
                        kwargs['controller'] = CategoryController()
                    widget = cls(**kwargs)
                    widgets.append(widget)
                    if hasattr(widget, 'on_load'):
                        widget.on_load()
                    widget.show()
                    app.processEvents()
                    if widget.grab().isNull():
                        raise RuntimeError('A renderização retornou imagem vazia: ' + cls.__name__)
                    widget.hide()
                    checked.append(name + '.' + cls.__name__)
            except Exception:
                errors.append(traceback.format_exc())
        result = {'checked': checked, 'errors': errors, 'ok': not errors}
        # Windows windowed executables do not expose stdout. Persist explicit evidence.
        if target is not None:
            target.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
        if sys.stdout is not None:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1 if errors else 0
    finally:
        if fault_log is not None:
            faulthandler.disable()
            fault_log.close()
        sys.excepthook = old_hook
        logging.getLogger().removeHandler(collector)
        for widget in widgets:
            widget.deleteLater()
        app.processEvents()
