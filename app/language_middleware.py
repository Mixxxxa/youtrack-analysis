# Copyright 2025 Mikhail Gelvikh
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from fastapi import Request, Depends
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import URL
from gettext import GNUTranslations, translation
from dataclasses import dataclass
from typing import Literal, Annotated, Optional


class LanguageSettings:
    @dataclass
    class Language:
        code: str
        display_name: str
        date_format: str

    SUPPORTED_LANGUAGES: list[Language] = [
        Language(code='en', display_name='English', date_format='dd.MM.yyyy (EEE) HH:mm:ss'),
        Language(code='ru', display_name='Русский', date_format='dd.MM.yyyy (EEE) HH:mm:ss')
    ]
    
    @staticmethod
    def is_supported(lang: str) -> bool:
        for i in LanguageSettings.SUPPORTED_LANGUAGES:
            if i.code == lang:
                return True
        return False
    
    @staticmethod
    def supported_codes() -> Literal['ru', 'en']:
        return ['en', 'ru']
    
    @staticmethod
    def default_language() -> Literal['en']:
        return 'en'
    

AvailableLanguageT = Literal['ru', 'en']


def convert_accept_language_values(header_text: str) -> list[str]:
    header_text = header_text.strip()
    if len(header_text) == 0 or header_text == '*':
        return []
    #'en-US,en;q=0.9,ru;q=0.8'
    ret: list[str] = []
    for i in header_text.split(','):
        i = i.strip()
        if len(i) == 0:
            continue
        split_char = '-' if i.find('-') != -1 else ';'
        val_parts = i.split(split_char)
        if len(val_parts) > 0:
            lang = val_parts[0].strip()
            if (1 < len(lang) <= 3) and (lang not in ret):
                ret.append(lang)
    return ret


def get_best_language_from_request(request: Request) -> str:
    """Определить язык из сессии или заголовков браузера"""
    # Сначала проверяем сессию
    if hasattr(request, 'session'):
        lang = request.session.get('language')
        if lang and LanguageSettings.is_supported(lang):
            return lang
    
    # Затем проверяем Accept-Language заголовок
    accept_language = request.headers.get("Accept-Language")
    if accept_language:
        candidates = convert_accept_language_values(accept_language)
        filtered = list(filter(LanguageSettings.is_supported, candidates))
        if len(filtered) > 0:
            return filtered[0]
    return LanguageSettings.default_language()


def get_lang_from_session(request: Request) -> Optional[str]:
    if hasattr(request, 'session'):
        lang = request.session.get('language')
        if lang and LanguageSettings.is_supported(lang):
            return lang
    return None


def get_lang_prefered_lang_from_header(request: Request) -> Optional[str]:
    accept_language = request.headers.get("Accept-Language")
    if accept_language:
        candidates = convert_accept_language_values(accept_language)
        filtered = list(filter(LanguageSettings.is_supported, candidates))
        if len(filtered) > 0:
            return filtered[0]
    return None


def get_lang_from_url(request: Request) -> Optional[str]:
    path = request.url.path
    parts = path.split('/')
    if len(parts) >= 2 and LanguageSettings.is_supported(lang := parts[1].strip().lower()):
        return lang
    return None


def get_link_for_lang(url: URL|str, lang: str) -> URL:
    if isinstance(url, str):
        parsed = URL(url=url)
    else:
        parsed = url
    
    size = len(parsed.path)
    path = parsed.path

    if path == '/':
        return parsed.replace(path=f'/{lang}')
    
    # For the /ru/bla/bla/bla cases
    if size > 4 and path[0] == '/' and path[3] == '/':
        return parsed.replace(path=f'/{lang}{parsed.path[3:]}')
    
    # For the /ru cases
    if size == 3 and path[0]:
        return parsed.replace(path=f'/{lang}')
    
    # General case /blablabla
    return parsed.replace(path=f'/{lang}{parsed.path}')


class LanguageMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, templates: Jinja2Templates):
        super().__init__(app)
        self.templates = templates
        self.__translations: dict[str, GNUTranslations] = {}
        for lang in LanguageSettings.supported_codes():
            self.__translations[lang] = translation(
                domain='messages',
                localedir='translations',
                languages=[lang]
            )

    async def dispatch(self, request: Request, call_next):
        lang: Optional[str] = None
        if lang_from_url := get_lang_from_url(request):
            lang = lang_from_url
        elif lang_from_session := get_lang_from_session(request):
            lang = lang_from_session
        elif lang_from_header := get_lang_prefered_lang_from_header(request):
            lang = lang_from_header

        if not lang:
            lang = LanguageSettings.default_language()

        request.session['language'] = lang
        self.templates.env.globals['_'] = self.__translations[lang].gettext
        self.templates.env.globals['lang'] = lang
        request.state.gettext = self.__translations[lang].gettext
        response = await call_next(request)
        return response
    

LanguageDep = Annotated[AvailableLanguageT, Depends(get_best_language_from_request)]