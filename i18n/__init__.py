from typing import Optional

from config import config

LANG_ZH = {}
LANG_EN = {}

try:
    from .zh import LANG_ZH
    from .en import LANG_EN
except ImportError:
    pass


def get_current_lang() -> str:
    return getattr(config, 'current_language', 'zh')


def set_current_lang(lang: str):
    config.current_language = lang


def translate(key: str, lang: Optional[str] = None) -> str:
    if lang is None:
        lang = get_current_lang()

    if lang == 'en':
        return LANG_EN.get(key, key)
    return LANG_ZH.get(key, key)


def t(key: str, lang: Optional[str] = None) -> str:
    return translate(key, lang)


def get_available_languages():
    return [
        {"code": "zh", "name": "中文"},
        {"code": "en", "name": "English"},
    ]


class I18n:
    def __init__(self, lang: str = None):
        self.lang = lang or get_current_lang()

    def t(self, key: str) -> str:
        return translate(key, self.lang)

    def __call__(self, key: str) -> str:
        return self.t(key)


def create_i18n(lang: str = None) -> I18n:
    return I18n(lang)