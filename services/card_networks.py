"""Catálogo de domínio; valores comerciais são independentes do idioma da UI.

Inclui redes históricas para registrar cartões legados. Não informa aceitação
comercial atual nem identifica a bandeira a partir do nome/emissor do cartão.
"""

CARD_NETWORKS = (
    "Visa", "Mastercard", "Elo", "American Express", "Hipercard",
    "Diners Club", "Discover", "JCB", "UnionPay", "Maestro", "Cabal",
    "Banescard", "Aura", "Sorocred",
)


def normalize_card_network(value):
    """Retorna nome comercial canônico ou None; rejeita valores fora do catálogo."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Bandeira inválida.")
    value = value.strip()
    if not value or value.casefold() == "sem bandeira":
        return None
    for network in CARD_NETWORKS:
        if value.casefold() == network.casefold():
            return network
    raise ValueError("Bandeira inválida.")
