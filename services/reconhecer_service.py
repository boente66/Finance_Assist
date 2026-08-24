# -*- coding: utf-8 -*-
import re

from models.layouts.banco_brasil_layout import BancoBrasilLayoutModel
from models.layouts.bradesco_layout import BradescoLayoutModel
from models.layouts.itau_layout import ItauLayoutModel
from models.layouts.datani_layout import DataniLayoutModel
from models.layouts.picpay_layout import PicPayLayoutModel
from models.layouts.fatura_cartao_layout import FaturaCartaoLayoutModel


class ReconhecimentoService:

    INDICE_NAO_RECONHECIDO = 0

    # Migração
    INDICE_DATANI = 101

    # Extratos
    INDICE_PICPAY = 201
    INDICE_ITAU = 202
    INDICE_BANCO_BRASIL = 203
    INDICE_BRADESCO = 204
    INDICE_FATURA_CARTAO = 301

    SCORE_MINIMO = 5
    MAX_LINHAS_TEXTO = 100
    MAX_LINHAS_TABELA = 50

    def __init__(self):
        self.datani_layout = DataniLayoutModel()
        self.picpay_layout = PicPayLayoutModel()
        self.itau_layout = ItauLayoutModel()
        self.bb_layout = BancoBrasilLayoutModel()
        self.bradesco_layout = BradescoLayoutModel()
        self.fatura_cartao_layout = FaturaCartaoLayoutModel()

    # ======================================================
    # ENTRADA PRINCIPAL
    # ======================================================
    def reconhecer_layout(self, conteudo):
        if conteudo is None:
            return self._nao_reconhecido("Arquivo vazio.")

        tipo = self._identificar_tipo_documento(conteudo)

        match tipo:
            case "fatura":
                return self.reconhecer_fatura(conteudo)

            case "migracao":
                return self.reconhecer_migracao(conteudo)

            case "extrato":
                return self.reconhecer_extrato(conteudo)

            case _:
                return self._nao_reconhecido(
                    "Documento não reconhecido como extrato ou migração."
                )

    # ======================================================
    # IDENTIFICAR GRUPO DO DOCUMENTO
    # ======================================================
    def _identificar_tipo_documento(self, conteudo):
        score_fatura = self._score_fatura_cartao(conteudo)
        score_migracao = self._score_migracao(conteudo)
        score_extrato = self._score_extrato(conteudo)

        if score_fatura >= self.SCORE_MINIMO:
            return "fatura"

        # Em caso de empate, prioriza extrato bancário.
        if score_extrato >= score_migracao and score_extrato >= self.SCORE_MINIMO:
            return "extrato"

        if score_migracao >= self.SCORE_MINIMO:
            return "migracao"

        return None

    def reconhecer_fatura(self, conteudo):
        return self._melhor([
            self._candidato(
                indice=self.INDICE_FATURA_CARTAO,
                nome="fatura_cartao_estruturada",
                grupo="fatura",
                tipo_documento="fatura_cartao",
                layout=self.fatura_cartao_layout,
                score=self._score_fatura_cartao(conteudo),
            )
        ], "Fatura de cartão estruturada não localizada.")

    # ======================================================
    # RECONHECER DENTRO DO GRUPO
    # ======================================================
    def reconhecer_migracao(self, conteudo):
        candidatos = [
            self._candidato(
                indice=self.INDICE_DATANI,
                nome="datani",
                grupo="migracao",
                tipo_documento="migracao_sistema",
                layout=self.datani_layout,
                score=self._score_datani(conteudo),
            )
        ]

        return self._melhor(
            candidatos,
            "Migração de sistema não localizada."
        )

    def reconhecer_extrato(self, conteudo):
        candidatos = [
            self._candidato(
                indice=self.INDICE_PICPAY,
                nome="picpay",
                grupo="extrato",
                tipo_documento="extrato_bancario",
                layout=self.picpay_layout,
                score=self._score_picpay(conteudo),
            ),
            self._candidato(
                indice=self.INDICE_ITAU,
                nome="itau",
                grupo="extrato",
                tipo_documento="extrato_bancario",
                layout=self.itau_layout,
                score=self._score_itau(conteudo),
            ),
            self._candidato(
                indice=self.INDICE_BANCO_BRASIL,
                nome="banco_brasil",
                grupo="extrato",
                tipo_documento="extrato_bancario",
                layout=self.bb_layout,
                score=self._score_banco_do_brasil(conteudo),
            ),
            self._candidato(
                indice=self.INDICE_BRADESCO,
                nome="bradesco",
                grupo="extrato",
                tipo_documento="extrato_bancario",
                layout=self.bradesco_layout,
                score=self._score_bradesco(conteudo),
            ),
        ]

        return self._melhor(
            candidatos,
            "Extrato bancário não localizado."
        )

    # ======================================================
    # SCORES GERAIS
    # ======================================================
    def _score_migracao(self, conteudo):
        return self._score_datani(conteudo)

    def _score_extrato(self, conteudo):
        return max(
            self._score_picpay(conteudo),
            self._score_itau(conteudo),
            self._score_banco_do_brasil(conteudo),
            self._score_bradesco(conteudo),
        )

    def _score_fatura_cartao(self, conteudo):
        if not isinstance(conteudo, list) or not conteudo:
            return 0
        texto = self._conteudo_para_texto(conteudo)
        colunas = self._colunas(conteudo)
        colunas_compactas = {
            re.sub(r"[^a-z0-9]+", "", coluna) for coluna in colunas
        }
        score = 0
        if "fatura_cartao" in texto:
            score += 6
        tem_data = bool({
            "data", "datacompra", "datadacompra",
            "datalancamento", "datadelancamento",
        } & colunas_compactas)
        tem_descricao = bool(
            {"descricao", "estabelecimento", "historico", "lancamento"}
            & colunas_compactas
        )
        tem_valor = bool({"valor", "valorcompra"} & colunas_compactas)
        if tem_data and tem_descricao and tem_valor:
            score += 2
        if any("parcela" in coluna for coluna in colunas_compactas):
            score += 4
        if any("competencia" in coluna for coluna in colunas_compactas):
            score += 4
        if "cartao" in colunas_compactas or "fatura" in colunas_compactas:
            score += 3
        return score

    # ======================================================
    # SCORES — DATANI / MIGRAÇÃO
    # ======================================================
    def _score_datani(self, conteudo):
        score = 0

        texto = self._conteudo_para_texto(conteudo)
        colunas = self._colunas(conteudo)

        if "<transferencia>" in texto:
            score += 5

        if "importado" in texto:
            score += 2

        if "compensado" in texto:
            score += 2

        if "categoria" in texto or "categoria" in colunas:
            score += 2

        if "receita" in texto and "despesa" in texto:
            score += 2

        if (
            "descricao" in texto
            or "descrição" in texto
            or "descricao" in colunas
            or "descrição" in colunas
        ):
            score += 1

        return score

    # ======================================================
    # SCORES — PICPAY
    # ======================================================
    def _score_picpay(self, conteudo):
        score = 0

        texto = self._conteudo_para_texto(conteudo)
        colunas = self._colunas(conteudo)

        if "picpay" in texto:
            score += 5

        if "extrato de conta" in texto:
            score += 3

        if "saldo ao final do dia" in texto:
            score += 3

        if "origem / destino" in texto or "origem / destino" in colunas:
            score += 3

        if "forma de pagamento" in texto or "forma de pagamento" in colunas:
            score += 3

        if {"data", "hora", "tipo", "valor"}.issubset(colunas):
            score += 5

        if "pix recebido" in texto:
            score += 1

        if "pix enviado" in texto:
            score += 1

        if "troco guardado" in texto:
            score += 1

        if "dinheiro guardado" in texto:
            score += 1

        if "dinheiro resgatado" in texto:
            score += 1

        if "pagamento realizado" in texto:
            score += 1

        if "compra realizada" in texto:
            score += 1

        return score

    # ======================================================
    # SCORES — ITAÚ
    # ======================================================
    def _score_itau(self, conteudo):
        score = 0
        texto = self._conteudo_para_texto(conteudo)

        if "itaú" in texto or "itau" in texto:
            score += 5

        if "extrato conta" in texto:
            score += 3

        if "limite da conta" in texto:
            score += 3

        if "saldo do dia" in texto:
            score += 2

        if "agencia:" in texto or "agência:" in texto:
            score += 1

        movimentos = self._contar_linhas(
            texto,
            r"\d{2}/\d{2}/\d{4}\s+.+\s+-?\d{1,3}(?:\.\d{3})*,\d{2}"
        )

        score += min(movimentos, 5)

        return score

    # ======================================================
    # SCORES — BANCO DO BRASIL
    # ======================================================
    def _score_banco_do_brasil(self, conteudo):
        score = 0
        texto = self._conteudo_para_texto(conteudo)

        if "banco do brasil" in texto:
            score += 6

        movimentos_dc = self._contar_linhas(
            texto,
            r"\d{2}/\d{2}/\d{4}\s+.+\s+-?\d+[.,]\d{2}\s+[dc]$"
        )

        score += min(movimentos_dc * 2, 6)

        return score

    # ======================================================
    # SCORES — BRADESCO
    # ======================================================
    def _score_bradesco(self, conteudo):
        score = 0
        texto = self._conteudo_para_texto(conteudo)

        if "bradesco" in texto:
            score += 6

        if "next" in texto:
            score += 5

        if "extrato de conta" in texto:
            score += 2

        return score

    # ======================================================
    # HELPERS
    # ======================================================
    def _conteudo_para_texto(self, conteudo):
        if isinstance(conteudo, str):
            return conteudo.lower()

        if isinstance(conteudo, list):
            partes = []

            for linha in conteudo[:self.MAX_LINHAS_TABELA]:
                if isinstance(linha, dict):
                    partes.extend(
                        str(valor)
                        for valor in linha.values()
                        if valor is not None
                    )

            return " ".join(partes).lower()

        return ""

    def _colunas(self, conteudo):
        if not isinstance(conteudo, list) or not conteudo:
            return set()

        primeira = conteudo[0]

        if not isinstance(primeira, dict):
            return set()

        return {
            str(chave).strip().lower()
            for chave in primeira.keys()
        }

    def _contar_linhas(self, texto: str, padrao: str) -> int:
        total = 0

        for linha in texto.splitlines()[:self.MAX_LINHAS_TEXTO]:
            if re.search(padrao, linha.strip()):
                total += 1

        return total

    def _candidato(
        self,
        indice,
        nome,
        grupo,
        tipo_documento,
        layout,
        score
    ):
        return {
            "indice": indice,
            "nome": nome,
            "grupo": grupo,
            "tipo_documento": tipo_documento,
            "tipo_layout": nome,
            "layout": layout,
            "score": score,
            "mensagem": "Layout reconhecido.",
        }

    def _melhor(self, candidatos, mensagem):
        melhor = max(candidatos, key=lambda c: c["score"])

        if melhor["score"] < self.SCORE_MINIMO:
            return self._nao_reconhecido(mensagem)

        return melhor

    def _nao_reconhecido(self, mensagem):
        return {
            "indice": self.INDICE_NAO_RECONHECIDO,
            "nome": "nao_reconhecido",
            "grupo": None,
            "tipo_documento": "desconhecido",
            "tipo_layout": None,
            "layout": None,
            "score": 0,
            "mensagem": mensagem,
        }

    def is_comprovante(self, conteudo):
        texto = self._conteudo_para_texto(conteudo)
        return "comprovante" in texto
