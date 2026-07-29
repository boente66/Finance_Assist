# -*- coding: utf-8 -*-
import os
import logging
import re
from typing import List, Optional, Callable

from services.infrastructure.csv_service import CsvService
from services.infrastructure.pdf_service import PdfService
from services.infrastructure.txt_service import TxtService
from services.infrastructure.xlsx_service import XlsxService

from services.reconhecer_service import ReconhecimentoService
from services.categorizacao_service import CategorizacaoService
from services.category_service import CategoryService


logger = logging.getLogger(__name__)


class ImportacaoService:

    def __init__(self):
        self.pdf_service = PdfService()
        self.csv_service = CsvService()
        self.xlsx_service = XlsxService()
        self.txt_service = TxtService()

        self.reconhecimento_service = ReconhecimentoService()
        self.categorizacao_service = CategorizacaoService()
        self.category_service = CategoryService()

    # ======================================================
    # MÉTODO PRINCIPAL
    # ======================================================
    def importar(
        self,
        caminho_arquivo: str,
        id_usuario: int,
        id_conta: int,
        progress_callback: Optional[Callable] = None
    ) -> List[dict]:

        if not caminho_arquivo:
            raise ValueError("Arquivo não informado.")

        if not id_usuario or not id_conta:
            raise ValueError("Usuário ou conta inválidos.")

        if not os.path.exists(caminho_arquivo):
            raise FileNotFoundError("Arquivo não encontrado.")

        try:
            if progress_callback:
                progress_callback(5, "Validando arquivo...")

            extensao = os.path.splitext(caminho_arquivo)[1].lower()

            conteudo = self._ler_conteudo(
                caminho_arquivo=caminho_arquivo,
                extensao=extensao,
                progress_callback=progress_callback
            )

            if not conteudo:
                logger.warning("Arquivo sem conteúdo extraído.")
                return []

            if progress_callback:
                progress_callback(35, "Reconhecendo layout...")

            resultado_reconhecimento = (
                self.reconhecimento_service
                .reconhecer_layout(conteudo)
            )

            if resultado_reconhecimento["indice"] == 0:
                raise ValueError(
                    resultado_reconhecimento.get(
                        "mensagem",
                        "Layout não reconhecido."
                    )
                )

            layout = resultado_reconhecimento["layout"]

            if progress_callback:
                progress_callback(50, "Processando layout...")

            dados = layout.parse(conteudo)

            if not isinstance(dados, list):
                logger.warning("Layout retornou dados inválidos.")
                return []

            tipo_documento = resultado_reconhecimento.get(
                "tipo_documento",
                getattr(layout, "tipo_documento", "desconhecido")
            )

            if progress_callback:
                progress_callback(70, "Normalizando dados...")

            resultado = self._normalizar(
                dados=dados,
                id_usuario=id_usuario,
                id_conta=id_conta,
                tipo_documento=str(tipo_documento).lower()
            )

            if progress_callback:
                progress_callback(100, "Finalizado.")

            return resultado

        except Exception:
            logger.exception("Erro na importação")
            raise

    # ======================================================
    # LEITURA DO CONTEÚDO
    # ======================================================
    def _ler_conteudo(
        self,
        caminho_arquivo: str,
        extensao: str,
        progress_callback: Optional[Callable] = None
    ):

        match extensao:

            case ".pdf":
                if progress_callback:
                    progress_callback(15, "Extraindo texto do PDF...")

                return self.pdf_service.ler_texto(caminho_arquivo)

            case ".csv":
                if progress_callback:
                    progress_callback(20, "Lendo CSV...")

                return self.csv_service.ler(caminho_arquivo)

            case ".xlsx" | ".xls":
                if progress_callback:
                    progress_callback(20, "Lendo planilha...")

                return self.xlsx_service.ler(caminho_arquivo)

            case ".txt":
                if progress_callback:
                    progress_callback(20, "Lendo TXT...")

                return self.txt_service.ler(caminho_arquivo)

            case _:
                raise ValueError("Formato de arquivo não suportado.")

    # ======================================================
    # NORMALIZAÇÃO
    # ======================================================
    def _normalizar(
        self,
        dados: list,
        id_usuario: int,
        id_conta: int,
        tipo_documento: str
    ) -> List[dict]:

        dados_final = []

        for item in dados:

            if not isinstance(item, dict):
                continue

            data = item.get("Data")
            descricao = item.get("Descricao")
            valor = item.get("Valor")

            if not data or not descricao:
                continue

            descricao = self._limpar_descricao_bancaria(
                str(descricao).strip()
            )

            valor = self._parse_valor(valor)

            if valor is None:
                continue

            tipo = "Despesa" if valor < 0 else "Receita"

            id_categoria = None
            confianca = 0.0

            match tipo_documento:

                case "extrato_bancario":
                    try:
                        id_categoria, confianca = (
                            self.categorizacao_service.categorizar(
                                descricao,
                                valor,
                                id_usuario
                            )
                        )
                    except Exception:
                        logger.exception(
                            "Erro ao categorizar extrato bancário"
                        )
                        id_categoria = None
                        confianca = 0.0

                case "exportacao_sistema" | "migracao_sistema":
                    categoria_pai = (
                        item.get("CategoriaPai")
                        or item.get("Categoria")
                    )

                    subcategoria = item.get("Subcategoria")

                    if categoria_pai:
                        id_categoria = (
                            self.category_service
                            .resolver_categoria_importacao(
                                categoria_pai_nome=categoria_pai,
                                subcategoria_nome=subcategoria,
                                valor=valor,
                                id_usuario=id_usuario
                            )
                        )
                        confianca = 1.0

                case _:
                    logger.warning(
                        "Tipo de documento desconhecido na importação: %s",
                        tipo_documento
                    )

            dados_final.append({
                "Data": data,
                "Descricao": descricao,
                "Valor": valor,
                "Tipo": tipo,
                "ID_Categoria": id_categoria,
                "ID_Favorecido": item.get("ID_Favorecido"),
                "Favorecido": item.get("Favorecido"),
                "ID_Usuario": id_usuario,
                "ID_Conta": id_conta,
                "ConfiancaIA": round(float(confianca or 0), 2)
            })

        return dados_final

    # ======================================================
    # PARSE DE VALOR
    # ======================================================
    def _parse_valor(self, valor):
        if valor is None:
            return None

        try:
            if isinstance(valor, (int, float)):
                return float(valor)

            valor_str = str(valor).strip()

            negativo = (
                "-" in valor_str
                or "−" in valor_str
            )

            valor_str = (
                valor_str
                .replace("R$", "")
                .replace(" ", "")
                .replace("+", "")
                .replace("-", "")
                .replace("−", "")
            )

            if "," in valor_str:
                valor_str = (
                    valor_str
                    .replace(".", "")
                    .replace(",", ".")
                )

            numero = float(valor_str)

            return -numero if negativo else numero

        except Exception:
            logger.warning("Valor inválido na importação: %s", valor)
            return None

    # ======================================================
    # LIMPEZA DE DESCRIÇÃO BANCÁRIA
    # ======================================================
    def _limpar_descricao_bancaria(self, descricao: str) -> str:
        if not descricao:
            return descricao

        descricao = descricao.upper()

        descricao = re.sub(r"\b(C|D)\b$", "", descricao)
        descricao = re.sub(r"\s+", " ", descricao)

        return descricao.strip()

    # ======================================================
    # COMPROVANTE PDF
    # ======================================================
    def importar_comprovante_pdf(
        self,
        caminho_arquivo: str
    ) -> Optional[bytes]:

        if not caminho_arquivo:
            raise ValueError("Arquivo não informado.")

        if not os.path.exists(caminho_arquivo):
            raise FileNotFoundError("Arquivo não encontrado.")

        extensao = os.path.splitext(caminho_arquivo)[1].lower()

        if extensao != ".pdf":
            raise ValueError(
                "Apenas arquivos PDF são suportados para comprovantes."
            )

        try:
            return self.pdf_service.ler_bytes(caminho_arquivo)

        except Exception:
            logger.exception("Erro ao ler comprovante PDF")
            raise
