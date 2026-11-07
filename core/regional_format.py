"""Presentation locale; numeric amounts and ISO dates remain unchanged in storage."""
from PyQt5.QtCore import QLocale


class RegionalFormat:
    @staticmethod
    def language():
        from core.translator_app import TranslatorApp
        return TranslatorApp._lang_code(TranslatorApp._current_lang)

    @classmethod
    def locale(cls):
        return QLocale({'pt': 'pt_BR', 'en': 'en_US', 'es': 'es_ES'}.get(cls.language(), 'pt_BR'))

    @classmethod
    def date_pattern(cls):
        return 'MM/dd/yyyy' if cls.language() == 'en' else 'dd/MM/yyyy'

    @classmethod
    def configure_widget(cls, widget):
        from PyQt5.QtWidgets import QDateEdit, QDoubleSpinBox
        locale = cls.locale()
        if isinstance(widget, QDateEdit):
            widget.setLocale(locale)
            widget.setDisplayFormat(cls.date_pattern())
        elif isinstance(widget, QDoubleSpinBox):
            widget.setLocale(locale)
            if widget.property('_regional_money') is None:
                widget.setProperty('_regional_money', bool(widget.prefix().strip() in ('R$', '$', 'US$', '€')))
            if widget.property('_regional_money'):
                symbol = locale.currencySymbol(QLocale.CurrencySymbol)
                widget.setPrefix('' if cls.language() == 'es' else symbol + ' ')
                widget.setSuffix(' €' if cls.language() == 'es' else '')

    @classmethod
    def configure_tree(cls, widget):
        from PyQt5.QtWidgets import QDateEdit, QDoubleSpinBox
        cls.configure_widget(widget)
        from PyQt5.QtWidgets import QWidget
        for child in widget.findChildren(QWidget):
            cls.configure_widget(child)
