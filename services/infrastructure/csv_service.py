import csv
import io
import re
import unicodedata
from datetime import datetime


class CsvService:

    def ler(self, caminho_csv: str):
        if not caminho_csv:
            raise ValueError("Arquivo CSV não informado.")

        texto = self._ler_texto(caminho_csv)
        if not texto.strip():
            return []

        dialect = self._descobrir_dialeto(texto)
        reader = csv.reader(io.StringIO(texto), dialect)

        try:
            headers = next(reader)
        except StopIteration:
            return []

        headers_norm = [self._normalizar_chave(h) for h in headers]
        registros = []

        for row in reader:
            if not row or all(not str(col).strip() for col in row):
                continue

            dados_brutos = {}
            for idx, header in enumerate(headers_norm):
                valor = row[idx] if idx < len(row) else ""
                if header:
                    dados_brutos[header] = valor

            normalizado = self._normalizar_linha(dados_brutos)
            if not normalizado and len(row) >= 15:
                normalizado = self._normalizar_linha({
                    "data": row[6] if len(row) > 6 else "",
                    "descricao": row[8] if len(row) > 8 else "",
                    "favorecido": row[9] if len(row) > 9 else "",
                    "receita": row[10] if len(row) > 10 else "",
                    "despesa": row[11] if len(row) > 11 else "",
                    "saldo": row[12] if len(row) > 12 else "",
                    "categoria": row[14] if len(row) > 14 else "",
                })

            if normalizado:
                registros.append(normalizado)

        return registros

    def _ler_texto(self, caminho_csv: str) -> str:
        encodings = ("utf-8-sig", "utf-8", "cp1252", "latin-1")

        ultimo_erro = None
        for encoding in encodings:
            try:
                with open(caminho_csv, "r", encoding=encoding, newline="") as arquivo:
                    return arquivo.read()
            except UnicodeDecodeError as exc:
                ultimo_erro = exc

        raise UnicodeDecodeError(
            "csv",
            b"",
            0,
            1,
            f"Não foi possível decodificar o CSV. Último erro: {ultimo_erro}"
        )

    def _descobrir_dialeto(self, texto: str):
        amostra = texto[:4096]
        try:
            return csv.Sniffer().sniff(amostra, delimiters=",;|\t")
        except csv.Error:
            return csv.get_dialect("excel")

    def _normalizar_chave(self, valor: str) -> str:
        if valor is None:
            return ""

        texto = unicodedata.normalize("NFKD", str(valor))
        texto = texto.encode("ascii", "ignore").decode("ascii")
        texto = texto.lower().strip()
        texto = re.sub(r"[^a-z0-9]+", "_", texto)
        return texto.strip("_")

    def _normalizar_linha(self, dados: dict):
        data = self._parse_data(
            dados.get("data")
            or dados.get("data_lancamento")
            or dados.get("data_movimento")
        )

        descricao = (
            (dados.get("descricao") or "").strip()
            or (dados.get("favorecido") or "").strip()
        )

        if not data or not descricao:
            return None

        valor = self._parse_valor(
            dados.get("receita"),
            dados.get("despesa"),
            dados.get("valor"),
            dados.get("saldo")
        )

        if valor == 0.0:
            return None

        categoria_raw = (
            (dados.get("categoria") or "").strip()
            or (dados.get("categoria_pai") or "").strip()
        )

        categoria_pai, subcategoria = self._parse_categoria(categoria_raw)

        resultado = {
            "Data": data,
            "Descricao": descricao,
            "Valor": valor,
            "CategoriaPai": categoria_pai,
            "Subcategoria": subcategoria,
        }
        campos_fatura = {
            "parcela", "parcelas", "numero_parcela", "num_parcelas",
            "parcela_atual", "competencia", "competencia_mes",
            "competencia_ano", "fatura", "cartao",
        }
        if campos_fatura.intersection(dados):
            resultado["TipoDocumento"] = "fatura_cartao"
            for campo in campos_fatura:
                if campo in dados:
                    resultado[campo] = dados.get(campo)
        return resultado

    def _parse_data(self, valor: str):
        if not valor:
            return None

        valor = str(valor).strip()
        formatos = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y")

        for formato in formatos:
            try:
                return datetime.strptime(valor, formato).strftime("%Y-%m-%d")
            except ValueError:
                continue

        return None

    def _parse_valor(self, receita, despesa, valor, saldo):
        if receita not in (None, ""):
            return abs(self._to_float(receita))

        if despesa not in (None, ""):
            return -abs(self._to_float(despesa))

        if valor not in (None, ""):
            return self._to_float(valor)

        if saldo not in (None, ""):
            return self._to_float(saldo)

        return 0.0

    def _to_float(self, valor):
        texto = str(valor).strip()
        if not texto:
            return 0.0

        negativo = False

        if texto.startswith("(") and texto.endswith(")"):
            negativo = True
            texto = texto[1:-1]

        texto = re.sub(r"[^\d,.\-]", "", texto)

        if "," in texto and "." in texto:
            texto = texto.replace(".", "").replace(",", ".")
        elif "," in texto:
            texto = texto.replace(",", ".")

        try:
            numero = float(texto)
        except ValueError:
            return 0.0

        if negativo:
            numero = -abs(numero)

        return numero

    def _parse_categoria(self, categoria_str: str):
        categoria_str = (categoria_str or "").strip()

        if not categoria_str:
            return None, None

        if "<transferencia>" in categoria_str.lower():
            return "Transferência", None

        if ":" in categoria_str:
            partes = [parte.strip() for parte in categoria_str.split(":") if parte.strip()]
            if not partes:
                return None, None

            categoria_pai = partes[0]
            subcategoria = ":".join(partes[1:]) if len(partes) > 1 else None
            return categoria_pai, subcategoria

        return categoria_str, None
