# core/session.py

class Session:
    """
    Estado global da aplicação.

    Responsável por:
    - Usuário logado
    - Configurações globais (idioma, tema, moeda)
    - Notificação de mudanças (idioma / tema)
    """

    # ---------------------------------------
    # ESTADO
    # ---------------------------------------
    usuario = None

    _config_padrao = {
        "idioma": "pt",
        "tema": "Primavera",
        "moeda": "BRL"
    }

    configuracoes = _config_padrao.copy()

    # listeners
    _idioma_listeners = []
    _tema_listeners = []

    # ---------------------------------------
    # NORMALIZAÇÃO
    # ---------------------------------------
    _idioma_map = {
        "Português": "pt",
        "Inglês": "en",
        "Espanhol": "es",
        "pt": "pt",
        "en": "en",
        "es": "es"
    }

    _tema_map = {
        "Claro": "Primavera",
        "Escuro": "Noite Intensa",
        "Verde": "Prosperidade",
        "claro": "Primavera",
        "escuro": "Noite Intensa",
        "verde": "Prosperidade",
        "Primavera": "Primavera",
        "Noite Intensa": "Noite Intensa",
        "Prosperidade": "Prosperidade",
        "Verão Quente": "Verão Quente",
        "Personalizado": "Personalizado",
        "PRIMAVERA": "Primavera",
        "NOITE_INTENSA": "Noite Intensa",
        "PROSPERIDADE": "Prosperidade",
        "VERAO_QUENTE": "Verão Quente",
        "PERSONALIZADO": "Personalizado",
    }

    @classmethod
    def _normalize_idioma(cls, valor):
        return cls._idioma_map.get(valor, "pt")

    @classmethod
    def _normalize_tema(cls, valor):
        if not isinstance(valor, str):
            return "Primavera"

        valor = valor.strip()
        return cls._tema_map.get(valor, "Primavera")

    # ---------------------------------------
    # USUÁRIO
    # ---------------------------------------
    @classmethod
    def set_usuario(cls, usuario: dict | None):
        cls.usuario = usuario

        if not usuario:
            return

        if "Idioma" in usuario:
            idioma = cls._normalize_idioma(usuario["Idioma"])
            cls.set_config("idioma", idioma, notify=False)

        if "Tema" in usuario:
            tema = cls._normalize_tema(usuario["Tema"])
            cls.set_config("tema", tema, notify=False)

    @classmethod
    def get_usuario(cls):
        return cls.usuario

    # ---------------------------------------
    # CONFIGURAÇÕES
    # ---------------------------------------
    @classmethod
    def set_config(cls, chave: str, valor, notify: bool = True):

        if chave not in cls._config_padrao:
            return

        if chave == "idioma":
            valor = cls._normalize_idioma(valor)

        elif chave == "tema":
            valor = cls._normalize_tema(valor)

        cls.configuracoes[chave] = valor

        if not notify:
            return

        if chave == "idioma":
            cls._notify_idioma(valor)

        elif chave == "tema":
            cls._notify_tema(valor)

    @classmethod
    def load_config(cls, config: dict):
        for chave, valor in config.items():
            if chave in cls._config_padrao:

                if chave == "idioma":
                    valor = cls._normalize_idioma(valor)

                elif chave == "tema":
                    valor = cls._normalize_tema(valor)

                cls.configuracoes[chave] = valor

    @classmethod
    def get_config(cls, chave: str, default=None):
        valor = cls.configuracoes.get(chave, default)

        # 🔥 proteção extra
        if chave == "tema":
            return cls._normalize_tema(valor)

        return valor

    @classmethod
    def reset_config(cls):
        cls.configuracoes = cls._config_padrao.copy()

    # ---------------------------------------
    # LISTENERS — IDIOMA
    # ---------------------------------------
    @classmethod
    def on_idioma_change(cls, callback):
        if callback not in cls._idioma_listeners:
            cls._idioma_listeners.append(callback)

    @classmethod
    def _notify_idioma(cls, idioma):
        for callback in list(cls._idioma_listeners):
            try:
                callback(idioma)
            except Exception:
                pass

    # ---------------------------------------
    # LISTENERS — TEMA
    # ---------------------------------------
    @classmethod
    def on_tema_change(cls, callback):
        if callback not in cls._tema_listeners:
            cls._tema_listeners.append(callback)

    @classmethod
    def _notify_tema(cls, tema):
        for callback in list(cls._tema_listeners):
            try:
                if callable(callback):
                    callback(tema)
            except Exception:
                pass
