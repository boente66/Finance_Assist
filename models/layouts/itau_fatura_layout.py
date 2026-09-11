"""Layout validado com faturas reais Itaú Mastercard em PDF."""

import re

from models.layouts.fatura_pdf_base import FaturaPdfBaseLayout


class ItauFaturaLayoutModel(FaturaPdfBaseLayout):
    nome = "Itaú Mastercard PDF"

    def parse(self, conteudo):
        if not isinstance(conteudo, str):
            return []
        vencimento = re.search(r"Vencimento:\s*(\d{2})/(\d{2})/(20\d{2})", conteudo, re.I)
        if not vencimento:
            vencimento = re.search(r"Data de Vencimento\s+.*?(\d{2})/(\d{2})/(20\d{2})", conteudo, re.I | re.S)
        if not vencimento:
            return []
        _, mes_texto, ano_texto = vencimento.groups()
        mes, ano = int(mes_texto), int(ano_texto)

        inicio = re.search(r"Lançamentos:\s*compras e saques", conteudo, re.I)
        if not inicio:
            return []
        trecho = conteudo[inicio.end():]
        fim = re.search(r"(?:Lançamentos no cartão|L\s+Total dos lançamentos atuais)", trecho, re.I)
        if fim:
            trecho = trecho[:fim.start()]

        padrao = re.compile(
            r"^[ \t]*(\d{2})/(\d{2})[ \t]+(.+?)[ \t]+"
            r"(-?\d{1,3}(?:\.\d{3})*,\d{2})(?:[ \t]+.*)?$",
            re.MULTILINE,
        )
        itens = []
        for match in padrao.finditer(trecho):
            dia, mes_compra, descricao, valor_texto = match.groups()
            valor = self.valor_br(valor_texto)
            if valor is None or valor <= 0:
                continue
            ano_compra = ano - (1 if int(mes_compra) > mes else 0)
            itens.append(self.item(
                f"{ano_compra:04d}-{int(mes_compra):02d}-{int(dia):02d}",
                descricao, valor, mes, ano,
            ))
        return itens
