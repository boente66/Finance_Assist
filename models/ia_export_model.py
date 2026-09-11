# models/ia_export_model.py

class IAExportModel:
    """
    Model responsável SOMENTE por escrever arquivos.
    """

    def __init__(self):
        self.data = []

    def set_data(self, data: list):
        self.data = data

    def export_to_csv(self, file_path: str) -> bool:
        try:
            import pandas as pd
        except ImportError as exc:
            raise RuntimeError(
                "Dependência 'pandas' ausente. Instale o ambiente completo "
                "para exportar CSV."
            ) from exc

        df = pd.DataFrame(self.data)
        df.to_csv(file_path, index=False)
        return True

    def export_to_xlsx(self, file_path: str) -> bool:
        try:
            import pandas as pd
        except ImportError as exc:
            raise RuntimeError(
                "Dependência 'pandas' ausente. Instale o ambiente completo "
                "para exportar XLSX."
            ) from exc

        df = pd.DataFrame(self.data)
        df.to_excel(file_path, index=False)
        return True

    def export_statement_pdf(self, file_path, conta, transacoes, data_inicio, data_fim):
        from utilitarios.financial_pdf import FinancialPDF
        return FinancialPDF.extrato(file_path, conta, transacoes, data_inicio, data_fim)
