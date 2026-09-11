import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile


logger = logging.getLogger(__name__)


class MakePDF:
    """
    Classe de INFRAESTRUTURA para manipulação de PDF.

    Responsabilidades:
    - Ler PDF
    - Extrair texto
    - Aplicar OCR
    - Gerar PDF
    - Ler bytes do PDF
    """

    # ==========================================================
    # LEITURA BINÁRIA
    # ==========================================================
    @staticmethod
    def ler_bytes(caminho_arquivo):
        if not caminho_arquivo:
            return None

        try:
            with open(caminho_arquivo, "rb") as arquivo:
                return arquivo.read()

        except Exception as e:
            print(f"Erro ao ler bytes do PDF: {e}")
            return None

    # ==========================================================
    # LEITURA SIMPLES (PyPDF2)
    # ==========================================================
    @staticmethod
    def importar_pdf(caminho_arquivo, senha=None):
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(caminho_arquivo)
            if reader.is_encrypted and not reader.decrypt(senha or ""):
                raise ValueError("Senha da fatura PDF incorreta ou não informada.")
            texto = ""

            for page in reader.pages:
                texto += page.extract_text() or ""

            return texto

        except ValueError:
            raise
        except Exception:
            logger.exception("Erro ao extrair texto digital do PDF")
            return None

    # ==========================================================
    # LEITURA AVANÇADA (pdfplumber + OCR)
    # ==========================================================
    @staticmethod
    def ler_pdf(caminho_arquivo, senha=None):
        try:
            # Faturas digitais preservam melhor a ordem dos lançamentos pelo
            # fluxo textual. A leitura tabular continua como fallback para
            # extratos bancários e PDFs sem texto utilizável.
            texto_digital = MakePDF.importar_pdf(caminho_arquivo, senha)
            marcador = (texto_digital or "").lower()
            if len(marcador.strip()) >= 100 and "fatura" in marcador and (
                "nubank" in marcador or "picpay mastercard" in marcador
                or "itau unibanco" in marcador or "banco itaú" in marcador
            ):
                return texto_digital.strip()

            import pdfplumber
            import pdf2image
            import pytesseract

            texto = ""

            with pdfplumber.open(caminho_arquivo, password=senha) as pdf:
                for pagina in pdf.pages:

                    tabela = pagina.extract_table()

                    if tabela:
                        for linha in tabela:
                            if linha:
                                linha_formatada = "  ".join(
                                    str(c).strip()
                                    for c in linha
                                    if c
                                )
                                texto += linha_formatada + "\n"
                    else:
                        texto_bruto = pagina.extract_text()
                        if texto_bruto:
                            texto += texto_bruto + "\n"

            if not texto.strip():
                if getattr(sys, 'frozen', False) and sys.platform.startswith('linux'):
                    return MakePDF._ocr_pdf_sistema(caminho_arquivo)
                imagens = pdf2image.convert_from_path(
                    caminho_arquivo
                )

                for img in imagens:
                    texto += pytesseract.image_to_string(
                        img,
                        lang="por"
                    ) + "\n"

            return texto.strip() or None

        except ValueError:
            raise
        except Exception as e:
            logger.exception("Erro ao ler PDF")
            return None

    @staticmethod
    def _external_environment(environ=None):
        """Restore the host loader path for child processes, never globally."""
        env = dict(os.environ if environ is None else environ)
        original = env.pop('LD_LIBRARY_PATH_ORIG', '')
        if original:
            env['LD_LIBRARY_PATH'] = original
        else:
            env.pop('LD_LIBRARY_PATH', None)
        return env

    @staticmethod
    def _ocr_pdf_sistema(caminho_arquivo):
        """Use distro Poppler/Tesseract without inheriting frozen C++ libraries."""
        env = MakePDF._external_environment()
        with tempfile.TemporaryDirectory(prefix='finance-assist-ocr-') as folder:
            prefix = str(Path(folder) / 'page')
            subprocess.run(
                ['pdftoppm', '-r', '200', '-png', str(Path(caminho_arquivo).resolve()), prefix],
                env=env, check=True, capture_output=True, timeout=300,
            )
            pages = sorted(Path(folder).glob('page-*.png'),
                           key=lambda p: int(p.stem.rsplit('-', 1)[1]))
            if not pages:
                raise RuntimeError('Poppler não gerou páginas para OCR')
            texts = []
            for page in pages:
                result = subprocess.run(
                    ['tesseract', str(page), 'stdout', '-l', 'por'],
                    env=env, check=True, capture_output=True, text=True,
                    encoding='utf-8', errors='replace', timeout=120,
                )
                texts.append(result.stdout)
            return '\n'.join(texts).strip() or None

    # ==========================================================
    # VISUALIZAÇÃO
    # ==========================================================
    @staticmethod
    def visualizar_pdf(caminho_arquivo):
        return MakePDF.importar_pdf(caminho_arquivo)

    # ==========================================================
    # GERAR PDF COM TEXTO
    # ==========================================================
    @staticmethod
    def gerar_pdf(caminho_arquivo, titulo, conteudo):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas

            c = canvas.Canvas(caminho_arquivo, pagesize=A4)
            width, height = A4

            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, height - 50, titulo)

            c.setFont("Helvetica", 12)
            y = height - 80

            for linha in conteudo.split("\n"):
                c.drawString(50, y, linha)
                y -= 18

                if y < 50:
                    c.showPage()
                    y = height - 50

            c.save()
            return True

        except Exception as e:
            print(f"Erro ao gerar PDF: {e}")
            return False

    # ==========================================================
    # GERAR PDF SIMPLES A PARTIR DE LISTA
    # ==========================================================
    @staticmethod
    def create_pdf_from_data(data, file_path):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas

            c = canvas.Canvas(file_path, pagesize=A4)
            width, height = A4

            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, height - 50, "Relatório")

            c.setFont("Helvetica", 10)
            y = height - 80

            for item in data:
                c.drawString(50, y, str(item))
                y -= 20

                if y < 50:
                    c.showPage()
                    y = height - 50

            c.save()
            return True

        except Exception as e:
            print(f"Erro ao criar PDF: {e}")
            return False
