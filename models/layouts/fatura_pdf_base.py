"""Utilidades comuns aos layouts reais de fatura em PDF."""

from datetime import date
import re
import unicodedata

from models.layouts.base_layout import BaseLayout


class FaturaPdfBaseLayout(BaseLayout):
    tipo_documento = "fatura_cartao"
    MESES = {
        "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
        "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
    }

    @staticmethod
    def texto_sem_acentos(valor):
        return unicodedata.normalize("NFKD", str(valor or "")).encode(
            "ascii", "ignore"
        ).decode("ascii").upper()

    @staticmethod
    def valor_br(valor):
        texto = str(valor or "").replace("R$", "").replace("−", "-").strip()
        negativo = texto.startswith("-")
        texto = re.sub(r"[^\d,.]", "", texto).replace(".", "").replace(",", ".")
        try:
            numero = float(texto)
        except ValueError:
            return None
        return -numero if negativo else numero

    @classmethod
    def data_abreviada(cls, dia, mes, ano_fatura, mes_fatura):
        mes_numero = cls.MESES[cls.texto_sem_acentos(mes)[:3]]
        ano = int(ano_fatura) - (1 if mes_numero > int(mes_fatura) else 0)
        return date(ano, mes_numero, int(dia)).isoformat()

    @staticmethod
    def parcela(descricao):
        match = re.search(r"(?:PARCELA\s*)?(\d{1,2})\s*/\s*(\d{1,2})\b", descricao, re.I)
        if not match:
            return 1, 1
        atual, total = map(int, match.groups())
        return (atual, total) if 1 <= atual <= total else (1, 1)

    @staticmethod
    def item(data, descricao, valor, mes, ano):
        atual, total = FaturaPdfBaseLayout.parcela(descricao)
        return {
            "Data": data,
            "Descricao": descricao.strip(),
            "Valor": abs(float(valor)),
            "Parcela_Atual": atual,
            "Num_Parcelas": total,
            "Competencia_Mes": int(mes),
            "Competencia_Ano": int(ano),
            "Previsto": 0,
        }
