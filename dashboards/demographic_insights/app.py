"""
Demographic Insights Dashboard
----------------------------
Interactive dashboard for analyzing student demographics and their academic performance.
"""

import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Page configuration
st.set_page_config(page_title="Demographic Insights Dashboard", page_icon="👥", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for better styling
st.markdown(
    """
    <style>
    .main .block-container {
        padding: 2rem 3rem;
    }
    .stDataFrame {
        width: 100%;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 0.125rem 0.25rem rgba(0,0,0,0.075);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 2.5rem;
        padding: 0 1rem;
        border-radius: 0.5rem 0.5rem 0 0;
    }
    .highlight-metric {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .insight-box {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 0.5rem 0.5rem 0;
    }
    </style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600)  # Cache data for 1 hour
def load_demographic_data():
    """Load demographic and performance data from the database with enhanced metrics."""
    try:
        # Connect to the database
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/student_data_db")
        engine = create_engine(db_url)

        # Query to get comprehensive student demographic and performance data
        query = """
        WITH student_demographics AS (
            SELECT
                s.id as student_id,
                s.student_id as student_code,
                s.first_name || ' ' || s.last_name as student_name,
                s.gender,
                s.date_of_birth,
                s.current_class,
                s.current_section,
                s.status,
                s.is_scholarship_recipient,
                s.is_special_needs,
                s.monthly_family_income,
                EXTRACT(YEAR FROM age(s.date_of_birth)) as age,
                CASE
                    WHEN EXTRACT(YEAR FROM age(s.date_of_birth)) < 6 THEN 'Under 6'
                    WHEN EXTRACT(YEAR FROM age(s.date_of_birth)) BETWEEN 6 AND 8 THEN '6-8'
                    WHEN EXTRACT(YEAR FROM age(s.date_of_birth)) BETWEEN 9 AND 11 THEN '9-11'
                    WHEN EXTRACT(YEAR FROM age(s.date_of_birth)) BETWEEN 12 AND 14 THEN '12-14'
                    WHEN EXTRACT(YEAR FROM age(s.date_of_birth)) BETWEEN 15 AND 17 THEN '15-17'
                    ELSE '18+'
                END as age_group,
                CASE
                    WHEN s.monthly_family_income < 10000 THEN 'Low Income'
                    WHEN s.monthly_family_income BETWEEN 10000 AND 30000 THEN 'Middle Income'
                    WHEN s.monthly_family_income > 30000 THEN 'High Income'
                    ELSE 'Unknown'
                END as income_category,

                -- Geographic information
                d.name as division,
                dist.name as district,
                u.name as upazila,

                -- School information
                sch.name as school_name,
                sch.type as school_type,
                sch.category as school_category,

                -- Enrollment information
                e.academic_year,
                e.section,
                e.roll_number,
                e.enrollment_date,
                e.final_percentage,
                e.final_grade,
                e.final_result,

                -- Performance metrics
                COALESCE(AVG(ar.percentage), 0) as avg_grade,
                COUNT(ar.id) as grades_count,
                COUNT(DISTINCT ar.subject_id) as subjects_count,
                COUNT(CASE WHEN ar.percentage >= 90 THEN 1 END) as a_grades,
                COUNT(CASE WHEN ar.percentage >= 80 AND ar.percentage < 90 THEN 1 END) as b_grades,
                COUNT(CASE WHEN ar.percentage >= 70 AND ar.percentage < 80 THEN 1 END) as c_grades,
                COUNT(CASE WHEN ar.percentage >= 60 AND ar.percentage < 70 THEN 1 END) as d_grades,
                COUNT(CASE WHEN ar.percentage < 60 THEN 1 END) as f_grades,

                -- Attendance metrics
                COALESCE(AVG(CASE WHEN att.status = 'present' THEN 1.0 ELSE 0.0 END) * 100, 0) as attendance_rate,
                COUNT(att.id) as total_attendance_records,

                MAX(ar.created_at) as last_assessment_date

            FROM students s
            LEFT JOIN enrollments e ON s.id = e.student_id AND e.is_active = true
            LEFT JOIN schools sch ON e.school_id = sch.id
            LEFT JOIN divisions d ON s.division_id = d.id
            LEFT JOIN districts dist ON s.district_id = dist.id
            LEFT JOIN upazilas u ON s.upazila_id = u.id
            LEFT JOIN assessment_results ar ON s.id = ar.student_id
            LEFT JOIN attendances att ON s.id = att.student_id
            WHERE s.is_deleted = false
            AND s.status = 'active'
            GROUP BY s.id, s.student_id, s.first_name, s.last_name, s.gender,
                     s.date_of_birth, s.current_class, s.current_section, s.status,
                     s.is_scholarship_recipient, s.is_special_needs, s.monthly_family_income,
                     d.name, dist.name, u.name, sch.name, sch.type, sch.category,
                     e.academic_year, e.section, e.roll_number, e.enrollment_date,
                     e.final_percentage, e.final_grade, e.final_result
        )
        SELECT
            *,
            CASE
                WHEN avg_grade >= 90 THEN 'A (90-100)'
                WHEN avg_grade >= 80 THEN 'B (80-89)'
                WHEN avg_grade >= 70 THEN 'C (70-79)'
                WHEN avg_grade >= 60 THEN 'D (60-69)'
                WHEN avg_grade > 0 THEN 'F (<60)'
                ELSE 'No Grades'
            END as performance_category,
            CASE
                WHEN avg_grade >= 90 THEN 'A'
                WHEN avg_grade >= 80 THEN 'B'
                WHEN avg_grade >= 70 THEN 'C'
                WHEN avg_grade >= 60 THEN 'D'
                WHEN avg_grade > 0 THEN 'F'
                ELSE 'N/A'
            END as performance_letter
        FROM student_demographics
        ORDER BY student_name;
        """

        df = pd.read_sql(query, engine)

        # Convert date columns to datetime
        date_columns = ["date_of_birth", "enrollment_date", "last_assessment_date"]
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        # Calculate additional metrics
        if "date_of_birth" in df.columns:
            df["age"] = (pd.Timestamp.now() - df["date_of_birth"]).dt.days // 365

        # Add year and month columns for time series analysis
        if "enrollment_date" in df.columns:
            df["enrollment_year"] = df["enrollment_date"].dt.year
            df["enrollment_month"] = df["enrollment_date"].dt.month
            df["enrollment_year_month"] = df["enrollment_date"].dt.to_period("M").astype(str)

        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()


def setup_sidebar(df):
    """Set up the sidebar with enhanced filters and options."""
    st.sidebar.title("🔍 Filters & Options")

    # Date range filter
    with st.sidebar.expander("📅 Date Range", expanded=False):
        if "enrollment_date" in df.columns and not df["enrollment_date"].isna().all():
            min_date = df["enrollment_date"].min().to_pydatetime()
            max_date = df["enrollment_date"].max().to_pydatetime()
            date_range = st.date_input(
                "Enrollment Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                help="Filter students by their enrollment date range",
            )
            if len(date_range) == 2:
                start_date, end_date = date_range
            else:
                start_date, end_date = min_date, max_date
        else:
            start_date, end_date = None, None

    # Class and grade filters
    with st.sidebar.expander("🏫 Class & Grade", expanded=True):
        # Class multi-select
        if "current_class" in df.columns:
            class_options = sorted(df["current_class"].dropna().unique().tolist())
            selected_classes = st.multiselect(
                "Classes",
                options=class_options,
                default=class_options[: min(5, len(class_options))],
                help="Filter by one or more classes",
            )
        else:
            selected_classes = []

        # Section filter
        if "current_section" in df.columns:
            section_options = ["All"] + sorted(df["current_section"].dropna().unique().tolist())
            selected_section = st.selectbox("Section", section_options, index=0, help="Filter by section")
        else:
            selected_section = "All"

    # Demographic filters
    with st.sidebar.expander("👥 Demographics", expanded=True):
        # Gender filter
        if "gender" in df.columns:
            gender_options = ["All"] + sorted(df["gender"].dropna().unique().tolist())
            selected_gender = st.selectbox("Gender", gender_options, index=0, help="Filter by gender")
        else:
            selected_gender = "All"

        # Age group filter
        if "age_group" in df.columns:
            age_groups = ["All"] + sorted(df["age_group"].dropna().unique().tolist())
            selected_age_group = st.selectbox("Age Group", age_groups, index=0, help="Filter by age group")
        else:
            selected_age_group = "All"

        # Income category filter
        if "income_category" in df.columns:
            income_categories = ["All"] + sorted(df["income_category"].dropna().unique().tolist())
            selected_income = st.selectbox(
                "Income Category", income_categories, index=0, help="Filter by family income category"
            )
        else:
            selected_income = "All"

    # Geographic filters
    with st.sidebar.expander("🌍 Geographic", expanded=False):
        # Division filter
        if "division" in df.columns:
            division_options = ["All"] + sorted(df["division"].dropna().unique().tolist())
            selected_division = st.selectbox("Division", division_options, index=0, help="Filter by administrative division")
        else:
            selected_division = "All"

        # District filter
        if "district" in df.columns:
            if selected_division != "All":
                district_options = ["All"] + sorted(
                    df[df["division"] == selected_division]["district"].dropna().unique().tolist()
                )
            else:
                district_options = ["All"] + sorted(df["district"].dropna().unique().tolist())
            selected_district = st.selectbox("District", district_options, index=0, help="Filter by district")
        else:
            selected_district = "All"

    # School filters
    with st.sidebar.expander("🏫 School", expanded=False):
        # School type filter
        if "school_type" in df.columns:
            school_type_options = ["All"] + sorted(df["school_type"].dropna().unique().tolist())
            selected_school_type = st.selectbox("School Type", school_type_options, index=0, help="Filter by school type")
        else:
            selected_school_type = "All"

        # School category filter
        if "school_category" in df.columns:
            school_category_options = ["All"] + sorted(df["school_category"].dropna().unique().tolist())
            selected_school_category = st.selectbox(
                "School Category", school_category_options, index=0, help="Filter by school category"
            )
        else:
            selected_school_category = "All"

    # Performance filters
    with st.sidebar.expander("📊 Performance", expanded=False):
        # Performance category filter
        if "performance_category" in df.columns:
            performance_options = ["All"] + sorted(df["performance_category"].dropna().unique().tolist())
            selected_performance = st.selectbox(
                "Performance Category", performance_options, index=0, help="Filter by performance category"
            )
        else:
            selected_performance = "All"

        # Scholarship filter
        if "is_scholarship_recipient" in df.columns:
            scholarship_options = ["All", "Yes", "No"]
            selected_scholarship = st.selectbox(
                "Scholarship Recipients", scholarship_options, index=0, help="Filter by scholarship status"
            )
        else:
            selected_scholarship = "All"

        # Special needs filter
        if "is_special_needs" in df.columns:
            special_needs_options = ["All", "Yes", "No"]
            selected_special_needs = st.selectbox(
                "Special Needs", special_needs_options, index=0, help="Filter by special needs status"
            )
        else:
            selected_special_needs = "All"

    # Display options
    with st.sidebar.expander("⚙️ Display Options", expanded=False):
        show_percentages = st.checkbox("Show Percentages in Charts", value=True)
        chart_height = st.slider("Chart Height", min_value=300, max_value=800, value=500, step=50)
        color_scheme = st.selectbox("Color Scheme", ["plotly", "viridis", "plasma", "inferno", "magma", "cividis"], index=0)

    # Export options
    with st.sidebar.expander("📤 Export", expanded=False):
        if st.button("📊 Export Current View as CSV"):
            # This would be implemented to export the filtered data
            st.info("Export functionality would be implemented here")

        if st.button("📈 Generate Report"):
            st.info("Report generation would be implemented here")

    # Return all filter values
    return {
        "date_range": (start_date, end_date) if start_date and end_date else None,
        "classes": selected_classes,
        "section": selected_section,
        "gender": selected_gender,
        "age_group": selected_age_group,
        "income": selected_income,
        "division": selected_division,
        "district": selected_district,
        "school_type": selected_school_type,
        "school_category": selected_school_category,
        "performance": selected_performance,
        "scholarship": selected_scholarship,
        "special_needs": selected_special_needs,
        "show_percentages": show_percentages,
        "chart_height": chart_height,
        "color_scheme": color_scheme,
    }


def apply_filters(df, filters):
    """Apply all selected filters to the dataframe."""
    filtered_df = df.copy()

    # Date range filter
    if filters["date_range"] and "enrollment_date" in filtered_df.columns:
        start_date, end_date = filters["date_range"]
        filtered_df = filtered_df[
            (filtered_df["enrollment_date"].dt.date >= start_date) & (filtered_df["enrollment_date"].dt.date <= end_date)
        ]

    # Class filter
    if filters["classes"] and "current_class" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["current_class"].isin(filters["classes"])]

    # Section filter
    if filters["section"] != "All" and "current_section" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["current_section"] == filters["section"]]

    # Gender filter
    if filters["gender"] != "All" and "gender" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["gender"] == filters["gender"]]

    # Age group filter
    if filters["age_group"] != "All" and "age_group" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["age_group"] == filters["age_group"]]

    # Income filter
    if filters["income"] != "All" and "income_category" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["income_category"] == filters["income"]]

    # Division filter
    if filters["division"] != "All" and "division" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["division"] == filters["division"]]

    # District filter
    if filters["district"] != "All" and "district" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["district"] == filters["district"]]

    # School type filter
    if filters["school_type"] != "All" and "school_type" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["school_type"] == filters["school_type"]]

    # School category filter
    if filters["school_category"] != "All" and "school_category" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["school_category"] == filters["school_category"]]

    # Performance filter
    if filters["performance"] != "All" and "performance_category" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["performance_category"] == filters["performance"]]

    # Scholarship filter
    if filters["scholarship"] != "All" and "is_scholarship_recipient" in filtered_df.columns:
        scholarship_value = filters["scholarship"] == "Yes"
        filtered_df = filtered_df[filtered_df["is_scholarship_recipient"] == scholarship_value]

    # Special needs filter
    if filters["special_needs"] != "All" and "is_special_needs" in filtered_df.columns:
        special_needs_value = filters["special_needs"] == "Yes"
        filtered_df = filtered_df[filtered_df["is_special_needs"] == special_needs_value]

    return filtered_df


def display_key_metrics(df):
    """Display key demographic metrics in an attractive layout."""
    st.markdown("### 📊 Key Demographics Overview")

    # Create columns for metrics
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        total_students = len(df)
        st.markdown(
            f"""
        <div class="highlight-metric">
            <h3 style="margin: 0; font-size: 2rem;">👥</h3>
            <h2 style="margin: 0;">{total_students:,}</h2>
            <p style="margin: 0; opacity: 0.8;">Total Students</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        if "gender" in df.columns:
            gender_dist = df["gender"].value_counts()
            if len(gender_dist) >= 2:
                female_pct = (gender_dist.get("Female", 0) / total_students * 100) if total_students > 0 else 0
                st.markdown(
                    f"""
                <div class="highlight-metric">
                    <h3 style="margin: 0; font-size: 2rem;">♀️</h3>
                    <h2 style="margin: 0;">{female_pct:.1f}%</h2>
                    <p style="margin: 0; opacity: 0.8;">Female Students</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                <div class="highlight-metric">
                    <h3 style="margin: 0; font-size: 2rem;">♀️</h3>
                    <h2 style="margin: 0;">N/A</h2>
                    <p style="margin: 0; opacity: 0.8;">Female Students</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                f"""
            <div class="highlight-metric">
                <h3 style="margin: 0; font-size: 2rem;">♀️</h3>
                <h2 style="margin: 0;">N/A</h2>
                <p style="margin: 0; opacity: 0.8;">Female Students</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

    with col3:
        if "avg_grade" in df.columns:
            avg_performance = df["avg_grade"].mean()
            st.markdown(
                f"""
            <div class="highlight-metric">
                <h3 style="margin: 0; font-size: 2rem;">📈</h3>
                <h2 style="margin: 0;">{avg_performance:.1f}%</h2>
                <p style="margin: 0; opacity: 0.8;">Avg Performance</p>
            </div>
            """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
            <div class="highlight-metric">
                <h3 style="margin: 0; font-size: 2rem;">📈</h3>
                <h2 style="margin: 0;">N/A</h2>
                <p style="margin: 0; opacity: 0.8;">Avg Performance</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

    with col4:
        if "is_scholarship_recipient" in df.columns:
            scholarship_pct = (df["is_scholarship_recipient"].sum() / total_students * 100) if total_students > 0 else 0
            st.markdown(
                f"""
            <div class="highlight-metric">
                <h3 style="margin: 0; font-size: 2rem;">🎓</h3>
                <h2 style="margin: 0;">{scholarship_pct:.1f}%</h2>
                <p style="margin: 0; opacity: 0.8;">Scholarship Recipients</p>
            </div>
            """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
            <div class="highlight-metric">
                <h3 style="margin: 0; font-size: 2rem;">🎓</h3>
                <h2 style="margin: 0;">N/A</h2>
                <p style="margin: 0; opacity: 0.8;">Scholarship Recipients</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

    with col5:
        if "division" in df.columns:
            divisions_count = df["division"].nunique()
            st.markdown(
                f"""
            <div class="highlight-metric">
                <h3 style="margin: 0; font-size: 2rem;">🌍</h3>
                <h2 style="margin: 0;">{divisions_count}</h2>
                <p style="margin: 0; opacity: 0.8;">Divisions</p>
            </div>
            """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
            <div class="highlight-metric">
                <h3 style="margin: 0; font-size: 2rem;">🌍</h3>
                <h2 style="margin: 0;">N/A</h2>
                <p style="margin: 0; opacity: 0.8;">Divisions</p>
            </div>
            """,
                unsafe_allow_html=True,
            )


def create_demographic_charts(df, filters):
    """Create comprehensive demographic analysis charts."""

    # Gender Distribution
    if "gender" in df.columns and not df["gender"].isna().all():
        st.markdown("#### 👫 Gender Distribution")
        col1, col2 = st.columns([2, 1])

        with col1:
            gender_counts = df["gender"].value_counts()
            fig_gender = px.pie(
                values=gender_counts.values,
                names=gender_counts.index,
                title="Student Distribution by Gender",
                color_discrete_sequence=px.colors.qualitative.Set3,
                height=filters["chart_height"] // 2,
            )
            fig_gender.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig_gender, use_container_width=True)

        with col2:
            st.markdown("**Gender Statistics:**")
            for gender, count in gender_counts.items():
                percentage = (count / len(df)) * 100
                st.markdown(f"- **{gender}**: {count:,} ({percentage:.1f}%)")

    # Age Distribution
    if "age_group" in df.columns and not df["age_group"].isna().all():
        st.markdown("#### 🎂 Age Group Distribution")
        age_counts = df["age_group"].value_counts().sort_index()

        fig_age = px.bar(
            x=age_counts.index,
            y=age_counts.values,
            title="Student Distribution by Age Group",
            labels={"x": "Age Group", "y": "Number of Students"},
            color=age_counts.values,
            color_continuous_scale=filters["color_scheme"],
            height=filters["chart_height"] // 2,
        )
        fig_age.update_layout(showlegend=False)
        st.plotly_chart(fig_age, use_container_width=True)

    # Income Distribution
    if "income_category" in df.columns and not df["income_category"].isna().all():
        st.markdown("#### 💰 Family Income Distribution")
        col1, col2 = st.columns(2)

        with col1:
            income_counts = df["income_category"].value_counts()
            fig_income = px.pie(
                values=income_counts.values,
                names=income_counts.index,
                title="Distribution by Family Income Category",
                color_discrete_sequence=px.colors.qualitative.Pastel,
                height=filters["chart_height"] // 2,
            )
            st.plotly_chart(fig_income, use_container_width=True)

        with col2:
            # Income vs Performance analysis
            if "avg_grade" in df.columns:
                income_performance = df.groupby("income_category")["avg_grade"].mean().reset_index()
                fig_income_perf = px.bar(
                    income_performance,
                    x="income_category",
                    y="avg_grade",
                    title="Average Performance by Income Category",
                    labels={"income_category": "Income Category", "avg_grade": "Average Grade (%)"},
                    color="avg_grade",
                    color_continuous_scale="Viridis",
                    height=filters["chart_height"] // 2,
                )
                st.plotly_chart(fig_income_perf, use_container_width=True)


def create_geographic_analysis(df, filters):
    """Create geographic distribution analysis."""
    st.markdown("### 🌍 Geographic Distribution Analysis")

    # Division-wise distribution
    if "division" in df.columns and not df["division"].isna().all():
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 📍 Distribution by Division")
            division_counts = df["division"].value_counts()

            fig_division = px.bar(
                x=division_counts.values,
                y=division_counts.index,
                orientation="h",
                title="Student Count by Division",
                labels={"x": "Number of Students", "y": "Division"},
                color=division_counts.values,
                color_continuous_scale=filters["color_scheme"],
                height=filters["chart_height"],
            )
            st.plotly_chart(fig_division, use_container_width=True)

        with col2:
            # Performance by division
            if "avg_grade" in df.columns:
                st.markdown("#### 📊 Performance by Division")
                division_performance = df.groupby("division").agg({"avg_grade": "mean", "student_id": "count"}).reset_index()
                division_performance.columns = ["Division", "Avg_Performance", "Student_Count"]

                fig_div_perf = px.scatter(
                    division_performance,
                    x="Student_Count",
                    y="Avg_Performance",
                    size="Student_Count",
                    color="Avg_Performance",
                    hover_name="Division",
                    title="Division Performance vs Student Count",
                    labels={"Student_Count": "Number of Students", "Avg_Performance": "Average Performance (%)"},
                    color_continuous_scale="RdYlGn",
                    height=filters["chart_height"],
                )
                st.plotly_chart(fig_div_perf, use_container_width=True)


def create_performance_analysis(df, filters):
    """Create performance-related demographic analysis."""
    st.markdown("### 📈 Performance Analysis by Demographics")

    if "avg_grade" in df.columns and "gender" in df.columns:
        # Gender vs Performance
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 👫 Performance by Gender")
            fig_gender_perf = px.box(
                df,
                x="gender",
                y="avg_grade",
                title="Performance Distribution by Gender",
                labels={"gender": "Gender", "avg_grade": "Average Grade (%)"},
                color="gender",
                height=filters["chart_height"] // 1.5,
            )
            st.plotly_chart(fig_gender_perf, use_container_width=True)

        with col2:
            # Age group vs Performance
            if "age_group" in df.columns:
                st.markdown("#### 🎂 Performance by Age Group")
                fig_age_perf = px.violin(
                    df,
                    x="age_group",
                    y="avg_grade",
                    title="Performance Distribution by Age Group",
                    labels={"age_group": "Age Group", "avg_grade": "Average Grade (%)"},
                    color="age_group",
                    height=filters["chart_height"] // 1.5,
                )
                st.plotly_chart(fig_age_perf, use_container_width=True)

    # Performance categories distribution
    if "performance_category" in df.columns:
        st.markdown("#### 🏆 Performance Categories Distribution")
        perf_counts = df["performance_category"].value_counts()

        fig_perf_cat = px.bar(
            x=perf_counts.index,
            y=perf_counts.values,
            title="Distribution of Performance Categories",
            labels={"x": "Performance Category", "y": "Number of Students"},
            color=perf_counts.values,
            color_continuous_scale="RdYlGn",
            height=filters["chart_height"] // 2,
        )
        st.plotly_chart(fig_perf_cat, use_container_width=True)


def create_correlation_analysis(df, filters):
    """Create correlation analysis between different demographic factors."""
    st.markdown("### 🔗 Correlation Analysis")

    # Create correlation matrix for numerical columns
    numerical_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if len(numerical_cols) > 1:
        correlation_matrix = df[numerical_cols].corr()

        fig_corr = px.imshow(
            correlation_matrix,
            title="Correlation Matrix of Numerical Variables",
            color_continuous_scale="RdBu",
            aspect="auto",
            height=filters["chart_height"],
        )
        fig_corr.update_layout(xaxis_title="Variables", yaxis_title="Variables")
        st.plotly_chart(fig_corr, use_container_width=True)

        # Insights from correlation
        st.markdown("#### 💡 Key Insights from Correlation Analysis")

        # Find strongest correlations
        corr_pairs = []
        for i in range(len(correlation_matrix.columns)):
            for j in range(i + 1, len(correlation_matrix.columns)):
                corr_value = correlation_matrix.iloc[i, j]
                if abs(corr_value) > 0.3:  # Only show correlations > 0.3
                    corr_pairs.append(
                        {
                            "var1": correlation_matrix.columns[i],
                            "var2": correlation_matrix.columns[j],
                            "correlation": corr_value,
                        }
                    )

        if corr_pairs:
            corr_df = pd.DataFrame(corr_pairs)
            corr_df = corr_df.sort_values("correlation", key=abs, ascending=False)

            for _, row in corr_df.head(5).iterrows():
                correlation_strength = "Strong" if abs(row["correlation"]) > 0.7 else "Moderate"
                correlation_direction = "positive" if row["correlation"] > 0 else "negative"

                st.markdown(
                    f"""
                <div class="insight-box">
                    <strong>{correlation_strength} {correlation_direction} correlation</strong> between
                    <em>{row['var1']}</em> and <em>{row['var2']}</em>
                    (r = {row['correlation']:.3f})
                </div>
                """,
                    unsafe_allow_html=True,
                )


def create_detailed_data_table(df):
    """Create a detailed data table with search and filter capabilities."""
    st.markdown("### 📋 Detailed Student Data")

    # Select relevant columns for display
    display_columns = [
        "student_name",
        "gender",
        "age",
        "current_class",
        "division",
        "district",
        "school_name",
        "school_type",
        "avg_grade",
        "performance_category",
        "is_scholarship_recipient",
    ]

    # Filter columns that exist in the dataframe
    available_columns = [col for col in display_columns if col in df.columns]

    if available_columns:
        display_df = df[available_columns].copy()

        # Format boolean columns
        bool_columns = ["is_scholarship_recipient", "is_special_needs"]
        for col in bool_columns:
            if col in display_df.columns:
                display_df[col] = display_df[col].map({True: "Yes", False: "No"})

        # Add search functionality
        search_term = st.text_input("🔍 Search students:", placeholder="Enter student name, school, or division...")

        if search_term:
            # Search across text columns
            text_columns = display_df.select_dtypes(include=["object"]).columns
            mask = (
                display_df[text_columns]
                .apply(lambda x: x.astype(str).str.contains(search_term, case=False, na=False))
                .any(axis=1)
            )
            display_df = display_df[mask]

        # Display the table
        st.dataframe(display_df, use_container_width=True, height=400)

        # Summary statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Displayed Records", len(display_df))
        with col2:
            if "avg_grade" in display_df.columns:
                avg_grade = display_df["avg_grade"].mean()
                st.metric("Average Grade", f"{avg_grade:.1f}%")
        with col3:
            if "gender" in display_df.columns:
                female_pct = (display_df["gender"] == "Female").mean() * 100
                st.metric("Female %", f"{female_pct:.1f}%")


def main():
    """Main application function."""
    # Header
    st.title("👥 Demographic Insights Dashboard")
    st.markdown("**Comprehensive analysis of student demographics and their impact on academic performance**")
    st.markdown("---")

    # Load data
    with st.spinner("Loading demographic data..."):
        df = load_demographic_data()

    if df.empty:
        st.error("No data available. Please check your database connection and ensure data exists.")
        return

    # Setup sidebar filters
    filters = setup_sidebar(df)

    # Apply filters
    filtered_df = apply_filters(df, filters)

    if filtered_df.empty:
        st.warning("No data matches the selected filters. Please adjust your filter criteria.")
        return

    # Display key metrics
    display_key_metrics(filtered_df)

    # Create tabs for different analyses
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📊 Demographics", "🌍 Geographic", "📈 Performance", "🔗 Correlations", "📋 Data Table"]
    )

    with tab1:
        create_demographic_charts(filtered_df, filters)

    with tab2:
        create_geographic_analysis(filtered_df, filters)

    with tab3:
        create_performance_analysis(filtered_df, filters)

    with tab4:
        create_correlation_analysis(filtered_df, filters)

    with tab5:
        create_detailed_data_table(filtered_df)

    # Footer
    st.markdown("---")
    st.markdown(f"**Data last updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown(f"**Total records analyzed:** {len(filtered_df):,} out of {len(df):,}")


if __name__ == "__main__":
    main()
