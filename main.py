import argparse
import flask
import logging
import pathlib
import requests

from datetime import timezone, timedelta
from pages.timeline import get_timeline_page_data
from youtrack import YouTrackConfig, InvalidIssueIdError


logger = logging.getLogger("youtrack-analysis")
app = flask.Flask(__name__)


@app.route('/')
def index():
    return flask.redirect(flask.url_for('timeline'))


@app.route('/timeline')
def timeline():
    issue_id = flask.request.args.get('issue', '').strip().lower()
    config: YouTrackConfig = app.config['yt-config']

    try:
        try:
            if len(issue_id) > 0:
                tz = timezone(timedelta(hours=3))
                data = get_timeline_page_data(issue_id=issue_id, tz=tz, config=config)
                return flask.render_template('timeline.html.jinja', **data)
            return flask.render_template('timeline_empty.html.jinja', 
                                         is_error=False, 
                                         notification_text=f'Сервис работает в тестовом режиме. В случае обнаружения проблем обратитесь к {config.support_person}.',
                                         host_name=config.host)
        except requests.HTTPError as e:
            logger.warning(f"Connection EXCEPTION: {e}")
            if e.response.status_code == 404:
                return flask.render_template('timeline_empty.html.jinja', 
                                             is_error=True, 
                                             notification_text=f"Задача с ID '{issue_id}' не найдена",
                                             host_name=config.host)
            raise
    except InvalidIssueIdError as e:
        logger.warning(f"Invalid issue EXCEPTION: {e}")
        return flask.render_template('timeline_empty.html.jinja', 
                                     is_error=True, 
                                     notification_text=f"Неправильный ID или URL задачи: '{issue_id}'",
                                     host_name=config.host)
    except Exception as e:
        logger.warning(f"General EXCEPTION: {e}", exc_info=True)
        return flask.render_template('timeline_empty.html.jinja', 
                                     is_error=True, 
                                     notification_text=f"Не удалось получить информацию по задаче '{issue_id}'. Обратитесь к {config.support_person} для устранения проблемы.",
                                     host_name=config.host)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description='Collects information about YoutTrack issue and visualize it')
    arg_parser.add_argument('-c', '--config', required=True, type=pathlib.Path, help='Configuration file')
    args = arg_parser.parse_args()

    config = YouTrackConfig.from_file(args.config)
    app.config['yt-config'] = config

    logging.basicConfig(level=logging.DEBUG if config.debug else logging.INFO)

    if config.debug:
        app.config["TEMPLATES_AUTO_RELOAD"] = True
        app.jinja_env.auto_reload = True
        app.run(debug=True, port=config.port)
    else:
        #TODO: https://flask.palletsprojects.com/en/stable/deploying/
        app.run(debug=False, host='0.0.0.0', port=config.port)
                       