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


from aiohttp import ClientResponseError
from contextlib import asynccontextmanager
from datetime import timezone, timedelta
from typing import Optional, Callable, Annotated, Any
import logging
import os

from fastapi import FastAPI, Request, status, Query, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from youtrack.helper import YouTrackHelper
from youtrack.utils.exceptions import InvalidIssueIdError, UnableToCountIssues, TooMuchIssuesInBatchError

from .settings import Settings, LocalSettings
from .utils.log import logger
from .timeline import get_timeline_page_data
from .language_middleware import LanguageMiddleware, LanguageSettings, LanguageDep, get_link_for_lang
from .batch import (
    get_basic_batch_context,
    get_batch_scope_overrun_data,
    get_batch_scope_increase_data,
    BadQueryError,
    BadDatesError
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Init
    local = LocalSettings()
    logging.basicConfig(level=logging.DEBUG if local.debug else logging.INFO)

    logger.info(f'Loaded local settings:\n{local}')

    logger.info(f'Connecting to: {local.host}...')
    helper = YouTrackHelper(instance_url=local.host,
                            api_key=local.api_key)
    app.state.settings = Settings(app_config=local,
                                  yt_config=await helper.get_instance_settings())

    settings: Settings = app.state.settings
    logger.info(f'Loaded remote settings:\n{settings.yt_config}')

    yield
    # Clean-up
    pass


templates = Jinja2Templates(directory="templates")
app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.add_middleware(LanguageMiddleware, templates=templates)
app.add_middleware(SessionMiddleware, secret_key=os.urandom(24))


# Uncomment to profile
# if PROFILING:
#     from pyinstrument import Profiler
#     @app.middleware("http")
#     async def profile_request(request: Request, call_next):
#         profiling = request.query_params.get("profile", False)
#         if profiling:
#             profiler = Profiler()
#             profiler.start()
#             await call_next(request)
#             profiler.stop()
#             return HTMLResponse(profiler.output_html())
#         else:
#             return await call_next(request)


def get_basic_html_context(request: Request):
    session_lang: str = request.session['language']
    settings: Settings = request.app.state.settings
    return {
        'request': request,
        'host_name': settings.app_config.host,
        'support_person': settings.app_config.support_person,
        'settings': {
            'lang_code': session_lang,
            'date_format': 'dd MMMM yyyy (EEE)',            # for luxon
            'datetime_format': 'dd MMMM yyyy (EEE) HH:mm',  # for luxon
            'timezone': 'UTC+3'                             # for luxon
        },
        'supported_languages': [{
            'code': i.code,
            'display_name': i.display_name,
            'is_active': i.code == session_lang
        } for i in LanguageSettings.SUPPORTED_LANGUAGES],
        'get_link_for_lang': get_link_for_lang
    }


def set_error(context: Any, text: str, is_error: bool = True) -> None:
    if ('error_text', 'is_error') in context:
        raise RuntimeError('An error was already written before')
    context['error_text'] = text
    context['is_error'] = is_error


@app.get("/", include_in_schema=False)
async def root(request: Request, lang: LanguageDep):
    """
    Главная страница - перенаправляет пользователя на соответствующую языковую страницу.
    """
    return RedirectResponse(url=request.url_for('home', lang=lang))


@app.get("/timeline", include_in_schema=False)
async def timeline_redirect(request: Request, issue: Optional[str] = None):
    session_lang: str = request.session['language']
    base_url = request.url_for('timeline', lang=session_lang)
    if issue:
        return RedirectResponse(url=base_url.include_query_params(issue=issue))
    return RedirectResponse(url=base_url)


@app.get("/batch", include_in_schema=False)
async def batch_redirect(request: Request, batch_mode: str|None = None):
    session_lang: str = request.session['language']
    new_url = get_link_for_lang(url=request.url, lang=session_lang)
    return RedirectResponse(url=new_url)


@app.get("/batch/{batch_mode}", include_in_schema=False)
async def batch_mode_redirect(request: Request, batch_mode: str):
    session_lang: str = request.session['language']
    new_url = get_link_for_lang(url=request.url, lang=session_lang)
    return RedirectResponse(url=new_url)


@app.get("/{lang}", include_in_schema=False)
async def home(lang: str, request: Request):
    session_lang: str = request.session['language']
    if lang != session_lang:
        return RedirectResponse(url=request.url_for('home', lang=session_lang))

    return templates.TemplateResponse(
        request=request,
        name="home.html.jinja",
        context=get_basic_html_context(request)
    )


@app.get("/{lang}/batch", response_class=HTMLResponse)
async def batch(request: Request, lang: str):
    session_lang: str = request.session['language']
    return RedirectResponse(url=request.url_for('scope_overrun', lang=session_lang, batch_mode='scope-overrun'))


@app.get("/{lang}/timeline", response_class=HTMLResponse)
async def timeline(request: Request, lang: str, issue: Optional[str] = None):
    session_lang: str = request.session['language']
    if lang != session_lang:
        base_url = request.url_for('timeline', lang=session_lang)
        if issue:
            return RedirectResponse(url=base_url.include_query_params(issue=issue))
        return RedirectResponse(url=base_url)

    _: Callable[[str], str] = request.state.gettext
    settings: Settings = request.app.state.settings
    tz = timezone(timedelta(hours=3))
    context = get_basic_html_context(request)
    target_template = "timeline_empty.html.jinja"

    try:
        try:
            if issue and len(issue) > 0:
                data = await get_timeline_page_data(translator=_,
                                                    issue_id=issue,
                                                    tz=tz,
                                                    settings=settings)
                context |= data
                target_template = "timeline.html.jinja"
            else:
                set_error(context=context,
                          is_error=False,
                          text=_('base.service_wip') % dict(support_person=settings.app_config.support_person))
        except ClientResponseError as e:
            if e.status != status.HTTP_404_NOT_FOUND:
                raise  # Catch later
            set_error(context=context,
                      text=_("base.invalid_issue_id_or_url") % dict(issue_id=issue))
    except InvalidIssueIdError:
        set_error(context=context,
                  text=_("base.invalid_issue_id_or_url") % dict(issue_id=issue))
    except Exception as e:
        logger.exception(msg=e)
        set_error(context=context,
                  text=_("base.unable_to_get_info_with_id_and_person") % dict(issue_id=issue,
                                                                              support_person=settings.app_config.support_person))
    return templates.TemplateResponse(
        request=request,
        name=target_template,
        context=context
    )


@app.get("/{lang}/batch/{batch_mode}", response_class=HTMLResponse)
async def scope_overrun(request: Request,
                        lang: str,
                        batch_mode: str = '',
                        project: str|None = None,
                        component: Annotated[list[str], Query()] = [],
                        begin: str|None = None,
                        end: str|None = None):
    session_lang: str = request.session['language']
    if lang != session_lang:
        base_url = request.url_for('scope_overrun', lang=session_lang, batch_mode=batch_mode)
        if component or begin or end:
            return RedirectResponse(url=base_url.include_query_params(component=component, begin=begin, end=end))
        return RedirectResponse(url=base_url)

    if batch_mode not in ('scope-increase', 'scope-overrun'):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    _: Callable[[str], str] = request.state.gettext
    settings: Settings = request.app.state.settings

    context = get_basic_html_context(request)
    context |= get_basic_batch_context(translator=_,
                                       settings=settings,
                                       sub_mode=batch_mode)
    render_template = 'batch.html.jinja'

    try:
        if batch_mode == 'scope-overrun':
            data = await get_batch_scope_overrun_data(translator=_,
                                                      settings=settings,
                                                      project=project,
                                                      components=component,
                                                      begin=begin,
                                                      end=end)
        elif batch_mode == 'scope-increase':
            render_template = 'scope_increase.html.jinja'
            data = await get_batch_scope_increase_data(translator=_,
                                                       settings=settings,
                                                       project=project,
                                                       components=component,
                                                       begin=begin,
                                                       end=end)
        context |= data
        assert 'batch_sub_mode' in context and len(context['batch_sub_mode']), 'Sub mode should be specified'
    except BadQueryError as e:
        bad_params_str = ','.join(["'" + param + "'" for param in e.bad_params])
        set_error(context=context,
                  text=_('batch.bad_request') % dict(bad_components=bad_params_str))
    except BadDatesError:
        set_error(context=context,
                  text=_('batch.bad_dates'))
    except UnableToCountIssues:
        set_error(context=context,
                  text=_('batch.unable_to_get_issues'))
    except TooMuchIssuesInBatchError:
        set_error(context=context,
                  text=_("batch.too_much_issues") % dict(limit=YouTrackHelper.MAX_ISSUE_COUNT,
                                                         support_person=settings.app_config.support_person))
    except Exception as e:
        logger.exception(msg=e)
        set_error(context=context, text=str(e))

    return templates.TemplateResponse(
        request=request,
        name=render_template,
        context=context
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException) -> HTMLResponse:
    context = get_basic_html_context(request)
    return templates.TemplateResponse(
        request=request,
        name="errors/404.html.jinja",
        context=context,
        status_code=404
    )


@app.exception_handler(Exception)
async def internal_error_handler(request: Request, exc: Exception) -> HTMLResponse:
    context = get_basic_html_context(request)
    logger.exception(msg=exc)
    return templates.TemplateResponse(
        request=request,
        name="errors/500.html.jinja",
        context=context,
        status_code=500
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)
