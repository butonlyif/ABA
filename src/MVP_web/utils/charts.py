"""
====================================
ABA智能助手 - 数据可视化模块
====================================

使用Plotly生成可视化图表：
- 类别分布饼图
- 进展趋势折线图
- 家长关注度柱状图
- 时间线日历图
"""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import List, Dict, Optional


COLORS = {
    "primary": "#4A90D9",
    "secondary": "#6C757D",
    "success": "#28A745",
    "warning": "#FFC107",
    "danger": "#DC3545",
    "info": "#17A2B8",
    "purple": "#7B68EE",
    "orange": "#FF8C00",
    "pink": "#FF69B4",
    "teal": "#20B2AA",
}

CHART_TEMPLATE = "plotly_white"


def create_category_pie_chart(category_stats: Dict[str, int], title: str = "类别分布") -> go.Figure:
    """创建类别分布饼图"""
    if not category_stats:
        return create_empty_chart("暂无数据")

    labels = list(category_stats.keys())
    values = list(category_stats.values())

    color_list = list(COLORS.values())[:len(labels)]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        marker=dict(colors=color_list),
        textinfo='label+percent',
        textposition='outside',
        hole=0.4,
        hovertemplate="<b>%{label}</b><br>数量: %{value}<br>占比: %{percent}<extra></extra>"
    )])

    fig.update_layout(
        title=dict(text=title, font=dict(size=18, color="#343A40")),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        template=CHART_TEMPLATE,
        height=400,
        margin=dict(t=80, b=80, l=40, r=40)
    )

    return fig


def create_progress_line_chart(logs: List[Dict], title: str = "进展趋势") -> go.Figure:
    """创建进展趋势折线图"""
    if not logs:
        return create_empty_chart("暂无数据")

    logs_sorted = sorted(logs, key=lambda x: x.get("log_date", ""))

    dates = [log.get("log_date", "")[:10] for log in logs_sorted]
    categories = [log.get("category", "其他") for log in logs_sorted]

    unique_dates = sorted(list(set(dates)))
    date_counts = {d: dates.count(d) for d in unique_dates}

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=list(date_counts.keys()),
        y=list(date_counts.values()),
        mode='lines+markers',
        name='记录数',
        line=dict(color=COLORS["primary"], width=3),
        marker=dict(size=10, color=COLORS["primary"], symbol='circle'),
        fill='tozeroy',
        fillcolor='rgba(74, 144, 217, 0.2)'
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=18, color="#343A40")),
        xaxis_title="日期",
        yaxis_title="记录数",
        template=CHART_TEMPLATE,
        height=350,
        hovermode='x unified',
        xaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.05)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.05)')
    )

    return fig


def create_concern_bar_chart(concern_counts: Dict[str, int], title: str = "家长关注点分析") -> go.Figure:
    """创建家长关注度柱状图"""
    if not concern_counts:
        return create_empty_chart("暂无数据")

    sorted_concerns = sorted(concern_counts.items(), key=lambda x: x[1], reverse=True)
    categories = [c[0] for c in sorted_concerns]
    counts = [c[1] for c in sorted_concerns]

    colors = [COLORS["primary"], COLORS["info"], COLORS["success"],
              COLORS["warning"], COLORS["purple"], COLORS["orange"]][:len(categories)]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=categories,
        y=counts,
        marker_color=colors,
        text=counts,
        textposition='outside',
        hovertemplate="<b>%{x}</b><br>次数: %{y}<extra></extra>"
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=18, color="#343A40")),
        xaxis_title="关注话题",
        yaxis_title="出现次数",
        template=CHART_TEMPLATE,
        height=350,
        showlegend=False,
        xaxis=dict(tickangle=-15),
        yaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.05)')
    )

    return fig


def create_activity_heatmap(logs: List[Dict], title: str = "活动热力图") -> go.Figure:
    """创建活动热力图"""
    if not logs:
        return create_empty_chart("暂无数据")

    logs_sorted = sorted(logs, key=lambda x: x.get("log_date", ""))

    if len(logs_sorted) < 7:
        return create_empty_chart("数据不足，无法生成热力图（需要至少7条记录）")

    last_30_days = []
    today = datetime.now()

    for i in range(30, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        count = sum(1 for log in logs_sorted if log.get("log_date", "")[:10] == day_str)
        last_30_days.append({
            "date": day_str,
            "day": day.strftime('%m/%d'),
            "weekday": day.strftime('%A')[:3],
            "count": count
        })

    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    weeks = []
    current_week = []

    for i, day_data in enumerate(last_30_days):
        weekday = (i % 7)
        current_week.append(day_data['count'])

        if weekday == 6 or i == len(last_30_days) - 1:
            while len(current_week) < 7:
                current_week.insert(0, 0)
            weeks.append(current_week)
            current_week = []

    fig = go.Figure(data=go.Heatmap(
        z=weeks,
        x=weekdays,
        y=[f'Week {i+1}' for i in range(len(weeks))],
        colorscale='Blues',
        showscale=True,
        colorbar=dict(title="记录数"),
        hovertemplate="<b>%{y}</b><br>%{x}<br>记录数: %{z}<extra></extra>"
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=18, color="#343A40")),
        template=CHART_TEMPLATE,
        height=250,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False)
    )

    return fig


def create_category_comparison_chart(category_stats: Dict[str, int], title: str = "类别对比") -> go.Figure:
    """创建类别对比柱状图"""
    if not category_stats:
        return create_empty_chart("暂无数据")

    categories = list(category_stats.keys())
    values = list(category_stats.values())

    colors = [COLORS["primary"], COLORS["info"], COLORS["success"],
              COLORS["warning"], COLORS["purple"], COLORS["orange"],
              COLORS["pink"], COLORS["teal"]][:len(categories)]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=categories,
        x=values,
        orientation='h',
        marker_color=colors,
        text=values,
        textposition='outside',
        hovertemplate="<b>%{y}</b><br>数量: %{x}<extra></extra>"
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=18, color="#343A40")),
        xaxis_title="数量",
        yaxis_title="类别",
        template=CHART_TEMPLATE,
        height=max(300, len(categories) * 50),
        showlegend=False,
        yaxis=dict(autorange="reversed"),
        xaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.05)')
    )

    return fig


def create_report_summary_chart(stats: Dict, title: str = "报告统计") -> go.Figure:
    """创建报告摘要仪表盘"""
    fig = make_subplots(
        rows=2, cols=2,
        specs=[[{"type": "indicator"}, {"type": "indicator"}],
               [{"type": "bar", "colspan": 2}, None]],
        subplot_titles=("总对话数", "总记录数", "类别分布"),
        row_heights=[0.4, 0.6],
        vertical_spacing=0.15,
        horizontal_spacing=0.1
    )

    conv_total = stats.get("conv_total", 0)
    log_total = stats.get("log_total", 0)
    category_stats = stats.get("category_stats", {})

    fig.add_trace(go.Indicator(
        mode="number",
        value=conv_total,
        title={"text": "对话轮次"},
        domain={'row': 0, 'column': 0},
        number=dict(valueformat='d', font=dict(size=24))
    ), row=1, col=1)

    fig.add_trace(go.Indicator(
        mode="number",
        value=log_total,
        title={"text": "记录条数"},
        domain={'row': 0, 'column': 1},
        number=dict(valueformat='d', font=dict(size=24))
    ), row=1, col=2)

    if category_stats:
        cats = list(category_stats.keys())
        vals = list(category_stats.values())

        fig.add_trace(go.Bar(
            x=cats,
            y=vals,
            marker_color=COLORS["primary"],
            showlegend=False
        ), row=2, col=1)

    fig.update_layout(
        title=dict(text=title, font=dict(size=18, color="#343A40")),
        template=CHART_TEMPLATE,
        height=400,
        showlegend=False
    )

    return fig


def create_empty_chart(message: str = "暂无数据") -> go.Figure:
    """创建空图表"""
    fig = go.Figure()

    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=16, color="#6C757D")
    )

    fig.update_layout(
        template=CHART_TEMPLATE,
        height=300,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
    )

    return fig


def create_trend_indicator(current: int, previous: int) -> go.Figure:
    """创建趋势指示器"""
    if previous == 0:
        change = 0
    else:
        change = ((current - previous) / previous) * 100

    fig = go.Figure()

    fig.add_trace(go.Indicator(
        mode="number+delta",
        value=current,
        delta={"value": change, "suffix": "%"},
        title={"text": "对比上期"},
        domain={'row': 0, 'column': 0}
    ))

    fig.update_layout(
        template=CHART_TEMPLATE,
        height=100,
        margin=dict(l=20, r=20, t=20, b=20)
    )

    return fig
