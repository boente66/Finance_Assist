"""Layout validado com faturas reais PicPay Mastercard."""

import re

from models.layouts.fatura_pdf_base import FaturaPdfBaseLayout


class PicPayFaturaLayoutModel(FaturaPdfBaseLayout):
    nome = "PicPay Mastercard PDF"

    def parse(self, conteudo):
        if not isinstance(conteudo, str):
            return []
        competencia = re.search(r"fatura de\s+([A-Za-zçÇ]+)", conteudo, re.I)
        vencimento = re.search(r"Vencimento:\s*\d{2}/\d{2}/(\d{4})", conteudo, re.I)
        if not vencimento:
            vencimento = re.search(r"\b\d{2}/\d{2}/(20\d{2})\b", conteudo)
        if not competencia or not vencimento:
            return []
        nomes = {"JANEIRO": 1, "FEVEREIRO": 2, "MARCO": 3, "ABRIL": 4,
                 "MAIO": 5, "JUNHO": 6, "JULHO": 7, "AGOSTO": 8,
                 "SETEMBRO": 9, "OUTUBRO": 10, "NOVEMBRO": 11, "DEZEMBRO": 12}
        mes = nomes.get(self.texto_sem_acentos(competencia.group(1)))
        ano = int(vencimento.group(1))
        if not mes:
            return []
        itens = []
        padrao = re.compile(
            r"^\s*(\d{2})/(\d{2})\s+(.+?)\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})\s*$",
            re.MULTILINE,
        )
        ignorar = ("PAGAMENTO DE FATURA", "CREDITO PULA COMPRA")
        for match in padrao.finditer(conteudo):
            dia, mes_compra, descricao, valor_texto = match.groups()
            descricao_normalizada = self.texto_sem_acentos(descricao)
            valor = self.valor_br(valor_texto)
            if valor is None or valor <= 0 or any(x in descricao_normalizada for x in ignorar):
                continue
            ano_compra = ano - (1 if int(mes_compra) > mes else 0)
            itens.append(self.item(
                f"{ano_compra:04d}-{int(mes_compra):02d}-{int(dia):02d}",
                descricao, valor, mes, ano,
            ))
        return itens
