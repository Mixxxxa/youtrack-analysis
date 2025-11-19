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


import pytest
from app.language_middleware import get_link_for_lang
from starlette.datastructures import URL
# from app.language_middleware import get_lang_from_url, LanguageMiddleware
# from fastapi import FastAPI, Request, HTTPException, status, Depends, Response
# from fastapi.testclient import TestClient
# from fastapi.templating import Jinja2Templates
# from starlette.middleware.sessions import SessionMiddleware


# @pytest.fixture
# def test_lang_app():
#    templates = Jinja2Templates(directory="templates")
#    app = FastAPI()
#    app.add_middleware(LanguageMiddleware, templates=templates)
#    app.add_middleware(SessionMiddleware, secret_key=0)
#    return app


@pytest.mark.parametrize(
    'target_lang, base, expected', [
        ('fr', '/', '/fr'),  # relative root
        ('fr', '/en/batch', '/fr/batch'),  # relative page with lang
        ('fr', 'https://mycorp.com', 'https://mycorp.com/fr'),  # absolute root
        ('fr', 'https://mycorp.com/en', 'https://mycorp.com/fr'),  # absolute root ends with lang
        ('fr', 'https://mycorp.com/timeline', 'https://mycorp.com/fr/timeline'),  # URL without lang
        ('fr', 'http://mycorp/timeline?issue=id-12680', 'http://mycorp/fr/timeline?issue=id-12680'),  # Intranet without lang
        ('fr', 'http://mycorp/ru/timeline?issue=id-12680', 'http://mycorp/fr/timeline?issue=id-12680'),  # Intranet
        ('fr', 'https://mycorp/ru/timeline?issue=id-12680', 'https://mycorp/fr/timeline?issue=id-12680'),
        ('fr', 'https://mycorp.com/ru/timeline?issue=id-12680', 'https://mycorp.com/fr/timeline?issue=id-12680'),
        ('fr', 'https://yt.mycorp.com/ru/timeline?issue=id-12680', 'https://yt.mycorp.com/fr/timeline?issue=id-12680'),
        ('fr', 'https://yt.mycorp.com:8080/ru/timeline?issue=id-12680', 'https://yt.mycorp.com:8080/fr/timeline?issue=id-12680'),
        ('fr', 'https://yt.mycorp.com:8080/ru/timeline?issue=id-12680#check', 'https://yt.mycorp.com:8080/fr/timeline?issue=id-12680#check'),
    ]
)
def test_change_url_lang(base: str, target_lang: str, expected: str):
    expectedUrl = URL(expected)
    asStr = get_link_for_lang(url=base, lang=target_lang)
    assert asStr == expected
    asUrl = get_link_for_lang(url=URL(url=base), lang=target_lang)
    assert asUrl == expectedUrl

# TODO later
# @pytest.mark.parametrize(
#     'link, expected', [
#         ('https://mycorp.com', None) # No lang
#         ('http://mycorp/timeline?issue=id-12680', None) # No lang
#         ('http://mycorp/ru/timeline?issue=id-12680', 'ru')
#         ('https://mycorp/ru/timeline?issue=id-12680', 'ru')
#         ('https://mycorp.com/ru/timeline?issue=id-12680', 'ru')
#         ('https://yt.mycorp.com/ru/timeline?issue=id-12680', 'ru')
#         ('https://yt.mycorp.com:8080/ru/timeline?issue=id-12680', 'ru')
#         ('https://yt.mycorp.com:8080/ru/timeline?issue=id-12680#check', 'ru')
#         ('https://yt.mycorp.com:8080/fr/timeline?issue=id-12680#check', None) # Unsupported
#     ]
# )
# def test_get_lang_from_url(test_lang_app: FastAPI, link: str, expected: str|None):
#     client = TestClient(test_lang_app)
#     response: Response = client.get()

#     val = get_lang_from_url()
#     assert val == URL(expected)
