import collections
import youtrack as yt
from datetime import timezone, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.express as ex
import plotly.io as pio
import operator
from dataclasses import dataclass, field
from functools import cached_property


def to_dict(data: yt.IssueInfo):
        overdues = [{'date': i.timestamp.format_ru(), 
                     'name': i.value} for i in data.overdues]
        tags = [{'text': i.name, 
                 'bg_color': i.background_color, 
                 'fg_color': i.foreground_color} for i in data.tags]
        comments = [{'creation_datetime': i.timestamp.to_datetime().isoformat(timespec='minutes'),
                     'author': i.author, 
                     'text': i.text} for i in data.comments]
        
        @dataclass
        class PersonPauses:
            pauses: list[yt.WorkItem] = field(default_factory=list)

            @cached_property
            def total(self) -> yt.Duration:
                sum = yt.Duration()
                for i in self.pauses:
                    sum += i.business_duration
                return sum

        pauses_total = yt.Duration()
        pauses_total_business = yt.Duration()
        pauses_by_people = collections.defaultdict(PersonPauses)

        for i in data.pauses:
            pauses_by_people[i.name].pauses.append(i)
            pauses_total += i.duration
            pauses_total_business += i.business_duration

        pauses = []
        for entry in sorted(pauses_by_people.items(), key=lambda x: x[1].total, reverse=True):
            name = entry[0]
            for i in sorted(entry[1].pauses):
                pauses.append({'name': name,
                   'begin': i.begin().format_ru(),
                   'end': i.end().format_ru(),
                   'duration': i.duration.format_yt_natural(),
                   'duration_order': i.duration.to_seconds(),
                   'duration_business': i.business_duration.format_yt(),
                   'duration_business_order': i.business_duration.to_seconds(),
                   'percents': round(i.business_duration.to_seconds() / pauses_total_business.to_seconds() * 100, 2) })
        #for name in sorted(pauses_by_people.items(), key=lambda x: x[1], reverse=True):
        #    for j 
        

        

        

        #pauses_by_people = sorted(pauses_by_people, reverse=True)

        #pauses_sorted = sorted(self.pauses, key=lambda x: (x.name, -x.business_duration.to_seconds()), reverse=False)
        #for i in pauses_sorted:
        #    pauses_total += i.duration
        #    pauses_total_business += i.business_duration
        #pauses = [{'name': i.name,
        #           'begin': i.begin().format_ru(),
        #           'end': i.end().format_ru(),
        #           'duration': i.duration.format_yt_natural(),
        #           'duration_order': i.duration.to_seconds(),
        #           'duration_business': i.business_duration.format_yt(),
        #           'duration_business_order': i.business_duration.to_seconds(),
        #           'percents': round(i.business_duration.to_seconds() / pauses_total_business.to_seconds() * 100, 2) } for i in pauses_sorted]

        subtasks = []
        subtasks_total_spent_time = yt.Duration()
        for i in sorted(data.subtasks, key=lambda x: x.spent_time_yt, reverse=True):
            subtasks_total_spent_time += i.spent_time_yt
            subtasks.append({'id': i.id,
                             'title': i.summary,
                             'state': i.state,
                             'spent_time': i.spent_time_yt.format_yt(),
                             'percent': f'{i.spent_time_yt.to_seconds() / data.spent_time_yt.to_seconds() * 100:.2f}'})

        return {
            # Basic
            'id': data.id,
            'summary': data.summary,
            'author': data.author,
            'state': data.state,
            'is_resolved': data.is_finished,
            'scope': data.scope.format_yt() if data.scope else None,
            'scope_overrun': data.scope_overrun,
            'creation_datetime': data.creation_datetime.format_ru(),
            'spent_time': data.spent_time.format_yt(),
            'reaction_time': data.reaction_time.format_yt_natural() if data.is_started else None,
            'resolution_time': data.resolution_time.format_yt_natural() if data.is_finished else None,

            # Containers
            'overdues': overdues,
            'tags': tags,
            'comments': comments,
            'yt_errors': data.yt_errors,
            'pauses': {
                'total': pauses_total.format_yt_natural(),
                'total_business': pauses_total_business.format_yt(),
                'entries': pauses
            },
            'subtasks': {
                'total': subtasks_total_spent_time.format_yt(),
                'entries': subtasks
            }
        }



def get_detailed_info(data: yt.IssueInfo) -> list[dict[str, str]]:
    cont = collections.defaultdict(yt.Duration)
    for work_item in data.work_items:
        key = (work_item.name, work_item.state) 
        cont[key] += work_item.duration

    cont = dict(sorted(cont.items(), key=operator.itemgetter(1,0), reverse=True))
    total_spent_time = data.spent_time.to_seconds()

    return [{'name': k[0],
             'state': k[1],
             'spent_time': v.format_yt(),
             'spent_time_order': v.to_seconds(),
             'percent': round(v.to_seconds() / total_spent_time * 100, 2)} for k,v in cont.items()]


def get_by_people_info(data: yt.IssueInfo) -> list[dict[str, str]]:
    cont = collections.defaultdict(yt.Duration)
    for work_item in data.work_items:
        cont[work_item.name] += work_item.duration

    cont = dict(sorted(cont.items(), key=lambda item: item[1], reverse=True))
    total_spent_time = data.spent_time.to_seconds()
    
    return [{'name': k, 
             'spent_time': v.format_yt(),
             'spent_time_order': v.to_seconds(),
             'percent': round(v.to_seconds() / total_spent_time * 100, 2)} for k,v in cont.items()]


def get_timeline_page_data(issue_id: str, tz: timezone, config: yt.YouTrackConfig):
    data = yt.ApiHelper(config=config).get_summary(id=issue_id)

    # Quickfix if there are no workitems
    df_workitems = pd.DataFrame({'Assignee': [],
                                 'Start': [],
                                 'Finish': [],
                                 'State': []})
    
    if not yt.is_empty(data.work_items):
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
    if not yt.is_empty(data.comments):
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
            'by_people': get_by_people_info(data)
        }
    )
    template_data.update(to_dict(data))
    return template_data