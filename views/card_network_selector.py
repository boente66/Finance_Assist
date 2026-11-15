"""Apresentação offline do catálogo fornecido pelo Controller."""
from pathlib import Path

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon

from core.translator_app import TranslatorApp


ICON_DIRECTORY = Path(__file__).resolve().parents[1] / "assets" / "icons" / "card-networks"
_ICONS = {
    "Visa": "visa", "Mastercard": "mastercard", "Elo": "elo",
    "American Express": "amex", "Hipercard": "hipercard", "Diners Club": "diners",
    "Discover": "discover", "JCB": "jcb", "UnionPay": "unionpay", "Maestro": "maestro",
}


def network_icon(network):
    path = ICON_DIRECTORY / (_ICONS.get(network, "generic") + ".svg")
    icon = QIcon(str(path))
    if icon.isNull():
        icon = QIcon(str(ICON_DIRECTORY / "generic.svg"))
    return icon


def populate_network_combo(combo, networks):
    combo.setIconSize(QSize(38, 24))
    combo.addItem(network_icon(None), TranslatorApp.get("Sem bandeira"), None)
    for network in networks:
        # Nomes comerciais não passam pelo tradutor.
        combo.addItem(network_icon(network), network, network)
