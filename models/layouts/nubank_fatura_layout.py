"""Layout validado com faturas reais Nubank em PDF."""

import re

from models.layouts.fatura_pdf_base import FaturaPdfBaseLayout


class NubankFaturaLayoutModel(FaturaPdfBaseLayout):
    nome = "Nubank PDF"

    def parse(self, conteudo):
        if not isinstance(conteudo, str):
            return []
        cabecalho = re.search(r"FATURA\s+(\d{1,2})\s+([A-ZÇ]{3})\s+(\d{4})", conteudo, re.I)
        if not cabecalho:
            return []
        _, mes_nome, ano_texto = cabecalho.groups()
        mes = self.MESES[self.texto_sem_acentos(mes_nome)[:3]]
        ano = int(ano_texto)
        padrao = re.compile(
            r"^\s*(\d{1,2})\s+([A-ZÇ]{3})\s+(?:••••\s*\d{4}\s+)?(.+?)\s+([−-]?R\$\s*[\d.]+,\d{2})\s*$",
            re.MULTILINE | re.I,
        )
        itens = []
        for match in padrao.finditer(conteudo):
            dia, mes_compra, descricao, valor_texto = match.groups()
            descricao_normalizada = self.texto_sem_acentos(descricao)
            valor = self.valor_br(valor_texto)
            if (
                valor is None or valor <= 0
                or descricao_normalizada.startswith("PAGAMENTO EM")
                or descricao_normalizada.startswith("SALDO RESTANTE")
            ):
                continue
            data = self.data_abreviada(dia, mes_compra, ano, mes)
            itens.append(self.item(data, descricao, valor, mes, ano))
        parcelados = re.compile(
            r"(\d{1,2})\s+([A-ZÇ]{3})\s*\n\s*([^\n]+?Parcela\s+\d+/\d+)\s*\n"
            r"(?:[^\n]*\n){0,3}?[^\n]*parcelas?\s+de\s+R\$\s*[\d.]+,\d{2}\.R\$\s*([\d.]+,\d{2})",
            re.I,
        )
        for match in parcelados.finditer(conteudo):
            dia, mes_compra, descricao, valor_texto = match.groups()
            data = self.data_abreviada(dia, mes_compra, ano, mes)
            item = self.item(data, descricao, self.valor_br(valor_texto), mes, ano)
            if not any(x["Data"] == data and x["Descricao"] == item["Descricao"] for x in itens):
                itens.append(item)
        itens.sort(key=lambda item: (item["Data"], item["Descricao"]))
        return itens
