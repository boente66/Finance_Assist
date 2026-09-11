import pytest
from models.layouts.nubank_fatura_layout import NubankFaturaLayoutModel
from services.reconhecer_service import ReconhecimentoService

PICPAY = """Esta é a sua fatura de Agosto.
Vencimento: 25/08/2026 | Fechamento: 19/08/2026
PicPay Mastercard® PLATINUM
Total da sua fatura R$ 285,65
Transações Nacionais
04/07 IOF DIARIO PARCELADO 0,21
04/07 IOF ADICIONAL PARCELADO 0,19
04/07 FIN DROGARIA LIDER 2 . 49,99
17/07 PAGAMENTO DE FATURA -214,08
18/08 CREDITO PULA COMPRA -44,90
18/07 NETFLIX ENTRETENIMENTO 44,90
28/07 GOOGLE ONE 49,99
01/08 99PAY *RECARGA SALDO 7,45
05/08 DL*UBERRIDES 3,93
12/08 GOOGLE CHATGPT 95,99
14/08 GOOGLE MICROSOFT ONED 33,00
18/08 NETFLIX.COM 44,90
"""

NUBANK = """Nubank
FATURA 27 AGO 2026 EMISSÃO E ENVIO 20 AGO 2026
RESUMO DA FATURA ATUAL
TRANSAÇÕES DE 20 JUL A 20 AGO
20 JUL •••• 5514 Shopee *Partirjuntos - Parcela 4/4 R$ 5,20
22 JUL Plano NuCel R$ 25,00
23 JUL Raia Drogasil - NuPay R$ 37,49
27 JUL Nubank+ R$ 29,00
09 AGO 99Food - NuPay R$ 41,03
20 JUL Pagamento em 20 JUL −R$ 208,22
20 JUL
 Cliente exemplo - Parcela 6/6
Total a pagar: R$ 420,70 (valor da transação de R$ 300,00 + R$ 4,32 de IOF
+ R$ 116,38 de juros) divididos em 6 parcelas de R$ 70,12.R$ 70,12
27 JUL Saldo restante da fatura anterior R$ 0,00
"""

ITAU = """Banco Itaú S.A.
Vencimento: 24/08/2026 = Total desta fatura 63,40
L Lançamentos atuais 69,40
Lançamentos: compras e saques
CLIENTE EXEMPLO
DATA ESTABELECIMENTO VALOR EM R$
21/07 Carteira digital 5,97 Encargos cobrados nesta fatura
25/07 LOJA EXEMPLO 01/05 27,76
26/07 ASSINATURA DIGITAL 8,34 Multa por atraso 2,00 % 0,00
26/07 TRANSPORTE 6,03
26/07 SERVICO ONLINE 5,99
27/07 SERVICO ONLINE 6,00
29/07 TRANSPORTE 4,32 Valor original da dívida 0,00
10/08 TRANSPORTE 4,99 % juros sobre dívida origem 0,00%
Lançamentos no cartão 69,40
L Total dos lançamentos atuais 69,40
Compras parceladas - próximas faturas
25/07 LOJA EXEMPLO 02/05 27,76
"""


@pytest.mark.parametrize("texto,nome,total,quantidade", [
    (PICPAY, "fatura_picpay_pdf", 330.55, 10),
    (NUBANK, "fatura_nubank_pdf", 207.84, 6),
    (ITAU, "fatura_itau_pdf", 69.40, 8),
])
def test_reconhece_layouts_reais_e_fecha_total(texto, nome, total, quantidade):
    reconhecimento = ReconhecimentoService().reconhecer_layout(texto)
    assert reconhecimento["nome"] == nome
    itens = reconhecimento["layout"].parse(texto)
    assert len(itens) == quantidade
    assert sum(item["Valor"] for item in itens) == pytest.approx(total)
    assert all(item["Competencia_Mes"] == 8 for item in itens)
    assert not any("PAGAMENTO" in item["Descricao"].upper() for item in itens)


def test_parcelas_e_ano_anterior_sao_preservados():
    itens = NubankFaturaLayoutModel().parse(NUBANK)
    parcela = next(item for item in itens if "6/6" in item["Descricao"])
    assert (parcela["Parcela_Atual"], parcela["Num_Parcelas"]) == (6, 6)
    assert parcela["Data"] == "2026-07-20"


def test_layout_generico_nao_aceita_planilha_ambigua():
    resultado = ReconhecimentoService().reconhecer_layout([{
        "Data": "05/08/2026", "Descricao": "Compra", "Valor": "123,45"
    }])
    assert resultado["tipo_documento"] != "fatura_cartao"
