# -*- coding: utf-8 -*-
"""Layout conservador para faturas estruturadas em CSV/XLSX."""

from datetime import datetime
import re
import unicodedata

from models.layouts.base_layout import BaseLayout


class FaturaCartaoLayoutModel(BaseLayout):
    tipo_documento = "fatura_cartao"

    @staticmethod
    def _chave(valor):
        texto = unicodedata.normalize("NFKD", str(valor or ""))
        texto = texto.encode("ascii", "ignore").decode("ascii").lower()
        return re.sub(r"[^a-z0-9]+", "_", texto).strip("_")

    def _linha(self, item):
        dados = {self._chave(chave): valor for chave, valor in item.items()}
        aliases = {
            "datacompra": "data_compra",
            "datadacompra": "data_compra",
            "datalancamento": "data_lancamento",
            "datadelancamento": "data_lancamento",
            "valorcompra": "valor_compra",
            "parcelaatual": "parcela_atual",
            "numeroparcela": "numero_parcela",
            "numparcelas": "num_parcelas",
            "numeroparcelas": "numero_parcelas",
            "competenciames": "competencia_mes",
            "competenciaano": "competencia_ano",
            "categoriapai": "categoria_pai",
        }
        for origem, destino in aliases.items():
            if origem in dados and destino not in dados:
                dados[destino] = dados[origem]
        return dados

    @staticmethod
    def _primeiro(dados, *chaves):
        for chave in chaves:
            valor = dados.get(chave)
            if valor not in (None, ""):
                return valor
        return None

    @staticmethod
    def _data(valor):
        texto = str(valor or "").strip()[:10]
        for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(texto, formato).date().isoformat()
            except ValueError:
                continue
        return None

    @staticmethod
    def _valor(valor):
        if isinstance(valor, (int, float)):
            return abs(float(valor))
        texto = re.sub(r"[^\d,.\-]", "", str(valor or ""))
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
        try:
            return abs(float(texto))
        except ValueError:
            return None

    @staticmethod
    def _parcelas(dados):
        atual = dados.get("parcela_atual") or dados.get("numero_parcela")
        total = dados.get("num_parcelas") or dados.get("numero_parcelas")
        composto = dados.get("parcela") or dados.get("parcelas")
        if composto not in (None, ""):
            match = re.fullmatch(r"\s*(\d{1,3})\s*/\s*(\d{1,3})\s*", str(composto))
            if match:
                atual, total = match.groups()
        try:
            atual, total = int(atual or 1), int(total or 1)
        except (TypeError, ValueError):
            return 1, 1
        if total < 1 or atual < 1 or atual > total:
            return 1, 1
        return atual, total

    @staticmethod
    def _competencia(dados):
        mes, ano = dados.get("competencia_mes"), dados.get("competencia_ano")
        composta = dados.get("competencia") or dados.get("fatura")
        if composta not in (None, ""):
            match = re.search(r"(\d{1,2})\s*[/\-]\s*(\d{4})", str(composta))
            if match:
                mes, ano = match.groups()
        try:
            mes, ano = int(mes), int(ano)
        except (TypeError, ValueError):
            return None, None
        return (mes, ano) if 1 <= mes <= 12 and ano >= 1900 else (None, None)

    def parse(self, conteudo):
        if not isinstance(conteudo, list):
            return []
        resultado = []
        for original in conteudo:
            if not isinstance(original, dict):
                continue
            dados = self._linha(original)
            data = self._data(self._primeiro(
                dados, "data", "data_compra", "data_lancamento"
            ))
            descricao = self._primeiro(
                dados, "descricao", "estabelecimento", "historico", "lancamento"
            )
            valor = self._valor(self._primeiro(dados, "valor", "valor_compra"))
            if (
                not data
                or not str(descricao or "").strip()
                or valor is None
                or valor <= 0
            ):
                continue
            atual, total = self._parcelas(dados)
            mes, ano = self._competencia(dados)
            resultado.append({
                "Data": data,
                "Descricao": str(descricao).strip(),
                "Valor": valor,
                "Parcela_Atual": atual,
                "Num_Parcelas": total,
                "Competencia_Mes": mes,
                "Competencia_Ano": ano,
                "CategoriaPai": self._primeiro(dados, "categoria_pai", "categoria"),
                "Subcategoria": dados.get("subcategoria"),
                "Favorecido": dados.get("favorecido"),
                "Notas": dados.get("notas"),
                "Previsto": 0,
            })
        return resultado
