# -*- coding: utf-8 -*-


class CategoriaMapModel:
    """
    Base de conhecimento da categorização automática.

    Este model NÃO acessa banco de dados.
    NÃO utiliza IA.
    NÃO possui dependências externas.

    Seu objetivo é fornecer uma estrutura única contendo:

    - Categorias padrão
    - Subcategorias padrão
    - Palavras-chave
    - Sinônimos

    Utilizado por:

    - CategoryService
    - CategorizacaoService
    """

    CATEGORIAS = [

        # =====================================================
        # RECEITAS
        # =====================================================
        {
            "CategoriaPai": "Receitas",
            "Subcategoria": "Salário",
            "Palavras": [
                "salario",
                "salário",
                "provento",
                "holerite",
                "contracheque",
                "folha",
                "pagamento",
                "remuneracao",
                "remuneração",
            ]
        },

        {
            "CategoriaPai": "Receitas",
            "Subcategoria": "Rendimentos",
            "Palavras": [
                "rendimento",
                "rendimentos",
                "juros",
                "aplicacao",
                "aplicação",
                "cdb",
                "cdi",
                "tesouro",
                "dividendo",
                "dividendos",
            ]
        },

        {
            "CategoriaPai": "Receitas",
            "Subcategoria": "Reembolso",
            "Palavras": [
                "reembolso",
                "estorno",
                "devolucao",
                "devolução",
            ]
        },

        # =====================================================
        # ALIMENTAÇÃO
        # =====================================================
        {
            "CategoriaPai": "Alimentação",
            "Subcategoria": "Mercado",
            "Palavras": [
                "mercado",
                "supermercado",
                "hipermercado",
                "carrefour",
                "extra",
                "assai",
                "atacadao",
                "atacadão",
                "savegnago",
                "condor",
                "big",
            ]
        },

        {
            "CategoriaPai": "Alimentação",
            "Subcategoria": "Restaurante",
            "Palavras": [
                "restaurante",
                "lanchonete",
                "lanche",
                "pizza",
                "hamburguer",
                "hambúrguer",
                "churrascaria",
                "bar",
            ]
        },

        {
            "CategoriaPai": "Alimentação",
            "Subcategoria": "Delivery",
            "Palavras": [
                "ifood",
                "99 food",
                "delivery",
                "rappi",
                "ubereats",
            ]
        },

        {
            "CategoriaPai": "Alimentação",
            "Subcategoria": "Café",
            "Palavras": [
                "coffee",
                "cafe",
                "café",
                "gran coffee",
                "starbucks",
            ]
        },

        # =====================================================
        # TRANSPORTE
        # =====================================================
        {
            "CategoriaPai": "Transporte",
            "Subcategoria": "Aplicativo",
            "Palavras": [
                "uber",
                "99",
                "99 tecnolog",
                "99app",
                "cabify",
            ]
        },

        {
            "CategoriaPai": "Telefone",
            "Subcategoria" : "Plano Controle/Pos Pago",
            "Palavras": [
             "Pix Claro S.A",
             "Claro S.A",
             "Vivo S.A",
             "Vivo",
             "Tim",
             "NuCel",
             "Plano NuCel"

            ]
        },


        {
            "CategoriaPai": "Transporte",
            "Subcategoria": "Combustível",
            "Palavras": [
                "posto",
                "shell",
                "ipiranga",
                "petrobras",
                "ale",
                "combustivel",
                "combustível",
                "gasolina",
                "etanol",
                "diesel",
            ]
        },

        {
            "CategoriaPai": "Transporte",
            "Subcategoria": "Transporte Público",
            "Palavras": [
                "onibus",
                "ônibus",
                "metro",
                "metrô",
                "trem",
                "bilhete",
            ]
        },

        # =====================================================
        # MORADIA
        # =====================================================
        {
            "CategoriaPai": "Moradia",
            "Subcategoria": "Aluguel",
            "Palavras": [
                "aluguel",
                "locacao",
                "locação",
            ]
        },

        {
            "CategoriaPai": "Moradia",
            "Subcategoria": "Energia",
            "Palavras": [
                "energia",
                "enel",
                "cemig",
                "cpfl",
                "light",
            ]
        },

        {
            "CategoriaPai": "Moradia",
            "Subcategoria": "Água",
            "Palavras": [
                "agua",
                "água",
                "saneamento",
                "sabesp",
                "copasa",
            ]
        },

        {
            "CategoriaPai": "Moradia",
            "Subcategoria": "Internet",
            "Palavras": [
                "internet",
                "claro",
                "vivo",
                "tim",
                "oi",
                "fibra",
            ]
        },

        # =====================================================
        # SAÚDE
        # =====================================================
        {
            "CategoriaPai": "Saúde",
            "Subcategoria": "Farmácia",
            "Palavras": [
                "farmacia",
                "farmácia",
                "drogaria",
                "droga",
                "raia",
                "pacheco",
                "pague menos",
            ]
        },

        {
            "CategoriaPai": "Saúde",
            "Subcategoria": "Consulta",
            "Palavras": [
                "consulta",
                "hospital",
                "clinica",
                "clínica",
                "medico",
                "médico",
            ]
        },

        # =====================================================
        # CARTÕES
        # =====================================================
        {
            "CategoriaPai": "Cartões",
            "Subcategoria": "Pagamento de Fatura",
            "Palavras": [
                "fatura paga",
                "pagamento fatura",
                "cartao",
                "cartão",
                "itau multipl",
                "nubank",
            ]
        },

        # =====================================================
        # INVESTIMENTOS
        # =====================================================
        {
            "CategoriaPai": "Investimentos",
            "Subcategoria": "Aplicação",
            "Palavras": [
                "aplicacao",
                "aplicação",
                "cofrinhos",
                "investimento",
                "cdb",
            ]
        },

        {
            "CategoriaPai": "Investimentos",
            "Subcategoria": "Resgate",
            "Palavras": [
                "resgate",
                "resgate cdb",
                "resgate investimento",
            ]
        },

        # =====================================================
        # TRANSFERÊNCIAS
        # =====================================================
        {
            "CategoriaPai": "Transferências",
            "Subcategoria": "PIX / TED",
            "Palavras": [
                "pix",
                "ted",
                "doc",
                "transferencia",
                "transferência",
            ]
        },

        # =====================================================
        # OUTROS
        # =====================================================
        {
            "CategoriaPai": "Outros",
            "Subcategoria": "Diversos",
            "Palavras": []
        },
    ]

    @classmethod
    def get_all(cls):
        return cls.CATEGORIAS

    @classmethod
    def get_categorias_pai(cls):
        return sorted(
            {c["CategoriaPai"] for c in cls.CATEGORIAS}
        )

    @classmethod
    def get_subcategorias(cls, categoria_pai):
        return [
            c
            for c in cls.CATEGORIAS
            if c["CategoriaPai"] == categoria_pai
        ]