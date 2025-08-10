import argparse
from flask import Flask, g, redirect, url_for, request, render_template
from flask_babel import Babel, _
import logging
import pathlib
import requests

from datetime import timezone, timedelta
from pages.timeline import get_timeline_page_data
from youtrack import YouTrackConfig, InvalidIssueIdError


logger = logging.getLogger("youtrack-analysis")
app = Flask(__name__)
babel = Babel(app)


def get_locale():
    # # if a user is logged in, use the locale from the user settings
    # user = getattr(g, 'user', None)
    # if user is not None:
    #     return user.locale
    # # otherwise try to guess the language from the user accept
    # # header the browser transmits.  We support de/fr/en in this
    # # example.  The best match wins.
    return request.accept_languages.best_match(['en', 'ru'])


@app.route('/')
def index():

    return redirect(url_for('timeline'))


@app.route('/timeline')
def timeline():
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
                notification_text=_("The service works in the test mode. In case of errors or incorrect data ask '%(support_person)' for help", support_person=config.support_person),
                host_name=config.host
            )
        except requests.HTTPError as e:
            logger.warning(f"Connection EXCEPTION: {e}")
            if e.response.status_code == 404:
                return render_template(
                    'timeline_empty.html.jinja', 
                    is_error=True, 
                    notification_text=_("The issue '%(issue_id)' was not found", issue_id=issue_id),
                    host_name=config.host
                )
            raise
    except InvalidIssueIdError as e:
        logger.warning(f"Invalid issue EXCEPTION: {e}")
        return render_template(
            'timeline_empty.html.jinja', 
            is_error=True, 
            notification_text=_("Invalid issue ID or URL: 'issue_id'", issue_id=issue_id),
            host_name=config.host
        )
    except Exception as e:
        logger.warning(f"General EXCEPTION: {e}", exc_info=True)
        return render_template(
            'timeline_empty.html.jinja', 
            is_error=True, 
            notification_text=f"Не удалось получить информацию по задаче '{issue_id}'. Обратитесь к {config.support_person} для устранения проблемы.",
            host_name=config.host
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    arg_parser = argparse.ArgumentParser(description='Collects information about YoutTrack issue and visualize it')
    arg_parser.add_argument('-c', '--config', required=True, type=pathlib.Path, help='Configuration file')
    args = arg_parser.parse_args()

    config = YouTrackConfig.from_file(args.config)
    app.config['yt-config'] = config

    if config.debug:
        app.config["TEMPLATES_AUTO_RELOAD"] = True
        app.jinja_env.auto_reload = True
        app.run(debug=True, port=config.port)
    else:
        #TODO: https://flask.palletsprojects.com/en/stable/deploying/
        app.run(debug=False, host='0.0.0.0', port=config.port)
                       