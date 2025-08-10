import argparse
from flask import Flask, g, redirect, url_for, request, render_template, session
from flask_babel import Babel, _
import logging
import pathlib
import requests
import os
from dataclasses import dataclass

from datetime import timezone, timedelta
from pages.timeline import get_timeline_page_data
from youtrack import YouTrackConfig, InvalidIssueIdError


logger = logging.getLogger("youtrack-analysis")
app = Flask(__name__)


class LanguageSettings:
    @dataclass
    class Language:
        code: str
        display_name: str

    SUPPORTED_LANGUAGES: list[Language] = [
        Language(code='en', display_name='English'),
        Language(code='ru', display_name='Русский')
    ]
    
    @staticmethod
    def is_supported(lang: str) -> bool:
        for i in LanguageSettings.SUPPORTED_LANGUAGES:
            if i.code == lang:
                return True
        return False
    
    @staticmethod
    def supported_codes() -> list[str]:
        return ['en', 'ru']
    

def get_locale():
    if request.view_args and 'language' in request.view_args:
        if LanguageSettings.is_supported(request.view_args['language']):
            session['language'] = request.view_args['language']
            return request.view_args['language']
    if 'language' in session and LanguageSettings.is_supported(session['language']):
        return session['language']
    return request.accept_languages.best_match(LanguageSettings.supported_codes())


babel = Babel(app, locale_selector=get_locale)


@app.route('/favicon.ico')
def favicon():
    return '', 204
    #return app.send_static_file('favicon.ico')


@app.route('/')
def root():
    is_lang_present: bool = 'language' in session
    lang = session['language'] if is_lang_present else get_locale()
    if not lang:
        lang = 'en'
    if not is_lang_present:
        session['language'] = lang
    return redirect(url_for('timeline', language=lang))


@app.route('/<language>')
def set_language_and_redirect(language='en'):
    if language not in LanguageSettings.SUPPORTED_LANGUAGES:
        language = get_locale()

    if 'language' not in session:
        session['language'] = language
    
    issue_id = request.args.get('issue', '').strip().lower()
    if len(issue_id) > 0:
        return redirect(url_for('timeline', language=language, issue=issue_id))
    else:
        return redirect(url_for('timeline', language=language))


#@app.route('/timeline')

@app.route('/<language>/timeline')
def timeline(language='en'):
    issue_id = request.args.get('issue', '').strip().lower()
    config: YouTrackConfig = app.config['yt-config']

    try:
        try:
            if len(issue_id) > 0:
                tz = timezone(timedelta(hours=3))
                data = get_timeline_page_data(issue_id=issue_id, tz=tz, config=config)
                return render_template(
                    'timeline.html.jinja', 
                    **data
                )
            return render_template(
                'timeline_empty.html.jinja', 
                is_error=False, 
                notification_text=_('base.service_wip', support_person=config.support_person),
                host_name=config.host
            )
        except requests.HTTPError as e:
            logger.warning(f"Connection EXCEPTION: {e}")
            if e.response.status_code == 404:
                return render_template(
                    'timeline_empty.html.jinja', 
                    is_error=True, 
                    notification_text=_('base.issue_not_found_with_id', issue_id=issue_id),
                    host_name=config.host
                )
            raise
    except InvalidIssueIdError as e:
        logger.warning(f"Invalid issue EXCEPTION: {e}")
        return render_template(
            'timeline_empty.html.jinja', 
            is_error=True, 
            notification_text=_("base.invalid_issue_id_or_url", 
                                issue_id=issue_id),
            host_name=config.host
        )
    except Exception as e:
        logger.warning(f"General EXCEPTION: {e}", exc_info=True)
        return render_template(
            'timeline_empty.html.jinja', 
            is_error=True, 
            notification_text=_("base.unable_to_get_info_with_id_and_person", 
                                issue_id=issue_id, 
                                support_person=config.support_person),
            host_name=config.host
        )
    

@app.context_processor
def inject_conf_vars():
    def url_for_other_language(lang):
        endpoint = request.endpoint
        view_args = dict(request.view_args or {})
        view_args['language'] = lang
        query_params = {}
        for k in request.args.keys():
            vals = request.args.getlist(k)
            query_params[k] = vals if len(vals) > 1 else vals[0]
        return url_for(endpoint, **view_args, **query_params)
    
    current_language = get_locale()
    return {
        'supported_languages': [{
            'code': i.code,
            'display_name': i.display_name,
            'is_active': i.code == current_language
        } for i in LanguageSettings.SUPPORTED_LANGUAGES],
        'url_for_language': url_for_other_language
    }


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description='Collects information about YoutTrack issue and visualize it')
    arg_parser.add_argument('-c', '--config', required=True, type=pathlib.Path, help='Configuration file')
    args = arg_parser.parse_args()

    config = YouTrackConfig.from_file(args.config)
    app.config['yt-config'] = config
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
    app.secret_key = os.urandom(24)

    logging.basicConfig(level=logging.DEBUG if config.debug else logging.INFO)

    if config.debug:
        app.config["TEMPLATES_AUTO_RELOAD"] = True
        app.jinja_env.auto_reload = True
        app.run(debug=True, port=config.port)
    else:
        #TODO: https://flask.palletsprojects.com/en/stable/deploying/
        app.run(debug=False, host='0.0.0.0', port=config.port)
                       