# -*- coding: utf-8 -*-
import re
from datetime import datetime

from models.layouts.base_layout import BaseLayout


class ItauLayoutModel(BaseLayout):
    """
    Layout responsável por interpretar extrato do Itaú.

    NÃO faz reconhecimento.
    NÃO lê PDF.
    Apenas transforma texto já extraído em estrutura padronizada.
    """

    tipo_documento = "extrato_bancario"

    # =====================================================
    # PARSE PRINCIPAL
    # =====================================================
    def parse(self, texto: str) -> list:
        lancamentos = []

        if not texto:
            return lancamentos

        for linha in texto.splitlines():
            linha = linha.strip()

            if not linha:
                continue

            if self._linha_ignorada(linha):
                continue

            lanc = self._parse_linha(linha)

            if lanc:
                lancamentos.append(lanc)

        return lancamentos

    # =====================================================
    # FILTRO DE LINHAS
    # =====================================================
    def _linha_ignorada(self, linha: str) -> bool:
        linha_upper = linha.upper().strip()

        palavras_ignorar = [
            "SALDO DO DIA",
            "SALDO ANTERIOR",
            "POSIÇÃO CONSOLIDADA",
            "POSICAO CONSOLIDADA",
            "EXTRATO CONTA",
            "EXTRATO CONTA / LANÇAMENTOS",
            "EXTRATO CONTA / LANCAMENTOS",
            "PERÍODO DE VISUALIZAÇÃO",
            "PERIODO DE VISUALIZACAO",
            "EMITIDO EM",
            "LIMITE DA CONTA",
            "TOTAL CONTRATADO",
            "AGÊNCIA:",
            "AGENCIA:",
            "CONTA:",
            "DATA LANÇAMENTOS VALOR",
            "DATA LANCAMENTOS VALOR",
            "AVISO!",
        ]

        return any(p in linha_upper for p in palavras_ignorar)

    # =====================================================
    # PARSE DE CADA LINHA
    # =====================================================
    def _parse_linha(self, linha: str) -> dict | None:
        """
        Suporta padrões reais Itaú:

        01/01/2024 DESCRICAO QUALQUER -123,45
        01/01/2024 DESCRICAO QUALQUER 123,45
        01/01/2024 DESCRICAO QUALQUER -123,45 1.500,00

        Também trata descrições extraídas com sufixos colados:
        PIX QRS 99 TECNOLOG16/06
        RSCSS GRAN COFFEE1505
        RSCSS BARBEARIA AM1306
        """

        linha = self._normalizar_linha(linha)

        padrao = re.match(
            r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+"
            r"(-?\d{1,3}(?:\.\d{3})*,\d{2})"
            r"(?:\s+\d{1,3}(?:\.\d{3})*,\d{2})?$",
            linha
        )

        if not padrao:
            return None

        data_raw, descricao_raw, valor_raw = padrao.groups()

        data = self._parse_data(data_raw)
        if not data:
            return None

        valor = self._parse_valor(valor_raw)
        descricao = self._limpar_descricao(descricao_raw)

        if not descricao:
            return None

        return {
            "Data": data,
            "Descricao": descricao,
            "Valor": valor,
        }

    # =====================================================
    # LIMPEZA
    # =====================================================
    def _normalizar_linha(self, linha: str) -> str:
        linha = str(linha or "").strip()
        linha = re.sub(r"\s+", " ", linha)
        return linha

    def _limpar_descricao(self, descricao: str) -> str:
        descricao = str(descricao or "").strip()

        # Remove data colada no final: TECNOLOG16/06, LEONARD13/06
        descricao = re.sub(
            r"(?<=[A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç])\d{2}/\d{2}$",
            "",
            descricao
        )

        # Remove data compacta colada no final: COFFEE1505, BEBIDAS1306
        descricao = re.sub(
            r"(?<=[A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç])\d{4}$",
            "",
            descricao
        )

        # Remove hífens duplicados e espaços extras
        descricao = re.sub(r"\s+", " ", descricao)
        descricao = descricao.strip(" -")

        return descricao.strip()

    # =====================================================
    # CONVERSÕES
    # =====================================================
    def _parse_data(self, data_str: str) -> str | None:
        try:
            return datetime.strptime(
                data_str,
                "%d/%m/%Y"
            ).strftime("%Y-%m-%d")
        except Exception:
            return None

    def _parse_valor(self, valor_str: str) -> float:
        valor_str = str(valor_str).replace(".", "").replace(",", ".")
        return float(valor_str)