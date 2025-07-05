"""Enrollment Trends Dashboard - Streamlit Application
Comprehensive time-series analysis of student enrollment patterns across Bangladesh
"""

import logging
import os
import sys
import warnings
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

warnings.filterwarnings("ignore")

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import services
from dashboards.enrollment_trends.data_service import EnrollmentDataService
from dashboards.enrollment_trends.visualization_service import EnrollmentVisualizationService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(page_title="📈 Enrollment Trends Dashboard", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

# Custom CSS
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        padding: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
    }

    .metric-label {
        font-size: 0.9rem;
        color: #666;
        margin-top: 0.5rem;
    }

    .filter-section {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }

    .insight-box {
        background: #e3f2fd;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2196f3;
        margin: 1rem 0;
    }

    .warning-box {
        background: #fff3e0;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #ff9800;
        margin: 1rem 0;
    }

    .success-box {
        background: #e8f5e8;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #4caf50;
        margin: 1rem 0;
    }
</style>
""",
    unsafe_allow_html=True,
)


class EnrollmentTrendsDashboard:
    """Main dashboard class for enrollment trends analysis."""

    def __init__(self):
        self.data_service = EnrollmentDataService()
        self.viz_service = EnrollmentVisualizationService()
        self.initialize_session_state()

    def initialize_session_state(self):
        """Initialize session state variables."""
        if "last_refresh" not in st.session_state:
            st.session_state.last_refresh = datetime.now()
        if "auto_refresh" not in st.session_state:
            st.session_state.auto_refresh = False
        if "selected_filters" not in st.session_state:
            st.session_state.selected_filters = {}

    def render_header(self):
        """Render the dashboard header."""
        st.markdown('<h1 class="main-header">📈 Bangladesh Education Enrollment Trends Dashboard</h1>', unsafe_allow_html=True)

        # Dashboard description
        st.markdown(
            """
        <div class="insight-box">
            <h4>🎯 Dashboard Overview</h4>
            <p>This comprehensive dashboard provides time-series analysis of student enrollment patterns across Bangladesh,
            helping education policymakers and administrators understand enrollment trends, seasonal patterns, and
            regional variations to make data-driven decisions.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    def render_sidebar_filters(self) -> Dict[str, Any]:
        """Render sidebar filters and return selected values."""
        st.sidebar.markdown("## 🔍 Filters & Controls")

        # Get filter options
        filter_options = self.data_service.get_filter_options()

        filters = {}

        # Time range selection
        st.sidebar.markdown("### 📅 Time Range")
        date_range = st.sidebar.date_input(
            "Select Date Range",
            value=(date(2020, 1, 1), date.today()),
            min_value=date(2015, 1, 1),
            max_value=date.today(),
            key="date_range",
        )

        if len(date_range) == 2:
            filters["start_date"] = date_range[0]
            filters["end_date"] = date_range[1]

        # Academic year filter
        st.sidebar.markdown("### 🎓 Academic Period")
        academic_years = filter_options.get("academic_years", [])
        if academic_years:
            selected_years = st.sidebar.multiselect(
                "Academic Years",
                options=academic_years,
                default=academic_years[:3] if len(academic_years) >= 3 else academic_years,
                key="academic_years",
            )
            filters["academic_years"] = selected_years

        # Geographic filters
        st.sidebar.markdown("### 🗺️ Geographic Filters")

        divisions = filter_options.get("divisions", [])
        if divisions:
            selected_divisions = st.sidebar.multiselect(
                "Divisions", options=["All"] + divisions, default=["All"], key="divisions"
            )
            if "All" not in selected_divisions:
                filters["divisions"] = selected_divisions

        # School type filter
        st.sidebar.markdown("### 🏫 School Characteristics")
        school_types = filter_options.get("school_types", [])
        if school_types:
            selected_school_types = st.sidebar.multiselect(
                "School Types", options=["All"] + school_types, default=["All"], key="school_types"
            )
            if "All" not in selected_school_types:
                filters["school_types"] = selected_school_types

        # Grade level filter
        grade_levels = filter_options.get("grade_levels", [])
        if grade_levels:
            selected_grades = st.sidebar.multiselect(
                "Grade Levels", options=["All"] + grade_levels, default=["All"], key="grade_levels"
            )
            if "All" not in selected_grades:
                filters["grade_levels"] = selected_grades

        # Gender filter
        st.sidebar.markdown("### 👥 Demographics")
        gender_filter = st.sidebar.selectbox("Gender", options=["All", "Male", "Female"], index=0, key="gender")
        if gender_filter != "All":
            filters["gender"] = gender_filter

        # Analysis options
        st.sidebar.markdown("### ⚙️ Analysis Options")

        analysis_type = st.sidebar.selectbox(
            "Analysis Type",
            options=["Trend Analysis", "Seasonal Analysis", "Comparative Analysis", "Forecasting"],
            index=0,
            key="analysis_type",
        )
        filters["analysis_type"] = analysis_type

        aggregation_level = st.sidebar.selectbox(
            "Time Aggregation", options=["Monthly", "Quarterly", "Yearly"], index=0, key="aggregation"
        )
        filters["aggregation_level"] = aggregation_level

        # Refresh controls
        st.sidebar.markdown("### 🔄 Data Refresh")

        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("🔄 Refresh Data", key="refresh_btn"):
                st.session_state.last_refresh = datetime.now()
                st.experimental_rerun()

        with col2:
            auto_refresh = st.checkbox("Auto Refresh", value=st.session_state.auto_refresh)
            st.session_state.auto_refresh = auto_refresh

        # Last refresh time
        st.sidebar.markdown(f"**Last Updated:** {st.session_state.last_refresh.strftime('%H:%M:%S')}")

        return filters

    def render_key_metrics(self, filters: Dict[str, Any]):
        """Render key enrollment metrics."""
        st.markdown("## 📊 Key Enrollment Metrics")

        # Get metrics data
        metrics = self.data_service.get_key_metrics(filters)

        # Create metrics columns
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.markdown(
                f"""
            <div class="metric-card">
                <div class="metric-value">{metrics.get('total_enrollments', 0):,}</div>
                <div class="metric-label">Total Enrollments</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col2:
            growth_rate = metrics.get("enrollment_growth_rate", 0)
            growth_color = "green" if growth_rate > 0 else "red" if growth_rate < 0 else "gray"
            st.markdown(
                f"""
            <div class="metric-card">
                <div class="metric-value" style="color: {growth_color};">{growth_rate:+.1f}%</div>
                <div class="metric-label">Growth Rate (YoY)</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col3:
            st.markdown(
                f"""
            <div class="metric-card">
                <div class="metric-value">{metrics.get('active_schools', 0):,}</div>
                <div class="metric-label">Active Schools</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col4:
            retention_rate = metrics.get("retention_rate", 0)
            st.markdown(
                f"""
            <div class="metric-card">
                <div class="metric-value">{retention_rate:.1f}%</div>
                <div class="metric-label">Retention Rate</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col5:
            dropout_rate = metrics.get("dropout_rate", 0)
            dropout_color = "red" if dropout_rate > 10 else "orange" if dropout_rate > 5 else "green"
            st.markdown(
                f"""
            <div class="metric-card">
                <div class="metric-value" style="color: {dropout_color};">{dropout_rate:.1f}%</div>
                <div class="metric-label">Dropout Rate</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    def render_enrollment_trends(self, filters: Dict[str, Any]):
        """Render enrollment trends analysis."""
        st.markdown("## 📈 Enrollment Trends Analysis")

        # Get trends data
        trends_data = self.data_service.get_enrollment_trends(filters)

        if not trends_data:
            st.warning("No enrollment trends data available for the selected filters.")
            return

        # Create tabs for different trend analyses
        tab1, tab2, tab3, tab4 = st.tabs(
            ["📊 Overall Trends", "🔄 Seasonal Patterns", "📍 Regional Trends", "🎯 Demographic Trends"]
        )

        with tab1:
            self.render_overall_trends(trends_data, filters)

        with tab2:
            self.render_seasonal_patterns(trends_data, filters)

        with tab3:
            self.render_regional_trends(filters)

        with tab4:
            self.render_demographic_trends(filters)

    def render_overall_trends(self, trends_data: List[Dict], filters: Dict[str, Any]):
        """Render overall enrollment trends."""
        st.markdown("### 📊 Overall Enrollment Trends")

        # Create main trends chart
        fig = self.viz_service.create_enrollment_trends_chart(trends_data, filters.get("aggregation_level", "Monthly"))
        st.plotly_chart(fig, use_container_width=True)

        # Trend analysis insights
        if trends_data:
            df = pd.DataFrame(trends_data)

            # Calculate trend statistics
            if len(df) > 1:
                latest_enrollment = df.iloc[-1]["enrollment_count"]
                previous_enrollment = df.iloc[-2]["enrollment_count"]
                change = ((latest_enrollment - previous_enrollment) / previous_enrollment) * 100

                # Growth rate analysis
                if len(df) >= 12:  # At least 12 periods for meaningful analysis
                    recent_avg = df.tail(6)["enrollment_count"].mean()
                    earlier_avg = df.head(6)["enrollment_count"].mean()
                    overall_growth = ((recent_avg - earlier_avg) / earlier_avg) * 100

                    if overall_growth > 5:
                        st.markdown(
                            f"""
                        <div class="success-box">
                            <h4>📈 Positive Growth Trend</h4>
                            <p>Enrollment shows a strong positive trend with {overall_growth:.1f}% growth over the analysis period.
                            Recent period change: {change:+.1f}%</p>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )
                    elif overall_growth < -5:
                        st.markdown(
                            f"""
                        <div class="warning-box">
                            <h4>📉 Declining Trend</h4>
                            <p>Enrollment shows a declining trend with {overall_growth:.1f}% change over the analysis period.
                            Recent period change: {change:+.1f}%</p>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f"""
                        <div class="insight-box">
                            <h4>📊 Stable Trend</h4>
                            <p>Enrollment remains relatively stable with {overall_growth:.1f}% change over the analysis period.
                            Recent period change: {change:+.1f}%</p>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )

        # Additional trend metrics
        col1, col2 = st.columns(2)

        with col1:
            # Volatility analysis
            volatility_data = self.data_service.get_enrollment_volatility(filters)
            fig_volatility = self.viz_service.create_volatility_chart(volatility_data)
            st.plotly_chart(fig_volatility, use_container_width=True)

        with col2:
            # Growth rate distribution
            growth_data = self.data_service.get_growth_rate_distribution(filters)
            fig_growth = self.viz_service.create_growth_distribution_chart(growth_data)
            st.plotly_chart(fig_growth, use_container_width=True)

    def render_seasonal_patterns(self, trends_data: List[Dict], filters: Dict[str, Any]):
        """Render seasonal enrollment patterns."""
        st.markdown("### 🔄 Seasonal Enrollment Patterns")

        # Get seasonal data
        seasonal_data = self.data_service.get_seasonal_patterns(filters)

        if not seasonal_data:
            st.info("No seasonal pattern data available for the selected filters.")
            return

        col1, col2 = st.columns(2)

        with col1:
            # Monthly seasonality
            fig_monthly = self.viz_service.create_monthly_seasonality_chart(seasonal_data)
            st.plotly_chart(fig_monthly, use_container_width=True)

        with col2:
            # Quarterly patterns
            fig_quarterly = self.viz_service.create_quarterly_patterns_chart(seasonal_data)
            st.plotly_chart(fig_quarterly, use_container_width=True)

        # Seasonal insights
        peak_months = self.data_service.get_peak_enrollment_months(seasonal_data)
        if peak_months:
            st.markdown(
                f"""
            <div class="insight-box">
                <h4>📅 Seasonal Insights</h4>
                <p><strong>Peak Enrollment Months:</strong> {', '.join(peak_months['high_months'])}</p>
                <p><strong>Low Enrollment Months:</strong> {', '.join(peak_months['low_months'])}</p>
                <p><strong>Seasonal Variation:</strong> {peak_months['variation']:.1f}% difference between peak and low periods</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # Academic calendar alignment
        fig_calendar = self.viz_service.create_academic_calendar_chart(seasonal_data)
        st.plotly_chart(fig_calendar, use_container_width=True)

    def render_regional_trends(self, filters: Dict[str, Any]):
        """Render regional enrollment trends."""
        st.markdown("### 📍 Regional Enrollment Trends")

        # Get regional data
        regional_data = self.data_service.get_regional_trends(filters)

        if not regional_data:
            st.info("No regional trends data available for the selected filters.")
            return

        col1, col2 = st.columns(2)

        with col1:
            # Regional comparison chart
            fig_regional = self.viz_service.create_regional_comparison_chart(regional_data)
            st.plotly_chart(fig_regional, use_container_width=True)

        with col2:
            # Regional growth rates
            fig_growth = self.viz_service.create_regional_growth_chart(regional_data)
            st.plotly_chart(fig_growth, use_container_width=True)

        # Regional heatmap
        fig_heatmap = self.viz_service.create_regional_heatmap(regional_data)
        st.plotly_chart(fig_heatmap, use_container_width=True)

        # Regional insights
        regional_insights = self.data_service.get_regional_insights(regional_data)
        if regional_insights:
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(
                    f"""
                <div class="success-box">
                    <h4>🏆 Top Performing Region</h4>
                    <p><strong>{regional_insights['top_region']}</strong></p>
                    <p>Growth Rate: {regional_insights['top_growth']:+.1f}%</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            with col2:
                st.markdown(
                    f"""
                <div class="warning-box">
                    <h4>⚠️ Needs Attention</h4>
                    <p><strong>{regional_insights['lowest_region']}</strong></p>
                    <p>Growth Rate: {regional_insights['lowest_growth']:+.1f}%</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            with col3:
                st.markdown(
                    f"""
                <div class="insight-box">
                    <h4>📊 Regional Variation</h4>
                    <p>Coefficient of Variation: {regional_insights['variation']:.1f}%</p>
                    <p>Standard Deviation: {regional_insights['std_dev']:.0f}</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )

    def render_demographic_trends(self, filters: Dict[str, Any]):
        """Render demographic enrollment trends."""
        st.markdown("### 🎯 Demographic Enrollment Trends")

        # Get demographic data
        demographic_data = self.data_service.get_demographic_trends(filters)

        if not demographic_data:
            st.info("No demographic trends data available for the selected filters.")
            return

        # Create tabs for different demographic analyses
        demo_tab1, demo_tab2, demo_tab3 = st.tabs(["👥 Gender Trends", "🎓 Grade Level Trends", "🏫 School Type Trends"])

        with demo_tab1:
            self.render_gender_trends(demographic_data)

        with demo_tab2:
            self.render_grade_level_trends(demographic_data)

        with demo_tab3:
            self.render_school_type_trends(demographic_data)

    def render_gender_trends(self, demographic_data: Dict[str, Any]):
        """Render gender-based enrollment trends."""
        gender_data = demographic_data.get("gender_trends", [])

        if not gender_data:
            st.info("No gender trends data available.")
            return

        col1, col2 = st.columns(2)

        with col1:
            # Gender enrollment trends
            fig_gender = self.viz_service.create_gender_trends_chart(gender_data)
            st.plotly_chart(fig_gender, use_container_width=True)

        with col2:
            # Gender parity index
            fig_parity = self.viz_service.create_gender_parity_chart(gender_data)
            st.plotly_chart(fig_parity, use_container_width=True)

        # Gender insights
        gender_insights = self.data_service.get_gender_insights(gender_data)
        if gender_insights:
            parity_status = "Achieved" if 0.97 <= gender_insights["parity_index"] <= 1.03 else "Not Achieved"
            parity_color = "success-box" if parity_status == "Achieved" else "warning-box"

            st.markdown(
                f"""
            <div class="{parity_color}">
                <h4>⚖️ Gender Parity Analysis</h4>
                <p><strong>Current Parity Index:</strong> {gender_insights['parity_index']:.3f}</p>
                <p><strong>Parity Status:</strong> {parity_status}</p>
                <p><strong>Female Enrollment:</strong> {gender_insights['female_percentage']:.1f}%</p>
                <p><strong>Male Enrollment:</strong> {gender_insights['male_percentage']:.1f}%</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

    def render_grade_level_trends(self, demographic_data: Dict[str, Any]):
        """Render grade level enrollment trends."""
        grade_data = demographic_data.get("grade_trends", [])

        if not grade_data:
            st.info("No grade level trends data available.")
            return

        # Grade level trends chart
        fig_grades = self.viz_service.create_grade_level_trends_chart(grade_data)
        st.plotly_chart(fig_grades, use_container_width=True)

        # Transition rates
        col1, col2 = st.columns(2)

        with col1:
            transition_data = self.data_service.get_grade_transition_rates(grade_data)
            fig_transition = self.viz_service.create_transition_rates_chart(transition_data)
            st.plotly_chart(fig_transition, use_container_width=True)

        with col2:
            # Grade level distribution
            fig_distribution = self.viz_service.create_grade_distribution_chart(grade_data)
            st.plotly_chart(fig_distribution, use_container_width=True)

    def render_school_type_trends(self, demographic_data: Dict[str, Any]):
        """Render school type enrollment trends."""
        school_type_data = demographic_data.get("school_type_trends", [])

        if not school_type_data:
            st.info("No school type trends data available.")
            return

        # School type trends
        fig_school_types = self.viz_service.create_school_type_trends_chart(school_type_data)
        st.plotly_chart(fig_school_types, use_container_width=True)

        # Public vs Private analysis
        col1, col2 = st.columns(2)

        with col1:
            public_private_data = self.data_service.get_public_private_trends(school_type_data)
            fig_public_private = self.viz_service.create_public_private_chart(public_private_data)
            st.plotly_chart(fig_public_private, use_container_width=True)

        with col2:
            # School type market share
            fig_market_share = self.viz_service.create_school_type_market_share_chart(school_type_data)
            st.plotly_chart(fig_market_share, use_container_width=True)

    def render_forecasting_analysis(self, filters: Dict[str, Any]):
        """Render enrollment forecasting analysis."""
        st.markdown("## 🔮 Enrollment Forecasting")

        # Get historical data for forecasting
        historical_data = self.data_service.get_historical_enrollment_data(filters)

        if not historical_data or len(historical_data) < 12:
            st.warning("Insufficient historical data for reliable forecasting. Need at least 12 data points.")
            return

        # Forecasting parameters
        col1, col2, col3 = st.columns(3)

        with col1:
            forecast_periods = st.selectbox("Forecast Periods", options=[6, 12, 18, 24], index=1, key="forecast_periods")

        with col2:
            confidence_level = st.selectbox("Confidence Level", options=[80, 90, 95], index=1, key="confidence_level")

        with col3:
            forecast_method = st.selectbox(
                "Forecasting Method",
                options=["ARIMA", "Exponential Smoothing", "Linear Trend", "Seasonal Decomposition"],
                index=0,
                key="forecast_method",
            )

        # Generate forecast
        if st.button("🔮 Generate Forecast", key="generate_forecast"):
            with st.spinner("Generating enrollment forecast..."):
                forecast_data = self.data_service.generate_enrollment_forecast(
                    historical_data, forecast_periods, confidence_level, forecast_method
                )

                if forecast_data:
                    # Display forecast chart
                    fig_forecast = self.viz_service.create_forecast_chart(historical_data, forecast_data, confidence_level)
                    st.plotly_chart(fig_forecast, use_container_width=True)

                    # Forecast insights
                    forecast_insights = self.data_service.get_forecast_insights(forecast_data)

                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown(
                            f"""
                        <div class="insight-box">
                            <h4>📊 Forecast Summary</h4>
                            <p><strong>Method:</strong> {forecast_method}</p>
                            <p><strong>Forecast Period:</strong> {forecast_periods} periods</p>
                            <p><strong>Expected Growth:</strong> {forecast_insights['expected_growth']:+.1f}%</p>
                            <p><strong>Trend Direction:</strong> {forecast_insights['trend_direction']}</p>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )

                    with col2:
                        st.markdown(
                            f"""
                        <div class="warning-box">
                            <h4>⚠️ Forecast Accuracy</h4>
                            <p><strong>Model Accuracy:</strong> {forecast_insights['accuracy']:.1f}%</p>
                            <p><strong>MAPE:</strong> {forecast_insights['mape']:.2f}%</p>
                            <p><strong>Confidence Level:</strong> {confidence_level}%</p>
                            <p><em>Forecasts are estimates based on historical patterns</em></p>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )

                    # Scenario analysis
                    st.markdown("### 📈 Scenario Analysis")
                    scenario_data = self.data_service.get_scenario_analysis(forecast_data)
                    fig_scenarios = self.viz_service.create_scenario_chart(scenario_data)
                    st.plotly_chart(fig_scenarios, use_container_width=True)
                else:
                    st.error("Failed to generate forecast. Please try with different parameters.")

    def render_data_export(self, filters: Dict[str, Any]):
        """Render data export options."""
        st.markdown("## 📥 Data Export")

        export_col1, export_col2, export_col3 = st.columns(3)

        with export_col1:
            if st.button("📊 Export Trends Data", key="export_trends"):
                trends_data = self.data_service.get_enrollment_trends(filters)
                if trends_data:
                    df = pd.DataFrame(trends_data)
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download Trends CSV",
                        data=csv,
                        file_name=f"enrollment_trends_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                    )

        with export_col2:
            if st.button("📍 Export Regional Data", key="export_regional"):
                regional_data = self.data_service.get_regional_trends(filters)
                if regional_data:
                    df = pd.DataFrame(regional_data)
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download Regional CSV",
                        data=csv,
                        file_name=f"regional_enrollment_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                    )

        with export_col3:
            if st.button("📈 Export Full Report", key="export_report"):
                report_data = self.data_service.generate_comprehensive_report(filters)
                if report_data:
                    st.download_button(
                        label="Download Full Report",
                        data=report_data,
                        file_name=f"enrollment_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                    )

    def run(self):
        """Run the main dashboard application."""
        try:
            # Render header
            self.render_header()

            # Render sidebar filters
            filters = self.render_sidebar_filters()

            # Auto-refresh logic
            if st.session_state.auto_refresh:
                time_since_refresh = datetime.now() - st.session_state.last_refresh
                if time_since_refresh > timedelta(minutes=5):  # Auto-refresh every 5 minutes
                    st.session_state.last_refresh = datetime.now()
                    st.experimental_rerun()

            # Main content
            if filters.get("analysis_type") == "Forecasting":
                self.render_forecasting_analysis(filters)
            else:
                # Render key metrics
                self.render_key_metrics(filters)

                # Render enrollment trends
                self.render_enrollment_trends(filters)

            # Render data export options
            self.render_data_export(filters)

            # Footer
            st.markdown("---")
            st.markdown(
                """
            <div style="text-align: center; color: #666; padding: 1rem;">
                <p>📈 Bangladesh Education Data Warehouse - Enrollment Trends Dashboard</p>
                <p>Built with ❤️ for better education insights | Last updated: {}</p>
            </div>
            """.format(
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ),
                unsafe_allow_html=True,
            )

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            logger.error(f"Dashboard error: {e}", exc_info=True)


def main():
    """Main function to run the dashboard."""
    dashboard = EnrollmentTrendsDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()
