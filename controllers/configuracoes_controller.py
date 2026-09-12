# -*- coding: utf-8 -*-
import logging

from services.argos_service import ArgosService
from core.session import Session
from core.theme_manager import ThemeManager
from core.translator_app import TranslatorApp

from core.settings import (
    CONFIG_PADRAO,
    carregar_config,
    salvar_config,
    normalizar_idioma,
)

logger = logging.getLogger(__name__)


class ConfiguracoesController:
    """
    Controller de configurações globais da aplicação.

    Responsabilidades:
    - Ler configuração atual da Session.
    - Aplicar configurações em runtime.
    - Salvar configurações globais no configuracoes.json.
    - Controlar localização global do banco via db_path.
    - Não salvar preferência individual do usuário.

    Persistência global:
    core/settings.py -> JsonDatabase -> configuracoes.json

    Preferências do usuário logado pertencem ao domínio Usuário:
    UserController -> UserService -> UserModel -> SQLite usuarios.
    """

    DEFAULT_CONFIG = CONFIG_PADRAO

    def __init__(self):
        self.argos_service = ArgosService()

    # ==================================================
    # PERMISSÃO
    # ==================================================
    def _is_admin(self):
        usuario = Session.get_usuario()

        if not usuario:
            return False

        return usuario.get("Nivel_Acesso") == "admin"

    # ==================================================
    # CONFIG ATUAL / SESSION
    # ==================================================
    def obter_configuracoes(self):
        persistida = carregar_config() or {}
        return {
            "tema": Session.get_config(
                "tema",
                self.DEFAULT_CONFIG["tema"]
            ),
            "idioma": Session.get_config(
                "idioma",
                self.DEFAULT_CONFIG["idioma"]
            ),
            "moeda": Session.get_config(
                "moeda",
                self.DEFAULT_CONFIG["moeda"]
            ),
            "db_path": Session.get_config(
                "db_path",
                self.DEFAULT_CONFIG["db_path"]
            ),
            "backup_automatico": bool(persistida.get("backup_automatico", False)),
            "backup_intervalo_horas": int(persistida.get("backup_intervalo_horas", 24)),
            "backup_retencao": int(persistida.get("backup_retencao", 7)),
            "notificacoes_ativas": bool(persistida.get("notificacoes_ativas", True)),
            "alerta_intervalo_minutos": int(persistida.get("alerta_intervalo_minutos", 30)),
            "mensagem_boas_vindas": bool(persistida.get("mensagem_boas_vindas", True)),
        }

    # ==================================================
    # CONFIGURAÇÕES GLOBAIS / JSON
    # ==================================================
    def obter_configuracoes_globais(self):
        try:
            config = carregar_config() or {}

            return {
                "tema": config.get(
                    "tema",
                    self.DEFAULT_CONFIG["tema"]
                ),
                "idioma": normalizar_idioma(
                    config.get(
                        "idioma",
                        self.DEFAULT_CONFIG["idioma"]
                    )
                ),
                "moeda": config.get(
                    "moeda",
                    self.DEFAULT_CONFIG["moeda"]
                ),
                "db_path": config.get(
                    "db_path",
                    self.DEFAULT_CONFIG["db_path"]
                ),
                "backup_automatico": bool(config.get("backup_automatico", False)),
                "backup_intervalo_horas": int(config.get("backup_intervalo_horas", 24)),
                "backup_retencao": int(config.get("backup_retencao", 7)),
                "notificacoes_ativas": bool(config.get("notificacoes_ativas", True)),
                "alerta_intervalo_minutos": int(config.get("alerta_intervalo_minutos", 30)),
                "mensagem_boas_vindas": bool(config.get("mensagem_boas_vindas", True)),
            }

        except Exception:
            logger.exception("Erro ao obter configurações globais")
            return self.DEFAULT_CONFIG.copy()

    def set_configuracoes_globais(
        self,
        idioma,
        tema,
        moeda,
        db_path=None,
        backup_automatico=False,
        backup_intervalo_horas=24,
        backup_retencao=7,
        notificacoes_ativas=True,
        alerta_intervalo_minutos=30,
        mensagem_boas_vindas=True,
    ):
        """
        Salva padrão global no configuracoes.json.

        Apenas administradores podem alterar configurações globais.

        Observação:
        - db_path é salvo para o próximo início da aplicação.
        - Não troca conexão SQLite em tempo real.
        """

        try:
            if not self._is_admin():
                raise PermissionError(
                    "Apenas administradores podem alterar configurações globais."
                )

            config = carregar_config() or {}

            config["idioma"] = normalizar_idioma(
                idioma
                or config.get("idioma")
                or self.DEFAULT_CONFIG["idioma"]
            )

            config["tema"] = (
                tema
                or config.get("tema")
                or self.DEFAULT_CONFIG["tema"]
            )

            config["moeda"] = (
                moeda
                or config.get("moeda")
                or self.DEFAULT_CONFIG["moeda"]
            )

            config["db_path"] = (
                db_path
                or config.get("db_path")
                or self.DEFAULT_CONFIG["db_path"]
            )
            config["backup_automatico"] = bool(backup_automatico)
            config["backup_intervalo_horas"] = max(1, int(backup_intervalo_horas))
            config["backup_retencao"] = max(1, int(backup_retencao))
            config["notificacoes_ativas"] = bool(notificacoes_ativas)
            config["alerta_intervalo_minutos"] = max(5, int(alerta_intervalo_minutos))
            config["mensagem_boas_vindas"] = bool(mensagem_boas_vindas)

            if not salvar_config(config):
                raise RuntimeError(
                    "Não foi possível salvar as configurações globais."
                )

            self.set_idioma(config["idioma"])
            self.set_tema(config["tema"])
            self.set_moeda(config["moeda"])
            self.set_db_path(config["db_path"])

            return True

        except Exception:
            logger.exception("Erro ao salvar configurações globais")
            return False

    # ==================================================
    # APLICAÇÃO EM RUNTIME
    # ==================================================
    def set_tema(self, tema, app=None):
        try:
            tema = tema or self.DEFAULT_CONFIG["tema"]

            Session.set_config("tema", tema)
            ThemeManager.definir_tema(tema, app)

            return True

        except Exception:
            logger.exception("Erro ao aplicar tema")
            return False

    def set_idioma(self, idioma):
        try:
            idioma = normalizar_idioma(
                idioma or self.DEFAULT_CONFIG["idioma"]
            )

            Session.set_config("idioma", idioma)
            TranslatorApp.set_language(idioma)

            return True

        except Exception:
            logger.exception("Erro ao aplicar idioma")
            return False

    def set_moeda(self, moeda):
        try:
            moeda = moeda or self.DEFAULT_CONFIG["moeda"]

            Session.set_config("moeda", moeda)

            return True

        except Exception:
            logger.exception("Erro ao aplicar moeda")
            return False

    def set_db_path(self, db_path):
        try:
            if not db_path:
                return False

            Session.set_config("db_path", db_path)
            return True

        except Exception:
            logger.exception("Erro ao aplicar db_path")
            return False

    # ==================================================
    # GETTERS
    # ==================================================
    def get_tema(self):
        return Session.get_config(
            "tema",
            self.DEFAULT_CONFIG["tema"]
        )

    def get_idioma(self):
        return normalizar_idioma(
            Session.get_config(
                "idioma",
                self.DEFAULT_CONFIG["idioma"]
            )
        )

    def get_moeda(self):
        return Session.get_config(
            "moeda",
            self.DEFAULT_CONFIG["moeda"]
        )

    def get_db_path(self):
        return Session.get_config(
            "db_path",
            self.DEFAULT_CONFIG["db_path"]
        )

    # ==================================================
    # TRADUÇÃO AUXILIAR
    # ==================================================
    def traduzir(self, texto):
        idioma = self.get_idioma()

        if not texto:
            return ""

        try:
            return self.argos_service.traduzir(
                texto,
                origem="pt",
                destino=idioma
            )

        except Exception:
            logger.exception("Erro ao traduzir texto")
            return texto
