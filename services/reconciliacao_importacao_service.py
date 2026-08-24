# -*- coding: utf-8 -*-
"""Reconciliação local e determinística de itens financeiros importados."""

from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from difflib import SequenceMatcher
import re
import unicodedata


class ReconciliacaoImportacaoService:
    """Classifica importações sem decidir por similaridade em nome do usuário."""

    NOVO = "NOVO"
    DUPLICADO = "DUPLICADO"
    POSSIVEL_DUPLICADO = "POSSIVEL_DUPLICADO"

    DOMINIO_CONTA = "conta"
    DOMINIO_CARTAO = "cartao"

    LIMIAR_SIMILARIDADE = 0.78

    @staticmethod
    def normalizar_descricao(descricao):
        texto = unicodedata.normalize("NFKD", str(descricao or ""))
        texto = texto.encode("ascii", "ignore").decode("ascii").upper()
        texto = re.sub(r"\b(C|D)\b$", "", texto)
        return re.sub(r"\s+", " ", texto).strip()

    @staticmethod
    def normalizar_data(valor):
        if isinstance(valor, datetime):
            return valor.date().isoformat()
        if isinstance(valor, date):
            return valor.isoformat()

        texto = str(valor or "").strip()
        for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(texto[:10], formato).date().isoformat()
            except ValueError:
                continue
        return texto

    @staticmethod
    def normalizar_valor(valor):
        try:
            numero = Decimal(str(valor)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        except (InvalidOperation, TypeError, ValueError):
            numero = Decimal("0.00")
        return format(numero, ".2f")

    @staticmethod
    def _inteiro(valor, padrao=1):
        try:
            return int(valor)
        except (TypeError, ValueError):
            return padrao

    def chave_exata(self, item, dominio):
        base = (
            self._inteiro(item.get("ID_Usuario"), 0),
            self.normalizar_data(item.get("Data")),
            self.normalizar_valor(item.get("Valor")),
            self.normalizar_descricao(item.get("Descricao")),
        )

        if dominio == self.DOMINIO_CARTAO:
            return base + (
                self._inteiro(item.get("ID_Cartao"), 0),
                self._inteiro(item.get("Competencia_Mes"), 0),
                self._inteiro(item.get("Competencia_Ano"), 0),
                self._inteiro(item.get("Parcela_Atual"), 1),
                self._inteiro(item.get("Num_Parcelas"), 1),
            )

        return base + (self._inteiro(item.get("ID_Conta"), 0),)

    def _mesmo_contexto_aproximado(self, importado, existente, dominio):
        if self._inteiro(importado.get("ID_Usuario"), 0) != self._inteiro(
            existente.get("ID_Usuario"), 0
        ):
            return False
        if self.normalizar_data(importado.get("Data")) != self.normalizar_data(
            existente.get("Data")
        ):
            return False
        if self.normalizar_valor(importado.get("Valor")) != self.normalizar_valor(
            existente.get("Valor")
        ):
            return False

        if dominio == self.DOMINIO_CARTAO:
            campos = (
                "ID_Cartao", "Competencia_Mes", "Competencia_Ano",
                "Parcela_Atual", "Num_Parcelas",
            )
        else:
            campos = ("ID_Conta",)

        return all(
            self._inteiro(importado.get(campo), 0)
            == self._inteiro(existente.get(campo), 0)
            for campo in campos
        )

    def _melhor_correspondencia(self, importado, existentes, dominio):
        descricao = self.normalizar_descricao(importado.get("Descricao"))
        if not descricao:
            return None

        melhor = None
        melhor_score = 0.0
        for candidato in existentes:
            if not self._mesmo_contexto_aproximado(
                importado, candidato, dominio
            ):
                continue
            descricao_candidata = self.normalizar_descricao(
                candidato.get("Descricao")
            )
            if not descricao_candidata or descricao_candidata == descricao:
                continue
            score = SequenceMatcher(
                None, descricao, descricao_candidata, autojunk=False
            ).ratio()
            if score > melhor_score:
                melhor = candidato
                melhor_score = score

        if melhor is None or melhor_score < self.LIMIAR_SIMILARIDADE:
            return None
        return melhor, round(melhor_score, 2)

    @staticmethod
    def _resumo_correspondencia(item):
        if not item:
            return ""
        identificador = item.get("ID_Transacao") or item.get("ID_Lancamento")
        prefixo = f"#{identificador} · " if identificador else ""
        return (
            f"{prefixo}{item.get('Data', '')} · "
            f"{item.get('Descricao', '')} · {float(item.get('Valor', 0)):.2f}"
        )

    def reconciliar(self, importados, existentes, dominio):
        if dominio not in (self.DOMINIO_CONTA, self.DOMINIO_CARTAO):
            raise ValueError("Domínio de reconciliação inválido.")

        existentes = [dict(item) for item in (existentes or [])]
        ocorrencias = Counter(
            self.chave_exata(item, dominio) for item in existentes
        )
        por_chave = {}
        for item in existentes:
            por_chave.setdefault(self.chave_exata(item, dominio), []).append(item)

        resultado = []
        for original in importados or []:
            item = dict(original)
            chave = self.chave_exata(item, dominio)
            if ocorrencias[chave] > 0:
                ocorrencias[chave] -= 1
                correspondente = por_chave[chave].pop(0)
                item.update({
                    "StatusImportacao": self.DUPLICADO,
                    "MotivoReconciliacao": (
                        "Já existe uma ocorrência idêntica neste destino."
                    ),
                    "CorrespondenciaImportacao": self._resumo_correspondencia(
                        correspondente
                    ),
                    "Importar": False,
                })
            else:
                possivel = self._melhor_correspondencia(
                    item, existentes, dominio
                )
                if possivel:
                    correspondente, score = possivel
                    item.update({
                        "StatusImportacao": self.POSSIVEL_DUPLICADO,
                        "MotivoReconciliacao": (
                            f"Há item semelhante no mesmo dia e valor ({score:.0%})."
                        ),
                        "CorrespondenciaImportacao": self._resumo_correspondencia(
                            correspondente
                        ),
                        "SimilaridadeImportacao": score,
                        "Importar": False,
                    })
                else:
                    item.update({
                        "StatusImportacao": self.NOVO,
                        "MotivoReconciliacao": "Nenhuma ocorrência correspondente.",
                        "CorrespondenciaImportacao": "",
                        "Importar": True,
                    })
            resultado.append(item)

        return resultado

    @staticmethod
    def limites_periodo(itens):
        datas = [
            ReconciliacaoImportacaoService.normalizar_data(item.get("Data"))
            for item in (itens or [])
            if item.get("Data")
        ]
        datas = [valor for valor in datas if valor]
        return (min(datas), max(datas)) if datas else (None, None)
