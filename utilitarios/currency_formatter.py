from PyQt5.QtCore import QLocale


class CurrencyFormatter:
    """
    Utilitário para formatação e conversão de valores monetários.
    Usa QLocale (Qt) para evitar alterar locale global do sistema.
    """

    DEFAULT_LOCALE = "pt_BR"

    # ==========================================================
    # FORMATAÇÃO
    # ==========================================================
    @staticmethod
    def format(value: float, locale_code: str = None) -> str:
        """
        Formata um valor como moeda utilizando QLocale.

        Args:
            value (float): Valor numérico.
            locale_code (str): Código do locale (ex: "pt_BR", "en_US").

        Returns:
            str: Valor formatado como moeda.
        """
        if locale_code is None:
            from core.regional_format import RegionalFormat
            locale_code = RegionalFormat.locale().name()

        try:
            locale = QLocale(locale_code)
            return locale.toCurrencyString(float(value))
        except Exception:
            # fallback seguro
            return f"{float(value):.2f}"

    # ==========================================================
    # CONVERSÃO PARA FLOAT
    # ==========================================================
    @staticmethod
    def to_float(value) -> float:
        """
        Converte string monetária para float.

        Aceita:
        - "R$ 1.234,56"
        - "$1,234.56"
        - "1234,56"
        - "1234.56"
        """

        if isinstance(value, (int, float)):
            return float(value)

        if not value:
            raise ValueError("Valor vazio não pode ser convertido.")

        try:
            # Remove símbolos monetários comuns
            value = (
                str(value)
                .replace("US$", "")
                .replace("R$", "")
                .replace("$", "")
                .replace("€", "")
                .replace("£", "")
                .strip()
            )

            value = value.replace("\u00a0", "").replace("\u202f", "").replace(" ", "")
            if value.startswith("(") and value.endswith(")"):
                value = "-" + value[1:-1]
            if "," in value and "." in value:
                decimal = "," if value.rfind(",") > value.rfind(".") else "."
                value = value.replace("." if decimal == "," else ",", "").replace(decimal, ".")
            elif "," in value:
                from core.regional_format import RegionalFormat
                if RegionalFormat.language() == "en" and all(len(x) == 3 for x in value.split(",")[1:]):
                    value = value.replace(",", "")
                else:
                    value = value.replace(",", ".")
            elif "." in value:
                from core.regional_format import RegionalFormat
                if RegionalFormat.language() != "en" and all(len(x) == 3 for x in value.split(".")[1:]):
                    value = value.replace(".", "")

            return float(value)

        except Exception:
            raise ValueError(
                f"Não foi possível converter '{value}' para float."
            )

    # ==========================================================
    # CONVERSÃO PARA INT
    # ==========================================================
    @staticmethod
    def to_int(value) -> int:
        """
        Converte valor monetário para inteiro (descarta centavos).
        """
        return int(CurrencyFormatter.to_float(value))