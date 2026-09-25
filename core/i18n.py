# core/i18n.py

from core.session import Session

TRADUCOES = {
    "pt": {
        "Configurações": "Configurações",
        "Salvar": "Salvar",
        "Idioma": "Idioma",
        "Tema": "Tema",
        "Moeda": "Moeda"
    },
    "en": {
        "Configurações": "Settings",
        "Salvar": "Save",
        "Idioma": "Language",
        "Tema": "Theme",
        "Moeda": "Currency"
    },
    "es": {
        "Configurações": "Configuraciones",
        "Salvar": "Guardar",
        "Idioma": "Idioma",
        "Tema": "Tema",
        "Moeda": "Moneda"
    }
}

# Textos essenciais ficam disponíveis sem depender do pacote opcional Argos.
TRADUCOES["en"].update({
    "Relatórios": "Reports",
    "Informe de Rendimentos": "Income statement",
    "Ano Base:": "Base year:",
    "Visualizar": "Preview",
    "Imprimir": "Print",
    "Relatório financeiro auxiliar": "Auxiliary financial report",
    "Modelo fiscal por fonte pagadora": "Tax form by payer",
    "Dados fiscais": "Tax data",
    "Adicionar/editar dados fiscais": "Add/edit tax data",
    "Dados fiscais da fonte pagadora": "Payer tax data",
    "Ano-calendário:": "Calendar year:",
    "Fonte pagadora:": "Payer:",
    "CPF/CNPJ da fonte:": "Payer CPF/CNPJ:",
    "Natureza do rendimento:": "Income type:",
    "Informações complementares:": "Additional information:",
    "Dados inválidos": "Invalid data",
})
TRADUCOES["es"].update({
    "Relatórios": "Informes",
    "Informe de Rendimentos": "Informe de ingresos",
    "Ano Base:": "Año base:",
    "Visualizar": "Vista previa",
    "Imprimir": "Imprimir",
    "Relatório financeiro auxiliar": "Informe financiero auxiliar",
    "Modelo fiscal por fonte pagadora": "Modelo fiscal por pagador",
    "Dados fiscais": "Datos fiscales",
    "Adicionar/editar dados fiscais": "Añadir/editar datos fiscales",
    "Dados fiscais da fonte pagadora": "Datos fiscales del pagador",
    "Ano-calendário:": "Año natural:",
    "Fonte pagadora:": "Pagador:",
    "CPF/CNPJ da fonte:": "CPF/CNPJ del pagador:",
    "Natureza do rendimento:": "Naturaleza de los ingresos:",
    "Informações complementares:": "Información adicional:",
    "Dados inválidos": "Datos no válidos",
})

DEFAULT_LANG = "pt"


def _lang_code(idioma: str = None) -> str:
    idioma = idioma or DEFAULT_LANG
    return idioma.replace("-", "_").split("_", 1)[0]


def t(texto: str, idioma: str = None) -> str:
    if not texto:
        return texto

    idioma = _lang_code(
        idioma or Session.get_config("idioma", DEFAULT_LANG)
    )

    return TRADUCOES.get(idioma, {}).get(texto, texto)


def has(texto: str, idioma: str = None) -> bool:
    idioma = _lang_code(
        idioma or Session.get_config("idioma", DEFAULT_LANG)
    )

    return texto in TRADUCOES.get(idioma, {})


def register(idioma: str, chave: str, valor: str):
    idioma = _lang_code(idioma)

    if idioma not in TRADUCOES:
        TRADUCOES[idioma] = {}

    TRADUCOES[idioma][chave] = valor


def get_language_dict(idioma: str) -> dict:
    idioma = _lang_code(idioma)
    return TRADUCOES.get(idioma, {})


def idiomas_disponiveis():
    return list(TRADUCOES.keys())
