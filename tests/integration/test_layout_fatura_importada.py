from models.layouts.fatura_cartao_layout import FaturaCartaoLayoutModel
from services.reconhecer_service import ReconhecimentoService
from services.importacao_service import ImportacaoService

from conftest import criar_cartao, criar_usuario


def test_reconhece_e_normaliza_fatura_csv_estruturada():
    conteudo = [{
        "Data": "05/08/2026",
        "Descricao": "LOJA EXEMPLO",
        "Valor": "R$ 123,45",
        "TipoDocumento": "fatura_cartao",
        "parcela": "03/10",
        "competencia": "08/2026",
    }]
    reconhecimento = ReconhecimentoService().reconhecer_layout(conteudo)
    assert reconhecimento["tipo_documento"] == "fatura_cartao"

    item = reconhecimento["layout"].parse(conteudo)[0]
    assert item["Data"] == "2026-08-05"
    assert item["Valor"] == 123.45
    assert item["Parcela_Atual"] == 3
    assert item["Num_Parcelas"] == 10
    assert (item["Competencia_Mes"], item["Competencia_Ano"]) == (8, 2026)


def test_parcela_malformada_nao_e_inventada():
    item = FaturaCartaoLayoutModel().parse([{
        "Data": "2026-08-05",
        "Descricao": "Compra",
        "Valor": 10,
        "TipoDocumento": "fatura_cartao",
        "parcela": "10/03",
    }])[0]
    assert item["Parcela_Atual"] == 1
    assert item["Num_Parcelas"] == 1


def test_reconhece_colunas_usuais_de_planilha_de_fatura():
    conteudo = [{
        "Datadacompra": "2026-08-05",
        "Descricao": "Compra XLSX",
        "Valor": 10,
        "Parcela": "1/2",
    }]
    reconhecimento = ReconhecimentoService().reconhecer_layout(conteudo)
    assert reconhecimento["tipo_documento"] == "fatura_cartao"
    assert reconhecimento["layout"].parse(conteudo)[0]["Num_Parcelas"] == 2


def test_pdf_textual_generico_nao_e_anunciado_como_fatura_suportada():
    reconhecimento = ReconhecimentoService().reconhecer_layout(
        "Fatura do cartão com lançamentos diversos"
    )
    assert reconhecimento["tipo_documento"] != "fatura_cartao"


def test_pipeline_real_de_fatura_csv_chega_reconciliado(
    db, db_path, tmp_path, monkeypatch
):
    usuario = criar_usuario(db, "pipeline_fatura")
    cartao = criar_cartao(db, usuario)
    arquivo = tmp_path / "fatura.csv"
    arquivo.write_text(
        "Data,Descricao,Valor,Parcela,Competencia\n"
        "05/08/2026,Loja Exemplo,123.45,03/10,08/2026\n",
        encoding="utf-8",
    )
    service = ImportacaoService(db_path)
    monkeypatch.setattr(
        service.categorizacao_service,
        "categorizar",
        lambda *_args: (None, 0.0),
    )

    resultado = service.importar_fatura(
        str(arquivo),
        usuario,
        cartao,
        10,
        lambda _data, _fechamento: (8, 2026),
    )
    assert len(resultado) == 1
    assert resultado[0]["StatusImportacao"] == "NOVO"
    assert resultado[0]["Parcela_Atual"] == 3
    assert resultado[0]["Num_Parcelas"] == 10
