# -*- coding: utf-8 -*-
"""Configuração persistente e separação segura dos ambientes de execução."""

import os
import sys
import tempfile
from pathlib import Path

from database.json_database import JsonDatabase


RUNTIME_ENV_VARIABLE = "FINANCE_ASSIST_ENV"
DATA_DIR_VARIABLE = "FINANCE_ASSIST_DATA_DIR"
DB_PATH_VARIABLE = "FINANCE_ASSIST_DB_PATH"
VALID_RUNTIME_ENVIRONMENTS = {"production", "development", "test"}


def get_base_path():
    """Retorna a raiz dos recursos da aplicação."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_runtime_environment(environ=None, frozen=None):
    """Resolve o perfil sem permitir que testes usem dados de produção."""
    environ = os.environ if environ is None else environ
    configured = str(environ.get(RUNTIME_ENV_VARIABLE, "")).strip().lower()
    if configured:
        if configured not in VALID_RUNTIME_ENVIRONMENTS:
            raise ValueError(
                f"{RUNTIME_ENV_VARIABLE} deve ser production, development ou test."
            )
        return configured

    frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if frozen:
        return "production"
    if "pytest" in sys.modules or environ.get("PYTEST_CURRENT_TEST"):
        return "test"
    return "development"


def get_app_data_dir(
    runtime_environment=None,
    environ=None,
    home=None,
    base_dir=None,
):
    """Retorna um diretório gravável e exclusivo para cada ambiente."""
    environ = os.environ if environ is None else environ
    override = str(environ.get(DATA_DIR_VARIABLE, "")).strip()
    if override:
        path = Path(override).expanduser()
    else:
        environment = runtime_environment or get_runtime_environment(environ)
        home = Path(home or Path.home())
        if environment == "production":
            # Caminho histórico do aplicativo empacotado: preserva upgrades.
            path = home / ".financeassist"
        elif environment == "development":
            path = Path(base_dir or get_base_path()) / ".financeassist-development"
        else:
            path = Path(tempfile.gettempdir()) / "finance-assist-tests" / str(os.getpid())

    path = path.resolve()
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


BASE_DIR = get_base_path()
RUNTIME_ENVIRONMENT = get_runtime_environment()
DATA_DIR = get_app_data_dir(RUNTIME_ENVIRONMENT)


IDIOMA_MAP = {
    "Português": "pt", "Inglês": "en", "Espanhol": "es",
    "pt": "pt", "pt_BR": "pt", "pt-BR": "pt",
    "en": "en", "en_US": "en", "en-US": "en",
    "es": "es", "es_ES": "es", "es-ES": "es",
}


def normalizar_idioma(valor):
    return IDIOMA_MAP.get(valor, "pt")


DB_NAME = "financeiro.db"
DEFAULT_DB_PATH = os.path.join(DATA_DIR, DB_NAME)
CONFIG_PATH = os.path.join(DATA_DIR, "configuracoes.json")
DEFAULTS = {
    "idioma": "pt",
    "tema": "Primavera",
    "moeda": "BRL",
    "db_path": DEFAULT_DB_PATH,
    "backup_automatico": False,
    "backup_intervalo_horas": 24,
    "backup_retencao": 7,
    "notificacoes_ativas": True,
    "alerta_intervalo_minutos": 30,
    "mensagem_boas_vindas": True,
}

_config_db = JsonDatabase(file_path=CONFIG_PATH, default_data=DEFAULTS)


def _normalizar_db_path(value):
    if value == ":memory:":
        return value
    path = Path(str(value or DEFAULT_DB_PATH)).expanduser()
    if not path.is_absolute():
        path = Path(DATA_DIR) / path
    return str(path.resolve())


def _normalizar_config(config: dict) -> dict:
    cfg = DEFAULTS.copy()
    if isinstance(config, dict):
        cfg.update(config)
    cfg["idioma"] = normalizar_idioma(cfg.get("idioma"))
    cfg["tema"] = cfg.get("tema") or "Primavera"
    cfg["moeda"] = cfg.get("moeda") or "BRL"
    cfg["db_path"] = _normalizar_db_path(cfg.get("db_path"))
    return cfg


def carregar_config():
    try:
        return _normalizar_config(_config_db.load())
    except Exception:
        return DEFAULTS.copy()


def salvar_config(config: dict):
    try:
        return _config_db.save(_normalizar_config(config))
    except Exception:
        return False


def get_db_path():
    """Obtém o banco do ambiente atual ou um override explícito."""
    override = str(os.environ.get(DB_PATH_VARIABLE, "")).strip()
    if override:
        return _normalizar_db_path(override)
    return carregar_config().get("db_path", DEFAULT_DB_PATH)


DB_PATH = get_db_path()
