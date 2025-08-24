import argparse
from flask import Flask, g, redirect, url_for, request, render_template, session
from flask_babel import Babel, _
import logging
import pathlib
import requests
import os

from datetime import timezone, timedelta
from pages.timeline import get_timeline_page_data
from youtrack import YouTrackConfig, InvalidIssueIdError


logger = logging.getLogger("youtrack-analysis")
app = Flask(__name__)



SUPPORTED_LANGUAGES = ['en', 'ru']


def get_locale():
    if request.view_args and 'language' in request.view_args:
        if request.view_args['language'] in SUPPORTED_LANGUAGES:
            session['language'] = request.view_args['language']
            return request.view_args['language']
    if 'language' in session and session['language'] in SUPPORTED_LANGUAGES:
        return session['language']
    return request.accept_languages.best_match(SUPPORTED_LANGUAGES)


babel = Babel(app, locale_selector=get_locale)


@app.route('/favicon.ico')
def favicon():
    return '', 204
    #return app.send_static_file('favicon.ico')
    # или если нет файла:
    # return '', 204


@app.route('/')
@app.route('/<language>')
def index(language='en'):
    return redirect(url_for('timeline'))


@app.route('/<language>/timeline')
@app.route('/timeline')
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
                notification_text=_("Service works in test mode. In case of errors or incorrect data ask '%(support_person)s' for help", support_person=config.support_person),
                host_name=config.host
            )
        except requests.HTTPError as e:
            logger.warning(f"Connection EXCEPTION: {e}")
            if e.response.status_code == 404:
                return render_template(
                    'timeline_empty.html.jinja', 
                    is_error=True, 
                    notification_text=_("The issue '%(issue_id)s' was not found", 
                                        issue_id=issue_id),
                    host_name=config.host
                )
            raise
    except InvalidIssueIdError as e:
        logger.warning(f"Invalid issue EXCEPTION: {e}")
        return render_template(
            'timeline_empty.html.jinja', 
            is_error=True, 
            notification_text=_("Invalid issue ID or URL: '%(issue_id)s'", 
                                issue_id=issue_id),
            host_name=config.host
        )
    except Exception as e:
        logger.warning(f"General EXCEPTION: {e}", exc_info=True)
        return render_template(
            'timeline_empty.html.jinja', 
            is_error=True, 
            notification_text=_("Unable to fetch information for the issue '%(issue_id)s'. Please contact '%(support_person)s' to solve the problem", 
                                issue_id=issue_id, 
                                support_person=config.support_person),
            host_name=config.host
        )
    

@app.context_processor
def inject_conf_vars():
    return {
        'get_locale': get_locale,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    arg_parser = argparse.ArgumentParser(description='Collects information about YoutTrack issue and visualize it')
    arg_parser.add_argument('-c', '--config', required=True, type=pathlib.Path, help='Configuration file')
    args = arg_parser.parse_args()

    config = YouTrackConfig.from_file(args.config)
    app.config['yt-config'] = config
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
    app.secret_key = os.urandom(24)

    if config.debug:
        app.config["TEMPLATES_AUTO_RELOAD"] = True
        app.jinja_env.auto_reload = True
        app.run(debug=True, port=config.port)
    else:
        #TODO: https://flask.palletsprojects.com/en/stable/deploying/
        app.run(debug=False, host='0.0.0.0', port=config.port)
                       