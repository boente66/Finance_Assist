from PyQt5.QtCore import QDate, QLocale
from datetime import datetime, date
import re
from core.session import Session


class DateFormatter:

    # ======================================================
    # ISO → BR (YYYY-MM-DD → DD/MM/YYYY)
    # ======================================================
    @staticmethod
    def iso_to_br(date_str: str) -> str:
        if not date_str:
            return ""

        try:
            if isinstance(date_str, (datetime, date)):
                return date_str.strftime("%d/%m/%Y")

            dt = datetime.strptime(str(date_str), "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")

        except Exception:
            return str(date_str)

    # ======================================================
    # BR → ISO (DD/MM/YYYY → YYYY-MM-DD)
    # ======================================================
    @staticmethod
    def br_to_iso(date_str: str) -> str:
        if not date_str:
            return ""

        try:
            if isinstance(date_str, (datetime, date)):
                return date_str.strftime("%Y-%m-%d")

            dt = datetime.strptime(str(date_str), "%d/%m/%Y")
            return dt.strftime("%Y-%m-%d")

        except Exception:
            return str(date_str)

    # ======================================================
    # FORMATO LONGO (ex: 05 de março de 2026)
    # ======================================================
    @staticmethod
    def format_long(date_str: str, locale_code="pt_BR") -> str:

        if not date_str:
            return ""

        try:
            dt = QDate.fromString(str(date_str), "yyyy-MM-dd")

            if not dt.isValid():
                return str(date_str)

            locale = QLocale(locale_code)
            return locale.toString(dt, QLocale.LongFormat)

        except Exception:
            return str(date_str)

    # ======================================================
    # DATA DE HOJE ISO
    # ======================================================
    @staticmethod
    def today_iso() -> str:
        return datetime.today().strftime("%Y-%m-%d")

    # ======================================================
    # US → BR (MM/DD/YYYY ou MM-DD-YYYY)
    # ======================================================
    @staticmethod
    def us_to_br(date_str: str) -> str:

        if not date_str:
            return ""

        # datetime / date
        if isinstance(date_str, (datetime, date)):
            return date_str.strftime("%d/%m/%Y")

        # QDate
        if isinstance(date_str, QDate):
            if date_str.isValid():
                return date_str.toString("dd/MM/yyyy")
            return ""

        s = str(date_str)

        # remove espaços ao redor de separadores
        s = re.sub(r'\s*([/-])\s*', r'\1', s)

        for fmt in ("%m/%d/%Y", "%m-%d-%Y"):
            try:
                dt = datetime.strptime(s, fmt)
                return dt.strftime("%d/%m/%Y")
            except Exception:
                continue

        return s

    # ======================================================
    # VALIDADOR ISO
    # ======================================================
    @staticmethod
    def is_valid_iso(date_str: str) -> bool:
        try:
            datetime.strptime(str(date_str), "%Y-%m-%d")
            return True
        except Exception:
            return False

    # ======================================================
    # VALIDADOR BR
    # ======================================================
    @staticmethod
    def is_valid_br(date_str: str) -> bool:
        try:
            datetime.strptime(str(date_str), "%d/%m/%Y")
            return True
        except Exception:
            return False


    @staticmethod
    def map_nome_mes(mes: int) -> str:
        idioma = Session.get_config("idioma", "pt")
        idioma = str(idioma).replace("-", "_").split("_", 1)[0]
        meses = {
            "pt": [
                "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
            ],
            "en": [
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ],
            "es": [
                "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
            ]
        }
        lista = meses.get(idioma, meses["pt"])

        return lista[mes - 1] if 1 <= mes <= 12 else "Mês Inválido"
























































