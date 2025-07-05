"""
Student Performance Dashboard - Real-time Analytics
Interactive dashboard for analyzing student academic performance with live data updates.
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import redis
from dash import Input, Output, State, callback, dash_table, dcc, html
from dotenv import load_dotenv
from plotly.subplots import make_subplots
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Dash app with Bootstrap theme
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
    title="Student Performance Dashboard",
    suppress_callback_exceptions=True,
)

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/student_data_db")
engine = create_engine(DATABASE_URL)


# Redis for caching
def get_redis_client():
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        return redis.from_url(redis_url, decode_responses=True)
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
        return None


redis_client = get_redis_client()


# Data loading functions
def load_performance_data(filters=None):
    """Load student performance data with filters."""
    try:
        query = """
        WITH student_performance AS (
            SELECT
                s.id as student_id,
                s.student_id as student_code,
                s.first_name || ' ' || s.last_name as student_name,
                s.gender,
                s.current_class,
                s.status,
                EXTRACT(YEAR FROM AGE(s.date_of_birth)) as age,

                -- School information
                sch.name as school_name,
                sch.type as school_type,
                sch.category as school_category,

                -- Geographic information
                d.name as division,
                dist.name as district,
                u.name as upazila,

                -- Enrollment information
                e.academic_year,
                e.section,
                e.roll_number,
                e.final_percentage,
                e.final_grade,
                e.final_result,

                -- Assessment results
                ar.marks_obtained,
                ar.total_marks,
                ar.percentage as assessment_percentage,
                ar.letter_grade,
                ar.is_pass,
                ar.rank_in_class,
                ar.rank_in_school,

                -- Subject information
                sub.name as subject_name,
                sub.category as subject_category,

                -- Assessment information
                a.name as assessment_name,
                a.type as assessment_type,
                a.term,
                a.scheduled_date as assessment_date

            FROM students s
            LEFT JOIN enrollments e ON s.id = e.student_id AND e.is_active = true
            LEFT JOIN schools sch ON e.school_id = sch.id
            LEFT JOIN divisions d ON s.division_id = d.id
            LEFT JOIN districts dist ON s.district_id = dist.id
            LEFT JOIN upazilas u ON s.upazila_id = u.id
            LEFT JOIN assessment_results ar ON s.id = ar.student_id
            LEFT JOIN assessments a ON ar.assessment_id = a.id
            LEFT JOIN subjects sub ON ar.subject_id = sub.id
            WHERE s.is_deleted = false
            AND (e.is_deleted = false OR e.id IS NULL)
            AND (sch.is_deleted = false OR sch.id IS NULL)
        )
        SELECT * FROM student_performance
        WHERE student_id IS NOT NULL
        ORDER BY assessment_date DESC, student_name
        LIMIT 10000
        """

        df = pd.read_sql(query, engine)

        # Apply filters if provided
        if filters:
            if filters.get("division") and filters["division"] != "all":
                df = df[df["division"] == filters["division"]]
            if filters.get("grade") and filters["grade"] != "all":
                df = df[df["current_class"] == f"Class {filters['grade']}"]
            if filters.get("academic_year"):
                df = df[df["academic_year"] == filters["academic_year"]]
            if filters.get("school_type") and filters["school_type"] != "all":
                df = df[df["school_type"] == filters["school_type"]]

        return df

    except Exception as e:
        logger.error(f"Error loading performance data: {e}")
        return pd.DataFrame()


def get_key_metrics(filters=None):
    """Get key performance metrics."""
    try:
        df = load_performance_data(filters)

        if df.empty:
            return {"total_students": 0, "avg_performance": 0, "pass_rate": 0, "total_schools": 0, "total_assessments": 0}

        # Calculate metrics
        total_students = df["student_id"].nunique()
        avg_performance = df["assessment_percentage"].mean() if "assessment_percentage" in df.columns else 0
        pass_rate = (df["is_pass"].sum() / len(df) * 100) if "is_pass" in df.columns else 0
        total_schools = df["school_name"].nunique() if "school_name" in df.columns else 0
        total_assessments = df["assessment_name"].nunique() if "assessment_name" in df.columns else 0

        return {
            "total_students": total_students,
            "avg_performance": round(avg_performance, 1),
            "pass_rate": round(pass_rate, 1),
            "total_schools": total_schools,
            "total_assessments": total_assessments,
        }

    except Exception as e:
        logger.error(f"Error calculating metrics: {e}")
        return {"total_students": 0, "avg_performance": 0, "pass_rate": 0, "total_schools": 0, "total_assessments": 0}


# Layout components
def create_header():
    """Create dashboard header."""
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H1("🎓 Student Performance Dashboard", className="text-primary mb-0"),
                            html.P(
                                "Real-time analytics and insights into student academic performance",
                                className="text-muted mb-3",
                            ),
                            html.Hr(),
                        ]
                    )
                ]
            )
        ],
        fluid=True,
        className="bg-light py-3 mb-4",
    )


def create_filters():
    """Create filter controls."""
    return dbc.Card(
        [
            dbc.CardHeader([html.H5("📊 Filters & Controls", className="mb-0")]),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Label("Division:", className="fw-bold"),
                                    dcc.Dropdown(
                                        id="division-filter",
                                        options=[
                                            {"label": "All Divisions", "value": "all"},
                                            {"label": "Dhaka", "value": "Dhaka"},
                                            {"label": "Chittagong", "value": "Chittagong"},
                                            {"label": "Rajshahi", "value": "Rajshahi"},
                                            {"label": "Khulna", "value": "Khulna"},
                                            {"label": "Barisal", "value": "Barisal"},
                                            {"label": "Sylhet", "value": "Sylhet"},
                                            {"label": "Rangpur", "value": "Rangpur"},
                                            {"label": "Mymensingh", "value": "Mymensingh"},
                                        ],
                                        value="all",
                                        className="mb-3",
                                    ),
                                ],
                                md=3,
                            ),
                            dbc.Col(
                                [
                                    html.Label("Grade:", className="fw-bold"),
                                    dcc.Dropdown(
                                        id="grade-filter",
                                        options=[
                                            {"label": "All Grades", "value": "all"},
                                            {"label": "Grade 1", "value": "1"},
                                            {"label": "Grade 2", "value": "2"},
                                            {"label": "Grade 3", "value": "3"},
                                            {"label": "Grade 4", "value": "4"},
                                            {"label": "Grade 5", "value": "5"},
                                            {"label": "Grade 6", "value": "6"},
                                            {"label": "Grade 7", "value": "7"},
                                            {"label": "Grade 8", "value": "8"},
                                            {"label": "Grade 9", "value": "9"},
                                            {"label": "Grade 10", "value": "10"},
                                        ],
                                        value="all",
                                        className="mb-3",
                                    ),
                                ],
                                md=3,
                            ),
                            dbc.Col(
                                [
                                    html.Label("Academic Year:", className="fw-bold"),
                                    dcc.Dropdown(
                                        id="year-filter",
                                        options=[
                                            {"label": "2024-2025", "value": "2024-2025"},
                                            {"label": "2023-2024", "value": "2023-2024"},
                                            {"label": "2022-2023", "value": "2022-2023"},
                                        ],
                                        value="2024-2025",
                                        className="mb-3",
                                    ),
                                ],
                                md=3,
                            ),
                            dbc.Col(
                                [
                                    html.Label("School Type:", className="fw-bold"),
                                    dcc.Dropdown(
                                        id="school-type-filter",
                                        options=[
                                            {"label": "All Types", "value": "all"},
                                            {"label": "Government", "value": "government"},
                                            {"label": "Private", "value": "private"},
                                            {"label": "Non-Government", "value": "non_government"},
                                        ],
                                        value="all",
                                        className="mb-3",
                                    ),
                                ],
                                md=3,
                            ),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Button(
                                        "🔄 Refresh Data", id="refresh-btn", color="primary", size="sm", className="me-2"
                                    ),
                                    dbc.Button("📊 Export Data", id="export-btn", color="success", size="sm", className="me-2"),
                                    dbc.Switch(
                                        id="auto-refresh-switch",
                                        label="Auto Refresh (30s)",
                                        value=False,
                                        className="d-inline-block",
                                    ),
                                ]
                            )
                        ]
                    ),
                ]
            ),
        ],
        className="mb-4",
    )


def create_metrics_cards():
    """Create key metrics cards."""
    return dbc.Row(
        [
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H4("👥", className="text-primary mb-2"),
                                    html.H3(id="total-students-metric", children="0", className="mb-1"),
                                    html.P("Total Students", className="text-muted mb-0"),
                                    html.Small(id="students-change", className="text-success"),
                                ]
                            )
                        ],
                        className="h-100 border-start border-primary border-4",
                    )
                ],
                md=2,
            ),
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H4("📈", className="text-success mb-2"),
                                    html.H3(id="avg-performance-metric", children="0%", className="mb-1"),
                                    html.P("Average Performance", className="text-muted mb-0"),
                                    html.Small(id="performance-change", className="text-success"),
                                ]
                            )
                        ],
                        className="h-100 border-start border-success border-4",
                    )
                ],
                md=2,
            ),
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H4("✅", className="text-info mb-2"),
                                    html.H3(id="pass-rate-metric", children="0%", className="mb-1"),
                                    html.P("Pass Rate", className="text-muted mb-0"),
                                    html.Small(id="pass-rate-change", className="text-info"),
                                ]
                            )
                        ],
                        className="h-100 border-start border-info border-4",
                    )
                ],
                md=2,
            ),
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H4("🏫", className="text-warning mb-2"),
                                    html.H3(id="total-schools-metric", children="0", className="mb-1"),
                                    html.P("Schools", className="text-muted mb-0"),
                                    html.Small(id="schools-change", className="text-warning"),
                                ]
                            )
                        ],
                        className="h-100 border-start border-warning border-4",
                    )
                ],
                md=2,
            ),
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H4("📝", className="text-danger mb-2"),
                                    html.H3(id="total-assessments-metric", children="0", className="mb-1"),
                                    html.P("Assessments", className="text-muted mb-0"),
                                    html.Small(id="assessments-change", className="text-danger"),
                                ]
                            )
                        ],
                        className="h-100 border-start border-danger border-4",
                    )
                ],
                md=2,
            ),
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H4("⏰", className="text-secondary mb-2"),
                                    html.H3(id="last-updated", children="--:--", className="mb-1"),
                                    html.P("Last Updated", className="text-muted mb-0"),
                                    dbc.Spinner(size="sm", color="primary", id="loading-spinner"),
                                ]
                            )
                        ],
                        className="h-100 border-start border-secondary border-4",
                    )
                ],
                md=2,
            ),
        ],
        className="mb-4",
    )


def create_charts_section():
    """Create charts section."""
    return dbc.Container(
        [
            # Performance Trends
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader([html.H5("📈 Performance Trends Over Time", className="mb-0")]),
                                    dbc.CardBody([dcc.Graph(id="performance-trends-chart", style={"height": "400px"})]),
                                ]
                            )
                        ],
                        md=8,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader([html.H5("🎯 Grade Distribution", className="mb-0")]),
                                    dbc.CardBody([dcc.Graph(id="grade-distribution-chart", style={"height": "400px"})]),
                                ]
                            )
                        ],
                        md=4,
                    ),
                ],
                className="mb-4",
            ),
            # Regional and Subject Performance
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader([html.H5("🌍 Performance by Division", className="mb-0")]),
                                    dbc.CardBody([dcc.Graph(id="regional-performance-chart", style={"height": "400px"})]),
                                ]
                            )
                        ],
                        md=6,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader([html.H5("📚 Subject-wise Performance", className="mb-0")]),
                                    dbc.CardBody([dcc.Graph(id="subject-performance-chart", style={"height": "400px"})]),
                                ]
                            )
                        ],
                        md=6,
                    ),
                ],
                className="mb-4",
            ),
            # Gender and School Type Analysis
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader([html.H5("👫 Gender Performance Gap", className="mb-0")]),
                                    dbc.CardBody([dcc.Graph(id="gender-performance-chart", style={"height": "350px"})]),
                                ]
                            )
                        ],
                        md=6,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader([html.H5("🏫 School Type Comparison", className="mb-0")]),
                                    dbc.CardBody([dcc.Graph(id="school-type-chart", style={"height": "350px"})]),
                                ]
                            )
                        ],
                        md=6,
                    ),
                ],
                className="mb-4",
            ),
        ],
        fluid=True,
    )


def create_data_table():
    """Create detailed data table."""
    return dbc.Card(
        [
            dbc.CardHeader([html.H5("📋 Detailed Performance Data", className="mb-0")]),
            dbc.CardBody(
                [
                    dash_table.DataTable(
                        id="performance-table",
                        columns=[
                            {"name": "Student", "id": "student_name", "type": "text"},
                            {"name": "School", "id": "school_name", "type": "text"},
                            {"name": "Grade", "id": "current_class", "type": "text"},
                            {"name": "Division", "id": "division", "type": "text"},
                            {"name": "Subject", "id": "subject_name", "type": "text"},
                            {"name": "Assessment", "id": "assessment_name", "type": "text"},
                            {"name": "Marks", "id": "marks_obtained", "type": "numeric", "format": {"specifier": ".1f"}},
                            {"name": "Total", "id": "total_marks", "type": "numeric"},
                            {
                                "name": "Percentage",
                                "id": "assessment_percentage",
                                "type": "numeric",
                                "format": {"specifier": ".1f"},
                            },
                            {"name": "Grade", "id": "letter_grade", "type": "text"},
                            {"name": "Status", "id": "is_pass", "type": "text"},
                        ],
                        data=[],
                        page_size=20,
                        sort_action="native",
                        filter_action="native",
                        style_cell={"textAlign": "left", "padding": "10px"},
                        style_header={"backgroundColor": "rgb(230, 230, 230)", "fontWeight": "bold"},
                        style_data_conditional=[
                            {
                                "if": {"filter_query": "{is_pass} = True"},
                                "backgroundColor": "#d4edda",
                                "color": "black",
                            },
                            {
                                "if": {"filter_query": "{is_pass} = False"},
                                "backgroundColor": "#f8d7da",
                                "color": "black",
                            },
                        ],
                    )
                ]
            ),
        ],
        className="mb-4",
    )


# Main layout
app.layout = dbc.Container(
    [
        create_header(),
        create_filters(),
        create_metrics_cards(),
        create_charts_section(),
        create_data_table(),
        # Auto-refresh interval
        dcc.Interval(id="interval-component", interval=30 * 1000, n_intervals=0, disabled=True),  # 30 seconds
        # Store for data
        dcc.Store(id="performance-data-store"),
        dcc.Store(id="filters-store"),
    ],
    fluid=True,
)


# Callbacks
@app.callback(
    [Output("performance-data-store", "data"), Output("last-updated", "children")],
    [
        Input("interval-component", "n_intervals"),
        Input("refresh-btn", "n_clicks"),
        Input("division-filter", "value"),
        Input("grade-filter", "value"),
        Input("year-filter", "value"),
        Input("school-type-filter", "value"),
    ],
)
def update_data_store(n_intervals, refresh_clicks, division, grade, year, school_type):
    """Update the data store with fresh data."""
    filters = {"division": division, "grade": grade, "academic_year": year, "school_type": school_type}

    df = load_performance_data(filters)
    current_time = datetime.now().strftime("%H:%M:%S")

    return df.to_dict("records"), current_time


@app.callback(Output("interval-component", "disabled"), Input("auto-refresh-switch", "value"))
def toggle_auto_refresh(auto_refresh):
    """Toggle auto-refresh based on switch."""
    return not auto_refresh


@app.callback(
    [
        Output("total-students-metric", "children"),
        Output("avg-performance-metric", "children"),
        Output("pass-rate-metric", "children"),
        Output("total-schools-metric", "children"),
        Output("total-assessments-metric", "children"),
    ],
    Input("performance-data-store", "data"),
)
def update_metrics(data):
    """Update key metrics cards."""
    if not data:
        return "0", "0%", "0%", "0", "0"

    df = pd.DataFrame(data)

    total_students = df["student_id"].nunique() if "student_id" in df.columns else 0
    avg_performance = df["assessment_percentage"].mean() if "assessment_percentage" in df.columns else 0
    pass_rate = (df["is_pass"].sum() / len(df) * 100) if "is_pass" in df.columns and len(df) > 0 else 0
    total_schools = df["school_name"].nunique() if "school_name" in df.columns else 0
    total_assessments = df["assessment_name"].nunique() if "assessment_name" in df.columns else 0

    return (
        f"{total_students:,}",
        f"{avg_performance:.1f}%",
        f"{pass_rate:.1f}%",
        f"{total_schools:,}",
        f"{total_assessments:,}",
    )


@app.callback(Output("performance-trends-chart", "figure"), Input("performance-data-store", "data"))
def update_performance_trends(data):
    """Update performance trends chart."""
    if not data:
        return px.line(title="No data available")

    df = pd.DataFrame(data)

    if "assessment_date" not in df.columns or df.empty:
        return px.line(title="No assessment data available")

    # Convert assessment_date to datetime
    df["assessment_date"] = pd.to_datetime(df["assessment_date"])

    # Group by month and calculate average performance
    monthly_performance = (
        df.groupby(df["assessment_date"].dt.to_period("M"))
        .agg({"assessment_percentage": "mean", "student_id": "nunique"})
        .reset_index()
    )

    monthly_performance["month"] = monthly_performance["assessment_date"].astype(str)

    fig = px.line(
        monthly_performance,
        x="month",
        y="assessment_percentage",
        title="Average Performance Trends Over Time",
        labels={"assessment_percentage": "Average Percentage", "month": "Month"},
        markers=True,
    )

    fig.update_layout(xaxis_title="Month", yaxis_title="Average Performance (%)", hovermode="x unified")

    return fig


@app.callback(Output("grade-distribution-chart", "figure"), Input("performance-data-store", "data"))
def update_grade_distribution(data):
    """Update grade distribution chart."""
    if not data:
        return px.pie(title="No data available")

    df = pd.DataFrame(data)

    if "letter_grade" not in df.columns or df.empty:
        return px.pie(title="No grade data available")

    grade_counts = df["letter_grade"].value_counts().reset_index()
    grade_counts.columns = ["Grade", "Count"]

    fig = px.pie(
        grade_counts,
        values="Count",
        names="Grade",
        title="Grade Distribution",
        color_discrete_sequence=px.colors.qualitative.Set3,
    )

    return fig


@app.callback(Output("regional-performance-chart", "figure"), Input("performance-data-store", "data"))
def update_regional_performance(data):
    """Update regional performance chart."""
    if not data:
        return px.bar(title="No data available")

    df = pd.DataFrame(data)

    if "division" not in df.columns or df.empty:
        return px.bar(title="No regional data available")

    regional_performance = df.groupby("division").agg({"assessment_percentage": "mean", "student_id": "nunique"}).reset_index()

    fig = px.bar(
        regional_performance,
        x="division",
        y="assessment_percentage",
        title="Average Performance by Division",
        labels={"assessment_percentage": "Average Performance (%)", "division": "Division"},
        color="assessment_percentage",
        color_continuous_scale="Viridis",
    )

    fig.update_layout(xaxis_title="Division", yaxis_title="Average Performance (%)")

    return fig


@app.callback(Output("subject-performance-chart", "figure"), Input("performance-data-store", "data"))
def update_subject_performance(data):
    """Update subject performance chart."""
    if not data:
        return px.bar(title="No data available")

    df = pd.DataFrame(data)

    if "subject_name" not in df.columns or df.empty:
        return px.bar(title="No subject data available")

    subject_performance = (
        df.groupby("subject_name").agg({"assessment_percentage": "mean", "student_id": "nunique"}).reset_index()
    )

    fig = px.bar(
        subject_performance,
        x="subject_name",
        y="assessment_percentage",
        title="Average Performance by Subject",
        labels={"assessment_percentage": "Average Performance (%)", "subject_name": "Subject"},
        color="assessment_percentage",
        color_continuous_scale="Blues",
    )

    fig.update_layout(xaxis_title="Subject", yaxis_title="Average Performance (%)", xaxis={"tickangle": 45})

    return fig


@app.callback(Output("gender-performance-chart", "figure"), Input("performance-data-store", "data"))
def update_gender_performance(data):
    """Update gender performance chart."""
    if not data:
        return px.box(title="No data available")

    df = pd.DataFrame(data)

    if "gender" not in df.columns or df.empty:
        return px.box(title="No gender data available")

    fig = px.box(
        df,
        x="gender",
        y="assessment_percentage",
        title="Performance Distribution by Gender",
        labels={"assessment_percentage": "Performance (%)", "gender": "Gender"},
        color="gender",
    )

    return fig


@app.callback(Output("school-type-chart", "figure"), Input("performance-data-store", "data"))
def update_school_type_chart(data):
    """Update school type performance chart."""
    if not data:
        return px.violin(title="No data available")

    df = pd.DataFrame(data)

    if "school_category" not in df.columns or df.empty:
        return px.violin(title="No school type data available")

    fig = px.violin(
        df,
        x="school_category",
        y="assessment_percentage",
        title="Performance Distribution by School Type",
        labels={"assessment_percentage": "Performance (%)", "school_category": "School Type"},
        color="school_category",
        box=True,
    )

    return fig


@app.callback(Output("performance-table", "data"), Input("performance-data-store", "data"))
def update_performance_table(data):
    """Update performance data table."""
    if not data:
        return []

    df = pd.DataFrame(data)

    # Select relevant columns for the table
    table_columns = [
        "student_name",
        "school_name",
        "current_class",
        "division",
        "subject_name",
        "assessment_name",
        "marks_obtained",
        "total_marks",
        "assessment_percentage",
        "letter_grade",
        "is_pass",
    ]

    # Filter columns that exist in the dataframe
    available_columns = [col for col in table_columns if col in df.columns]

    if available_columns:
        table_df = df[available_columns].copy()

        # Format the data
        if "is_pass" in table_df.columns:
            table_df["is_pass"] = table_df["is_pass"].map({True: "Pass", False: "Fail"})

        return table_df.to_dict("records")

    return []


if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050)
