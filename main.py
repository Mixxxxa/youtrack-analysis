import logging
import pathlib
import collections
import logging
import youtrack as yt
import requests

import pandas as pd
import flask
import plotly.graph_objects as go
import plotly.express as ex
import plotly.io as pio
from datetime import timezone, timedelta
import argparse


logger = logging.getLogger("youtrack-analysis")
app = flask.Flask(__name__)


def get_detailed_info(data: yt.IssueInfo) -> list[dict[str, str]]:
    cont = collections.defaultdict(yt.Duration)
    for work_item in data.work_items:
        key = (work_item.name, work_item.state) 
        cont[key] += work_item.duration

    cont = dict(sorted(cont.items(), key=lambda item: item[1], reverse=True))
    total_spent_time = data.spent_time.to_seconds()

    return [{'name': k[0],
             'state': k[1],
             'spent_time': v.format_business(),
             'percent': f'{v.to_seconds() / total_spent_time * 100:.2f}%'} for k,v in cont.items()]


def get_by_people_info(data: yt.IssueInfo) -> list[dict[str, str]]:
    cont = collections.defaultdict(yt.Duration)
    for work_item in data.work_items:
        cont[work_item.name] += work_item.duration

    cont = dict(sorted(cont.items(), key=lambda item: item[1], reverse=True))
    total_spent_time = data.spent_time.to_seconds()
    
    return [{'name': k, 
             'spent_time': v.format_business(),
             'percent': f'{v.to_seconds() / total_spent_time * 100:.2f}%'} for k,v in cont.items()]


def get_by_type_info(data: yt.IssueInfo) -> list[dict[str, str]]:
    cont = collections.defaultdict(yt.Duration)
    for work_item in data.work_items:
        key = work_item.state
        cont[key] += work_item.duration

    cont = dict(sorted(cont.items(), key=lambda item: item[1], reverse=True))
    total_spent_time = data.spent_time.to_seconds()
    
    return [{'state':k,
             'spent_time': v.format_business(),
             'percent': f'{v.to_seconds() / total_spent_time * 100:.2f}%'} for k,v in cont.items()]


def get_timeline_page_data(issue_id: str, tz: timezone):
    config: yt.YouTrackConfig = app.config['yt-config']
    data = yt.ApiHelper(config=config).get_summary(id=issue_id)

    df_workitems = pd.DataFrame([{'Assignee': i.name,
                                  'Start': i.begin().to_datetime(tz),
                                  'Finish': i.end().to_datetime(tz),
                                  'State': i.state } for i in data.work_items])
    
    df_comments = pd.DataFrame([{'date': i.timestamp.to_datetime(tz),
                                 'author': i.author,
                                 'text': i.text } for i in data.comments])

    df_assignee_entries = []
    for i, v in enumerate(data.assignees):
        if i == 0:
            continue
        prev = data.assignees[i-1]
        df_assignee_entries.append({ 'date': prev.timestamp.to_datetime(tz), 'assignee': prev.value})
        df_assignee_entries.append({ 'date': v.timestamp.to_datetime(tz), 'assignee': prev.value})
        df_assignee_entries.append({ 'date': v.timestamp.to_datetime(tz), 'assignee': v.value})
    # hack: если задача не завершена, то рисуем линию assignee от последней активности до текущего момента
    if len(data.assignees) > 0:
        prev = data.assignees[-1]
        df_assignee_entries.append({ 'date': prev.timestamp.to_datetime(tz), 'assignee': prev.value })
        df_assignee_entries.append({ 'date': data.resolve_datetime.to_datetime(tz) if data.is_finished else yt.Timestamp.now().to_datetime(tz), 'assignee': prev.value })
    df_assignee = pd.DataFrame(df_assignee_entries)

    fig = ex.timeline(
        df_workitems, 
        x_start='Start', 
        x_end='Finish', 
        y='Assignee',
        color='State',
        category_orders = { "Assignee": list(reversed(list(dict.fromkeys([i.value for i in data.assignees])))) },
        color_discrete_map = {
            'Buffer': 'SkyBlue',
            'In progress': 'Orange',
            'Review': 'SeaGreen',
        }
    )
    fig.add_trace(go.Scatter(
            x=df_assignee['date'],
            y=df_assignee['assignee'],
            mode='lines',
            line=dict(width=2, color='red'),
            legendgroup="misc",
            legendgrouptitle_text="Misc",
            name='Assignee'
        )
    )
    fig.add_trace(go.Scatter(
        x=df_comments['date'],
        y=df_comments['author'],
        text=df_comments['text'],
        name='Комментарии',
        mode='markers',
        marker=dict(size=10, color='DarkViolet'),
        zorder=9999
    ))

    for i,work_item in enumerate(data.pauses):
        fig.add_vrect(
            x0=work_item.begin().to_datetime(tz),
            x1=work_item.end().to_datetime(tz),
            fillcolor="grey", 
            line_width=0,
            opacity=0.3,
            name='Pause',
            legendgroup="misc",
            showlegend=(i==0)
        )
    for i,overdue in enumerate(data.overdues):
        fig.add_vline(
            x=overdue.timestamp.to_datetime(tz),
            line_color="DarkRed", 
            showlegend=(i==0),
            name='Overdue', 
            legendgroup="misc"
        )
      
    fig.add_vline(
        x=data.creation_datetime.to_datetime(tz), 
        line_dash="dash",
        line_color="red", 
        opacity=1.0, 
        showlegend=True, 
        name='Created', 
        legendgroup="milestones",
        legendgrouptitle_text="Milestones"
    )
       
    if data.is_finished:
        fig.add_vline(
            x=data.resolve_datetime.to_datetime(tz), 
            line_dash="dash", 
            line_color="red", 
            opacity=1.0, 
            showlegend=True, 
            name='Resolved', 
            legendgroup="milestones"
        )
    if data.started_datetime is not None:
        fig.add_vline(
            x=data.started_datetime.to_datetime(tz), 
            line_dash="dash", 
            line_color="blue", 
            showlegend=True, 
            name='Взято в работу', 
            legendgroup="milestones"
        )
    fig.update_yaxes(showgrid=True)
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='var(--text-color)',
        margin=dict(l=0, r=0, t=30, b=20),
        height=360,
        legend=dict(groupclick="toggleitem"),
        yaxis_title=None
    )
    fig.update_xaxes(
        ticks="outside",
        ticklabelmode="period", 
        tickcolor="black", 
        ticklen=10, 
        minor=dict(
            ticklen=4,  
            dtick=7*24*60*60*1000,  
            tick0="2016-07-03", 
            griddash='dot', 
            gridcolor='white'
        ),
        range=[
            data.creation_datetime.to_datetime(tz), 
            data.resolve_datetime.to_datetime(tz) if data.is_finished else yt.Timestamp.now().to_datetime(tz)
        ],
        rangeslider_visible=True,
        tickformatstops=[
            dict(dtickrange=[60000, 3600000], value="%d %b %H:%M"),
            dict(dtickrange=[3600000, 86400000], value="%d %b %H:%M"),
            dict(dtickrange=[86400000, 604800000], value="%d %b %H:%M"),
            dict(dtickrange=[604800000, "M1"], value="%e. %b w"),
            dict(dtickrange=["M1", "M12"], value="%b '%y M"),
            dict(dtickrange=["M12", None], value="%Y Y")
        ]
    )
    template_data = dict(
        issue_url=config.get_issue_url(issue_id),
        graph_div=pio.to_html(fig, full_html=False, div_id='9cc162d8-61cf-4829-aede-73d8b3495197'),
        tables={
            'detailed': get_detailed_info(data),
            'by_type': get_by_type_info(data),
            'by_people': get_by_people_info(data)
        }
    )
    template_data.update(data.to_dict())
    return template_data


@app.route('/')
def index():
    return flask.redirect(flask.url_for('timeline'))


@app.route('/timeline')
def timeline():
    issue_id = flask.request.args.get('issue', '').strip().lower()
    config: yt.YouTrackConfig = app.config['yt-config']

    try:
        try:
            if len(issue_id) > 0:
                tz = timezone(timedelta(hours=3))
                data = get_timeline_page_data(issue_id=issue_id, tz=tz)
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
    except yt.InvalidIssueIdError as e:
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
    logging.basicConfig(level=logging.INFO)

    arg_parser = argparse.ArgumentParser(description='Collects information about YoutTrack issue and visualize it')
    arg_parser.add_argument('-c', '--config', required=True, type=pathlib.Path, help='Configuration file')
    args = arg_parser.parse_args()

    config = yt.YouTrackConfig.from_file(args.config)
    app.config['yt-config'] = config

    if config.debug:
        app.config["TEMPLATES_AUTO_RELOAD"] = True
        app.jinja_env.auto_reload = True
        app.run(debug=True, port=config.port)
    else:
        #TODO: https://flask.palletsprojects.com/en/stable/deploying/
        app.run(debug=False, host='0.0.0.0', port=config.port)
                       