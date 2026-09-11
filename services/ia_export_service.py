# services/ia_export_service.py

from models.ia_export_model import IAExportModel


class IAExportService:
    """
    Serviço responsável por TODA a lógica de exportação.
    """

    def __init__(self):
        self.model = IAExportModel()

    def exportar_extrato_conta(
        self,
        transacoes: list,
        conta: dict,
        data_inicio: str,
        data_fim: str,
        formato: str,
        caminho_arquivo: str
    ) -> bool:
        """
        Exporta extrato da conta no formato escolhido.
        """

        if not transacoes:
            raise ValueError("Não há dados para exportar.")

        # prepara dados (simples e limpo)
        dados = []
        for t in transacoes:
            dados.append({
                "Data": t["Data"],
                "Descrição": t["Descricao"],
                "Valor": t["Valor"],
                "Categoria": t.get("Categoria", ""),
                "Favorecido": t.get("Favorecido", ""),
            })

        self.model.set_data(dados)

        formato = formato.upper()

        if formato == "CSV":
            return self.model.export_to_csv(caminho_arquivo)

        if formato == "XLSX":
            return self.model.export_to_xlsx(caminho_arquivo)

        if formato == "PDF":
            return self.model.export_statement_pdf(
                caminho_arquivo, conta, transacoes, data_inicio, data_fim
            )

        raise ValueError("Formato de exportação inválido.")
