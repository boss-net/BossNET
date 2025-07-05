"""
Visualization Service for Student Performance Dashboard
Handles all chart creation and analytics visualizations.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


class VisualizationService:
    """Service class for creating visualizations."""

    def __init__(self):
        # Define color palette
        self.colors = {
            "primary": "#667eea",
            "secondary": "#764ba2",
            "success": "#28a745",
            "warning": "#ffc107",
            "danger": "#dc3545",
            "info": "#17a2b8",
        }
        self.color_schemes = {
            "primary": px.colors.qualitative.Set1,
            "secondary": px.colors.qualitative.Set2,
            "sequential": px.colors.sequential.Viridis,
            "diverging": px.colors.diverging.RdBu,
        }

    @staticmethod
    def create_performance_heatmap(df: pd.DataFrame) -> Optional[go.Figure]:
        """Create performance heatmap by region and subject."""
        if df.empty or "division" not in df.columns or "subject_name" not in df.columns:
            return None

        try:
            # Aggregate data for heatmap
            heatmap_data = df.groupby(["division", "subject_name"])["percentage"].mean().reset_index()
            heatmap_pivot = heatmap_data.pivot(index="division", columns="subject_name", values="percentage")

            fig = px.imshow(
                heatmap_pivot,
                title="Performance Heatmap by Region and Subject",
                labels=dict(x="Subject", y="Division", color="Average Percentage"),
                color_continuous_scale="RdYlGn",
                aspect="auto",
            )

            fig.update_layout(xaxis_title="Subject", yaxis_title="Division", height=500)

            return fig
        except Exception as e:
            logger.error(f"Error creating heatmap: {e}")
            return None

    @staticmethod
    def create_time_series_analysis(df: pd.DataFrame) -> Optional[go.Figure]:
        """Create time series analysis of performance trends."""
        if df.empty:
            return None

        try:
            # Convert assessment_date to datetime if needed
            df["assessment_date"] = pd.to_datetime(df["assessment_date"])

            # Aggregate by month
            monthly_performance = (
                df.groupby(df["assessment_date"].dt.to_period("M"))
                .agg({"percentage": ["mean", "std", "count"], "is_passed": "sum"})
                .reset_index()
            )

            monthly_performance.columns = ["month", "avg_percentage", "std_percentage", "assessment_count", "pass_count"]
            monthly_performance["month"] = monthly_performance["month"].astype(str)
            monthly_performance["pass_rate"] = (
                monthly_performance["pass_count"] / monthly_performance["assessment_count"]
            ) * 100

            # Create subplot
            fig = make_subplots(
                rows=2, cols=1, subplot_titles=("Average Performance Over Time", "Pass Rate Over Time"), vertical_spacing=0.1
            )

            # Performance trend
            fig.add_trace(
                go.Scatter(
                    x=monthly_performance["month"],
                    y=monthly_performance["avg_percentage"],
                    mode="lines+markers",
                    name="Average Performance",
                    line=dict(color="blue", width=2),
                ),
                row=1,
                col=1,
            )

            # Pass rate trend
            fig.add_trace(
                go.Scatter(
                    x=monthly_performance["month"],
                    y=monthly_performance["pass_rate"],
                    mode="lines+markers",
                    name="Pass Rate",
                    line=dict(color="green", width=2),
                ),
                row=2,
                col=1,
            )

            fig.update_layout(height=600, title_text="Performance Trends Over Time", showlegend=True)

            return fig
        except Exception as e:
            logger.error(f"Error creating time series: {e}")
            return None

    @staticmethod
    def create_comparative_analysis(df: pd.DataFrame) -> Optional[go.Figure]:
        """Create comparative analysis dashboards."""
        if df.empty:
            return None

        try:
            # Create subplots for different comparisons
            fig = make_subplots(
                rows=2,
                cols=2,
                subplot_titles=(
                    "Performance by Gender",
                    "Performance by Age Group",
                    "Performance by School Type",
                    "Performance by Socioeconomic Status",
                ),
                specs=[[{"type": "box"}, {"type": "box"}], [{"type": "box"}, {"type": "box"}]],
            )

            # Gender comparison
            if "gender" in df.columns:
                for gender in df["gender"].unique():
                    if pd.notna(gender):
                        gender_data = df[df["gender"] == gender]["percentage"]
                        fig.add_trace(go.Box(y=gender_data, name=gender, boxpoints="outliers"), row=1, col=1)

            # Age group comparison
            if "age_group" in df.columns:
                for age_group in df["age_group"].unique():
                    if pd.notna(age_group):
                        age_data = df[df["age_group"] == age_group]["percentage"]
                        fig.add_trace(go.Box(y=age_data, name=age_group, boxpoints="outliers"), row=1, col=2)

            # School type comparison (if available)
            if "school_type" in df.columns:
                for school_type in df["school_type"].unique():
                    if pd.notna(school_type):
                        school_data = df[df["school_type"] == school_type]["percentage"]
                        fig.add_trace(go.Box(y=school_data, name=school_type, boxpoints="outliers"), row=2, col=1)

            # Socioeconomic status comparison
            if "socioeconomic_status" in df.columns:
                for status in df["socioeconomic_status"].unique():
                    if pd.notna(status):
                        status_data = df[df["socioeconomic_status"] == status]["percentage"]
                        fig.add_trace(go.Box(y=status_data, name=status, boxpoints="outliers"), row=2, col=2)

            fig.update_layout(height=800, title_text="Comparative Performance Analysis", showlegend=False)

            return fig
        except Exception as e:
            logger.error(f"Error creating comparative analysis: {e}")
            return None

    @staticmethod
    def create_performance_distribution(df: pd.DataFrame) -> Dict[str, go.Figure]:
        """Create performance distribution charts."""
        charts = {}

        try:
            # Histogram
            fig_hist = px.histogram(
                df,
                x="percentage",
                nbins=20,
                title="Performance Distribution",
                labels={"percentage": "Percentage Score"},
                color_discrete_sequence=["#1f77b4"],
            )
            fig_hist.update_layout(showlegend=False)
            charts["histogram"] = fig_hist

            # Box plot by subject
            if "subject_name" in df.columns:
                fig_box = px.box(
                    df,
                    x="subject_name",
                    y="percentage",
                    title="Performance by Subject",
                    labels={"subject_name": "Subject", "percentage": "Percentage Score"},
                )
                fig_box.update_xaxes(tickangle=45)
                charts["subject_box"] = fig_box

            # Performance by region
            if "division" in df.columns:
                fig_region = px.box(
                    df,
                    x="division",
                    y="percentage",
                    title="Performance by Division",
                    labels={"division": "Division", "percentage": "Percentage Score"},
                )
                fig_region.update_xaxes(tickangle=45)
                charts["region_box"] = fig_region

            return charts
        except Exception as e:
            logger.error(f"Error creating distribution charts: {e}")
            return {}

    @staticmethod
    def create_equity_analysis(df: pd.DataFrame) -> Optional[go.Figure]:
        """Create equity analysis visualization."""
        if df.empty:
            return None

        try:
            # Calculate equity metrics
            equity_data = []

            # Gender equity
            if "gender" in df.columns:
                gender_equity = df.groupby("gender")["percentage"].agg(["mean", "count"]).reset_index()
                gender_equity["metric"] = "Gender"
                equity_data.append(gender_equity)

            # Socioeconomic equity
            if "socioeconomic_status" in df.columns:
                ses_equity = df.groupby("socioeconomic_status")["percentage"].agg(["mean", "count"]).reset_index()
                ses_equity["metric"] = "Socioeconomic Status"
                equity_data.append(ses_equity)

            # Rural/Urban equity
            if "is_rural" in df.columns:
                rural_equity = df.groupby("is_rural")["percentage"].agg(["mean", "count"]).reset_index()
                rural_equity["metric"] = "Rural/Urban"
                equity_data.append(rural_equity)

            if not equity_data:
                return None

            # Combine all equity data
            combined_equity = pd.concat(equity_data, ignore_index=True)

            # Create visualization
            fig = px.bar(
                combined_equity,
                x="metric",
                y="mean",
                color="gender" if "gender" in combined_equity.columns else "socioeconomic_status",
                title="Equity Analysis: Average Performance by Demographics",
                labels={"mean": "Average Percentage", "metric": "Demographic Factor"},
                barmode="group",
            )

            fig.update_layout(height=500, xaxis_title="Demographic Factor", yaxis_title="Average Percentage")

            return fig
        except Exception as e:
            logger.error(f"Error creating equity analysis: {e}")
            return None

    def create_performance_trends(self, data: List[Dict[str, Any]]) -> go.Figure:
        """Create performance trends over time."""
        if not data:
            return go.Figure().add_annotation(
                text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
            )

        df = pd.DataFrame(data)

        fig = go.Figure()

        # Add performance trend line
        fig.add_trace(
            go.Scatter(
                x=df["month"],
                y=df["avg_score"],
                mode="lines+markers",
                name="Average Performance",
                line=dict(color=self.colors["primary"], width=3),
                marker=dict(size=8, color=self.colors["primary"]),
            )
        )

        fig.update_layout(
            title="Student Performance Trends Over Time",
            xaxis_title="Month",
            yaxis_title="Average Score (%)",
            hovermode="x unified",
            showlegend=False,
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family="Arial, sans-serif", size=12),
            margin=dict(l=0, r=0, t=40, b=0),
        )

        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

        return fig

    def create_regional_performance_chart(self, data: List[Dict[str, Any]]) -> go.Figure:
        """Create regional performance bar chart"""
        if not data:
            return go.Figure().add_annotation(
                text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
            )

        df = pd.DataFrame(data)

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=df["division"],
                y=df["avg_score"],
                name="Average Score",
                marker_color=self.colors["primary"],
                text=df["avg_score"].round(1),
                textposition="outside",
            )
        )

        fig.update_layout(
            title="Performance by Division",
            xaxis_title="Division",
            yaxis_title="Average Score (%)",
            showlegend=False,
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family="Arial, sans-serif", size=12),
            margin=dict(l=0, r=0, t=40, b=0),
        )

        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

        return fig

    def create_gender_performance_chart(self, data: List[Dict[str, Any]]) -> go.Figure:
        """Create gender performance comparison chart"""
        if not data:
            return go.Figure().add_annotation(
                text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
            )

        df = pd.DataFrame(data)

        fig = go.Figure()

        colors = [self.colors["primary"], self.colors["secondary"]]

        fig.add_trace(
            go.Bar(
                x=df["gender"],
                y=df["avg_score"],
                name="Average Score",
                marker_color=colors[: len(df)],
                text=df["avg_score"].round(1),
                textposition="outside",
            )
        )

        fig.update_layout(
            title="Performance by Gender",
            xaxis_title="Gender",
            yaxis_title="Average Score (%)",
            showlegend=False,
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family="Arial, sans-serif", size=12),
            margin=dict(l=0, r=0, t=40, b=0),
        )

        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

        return fig

    def create_subject_performance_chart(self, data: List[Dict[str, Any]]) -> go.Figure:
        """Create subject performance horizontal bar chart"""
        if not data:
            return go.Figure().add_annotation(
                text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
            )

        df = pd.DataFrame(data)

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=df["avg_score"],
                y=df["subject"],
                orientation="h",
                name="Average Score",
                marker_color=self.colors["info"],
                text=df["avg_score"].round(1),
                textposition="outside",
            )
        )

        fig.update_layout(
            title="Subject-wise Performance",
            xaxis_title="Average Score (%)",
            yaxis_title="Subject",
            showlegend=False,
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family="Arial, sans-serif", size=12),
            margin=dict(l=0, r=0, t=40, b=0),
        )

        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
        fig.update_yaxes(showgrid=False)

        return fig

    def create_attendance_heatmap(self, data: List[Dict[str, Any]]) -> go.Figure:
        """Create attendance heatmap"""
        if not data:
            return go.Figure().add_annotation(
                text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
            )

        df = pd.DataFrame(data)

        # Pivot data for heatmap
        heatmap_data = df.pivot(index="division", columns="month", values="attendance_rate")

        fig = go.Figure(
            data=go.Heatmap(
                z=heatmap_data.values,
                x=heatmap_data.columns,
                y=heatmap_data.index,
                colorscale="RdYlGn",
                text=heatmap_data.values,
                texttemplate="%{text:.1f}%",
                textfont={"size": 10},
                colorbar=dict(title="Attendance Rate (%)"),
            )
        )

        fig.update_layout(
            title="Attendance Rate by Division and Month",
            xaxis_title="Month",
            yaxis_title="Division",
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family="Arial, sans-serif", size=12),
            margin=dict(l=0, r=0, t=40, b=0),
        )

        return fig

    def create_performance_trends_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create performance trends over time chart."""
        if df.empty or "assessment_date" not in df.columns:
            return self._create_empty_chart("No performance trends data available")

        try:
            # Convert assessment_date to datetime
            df["assessment_date"] = pd.to_datetime(df["assessment_date"])

            # Group by month and calculate metrics
            monthly_data = (
                df.groupby(df["assessment_date"].dt.to_period("M"))
                .agg({"assessment_percentage": ["mean", "count"], "is_pass": "mean"})
                .reset_index()
            )

            # Flatten column names
            monthly_data.columns = ["month", "avg_percentage", "assessment_count", "pass_rate"]
            monthly_data["month"] = monthly_data["month"].astype(str)
            monthly_data["pass_rate"] = monthly_data["pass_rate"] * 100

            # Create subplot with secondary y-axis
            fig = make_subplots(specs=[[{"secondary_y": True}]], subplot_titles=("Performance Trends Over Time",))

            # Add average percentage line
            fig.add_trace(
                go.Scatter(
                    x=monthly_data["month"],
                    y=monthly_data["avg_percentage"],
                    mode="lines+markers",
                    name="Average Performance (%)",
                    line=dict(color="#1f77b4", width=3),
                    marker=dict(size=8),
                    hovertemplate="<b>%{x}</b><br>Avg Performance: %{y:.1f}%<extra></extra>",
                ),
                secondary_y=False,
            )

            # Add pass rate line
            fig.add_trace(
                go.Scatter(
                    x=monthly_data["month"],
                    y=monthly_data["pass_rate"],
                    mode="lines+markers",
                    name="Pass Rate (%)",
                    line=dict(color="#ff7f0e", width=3, dash="dash"),
                    marker=dict(size=8),
                    hovertemplate="<b>%{x}</b><br>Pass Rate: %{y:.1f}%<extra></extra>",
                ),
                secondary_y=True,
            )

            # Add assessment count bars
            fig.add_trace(
                go.Bar(
                    x=monthly_data["month"],
                    y=monthly_data["assessment_count"],
                    name="Assessment Count",
                    opacity=0.3,
                    marker_color="#2ca02c",
                    hovertemplate="<b>%{x}</b><br>Assessments: %{y}<extra></extra>",
                ),
                secondary_y=True,
            )

            # Update layout
            fig.update_xaxes(title_text="Month")
            fig.update_yaxes(title_text="Performance (%)", secondary_y=False)
            fig.update_yaxes(title_text="Pass Rate (%) / Assessment Count", secondary_y=True)

            fig.update_layout(
                height=400, hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            return fig

        except Exception as e:
            return self._create_empty_chart(f"Error creating trends chart: {str(e)}")

    def create_regional_performance_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create regional performance comparison chart."""
        if df.empty or "division" not in df.columns:
            return self._create_empty_chart("No regional data available")

        try:
            # Calculate regional metrics
            regional_data = (
                df.groupby("division")
                .agg({"assessment_percentage": "mean", "student_id": "nunique", "is_pass": "mean"})
                .reset_index()
            )

            regional_data.columns = ["division", "avg_performance", "student_count", "pass_rate"]
            regional_data["pass_rate"] = regional_data["pass_rate"] * 100
            regional_data = regional_data.sort_values("avg_performance", ascending=True)

            # Create horizontal bar chart
            fig = go.Figure()

            # Add performance bars
            fig.add_trace(
                go.Bar(
                    y=regional_data["division"],
                    x=regional_data["avg_performance"],
                    orientation="h",
                    name="Average Performance",
                    marker=dict(
                        color=regional_data["avg_performance"],
                        colorscale="Viridis",
                        showscale=True,
                        colorbar=dict(title="Performance (%)"),
                    ),
                    text=regional_data["avg_performance"].round(1),
                    textposition="inside",
                    hovertemplate="<b>%{y}</b><br>"
                    + "Avg Performance: %{x:.1f}%<br>"
                    + "Students: %{customdata[0]}<br>"
                    + "Pass Rate: %{customdata[1]:.1f}%<extra></extra>",
                    customdata=regional_data[["student_count", "pass_rate"]],
                )
            )

            fig.update_layout(
                title="Average Performance by Division",
                xaxis_title="Average Performance (%)",
                yaxis_title="Division",
                height=400,
                showlegend=False,
            )

            return fig

        except Exception as e:
            return self._create_empty_chart(f"Error creating regional chart: {str(e)}")

    def create_subject_performance_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create subject-wise performance chart."""
        if df.empty or "subject_name" not in df.columns:
            return self._create_empty_chart("No subject data available")

        try:
            # Calculate subject metrics
            subject_data = (
                df.groupby("subject_name")
                .agg({"assessment_percentage": ["mean", "std", "count"], "is_pass": "mean"})
                .reset_index()
            )

            # Flatten column names
            subject_data.columns = ["subject", "avg_performance", "std_performance", "assessment_count", "pass_rate"]
            subject_data["pass_rate"] = subject_data["pass_rate"] * 100
            subject_data = subject_data.sort_values("avg_performance", ascending=False)

            # Create bar chart with error bars
            fig = go.Figure()

            fig.add_trace(
                go.Bar(
                    x=subject_data["subject"],
                    y=subject_data["avg_performance"],
                    error_y=dict(type="data", array=subject_data["std_performance"], visible=True),
                    marker=dict(
                        color=subject_data["avg_performance"],
                        colorscale="RdYlGn",
                        showscale=True,
                        colorbar=dict(title="Performance (%)"),
                    ),
                    text=subject_data["avg_performance"].round(1),
                    textposition="outside",
                    hovertemplate="<b>%{x}</b><br>"
                    + "Avg Performance: %{y:.1f}%<br>"
                    + "Std Dev: %{error_y.array:.1f}<br>"
                    + "Assessments: %{customdata[0]}<br>"
                    + "Pass Rate: %{customdata[1]:.1f}%<extra></extra>",
                    customdata=subject_data[["assessment_count", "pass_rate"]],
                )
            )

            fig.update_layout(
                title="Subject-wise Performance Analysis",
                xaxis_title="Subject",
                yaxis_title="Average Performance (%)",
                height=400,
                xaxis={"tickangle": 45},
                showlegend=False,
            )

            return fig

        except Exception as e:
            return self._create_empty_chart(f"Error creating subject chart: {str(e)}")

    def create_gender_performance_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create gender performance comparison chart."""
        if df.empty or "gender" not in df.columns:
            return self._create_empty_chart("No gender data available")

        try:
            # Create box plot for gender performance
            fig = px.box(
                df,
                x="gender",
                y="assessment_percentage",
                color="gender",
                title="Performance Distribution by Gender",
                labels={"assessment_percentage": "Performance (%)", "gender": "Gender"},
                color_discrete_sequence=px.colors.qualitative.Set2,
            )

            # Add mean markers
            gender_means = df.groupby("gender")["assessment_percentage"].mean()
            for gender, mean_val in gender_means.items():
                fig.add_shape(
                    type="line",
                    x0=gender,
                    x1=gender,
                    y0=mean_val - 2,
                    y1=mean_val + 2,
                    line=dict(color="red", width=3),
                )
                fig.add_annotation(
                    x=gender, y=mean_val + 5, text=f"μ={mean_val:.1f}%", showarrow=False, font=dict(color="red", size=12)
                )

            fig.update_layout(height=350, showlegend=False)

            return fig

        except Exception as e:
            return self._create_empty_chart(f"Error creating gender chart: {str(e)}")

    def create_school_type_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create school type performance chart."""
        if df.empty or "school_category" not in df.columns:
            return self._create_empty_chart("No school type data available")

        try:
            # Create violin plot for school type performance
            fig = px.violin(
                df,
                x="school_category",
                y="assessment_percentage",
                color="school_category",
                box=True,
                points="outliers",
                title="Performance Distribution by School Type",
                labels={"assessment_percentage": "Performance (%)", "school_category": "School Type"},
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )

            fig.update_layout(height=350, showlegend=False)

            return fig

        except Exception as e:
            return self._create_empty_chart(f"Error creating school type chart: {str(e)}")

    def create_grade_distribution_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create grade distribution pie chart."""
        if df.empty or "letter_grade" not in df.columns:
            return self._create_empty_chart("No grade data available")

        try:
            # Calculate grade distribution
            grade_counts = df["letter_grade"].value_counts()

            # Define grade colors
            grade_colors = {
                "A+": "#2E8B57",  # Sea Green
                "A": "#32CD32",  # Lime Green
                "A-": "#9ACD32",  # Yellow Green
                "B+": "#FFD700",  # Gold
                "B": "#FFA500",  # Orange
                "B-": "#FF8C00",  # Dark Orange
                "C+": "#FF6347",  # Tomato
                "C": "#FF4500",  # Orange Red
                "C-": "#DC143C",  # Crimson
                "D": "#B22222",  # Fire Brick
                "F": "#8B0000",  # Dark Red
            }

            colors = [grade_colors.get(grade, "#808080") for grade in grade_counts.index]

            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=grade_counts.index,
                        values=grade_counts.values,
                        hole=0.4,
                        marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2)),
                        textinfo="label+percent",
                        textposition="auto",
                        hovertemplate="<b>Grade %{label}</b><br>"
                        + "Count: %{value}<br>"
                        + "Percentage: %{percent}<extra></extra>",
                    )
                ]
            )

            fig.update_layout(
                title="Grade Distribution",
                height=400,
                showlegend=True,
                legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.01),
            )

            return fig

        except Exception as e:
            return self._create_empty_chart(f"Error creating grade distribution chart: {str(e)}")

    def create_performance_heatmap(self, df: pd.DataFrame) -> go.Figure:
        """Create performance heatmap by division and subject."""
        if df.empty or "division" not in df.columns or "subject_name" not in df.columns:
            return self._create_empty_chart("No data for heatmap")

        try:
            # Create pivot table
            heatmap_data = df.pivot_table(
                values="assessment_percentage", index="division", columns="subject_name", aggfunc="mean"
            )

            fig = go.Figure(
                data=go.Heatmap(
                    z=heatmap_data.values,
                    x=heatmap_data.columns,
                    y=heatmap_data.index,
                    colorscale="RdYlGn",
                    hoverongaps=False,
                    hovertemplate="<b>%{y}</b><br>" + "Subject: %{x}<br>" + "Avg Performance: %{z:.1f}%<extra></extra>",
                )
            )

            fig.update_layout(
                title="Performance Heatmap: Division vs Subject", xaxis_title="Subject", yaxis_title="Division", height=500
            )

            return fig

        except Exception as e:
            return self._create_empty_chart(f"Error creating heatmap: {str(e)}")

    def _create_empty_chart(self, message: str) -> go.Figure:
        """Create an empty chart with a message."""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            xanchor="center",
            yanchor="middle",
            showarrow=False,
            font=dict(size=16, color="gray"),
        )
        fig.update_layout(
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            height=400,
        )
        return fig


# Create a global instance
viz_service = VisualizationService()
