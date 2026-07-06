from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, dash_table
from dynaconf import Dynaconf
from sqlalchemy import create_engine


def load_settings() -> Dynaconf:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    return Dynaconf(
        envvar_prefix=False,
        load_dotenv=True,
        dotenv_path=str(env_path),
        environments=False,
    )


def build_engine(settings: Dynaconf):
    user = settings.get("DB_USER")
    password = settings.get("DB_PASSWORD")
    host = settings.get("DB_HOST", "localhost")
    port = settings.get("DB_PORT", 5432)
    database = settings.get("DB_DATABASE", "postgres")

    user_q = quote_plus(str(user))
    password_q = quote_plus(str(password))
    url = f"postgresql+psycopg://{user_q}:{password_q}@{host}:{port}/{database}"
    return create_engine(url)


def load_view(engine, view_name: str) -> pd.DataFrame:
    query = f"select * from characters.{view_name}"
    return pd.read_sql(query, engine)


def load_character_numeric(engine) -> pd.DataFrame:
    query = """
        select
            total_level,
            hp,
            str,
            dex,
            con,
            "int" as int_stat,
            wis,
            cha,
            notes_len
        from characters.character
        """
    return pd.read_sql(query, engine)


def load_multiclass_rate_by_class(engine) -> pd.DataFrame:
    query = """
    with class_counts as (
        select
            char_id,
            count(distinct class) as class_count
        from characters.character_class
        group by char_id
    ),
    class_membership as (
        select distinct
            cc.char_id,
            cc.class,
            case when cnt.class_count > 1 then 1 else 0 end as is_multiclass
        from characters.character_class cc
        join class_counts cnt on cnt.char_id = cc.char_id
    )
    select
        class,
        count(*) as characters_with_class,
        sum(is_multiclass) as multiclass_characters,
        round(100.0 * sum(is_multiclass)::numeric / nullif(count(*), 0), 2) as multiclass_rate_pct
    from class_membership
    group by class
    order by multiclass_rate_pct desc, characters_with_class desc
    """
    return pd.read_sql(query, engine)


def kpi_card(title: str, value: str) -> html.Div:
    return html.Div(
        className="kpi-card",
        children=[
            html.Div(title, className="kpi-title"),
            html.Div(value, className="kpi-value"),
        ],
    )


def render_overview(kpis_df: pd.DataFrame, class_df: pd.DataFrame, race_df: pd.DataFrame) -> html.Div:
    k = kpis_df.iloc[0]

    kpi_row = html.Div(
        className="kpi-row",
        children=[
            kpi_card("Total Characters", f"{int(k['total_characters']):,}"),
            kpi_card("Multiclass Characters", f"{int(k['multiclass_characters']):,}"),
            kpi_card("Level 20 Characters", f"{int(k['level_20_characters']):,}"),
            kpi_card("Average Level", f"{float(k['avg_total_level']):.2f}"),
        ],
    )

    class_top = class_df.sort_values("character_count", ascending=False).head(15)
    class_fig = px.bar(
        class_top,
        x="character_count",
        y="class",
        orientation="h",
        title="Top Classes",
        labels={"character_count": "Characters", "class": "Class"},
    )
    class_fig.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=60, b=20), yaxis=dict(autorange="reversed"))

    race_top = race_df.sort_values("character_count", ascending=False).head(15)
    race_fig = px.bar(
        race_top,
        x="character_count",
        y="race",
        orientation="h",
        title="Top Races",
        labels={"character_count": "Characters", "race": "Race"},
    )
    race_fig.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=60, b=20), yaxis=dict(autorange="reversed"))

    return html.Div(
        children=[
            kpi_row,
            html.Div(
                className="chart-grid",
                children=[
                    html.Div(className="chart-card", children=[dcc.Graph(figure=class_fig, config={"displayModeBar": False})]),
                    html.Div(className="chart-card", children=[dcc.Graph(figure=race_fig, config={"displayModeBar": False})]),
                ],
            ),
        ]
    )


def render_stats(maxed_df: pd.DataFrame, dump_df: pd.DataFrame) -> html.Div:
    maxed_fig = px.bar(
        maxed_df.sort_values("maxed_count", ascending=False),
        x="stat_name",
        y="maxed_count",
        title="Most Popular Stat To Max",
        labels={"stat_name": "Stat", "maxed_count": "Maxed Count"},
    )
    maxed_fig.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=60, b=20))

    dump_fig = px.bar(
        dump_df.sort_values("dump_count", ascending=False),
        x="stat_name",
        y="dump_count",
        title="Most Popular Dump Stat",
        labels={"stat_name": "Stat", "dump_count": "Dump Count"},
    )
    dump_fig.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=60, b=20))

    return html.Div(
        className="chart-grid",
        children=[
            html.Div(className="chart-card", children=[dcc.Graph(figure=maxed_fig, config={"displayModeBar": False})]),
            html.Div(className="chart-card", children=[dcc.Graph(figure=dump_fig, config={"displayModeBar": False})]),
        ],
    )


def render_classes(subclass_df: pd.DataFrame, notes_df: pd.DataFrame, multiclass_df: pd.DataFrame) -> html.Div:
    excluded_pattern = r"artificer|blood hunter"

    subclass_fig = px.bar(
        subclass_df.sort_values("subclass_count", ascending=False).head(20),
        x="subclass_count",
        y="class",
        color="most_popular_subclass",
        orientation="h",
        title="Most Popular Subclass Per Class",
        labels={"subclass_count": "Count", "class": "Class", "most_popular_subclass": "Subclass"},
    )
    subclass_fig.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=60, b=20), yaxis=dict(autorange="reversed"))

    notes_filtered = notes_df.loc[
        ~notes_df["class"].str.contains(excluded_pattern, case=False, na=False)
    ]
    notes_fig = px.bar(
        notes_filtered.sort_values("avg_notes_len", ascending=False),
        x="class",
        y="avg_notes_len",
        title="Average Notes Length By Class",
        labels={"class": "Class", "avg_notes_len": "Avg Notes Length"},
    )
    notes_fig.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=60, b=20), xaxis_tickangle=-30)

    multiclass_filtered = multiclass_df.loc[
        ~multiclass_df["class"].str.contains(excluded_pattern, case=False, na=False)
    ]
    multiclass_fig = px.bar(
        multiclass_filtered,
        x="multiclass_rate_pct",
        y="class",
        orientation="h",
        title="Multiclass Rate By Class",
        labels={"multiclass_rate_pct": "Multiclass Rate (%)", "class": "Class"},
    )
    multiclass_fig.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=60, b=20), yaxis=dict(autorange="reversed"))

    return html.Div(
        className="chart-grid",
        children=[
            html.Div(className="chart-card", children=[dcc.Graph(figure=subclass_fig, config={"displayModeBar": False})]),
            html.Div(className="chart-card", children=[dcc.Graph(figure=notes_fig, config={"displayModeBar": False})]),
            html.Div(className="chart-card", children=[dcc.Graph(figure=multiclass_fig, config={"displayModeBar": False})]),
        ],
    )


def render_data_explorer(class_df: pd.DataFrame, notes_df: pd.DataFrame) -> html.Div:
    combined = (
        class_df.rename(columns={"class": "category", "character_count": "count"})
        .assign(metric="class_popularity")
        .loc[:, ["metric", "category", "count"]]
    )

    notes_table = (
        notes_df.rename(columns={"class": "category", "avg_notes_len": "count"})
        .assign(metric="avg_notes_len_by_class")
        .loc[:, ["metric", "category", "count"]]
    )

    table_df = pd.concat([combined, notes_table], ignore_index=True)

    return html.Div(
        className="table-wrap",
        children=[
            html.H3("Data Explorer"),
            dash_table.DataTable(
                columns=[{"name": c, "id": c} for c in table_df.columns],
                data=table_df.to_dict("records"),
                page_size=20,
                sort_action="native",
                filter_action="native",
                style_table={"overflowX": "auto"},
                style_header={
                    "backgroundColor": "#f3eee4",
                    "fontWeight": "700",
                    "border": "1px solid #ddd3c4",
                },
                style_cell={
                    "padding": "10px",
                    "border": "1px solid #eee6d9",
                    "fontFamily": "Georgia, 'Times New Roman', serif",
                    "fontSize": "14px",
                },
                style_data_conditional=[
                    {
                        "if": {"row_index": "odd"},
                        "backgroundColor": "#fffdf9",
                    }
                ],
            ),
        ]
    )


def render_correlation_matrix(numeric_df: pd.DataFrame) -> html.Div:
    corr = numeric_df.corr(numeric_only=True).round(2)
    corr = corr.rename(
        columns={"int_stat": "int"},
        index={"int_stat": "int"},
    )

    fig = px.imshow(
        corr,
        text_auto=True,
        color_continuous_scale="RdBu",
        zmin=-1,
        zmax=1,
        aspect="auto",
        title="Correlation Matrix (Numeric Character Fields)",
    )
    fig.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=60, b=20))

    return html.Div(
        className="chart-grid",
        children=[
            html.Div(
                className="chart-card full-width",
                children=[dcc.Graph(figure=fig, config={"displayModeBar": False})],
            ),
        ],
    )


def build_app() -> Dash:
    settings = load_settings()
    engine = build_engine(settings)

    kpis_df = load_view(engine, "vw_dashboard_kpis")
    class_df = load_view(engine, "vw_class_popularity")
    maxed_df = load_view(engine, "vw_maxed_stats")
    dump_df = load_view(engine, "vw_dump_stats")
    subclass_df = load_view(engine, "vw_top_subclass_per_class")
    notes_df = load_view(engine, "vw_class_notes_summary")
    race_df = load_view(engine, "vw_race_popularity")
    numeric_df = load_character_numeric(engine)
    multiclass_df = load_multiclass_rate_by_class(engine)

    app = Dash(__name__)
    app.title = "DND Character Dashboard"

    app.layout = html.Div(
        className="page",
        children=[
            html.H1("DND Character Insights", className="page-title"),
            html.P(
                "Dashboard built from the characters schema and view layer.",
                className="page-subtitle",
            ),
            dcc.Tabs(
                className="tabs-shell",
                children=[
                    dcc.Tab(label="Overview", className="tab", selected_className="tab--selected", children=render_overview(kpis_df, class_df, race_df)),
                    dcc.Tab(label="Stats", className="tab", selected_className="tab--selected", children=render_stats(maxed_df, dump_df)),
                    # dcc.Tab(label="Correlation", className="tab", selected_className="tab--selected", children=render_correlation_matrix(numeric_df)),
                    dcc.Tab(label="Classes", className="tab", selected_className="tab--selected", children=render_classes(subclass_df, notes_df, multiclass_df)),
                    dcc.Tab(label="Explorer", className="tab", selected_className="tab--selected", children=render_data_explorer(class_df, notes_df)),
                ]
            ),
        ],
    )

    return app


if __name__ == "__main__":
    dash_app = build_app()
    dash_app.run(debug=True)
