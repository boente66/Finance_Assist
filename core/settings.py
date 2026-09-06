# -*- coding: utf-8 -*-
"""API compatível para consumidores antigos da configuração centralizada."""

from core.config import (
    CONFIG_PATH as ARQUIVO_CONFIG,
    DEFAULTS as CONFIG_PADRAO,
    carregar_config,
    normalizar_idioma,
    salvar_config,
)

__all__ = [
    "ARQUIVO_CONFIG",
    "CONFIG_PADRAO",
    "carregar_config",
    "salvar_config",
    "normalizar_idioma",
]
