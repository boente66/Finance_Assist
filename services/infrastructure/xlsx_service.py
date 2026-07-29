# -*- coding: utf-8 -*-
import re
import unicodedata


class XlsxService:

    @staticmethod
    def _normalizar_chave(chave) -> str:
        chave = str(chave or "").strip()

        chave = unicodedata.normalize("NFKD", chave)
        chave = chave.encode("ASCII", "ignore").decode("ASCII")

        chave = re.sub(r"\s+", "", chave)

        return chave

    @classmethod
    def _normalizar_linha(cls, linha: dict) -> dict:
        if not isinstance(linha, dict):
            return {}

        return {
            cls._normalizar_chave(chave): ("" if valor is None else valor)
            for chave, valor in linha.items()
        }

    def ler(self, caminho_xlsx: str):
        if not caminho_xlsx:
            raise ValueError("Arquivo XLSX não informado.")

        try:
            import pandas as pd

        except ImportError as exc:
            raise RuntimeError(
                "Dependência 'pandas' ausente. "
                "Instale o ambiente completo para importar XLSX."
            ) from exc

        try:
            df = pd.read_excel(caminho_xlsx)

            df = df.dropna(how="all")
            df = df.fillna("")

            dados = df.to_dict(orient="records")

            return [
                self._normalizar_linha(linha)
                for linha in dados
            ]

        except Exception as e:
            raise RuntimeError(
                f"Erro ao ler XLSX: {e}"
            ) from e