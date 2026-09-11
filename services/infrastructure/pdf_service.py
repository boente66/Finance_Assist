from utilitarios.makepdf import MakePDF


class PdfService:
    """
    Serviço de infraestrutura para manipulação de PDF.
    NÃO contém regra de negócio.
    """

    def ler_texto(self, caminho_arquivo: str, senha: str | None = None) -> str | None:
        if not caminho_arquivo:
            return None

        return MakePDF.ler_pdf(caminho_arquivo, senha)

    def gerar_pdf(
        self,
        caminho_arquivo: str,
        titulo: str,
        conteudo: str
    ) -> bool:
        return MakePDF.gerar_pdf(
            caminho_arquivo,
            titulo,
            conteudo
        )

    def ler_bytes(self, caminho_arquivo: str) -> bytes | None:
        if not caminho_arquivo:
            return None

        return MakePDF.ler_bytes(caminho_arquivo)
