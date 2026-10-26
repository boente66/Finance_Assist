import threading
import logging

from PyQt5.QtCore import QTimer

logger = logging.getLogger(__name__)


class ArgosService:

    _cache = {}
    _installed_pairs = set()
    _lock = threading.Lock()
    _ready_callbacks = []

    MAX_CACHE = 5000

    @classmethod
    def _backend(cls):
        try:
            from argostranslate import package, translate
        except ImportError as exc:
            raise RuntimeError(
                "Nao foi possivel carregar a dependencia opcional "
                "'argostranslate'. A traducao automatica ficara indisponivel "
                "ate o ambiente ser reinstalado."
            ) from exc

        return package, translate

    # ==================================================
    # DETECTAR SE MODELO EXISTE
    # ==================================================
    @classmethod
    def _is_installed(cls, origem, destino):
        try:
            _, translate = cls._backend()
            installed = translate.get_installed_languages()

            for lang in installed:
                if lang.code == origem:

                    translations = getattr(lang, "translations_to", None)

                    if translations is None:
                        translations = getattr(lang, "translations", [])

                    for t in translations:
                        try:
                            if t.to_lang.code == destino:
                                return True
                        except Exception:
                            continue

            return False

        except Exception:
            logger.exception("[Argos] Erro ao verificar instalação")
            return False

    # ==================================================
    # INSTALAR MODELO
    # ==================================================
    @classmethod
    def ensure_model(cls, origem, destino, background=False):

        key = (origem, destino)

        if key in cls._installed_pairs:
            return True

        if cls._is_installed(origem, destino):
            cls._installed_pairs.add(key)
            return True

        if background:
            threading.Thread(
                target=cls._install_model,
                args=(origem, destino),
                daemon=True
            ).start()
            return False

        return cls._install_model(origem, destino)

    @classmethod
    def _install_model(cls, origem, destino):

        with cls._lock:
            try:
                package, _ = cls._backend()
                logger.info(f"[Argos] Instalando modelo {origem}->{destino}")

                package.update_package_index()
                packages = package.get_available_packages()

                pkg = next(
                    (
                        p for p in packages
                        if p.from_code == origem and p.to_code == destino
                    ),
                    None
                )

                if not pkg:
                    logger.warning(
                        f"[Argos] Modelo não encontrado {origem}->{destino}"
                    )
                    return False

                path = pkg.download()
                package.install_from_path(path)

                cls._installed_pairs.add((origem, destino))
                cls._notify_ready(origem, destino)

                logger.info(f"[Argos] Modelo instalado {origem}->{destino}")
                return True

            except Exception:
                logger.exception("[Argos] Erro ao instalar modelo")
                return False

    @classmethod
    def on_model_ready(cls, callback):
        if callback not in cls._ready_callbacks:
            cls._ready_callbacks.append(callback)

    @classmethod
    def _notify_ready(cls, origem, destino):
        for callback in tuple(cls._ready_callbacks):
            try:
                QTimer.singleShot(0, lambda cb=callback: cb(origem, destino))
            except Exception:
                logger.exception("[Argos] Erro ao notificar modelo instalado")

    # ==================================================
    # TRADUÇÃO PRINCIPAL
    # ==================================================
    @classmethod
    def traduzir(cls, texto, origem, destino):

        if not texto:
            return texto

        key = (hash(texto), origem, destino)

        # CACHE
        if key in cls._cache:
            return cls._cache[key]

        try:
            _, translate = cls._backend()

            # evita verificar toda hora
            if (origem, destino) not in cls._installed_pairs:

                if not cls._is_installed(origem, destino):
                    cls.ensure_model(origem, destino, background=True)
                    return texto

                cls._installed_pairs.add((origem, destino))

            resultado = translate.translate(
                texto,
                origem,
                destino
            )

            # controle de cache
            if len(cls._cache) >= cls.MAX_CACHE:
                cls._cache.clear()

            cls._cache[key] = resultado

            return resultado

        except Exception:
            logger.exception("[Argos] Falha na tradução")
            return texto

    # ==================================================
    # TRADUÇÃO ASSÍNCRONA (SAFE UI THREAD)
    # ==================================================
    @classmethod
    def traduzir_async(cls, texto, callback, origem, destino):

        def worker():
            resultado = cls.traduzir(
                texto,
                origem,
                destino
            )

            try:
                # volta pra thread principal (PyQt safe)
                QTimer.singleShot(
                    0,
                    lambda: callback(resultado)
                )

            except Exception:
                logger.exception("[Argos] Erro no callback async")

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    # ==================================================
    # PRÉ-CARREGAMENTO
    # ==================================================
    @classmethod
    def preload(cls, pares=None):

        pares = pares or [("pt", "en")]

        for origem, destino in pares:
            cls.ensure_model(
                origem,
                destino,
                background=True
            )

    # ==================================================
    # LIMPAR CACHE
    # ==================================================
    @classmethod
    def clear_cache(cls):
        cls._cache.clear()
        logger.info("[Argos] Cache limpo")

    # ==================================================
    # LISTAR IDIOMAS INSTALADOS
    # ==================================================
    @classmethod
    def listar_idiomas_instalados(cls):
        try:
            _, translate = cls._backend()
            langs = translate.get_installed_languages()
            return [lang.code for lang in langs]

        except Exception:
            logger.exception("[Argos] Erro ao listar idiomas")
            return []

    # ==================================================
    # VERIFICAR STATUS DO PAR
    # ==================================================
    @classmethod
    def is_ready(cls, origem, destino):
        return cls._is_installed(origem, destino)
