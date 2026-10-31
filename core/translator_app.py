# -*- coding: utf-8 -*-
import weakref
import logging
import re

from PyQt5 import sip
from PyQt5.QtWidgets import QTableWidget

from services.argos_service import ArgosService
from core import i18n
from utilitarios.translation_storage import TranslationStorage

logger = logging.getLogger(__name__)


class TranslatorApp:
    """
    Gerenciador global de tradução da aplicação.

    Fluxo:
    1. Português retorna texto original.
    2. Busca tradução base no core.i18n.
    3. Busca tradução persistida em translations.json.
    4. Se não existir, usa Argos.
    5. Salva tradução nova no cache e no JSON.
    """

    _bindings = []
    _translations = {}
    _current_lang = "pt"
    _is_translating = False

    _storage = TranslationStorage()

    # ======================================================
    # UTIL
    # ======================================================
    @classmethod
    def _lang_code(cls, lang):
        return (lang or "pt").replace("-", "_").split("_", 1)[0]

    @classmethod
    def current_language(cls):
        return cls._current_lang

    # ======================================================
    # INICIALIZAÇÃO
    # ======================================================
    @classmethod
    def initialize(cls):
        """
        Carrega traduções persistidas do JSON.
        Chame uma vez no início da aplicação.
        """
        try:
            cls._translations = cls._storage.load() or {}
        except Exception:
            logger.exception("Erro ao carregar traduções persistidas")
            cls._translations = {}

    @classmethod
    def load_translations(cls, translations: dict):
        cls._translations = translations or {}

    @classmethod
    def save_translations(cls):
        try:
            cls._storage.save(cls._translations)
            return True
        except Exception:
            logger.exception("Erro ao salvar traduções")
            return False

    # ======================================================
    # CONFIGURAÇÃO DE IDIOMA
    # ======================================================
    @classmethod
    def set_language(cls, lang):
        lang = cls._lang_code(lang)

        if not lang:
            lang = "pt"

        if cls._current_lang == lang:
            return

        logger.info("Definindo idioma: %s", lang)

        cls._current_lang = lang
        cls.translate_all()

    # ======================================================
    # TRADUÇÃO
    # ======================================================
    @classmethod
    def get(cls, texto: str) -> str:
        if not texto:
            return ""

        destino = cls._lang_code(cls._current_lang)

        if destino == "pt":
            return texto

        # 1. Tradução base/manual do i18n.py
        try:
            if i18n.has(texto, destino):
                return i18n.t(texto, destino)
        except Exception:
            logger.exception("Erro ao consultar i18n")

        # 2. Cache em memória / JSON carregado
        lang_dict = cls._translations.get(destino, {})

        if texto in lang_dict:
            return lang_dict[texto]

        # 3. Argos fallback
        try:
            traduzido = ArgosService.traduzir(
                texto,
                origem="pt",
                destino=destino
            )

            if not traduzido or traduzido == texto:
                return texto

            # Salva em memória
            cls._translations.setdefault(destino, {})
            cls._translations[destino][texto] = traduzido

            # Salva no JSON
            cls.save_translations()

            return traduzido

        except Exception:
            logger.exception("Erro ao traduzir texto: %s", texto)
            return texto

    @classmethod
    def error(cls, error):
        """Traduz mensagens de domínio sem alterar o erro nem os valores financeiros."""
        text = str(error)
        match = re.fullmatch(
            r"O pagamento excede o valor máximo quitável de R\$ ([0-9]+\.[0-9]{2})\.", text
        )
        if match:
            return cls.get("O pagamento excede o valor máximo quitável de R$ {valor}.").format(
                valor=match.group(1)
            )
        return cls.get(text)

    # ======================================================
    # TABELAS
    # ======================================================
    @classmethod
    def table_headers(cls, table, headers):
        if table is None or sip.isdeleted(table):
            return

        try:
            original_headers = list(headers)
            translated = [cls.get(h) for h in original_headers]

            table.setHorizontalHeaderLabels(translated)

            table.setProperty("_financeassist_i18n_headers", original_headers)

        except Exception:
            logger.exception("Erro ao traduzir cabeçalhos da tabela")

    # ======================================================
    # AUTO TRANSLATION SIMPLES
    # ======================================================
    @classmethod
    def enable_auto_translation(cls, widget):
        if widget is None or sip.isdeleted(widget):
            return

        def callback():
            cls._translate_widget(widget)

        cls.bind(callback, widget)
        cls._translate_widget(widget)

    # ======================================================
    # CORE ENGINE
    # ======================================================
    @classmethod
    def _translate_widget(cls, widget):
        if widget is None or sip.isdeleted(widget):
            return

        # TEXT
        if hasattr(widget, "setText") and hasattr(widget, "text"):
            try:
                original = widget.property("_financeassist_i18n_text")

                if original is None:
                    original = widget.text()
                    widget.setProperty("_financeassist_i18n_text", original)

                widget.setText(cls.get(original))

            except RuntimeError:
                return

            except Exception:
                logger.exception("Erro ao traduzir texto do widget")

        # PLACEHOLDER
        if hasattr(widget, "setPlaceholderText") and hasattr(widget, "placeholderText"):
            try:
                original = widget.property("_financeassist_i18n_placeholder")

                if original is None:
                    original = widget.placeholderText()
                    widget.setProperty("_financeassist_i18n_placeholder", original)

                widget.setPlaceholderText(cls.get(original))

            except RuntimeError:
                return

            except Exception:
                logger.exception("Erro ao traduzir placeholder")

        # TABELAS
        if isinstance(widget, QTableWidget):
            try:
                original = widget.property("_financeassist_i18n_headers")

                if original is None:
                    original = []

                    for column in range(widget.columnCount()):
                        item = widget.horizontalHeaderItem(column)
                        original.append(item.text() if item else "")

                    widget.setProperty("_financeassist_i18n_headers", original)

                if original:
                    widget.setHorizontalHeaderLabels(
                        [cls.get(h) for h in original]
                    )

            except RuntimeError:
                return

            except Exception:
                logger.exception("Erro ao traduzir tabela")

    # ======================================================
    # BIND / UNBIND
    # ======================================================
    @classmethod
    def bind(cls, callback, widget):
        if widget is None or sip.isdeleted(widget):
            return

        for cb, ref in cls._bindings:
            obj = ref()

            if obj is widget and cb == callback:
                return

        cls._bindings.append(
            (callback, weakref.ref(widget))
        )

    @classmethod
    def unbind(cls, widget):
        if widget is None:
            return

        cls._bindings = [
            (cb, ref)
            for cb, ref in cls._bindings
            if ref() is not widget
        ]

    # ======================================================
    # EXECUÇÃO GLOBAL
    # ======================================================
    @classmethod
    def translate_all(cls):
        if cls._is_translating:
            return

        cls._is_translating = True

        try:
            novos = []

            for callback, widget_ref in cls._bindings:
                widget = widget_ref()

                if widget is None:
                    continue

                try:
                    if sip.isdeleted(widget):
                        continue

                    callback()
                    novos.append((callback, widget_ref))

                except RuntimeError:
                    continue

                except Exception:
                    logger.exception("Erro ao executar callback de tradução")
                    continue

            cls._bindings = novos

        finally:
            cls._is_translating = False

    @classmethod
    def _on_argos_ready(cls, origem, destino):
        if origem == "pt" and cls._lang_code(cls._current_lang) == destino:
            cls.translate_all()
    # ======================================================
    # LIMPEZA GERAL
    # ======================================================
    @classmethod
    def clear(cls):
        cls._bindings.clear()


ArgosService.on_model_ready(TranslatorApp._on_argos_ready)
