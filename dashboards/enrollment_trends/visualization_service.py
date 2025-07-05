"""
Visualization Service for Enrollment Trends Dashboard
Handles all chart creation and analytics visualizations for enrollment trends.
"""

import calendar
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


class EnrollmentVisualizationService:
    """Service class for creating enrollment trend visualizations."""

    def __init__(self):
        # Define color palettes
        self.colors = {
            "primary": "#1f77b4",
            "secondary": "#ff7f0e",
            "success": "#2ca02c",
            "danger": "#d62728",
            "warning": "#ff7f0e",
            "info": "#17becf",
            "purple": "#9467bd",
            "brown": "#8c564b",
            "pink": "#e377c2",
            "gray": "#7f7f7f",
            "olive": "#bcbd22",
            "cyan": "#17becf",
        }

        self.color_sequences = {
            "qualitative": px.colors.qualitative.Set1,
            "sequential": px.colors.sequential.Viridis,
            "diverging": px.colors.diverging.RdBu,
            "pastel": px.colors.qualitative.Pastel,
            "dark": px.colors.qualitative.Dark24,
        }

    def create_enrollment_trends_chart(
        self, trends_data: List[Dict[str, Any]], aggregation_level: str = "Monthly"
    ) -> go.Figure:
        """Create main enrollment trends chart."""
        if not trends_data:
            return self._create_empty_chart("No enrollment trends data available")

        try:
            df = pd.DataFrame(trends_data)

            # Create subplot with secondary y-axis
            fig = make_subplots(specs=[[{"secondary_y": True}]], subplot_titles=(f"Enrollment Trends ({aggregation_level})",))

            # Main enrollment trend line
            fig.add_trace(
                go.Scatter(
                    x=df["period"],
                    y=df["enrollment_count"],
                    mode="lines+markers",
                    name="Total Enrollments",
                    line=dict(color=self.colors["primary"], width=3),
                    marker=dict(size=8, color=self.colors["primary"]),
                    hovertemplate="<b>%{x}</b><br>Enrollments: %{y:,}<extra></extra>",
                ),
                secondary_y=False,
            )

            # Unique students line
            fig.add_trace(
                go.Scatter(
                    x=df["period"],
                    y=df["unique_students"],
                    mode="lines+markers",
                    name="Unique Students",
                    line=dict(color=self.colors["secondary"], width=2, dash="dash"),
                    marker=dict(size=6, color=self.colors["secondary"]),
                    hovertemplate="<b>%{x}</b><br>Unique Students: %{y:,}<extra></extra>",
                ),
                secondary_y=False,
            )

            # Retention rate on secondary axis
            fig.add_trace(
                go.Scatter(
                    x=df["period"],
                    y=df["retention_rate"],
                    mode="lines+markers",
                    name="Retention Rate (%)",
                    line=dict(color=self.colors["success"], width=2),
                    marker=dict(size=6, color=self.colors["success"]),
                    hovertemplate="<b>%{x}</b><br>Retention Rate: %{y:.1f}%<extra></extra>",
                ),
                secondary_y=True,
            )

            # Update layout
            fig.update_xaxes(title_text="Period")
            fig.update_yaxes(title_text="Number of Enrollments", secondary_y=False)
            fig.update_yaxes(title_text="Retention Rate (%)", secondary_y=True)

            fig.update_layout(
                height=500,
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                plot_bgcolor="white",
                paper_bgcolor="white",
            )

            # Add grid
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray", secondary_y=False)

            return fig

        except Exception as e:
            logger.error(f"Error creating enrollment trends chart: {e}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")

    def create_monthly_seasonality_chart(self, seasonal_data: List[Dict[str, Any]]) -> go.Figure:
        """Create monthly seasonality chart."""
        if not seasonal_data:
            return self._create_empty_chart("No seasonal data available")

        try:
            monthly_data = [d for d in seasonal_data if d["period_type"] == "monthly"]

            if not monthly_data:
                return self._create_empty_chart("No monthly seasonal data available")

            df = pd.DataFrame(monthly_data)

            # Create polar chart for seasonality
            fig = go.Figure()

            # Add enrollment seasonality
            fig.add_trace(
                go.Scatterpolar(
                    r=df["avg_enrollment"],
                    theta=df["period_name"],
                    mode="lines+markers",
                    name="Average Enrollment",
                    line=dict(color=self.colors["primary"], width=3),
                    marker=dict(size=8, color=self.colors["primary"]),
                    fill="toself",
                    fillcolor=f"rgba(31, 119, 180, 0.2)",
                )
            )

            fig.update_layout(
                title="Monthly Enrollment Seasonality",
                polar=dict(radialaxis=dict(visible=True, range=[0, max(df["avg_enrollment"]) * 1.1])),
                height=500,
                showlegend=True,
            )

            return fig

        except Exception as e:
            logger.error(f"Error creating seasonality chart: {e}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")

    def create_quarterly_patterns_chart(self, seasonal_data: List[Dict[str, Any]]) -> go.Figure:
        """Create quarterly patterns chart."""
        if not seasonal_data:
            return self._create_empty_chart("No seasonal data available")

        try:
            quarterly_data = [d for d in seasonal_data if d["period_type"] == "quarterly"]

            if not quarterly_data:
                return self._create_empty_chart("No quarterly seasonal data available")

            df = pd.DataFrame(quarterly_data)

            fig = go.Figure()

            # Bar chart for quarterly patterns
            fig.add_trace(
                go.Bar(
                    x=df["period_name"],
                    y=df["avg_enrollment"],
                    name="Average Enrollment",
                    marker_color=self.colors["secondary"],
                    text=df["avg_enrollment"],
                    textposition="outside",
                    hovertemplate="<b>%{x}</b><br>Avg Enrollment: %{y:,}<extra></extra>",
                )
            )

            # Add error bars for variability
            fig.add_trace(
                go.Scatter(
                    x=df["period_name"],
                    y=df["avg_enrollment"],
                    error_y=dict(type="data", array=df["std_enrollment"], visible=True, color="red", thickness=2),
                    mode="markers",
                    marker=dict(size=0),
                    name="Variability",
                    showlegend=False,
                )
            )

            fig.update_layout(
                title="Quarterly Enrollment Patterns",
                xaxis_title="Quarter",
                yaxis_title="Average Enrollment",
                height=400,
                plot_bgcolor="white",
                paper_bgcolor="white",
            )

            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

            return fig

        except Exception as e:
            logger.error(f"Error creating quarterly patterns chart: {e}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")

    def create_academic_calendar_chart(self, seasonal_data: List[Dict[str, Any]]) -> go.Figure:
        """Create academic calendar alignment chart."""
        if not seasonal_data:
            return self._create_empty_chart("No seasonal data available")

        try:
            monthly_data = [d for d in seasonal_data if d["period_type"] == "monthly"]

            if not monthly_data:
                return self._create_empty_chart("No monthly data for calendar chart")

            df = pd.DataFrame(monthly_data)

            # Create heatmap-style calendar
            fig = go.Figure()

            # Define academic calendar events
            academic_events = {
                "January": "New Year Break",
                "February": "Spring Term",
                "March": "Spring Term",
                "April": "Spring Break",
                "May": "Summer Term",
                "June": "Summer Term",
                "July": "Summer Break",
                "August": "Fall Preparation",
                "September": "Fall Term Start",
                "October": "Fall Term",
                "November": "Fall Term",
                "December": "Winter Break",
            }

            # Add enrollment bars
            fig.add_trace(
                go.Bar(
                    x=df["period_name"],
                    y=df["avg_enrollment"],
                    name="Average Enrollment",
                    marker=dict(
                        color=df["avg_enrollment"], colorscale="Viridis", showscale=True, colorbar=dict(title="Enrollment")
                    ),
                    text=[academic_events.get(month, "") for month in df["period_name"]],
                    textposition="inside",
                    hovertemplate="<b>%{x}</b><br>Enrollment: %{y:,}<br>Period: %{text}<extra></extra>",
                )
            )

            fig.update_layout(
                title="Enrollment Patterns vs Academic Calendar",
                xaxis_title="Month",
                yaxis_title="Average Enrollment",
                height=450,
                plot_bgcolor="white",
                paper_bgcolor="white",
                showlegend=False,
            )

            fig.update_xaxes(tickangle=45)
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

            return fig

        except Exception as e:
            logger.error(f"Error creating academic calendar chart: {e}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")

    def create_regional_comparison_chart(self, regional_data: List[Dict[str, Any]]) -> go.Figure:
        """Create regional enrollment comparison chart."""
        if not regional_data:
            return self._create_empty_chart("No regional data available")

        try:
            df = pd.DataFrame(regional_data)

            # Get latest year data for comparison
            latest_year = df["year"].max()
            latest_data = df[df["year"] == latest_year].copy()

            # Sort by enrollment count
            latest_data = latest_data.sort_values("enrollment_count", ascending=True)

            fig = go.Figure()

            # Horizontal bar chart
            fig.add_trace(
                go.Bar(
                    y=latest_data["division"],
                    x=latest_data["enrollment_count"],
                    orientation="h",
                    name="Total Enrollment",
                    marker=dict(
                        color=latest_data["enrollment_count"],
                        colorscale="Blues",
                        showscale=True,
                        colorbar=dict(title="Enrollment"),
                    ),
                    text=latest_data["enrollment_count"],
                    textposition="inside",
                    hovertemplate="<b>%{y}</b><br>Enrollment: %{x:,}<br>Schools: %{customdata[0]}<br>Retention: %{customdata[1]:.1f}%<extra></extra>",
                    customdata=latest_data[["active_schools", "retention_rate"]],
                )
            )

            fig.update_layout(
                title=f"Regional Enrollment Comparison ({latest_year})",
                xaxis_title="Total Enrollment",
                yaxis_title="Division",
                height=500,
                plot_bgcolor="white",
                paper_bgcolor="white",
                showlegend=False,
            )

            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
            fig.update_yaxes(showgrid=False)

            return fig

        except Exception as e:
            logger.error(f"Error creating regional comparison chart: {e}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")

    def create_regional_growth_chart(self, regional_data: List[Dict[str, Any]]) -> go.Figure:
        """Create regional growth rates chart."""
        if not regional_data:
            return self._create_empty_chart("No regional data available")

        try:
            df = pd.DataFrame(regional_data)

            # Get latest year growth rates
            latest_year = df["year"].max()
            growth_data = df[df["year"] == latest_year].copy()

            # Sort by growth rate
            growth_data = growth_data.sort_values("growth_rate", ascending=False)

            fig = go.Figure()

            # Color code based on growth rate
            colors = ["green" if x > 0 else "red" if x < 0 else "gray" for x in growth_data["growth_rate"]]

            fig.add_trace(
                go.Bar(
                    x=growth_data["division"],
                    y=growth_data["growth_rate"],
                    name="Growth Rate",
                    marker_color=colors,
                    text=growth_data["growth_rate"].round(1),
                    textposition="outside",
                    hovertemplate="<b>%{x}</b><br>Growth Rate: %{y:+.1f}%<extra></extra>",
                )
            )

            # Add zero line
            fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)

            fig.update_layout(
                title=f"Regional Growth Rates ({latest_year})",
                xaxis_title="Division",
                yaxis_title="Growth Rate (%)",
                height=400,
                plot_bgcolor="white",
                paper_bgcolor="white",
                showlegend=False,
            )

            fig.update_xaxes(tickangle=45, showgrid=False)
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

            return fig

        except Exception as e:
            logger.error(f"Error creating regional growth chart: {e}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")

    def create_regional_heatmap(self, regional_data: List[Dict[str, Any]]) -> go.Figure:
        """Create regional enrollment heatmap over time."""
        if not regional_data:
            return self._create_empty_chart("No regional data available")

        try:
            df = pd.DataFrame(regional_data)

            # Create pivot table for heatmap
            heatmap_data = df.pivot(index="division", columns="year", values="enrollment_count")

            fig = go.Figure(
                data=go.Heatmap(
                    z=heatmap_data.values,
                    x=heatmap_data.columns,
                    y=heatmap_data.index,
                    colorscale="Viridis",
                    hoverongaps=False,
                    hovertemplate="<b>%{y}</b><br>Year: %{x}<br>Enrollment: %{z:,}<extra></extra>",
                    colorbar=dict(title="Enrollment"),
                )
            )

            fig.update_layout(
                title="Regional Enrollment Heatmap Over Time",
                xaxis_title="Year",
                yaxis_title="Division",
                height=500,
                plot_bgcolor="white",
                paper_bgcolor="white",
            )

            return fig

        except Exception as e:
            logger.error(f"Error creating regional heatmap: {e}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")

    def create_gender_trends_chart(self, gender_data: List[Dict[str, Any]]) -> go.Figure:
        """Create gender enrollment trends chart."""
        if not gender_data:
            return self._create_empty_chart("No gender data available")

        try:
            df = pd.DataFrame(gender_data)

            fig = go.Figure()

            # Add traces for each gender
            for gender in df["gender"].unique():
                gender_df = df[df["gender"] == gender]

                fig.add_trace(
                    go.Scatter(
                        x=gender_df["year"],
                        y=gender_df["enrollment_count"],
                        mode="lines+markers",
                        name=f"{gender} Enrollment",
                        line=dict(width=3),
                        marker=dict(size=8),
                        hovertemplate=f"<b>{gender}</b><br>Year: %{{x}}<br>Enrollment: %{{y:,}}<extra></extra>",
                    )
                )

            fig.update_layout(
                title="Gender-wise Enrollment Trends",
                xaxis_title="Year",
                yaxis_title="Enrollment Count",
                height=400,
                plot_bgcolor="white",
                paper_bgcolor="white",
                hovermode="x unified",
            )

            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

            return fig

        except Exception as e:
            logger.error(f"Error creating gender trends chart: {e}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")

    def create_gender_parity_chart(self, gender_data: List[Dict[str, Any]]) -> go.Figure:
        """Create gender parity index chart."""
        if not gender_data:
            return self._create_empty_chart("No gender data available")

        try:
            df = pd.DataFrame(gender_data)

            # Calculate Gender Parity Index (GPI) for each year
            parity_data = []

            for year in df["year"].unique():
                year_data = df[df["year"] == year]

                female_enrollment = year_data[year_data["gender"] == "Female"]["enrollment_count"].sum()
                male_enrollment = year_data[year_data["gender"] == "Male"]["enrollment_count"].sum()

                gpi = female_enrollment / male_enrollment if male_enrollment > 0 else 0

                parity_data.append(
                    {"year": year, "gpi": gpi, "female_enrollment": female_enrollment, "male_enrollment": male_enrollment}
                )

            parity_df = pd.DataFrame(parity_data)

            fig = go.Figure()

            # Add GPI line
            fig.add_trace(
                go.Scatter(
                    x=parity_df["year"],
                    y=parity_df["gpi"],
                    mode="lines+markers",
                    name="Gender Parity Index",
                    line=dict(color=self.colors["purple"], width=3),
                    marker=dict(size=10, color=self.colors["purple"]),
                    hovertemplate="<b>Year: %{x}</b><br>GPI: %{y:.3f}<extra></extra>",
                )
            )

            # Add parity reference lines
            fig.add_hline(
                y=1.0,
                line_dash="solid",
                line_color="green",
                annotation_text="Perfect Parity (1.0)",
                annotation_position="right",
            )
            fig.add_hline(
                y=0.97,
                line_dash="dash",
                line_color="orange",
                annotation_text="Acceptable Range (0.97-1.03)",
                annotation_position="right",
            )
            fig.add_hline(y=1.03, line_dash="dash", line_color="orange")

            fig.update_layout(
                title="Gender Parity Index Over Time",
                xaxis_title="Year",
                yaxis_title="Gender Parity Index (Female/Male)",
                height=400,
                plot_bgcolor="white",
                paper_bgcolor="white",
                yaxis=dict(range=[0.8, 1.2]),
            )

            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

            return fig

        except Exception as e:
            logger.error(f"Error creating gender parity chart: {e}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")

    def create_grade_level_trends_chart(self, grade_data: List[Dict[str, Any]]) -> go.Figure:
        """Create grade level enrollment trends chart."""
        if not grade_data:
            return self._create_empty_chart("No grade level data available")

        try:
            df = pd.DataFrame(grade_data)

            # Create stacked area chart
            fig = go.Figure()

            # Get unique grades and sort them
            grades = sorted(df["grade_level"].unique())
            colors = px.colors.qualitative.Set3[: len(grades)]

            for i, grade in enumerate(grades):
                grade_df = df[df["grade_level"] == grade].sort_values("year")

                fig.add_trace(
                    go.Scatter(
                        x=grade_df["year"],
                        y=grade_df["enrollment_count"],
                        mode="lines",
                        name=grade,
                        stackgroup="one",
                        line=dict(width=0),
                        fillcolor=colors[i],
                        hovertemplate=f"<b>{grade}</b><br>Year: %{{x}}<br>Enrollment: %{{y:,}}<extra></extra>",
                    )
                )

            fig.update_layout(
                title="Grade Level Enrollment Trends (Stacked)",
                xaxis_title="Year",
                yaxis_title="Enrollment Count",
                height=500,
                plot_bgcolor="white",
                paper_bgcolor="white",
                hovermode="x unified",
            )

            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

            return fig

        except Exception as e:
            logger.error(f"Error creating grade level trends chart: {e}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")

    def create_transition_rates_chart(self, transition_data: List[Dict[str, Any]]) -> go.Figure:
        """Create grade transition rates chart."""
        if not transition_data:
            return self._create_empty_chart("No transition data available")

        try:
            df = pd.DataFrame(transition_data)

            fig = go.Figure()

            # Create waterfall-style chart
            fig.add_trace(
                go.Bar(
                    x=[f"{row['from_grade']} → {row['to_grade']}" for _, row in df.iterrows()],
                    y=df["transition_rate"],
                    name="Transition Rate",
                    marker=dict(
                        color=df["transition_rate"], colorscale="RdYlGn", showscale=True, colorbar=dict(title="Rate (%)")
                    ),
                    text=df["transition_rate"].round(1),
                    textposition="outside",
                    hovertemplate="<b>%{x}</b><br>Transition Rate: %{y:.1f}%<br>From: %{customdata[0]:,}<br>To: %{customdata[1]:,}<extra></extra>",
                    customdata=df[["current_enrollment", "next_enrollment"]],
                )
            )

            # Add reference line at 100%
            fig.add_hline(
                y=100, line_dash="dash", line_color="red", annotation_text="100% Transition", annotation_position="right"
            )

            fig.update_layout(
                title="Grade-to-Grade Transition Rates",
                xaxis_title="Grade Transition",
                yaxis_title="Transition Rate (%)",
                height=450,
                plot_bgcolor="white",
                paper_bgcolor="white",
                showlegend=False,
            )

            fig.update_xaxes(tickangle=45, showgrid=False)
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

            return fig

        except Exception as e:
            logger.error(f"Error creating transition rates chart: {e}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")

    def create_grade_distribution_chart(self, grade_data: List[Dict[str, Any]]) -> go.Figure:
        """Create grade level distribution pie chart."""
        if not grade_data:
            return self._create_empty_chart("No grade data available")

        try:
            df = pd.DataFrame(grade_data)

            # Get latest year data
            latest_year = df["year"].max()
            latest_data = df[df["year"] == latest_year]

            # Aggregate by grade level
            grade_totals = latest_data.groupby("grade_level")["enrollment_count"].sum().reset_index()

            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=grade_totals["grade_level"],
                        values=grade_totals["enrollment_count"],
                        hole=0.4,
                        textinfo="label+percent",
                        textposition="auto",
                        hovertemplate="<b>%{label}</b><br>Enrollment: %{value:,}<br>Percentage: %{percent}<extra></extra>",
                        marker=dict(colors=px.colors.qualitative.Set3, line=dict(color="#FFFFFF", width=2)),
                    )
                ]
            )

            fig.update_layout(
                title=f"Grade Level Distribution ({latest_year})",
                height=500,
                showlegend=True,
                legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.01),
            )

            return fig

        except Exception as e:
            logger.error(f"Error creating grade distribution chart: {e}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")

    def create_school_type_trends_chart(self, school_type_data: List[Dict[str, Any]]) -> go.Figure:
        """Create school type enrollment trends chart."""
        if not school_type_data:
            return self._create_empty_chart("No school type data available")

        try:
            df = pd.DataFrame(school_type_data)

            fig = go.Figure()

            # Add traces for each school type
            school_types = df["school_type"].unique()
            colors = px.colors.qualitative.Set1[: len(school_types)]

            for i, school_type in enumerate(school_types):
                type_df = df[df["school_type"] == school_type].sort_values("year")

                fig.add_trace(
                    go.Scatter(
                        x=type_df["year"],
                        y=type_df["enrollment_count"],
                        mode="lines+markers",
                        name=school_type,
                        line=dict(width=3, color=colors[i]),
                        marker=dict(size=8, color=colors[i]),
                        hovertemplate=f"<b>{school_type}</b><br>Year: %{{x}}<br>Enrollment: %{{y:,}}<br>Schools: %{{customdata}}<extra></extra>",
                        customdata=type_df["school_count"],
                    )
                )

            fig.update_layout(
                title="School Type Enrollment Trends",
                xaxis_title="Year",
                yaxis_title="Enrollment Count",
                height=500,
                plot_bgcolor="white",
                paper_bgcolor="white",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )

            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

            return fig

        except Exception as e:
            logger.error(f"Error creating school type trends chart: {e}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")

    def create_public_private_chart(self, public_private_data: List[Dict[str, Any]]) -> go.Figure:
        """Create public vs private enrollment chart."""
        if not public_private_data:
            return self._create_empty_chart("No public/private data available")

        try:
            df = pd.DataFrame(public_private_data)

            fig = go.Figure()

            # Add traces for public and private
            for category in ["Public", "Private"]:
                cat_df = df[df["category"] == category].sort_values("year")

                color = self.colors["primary"] if category == "Public" else self.colors["secondary"]

                fig.add_trace(
                    go.Scatter(
                        x=cat_df["year"],
                        y=cat_df["enrollment_count"],
                        mode="lines+markers",
                        name=f"{category} Schools",
                        line=dict(width=4, color=color),
                        marker=dict(size=10, color=color),
                        fill="tonexty" if category == "Private" else None,
                        hovertemplate=f"<b>{category} Schools</b><br>Year: %{{x}}<br>Enrollment: %{{y:,}}<br>Schools: %{{customdata}}<extra></extra>",
                        customdata=cat_df["school_count"],
                    )
                )

            fig.update_layout(
                title="Public vs Private School Enrollment",
                xaxis_title="Year",
                yaxis_title="Enrollment Count",
                height=450,
                plot_bgcolor="white",
                paper_bgcolor="white",
                hovermode="x unified",
            )

            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

            return fig

        except Exception as e:
            logger.error(f"Error creating public/private chart: {e}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")

    def create_school_type_market_share_chart(self, school_type_data: List[Dict[str, Any]]) -> go.Figure:
        """Create school type market share chart."""
        if not school_type_data:
            return self._create_empty_chart("No school type data available")

        try:
            df = pd.DataFrame(school_type_data)

            # Calculate market share over time
            market_share_data = []

            for year in df["year"].unique():
                year_data = df[df["year"] == year]
                total_enrollment = year_data["enrollment_count"].sum()

                for _, row in year_data.iterrows():
                    market_share = (row["enrollment_count"] / total_enrollment) * 100
                    market_share_data.append(
                        {
                            "year": year,
                            "school_type": row["school_type"],
                            "market_share": market_share,
                            "enrollment_count": row["enrollment_count"],
                        }
                    )

            share_df = pd.DataFrame(market_share_data)

            fig = go.Figure()

            # Create stacked bar chart
            school_types = share_df["school_type"].unique()
            colors = px.colors.qualitative.Set2[: len(school_types)]

            for i, school_type in enumerate(school_types):
                type_df = share_df[share_df["school_type"] == school_type].sort_values("year")

                fig.add_trace(
                    go.Bar(
                        x=type_df["year"],
                        y=type_df["market_share"],
                        name=school_type,
                        marker_color=colors[i],
                        hovertemplate=f"<b>{school_type}</b><br>Year: %{{x}}<br>Market Share: %{{y:.1f}}%<br>Enrollment: %{{customdata:,}}<extra></extra>",
                        customdata=type_df["enrollment_count"],
                    )
                )

            fig.update_layout(
                title="School Type Market Share Over Time",
                xaxis_title="Year",
                yaxis_title="Market Share (%)",
                height=450,
                plot_bgcolor="white",
                paper_bgcolor="white",
                barmode="stack",
                hovermode="x unified",
            )

            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

            return fig

        except Exception as e:
            logger.error(f"Error creating market share chart: {e}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")

    def create_volatility_chart(self, volatility_data: List[Dict[str, Any]]) -> go.Figure:
        """Create enrollment volatility chart."""
        if not volatility_data:
            return self._create_empty_chart("No volatility data available")

        try:
            df = pd.DataFrame(volatility_data)

            # Create subplot with secondary y-axis
            fig = make_subplots(specs=[[{"secondary_y": True}]], subplot_titles=("Enrollment Volatility Analysis",))

            # Add enrollment line
            fig.add_trace(
                go.Scatter(
                    x=df["period"],
                    y=df["enrollment_count"],
                    mode="lines",
                    name="Enrollment",
                    line=dict(color=self.colors["primary"], width=2),
                    hovertemplate="<b>%{x}</b><br>Enrollment: %{y:,}<extra></extra>",
                ),
                secondary_y=False,
            )

            # Add volatility line
            fig.add_trace(
                go.Scatter(
                    x=df["period"],
                    y=df["volatility"],
                    mode="lines+markers",
                    name="Volatility (%)",
                    line=dict(color=self.colors["danger"], width=2),
                    marker=dict(size=6, color=self.colors["danger"]),
                    hovertemplate="<b>%{x}</b><br>Volatility: %{y:.1f}%<extra></extra>",
                ),
                secondary_y=True,
            )

            # Update layout
            fig.update_xaxes(title_text="Period")
            fig.update_yaxes(title_text="Enrollment Count", secondary_y=False)
            fig.update_yaxes(title_text="Volatility (%)", secondary_y=True)

            fig.update_layout(height=400, hovermode="x unified", plot_bgcolor="white", paper_bgcolor="white")

            return fig

        except Exception as e:
            logger.error(f"Error creating volatility chart: {e}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")

    def create_growth_distribution_chart(self, growth_data: List[Dict[str, Any]]) -> go.Figure:
        """Create growth rate distribution histogram."""
        if not growth_data:
            return self._create_empty_chart("No growth distribution data available")

        try:
            df = pd.DataFrame(growth_data)

            fig = go.Figure()

            # Create histogram
            fig.add_trace(
                go.Bar(
                    x=df["bin_center"],
                    y=df["frequency"],
                    name="Frequency",
                    marker_color=self.colors["info"],
                    width=df["bin_end"] - df["bin_start"],
                    hovertemplate="<b>Growth Rate: %{x:.1f}%</b><br>Frequency: %{y}<br>Percentage: %{customdata:.1f}%<extra></extra>",
                    customdata=df["percentage"],
                )
            )

            fig.update_layout(
                title="Growth Rate Distribution",
                xaxis_title="Growth Rate (%)",
                yaxis_title="Frequency",
                height=400,
                plot_bgcolor="white",
                paper_bgcolor="white",
                showlegend=False,
            )

            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

            return fig

        except Exception as e:
            logger.error(f"Error creating growth distribution chart: {e}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")

    def create_forecast_chart(
        self, historical_data: List[Dict[str, Any]], forecast_data: Dict[str, Any], confidence_level: int
    ) -> go.Figure:
        """Create enrollment forecast chart."""
        if not historical_data or not forecast_data:
            return self._create_empty_chart("No forecast data available")

        try:
            hist_df = pd.DataFrame(historical_data)
            forecast_df = pd.DataFrame(forecast_data["forecast_data"])

            fig = go.Figure()

            # Add historical data
            fig.add_trace(
                go.Scatter(
                    x=hist_df["period"],
                    y=hist_df["enrollment_count"],
                    mode="lines+markers",
                    name="Historical Data",
                    line=dict(color=self.colors["primary"], width=3),
                    marker=dict(size=6, color=self.colors["primary"]),
                    hovertemplate="<b>%{x}</b><br>Actual: %{y:,}<extra></extra>",
                )
            )

            # Add forecast line
            fig.add_trace(
                go.Scatter(
                    x=forecast_df["period"],
                    y=forecast_df["forecast_value"],
                    mode="lines+markers",
                    name="Forecast",
                    line=dict(color=self.colors["secondary"], width=3, dash="dash"),
                    marker=dict(size=8, color=self.colors["secondary"]),
                    hovertemplate="<b>%{x}</b><br>Forecast: %{y:,}<extra></extra>",
                )
            )

            # Add confidence intervals
            fig.add_trace(
                go.Scatter(
                    x=forecast_df["period"],
                    y=forecast_df["upper_bound"],
                    mode="lines",
                    name=f"{confidence_level}% Confidence",
                    line=dict(width=0),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=forecast_df["period"],
                    y=forecast_df["lower_bound"],
                    mode="lines",
                    name=f"{confidence_level}% Confidence",
                    line=dict(width=0),
                    fill="tonexty",
                    fillcolor="rgba(255, 127, 14, 0.2)",
                    hovertemplate="<b>%{x}</b><br>Lower Bound: %{y:,}<extra></extra>",
                )
            )

            # Add vertical line to separate historical and forecast
            if len(hist_df) > 0:
                last_historical_period = hist_df["period"].iloc[-1]
                fig.add_vline(
                    x=last_historical_period,
                    line_dash="dot",
                    line_color="gray",
                    annotation_text="Forecast Start",
                    annotation_position="top",
                )

            fig.update_layout(
                title=f"Enrollment Forecast ({forecast_data.get('method', 'Unknown Method')})",
                xaxis_title="Period",
                yaxis_title="Enrollment Count",
                height=500,
                plot_bgcolor="white",
                paper_bgcolor="white",
                hovermode="x unified",
            )

            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

            return fig

        except Exception as e:
            logger.error(f"Error creating forecast chart: {e}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")

    def create_scenario_chart(self, scenario_data: List[Dict[str, Any]]) -> go.Figure:
        """Create scenario analysis chart."""
        if not scenario_data:
            return self._create_empty_chart("No scenario data available")

        try:
            df = pd.DataFrame(scenario_data)

            fig = go.Figure()

            # Add scenario lines
            scenarios = ["optimistic", "realistic", "pessimistic"]
            colors = [self.colors["success"], self.colors["primary"], self.colors["danger"]]
            line_styles = ["solid", "dash", "dot"]

            for i, scenario in enumerate(scenarios):
                fig.add_trace(
                    go.Scatter(
                        x=df["period"],
                        y=df[scenario],
                        mode="lines+markers",
                        name=f"{scenario.title()} Scenario",
                        line=dict(color=colors[i], width=3, dash=line_styles[i]),
                        marker=dict(size=8, color=colors[i]),
                        hovertemplate=f"<b>{scenario.title()}</b><br>Period: %{{x}}<br>Enrollment: %{{y:,}}<extra></extra>",
                    )
                )

            # Fill area between optimistic and pessimistic
            fig.add_trace(
                go.Scatter(
                    x=df["period"], y=df["optimistic"], mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=df["period"],
                    y=df["pessimistic"],
                    mode="lines",
                    line=dict(width=0),
                    fill="tonexty",
                    fillcolor="rgba(128, 128, 128, 0.1)",
                    name="Scenario Range",
                    hoverinfo="skip",
                )
            )

            fig.update_layout(
                title="Enrollment Forecast Scenarios",
                xaxis_title="Period",
                yaxis_title="Enrollment Count",
                height=450,
                plot_bgcolor="white",
                paper_bgcolor="white",
                hovermode="x unified",
            )

            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

            return fig

        except Exception as e:
            logger.error(f"Error creating scenario chart: {e}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")

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
            height=400,
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False),
        )

        return fig


# Create a global instance
enrollment_viz_service = EnrollmentVisualizationService()
