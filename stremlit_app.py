import datetime as dt
import os
from enum import Enum

import pandas as pd
import plotly.graph_objects as go
import psycopg2
import streamlit as st
from plotly.subplots import make_subplots

st.set_page_config(layout="wide", page_icon=":helicopter:")


class ReportType(Enum):
    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"


with st.sidebar:
    with st.form("inputs"):
        start_date = st.date_input(
            "Start Date:", value=dt.date.today() - dt.timedelta(days=365)
        )
        end_date = st.date_input("End Date:", value=dt.date.today())
        report_type_values = [rt.value for rt in ReportType]
        report_type_selection = st.selectbox(
            "Report Type",
            report_type_values,
            index=report_type_values.index(ReportType.WEEKLY.value),
        )
        submitted = st.form_submit_button("Submit 🚀")


def run_weekly_report(sdate, edate):
    conn = psycopg2.connect(
        database="tilly",
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PWD"),
        host="34.136.67.154",
        port="5432",
    )
    cur = conn.cursor()
    cur.execute(
        f"""
with memes_count as
(
select
date_trunc('week', created::timestamp)::date as week_start,
(date_trunc('week', created::timestamp)+ '6 days'::interval)::date as week_end,
count(*) as memes_created,
COUNT(CASE WHEN status='PUBLISHED' THEN id END) as published,
COUNT(CASE WHEN status <> 'PUBLISHED' THEN id END) as not_published

from meme where created between TO_DATE('{sdate}','YYYY-MM-DD') and TO_DATE('{edate}','YYYY-MM-DD') 
group by 1,2
order by 1
),
votes_count as(
select
date_trunc('week', created::timestamp)::date as week_start,
(date_trunc('week', created::timestamp)+ '6 days'::interval)::date as week_end,
count(*) as votes
from vote where created between TO_DATE('{sdate}','YYYY-MM-DD') and TO_DATE('{edate}','YYYY-MM-DD') 
group by 1,2
order by 1
)
select coalesce(memes_count.week_start,votes_count.week_start),
       coalesce(memes_count.week_end,votes_count.week_end),
       memes_count.memes_created,
       memes_count.published,
       memes_count.not_published,
       votes_count.votes 
from memes_count
full outer join  votes_count
on memes_count.week_start = votes_count.week_start

"""
    )
    df = pd.DataFrame(
        cur.fetchall(),
        columns=[
            "week_start",
            "week_end",
            "memes_created",
            "published",
            "not_published",
            "voted",
        ],
    )
    conn.close()
    return df


if not submitted:
    st.info("Please select the inputs and press Submit.", icon="ℹ")
else:
    match report_type_selection:
        case [ReportType.DAILY.value, ReportType.MONTHLY.value]:
            st.error(
                "The Daily or Monthly dashboard in not ready yet, but we are working on it 🚨"
            )
        case ReportType.WEEKLY.value:
            df = run_weekly_report(start_date, end_date)
            st.title("Weekly Statistics")
            fig = make_subplots(
                rows=2,
                cols=2,
                specs=[
                    [{"secondary_y": True}, {"secondary_y": True}],
                    [{"colspan": 2}, None],
                ],
                subplot_titles=("Created", "Voted", "Published vs. Not Published"),
            )

            fig.add_trace(
                go.Bar(
                    x=df["week_start"],
                    y=df["memes_created"],
                    name="Memes Created",
                    marker={"color": "#a7b814"},
                ),
                row=1,
                col=1,
                secondary_y=False,
            )
            fig.add_trace(
                go.Bar(
                    x=df["week_start"],
                    y=df["voted"],
                    name="Memes Voted",
                    marker={"color": "#945bc2"},
                ),
                row=1,
                col=2,
                secondary_y=False,
            )
            fig.add_trace(
                go.Bar(
                    x=df["week_start"],
                    y=df["published"],
                    name="Memes Published",
                    marker={"color": "#ffbb00"},
                ),
                row=2,
                col=1,
                secondary_y=False,
            )
            fig.add_trace(
                go.Bar(
                    x=df["week_start"],
                    y=df["not_published"],
                    name="Memes Not Published",
                    marker={"color": "#e64b4b"},
                ),
                row=2,
                col=1,
                secondary_y=False,
            )
            fig.update_layout(barmode="group", height=1000, width=1500)

            st.plotly_chart(fig, use_container_width=True)
