# -*- coding: utf-8 -*-
import re
from datetime import datetime

from models.layouts.base_layout import BaseLayout


class PicPayLayoutModel(BaseLayout):
    """
    Layout responsável por interpretar extrato do PicPay.

    NÃO faz reconhecimento.
    NÃO lê PDF.
    NÃO grava no banco.

    Apenas transforma texto extraído em estrutura padronizada.
    """

    tipo_documento = "extrato_bancario"

    MESES = {
        "janeiro": 1,
        "fevereiro": 2,
        "março": 3,
        "marco": 3,
        "abril": 4,
        "maio": 5,
        "junho": 6,
        "julho": 7,
        "agosto": 8,
        "setembro": 9,
        "outubro": 10,
        "novembro": 11,
        "dezembro": 12,
    }

    TIPOS_OPERACAO = [
        "Dinheiro guardado",
        "Dinheiro resgatado",
        "Empréstimo contratado",
        "Emprestimo contratado",
        "Pagamento realizado",
        "Compra realizada",
        "Troco guardado",
        "Pix recebido",
        "Pix enviado",
    ]

    # =====================================================
    # PARSE PRINCIPAL
    # =====================================================
    def parse(self, texto: str) -> list:
        lancamentos = []

        if not texto:
            return lancamentos

        data_atual = None
        buffer_linha = ""

        for linha in texto.splitlines():
            linha = self._normalizar_linha(linha)

            if not linha:
                continue

            data_bloco = self._extrair_data_bloco(linha)
            if data_bloco:
                data_atual = data_bloco
                continue

            if self._linha_ignorada(linha):
                continue

            if self._comeca_com_hora(linha):
                if buffer_linha:
                    lanc = self._parse_linha(buffer_linha, data_atual)
                    if lanc:
                        lancamentos.append(lanc)

                buffer_linha = linha
            else:
                if buffer_linha:
                    buffer_linha += " " + linha

        if buffer_linha:
            lanc = self._parse_linha(buffer_linha, data_atual)
            if lanc:
                lancamentos.append(lanc)

        return lancamentos

    # =====================================================
    # FILTROS
    # =====================================================
    def _linha_ignorada(self, linha: str) -> bool:
        linha_upper = linha.upper()

        ignorar = [
            "EXTRATO DE CONTA",
            "PERÍODO",
            "PERIODO",
            "SALDO FINAL DO PERÍODO",
            "SALDO FINAL DO PERIODO",
            "LEONARDO GABRIEL",
            "CPF:",
            "AGÊNCIA:",
            "AGENCIA:",
            "CONTA:",
            "HORA TIPO ORIGEM",
            "DOCUMENTO EMITIDO",
            "PICPAY SERVIÇOS",
            "PICPAY SERVICOS",
            "CNPJ:",
            "DÚVIDAS?",
            "DUVIDAS?",
            "OUVIDORIA",
        ]

        return any(p in linha_upper for p in ignorar)

    def _comeca_com_hora(self, linha: str) -> bool:
        return bool(re.match(r"^\d{2}:\d{2}\s+", linha))

    # =====================================================
    # DATA DO BLOCO
    # =====================================================
    def _extrair_data_bloco(self, linha: str) -> str | None:
        """
        Exemplo:
        28 de abril 2026 Saldo ao final do dia: R$ 0,00
        """

        padrao = re.match(
            r"^(\d{1,2})\s+de\s+([A-Za-zçÇãõáéíóúâêô]+)\s+(\d{4})",
            linha,
            re.IGNORECASE
        )

        if not padrao:
            return None

        dia_raw, mes_raw, ano_raw = padrao.groups()

        mes = self.MESES.get(mes_raw.lower())
        if not mes:
            return None

        try:
            data = datetime(
                int(ano_raw),
                mes,
                int(dia_raw)
            )

            return data.strftime("%Y-%m-%d")

        except Exception:
            return None

    # =====================================================
    # PARSE DE LANÇAMENTO
    # =====================================================
    def _parse_linha(self, linha: str, data_atual: str | None) -> dict | None:
        if not data_atual:
            return None

        linha = self._normalizar_linha(linha)

        if not self._comeca_com_hora(linha):
            return None

        valor_match = re.search(
            r"([+\-−]?\s*R?\$?\s*\d{1,3}(?:\.\d{3})*,\d{2})",
            linha
        )

        if not valor_match:
            return None

        valor_raw = valor_match.group(1)
        valor = self._parse_valor(valor_raw)

        hora = linha[:5]
        conteudo = linha[6:].strip()

        conteudo_sem_valor = (
            conteudo[:valor_match.start() - 6].strip()
            + " "
            + conteudo[valor_match.end() - 6:].strip()
        )

        conteudo_sem_valor = self._normalizar_linha(conteudo_sem_valor)

        tipo_operacao = self._extrair_tipo_operacao(conteudo_sem_valor)
        descricao_extra = conteudo_sem_valor

        if tipo_operacao:
            descricao_extra = descricao_extra.replace(tipo_operacao, "", 1).strip()

        descricao = self._montar_descricao(
            tipo_operacao=tipo_operacao,
            descricao_extra=descricao_extra
        )

        return {
            "Data": data_atual,
            "Hora": hora,
            "Descricao": descricao,
            "Valor": valor,
            "TipoOperacao": tipo_operacao,
            "OrigemDestino": descricao_extra,
        }

    def _extrair_tipo_operacao(self, texto: str) -> str:
        texto_norm = texto.lower()

        for tipo in self.TIPOS_OPERACAO:
            if texto_norm.startswith(tipo.lower()):
                return tipo

        return ""

    def _montar_descricao(self, tipo_operacao: str, descricao_extra: str) -> str:
        tipo_operacao = str(tipo_operacao or "").strip()
        descricao_extra = str(descricao_extra or "").strip()

        if tipo_operacao and descricao_extra:
            return f"{tipo_operacao} - {descricao_extra}"

        if tipo_operacao:
            return tipo_operacao

        return descricao_extra

    # =====================================================
    # CONVERSÕES
    # =====================================================
    def _parse_valor(self, valor_str: str) -> float:
        valor_str = str(valor_str or "").strip()

        negativo = "-" in valor_str or "−" in valor_str

        valor_str = (
            valor_str
            .replace("R$", "")
            .replace(" ", "")
            .replace("+", "")
            .replace("-", "")
            .replace("−", "")
            .replace(".", "")
            .replace(",", ".")
        )

        valor = float(valor_str)

        return -valor if negativo else valor

    def _normalizar_linha(self, linha: str) -> str:
        linha = str(linha or "").strip()
        linha = linha.replace("−", "-")
        linha = re.sub(r"\s+", " ", linha)
        return linha