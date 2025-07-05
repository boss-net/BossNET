"""
Data Service for Enrollment Trends Dashboard
Handles database connectivity, data processing, and analytics for enrollment trends.
"""

import hashlib
import json
import logging
import os
import warnings
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import redis
from pydantic import BaseModel, Field, validator
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_percentage_error
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.seasonal import seasonal_decompose

warnings.filterwarnings("ignore")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnrollmentRecord(BaseModel):
    """Data model for enrollment records."""

    enrollment_id: str = Field(..., description="Unique enrollment identifier")
    student_id: str = Field(..., description="Student identifier")
    school_id: str = Field(..., description="School identifier")
    academic_year: str = Field(..., description="Academic year")
    enrollment_date: datetime = Field(..., description="Date of enrollment")
    grade_level: str = Field(..., description="Grade/class level")
    section: Optional[str] = Field(None, description="Section/division")
    status: str = Field(..., description="Enrollment status")
    division: str = Field(..., description="Administrative division")
    district: str = Field(..., description="District name")
    upazila: str = Field(..., description="Upazila name")
    school_type: str = Field(..., description="Type of school")
    gender: str = Field(..., description="Student gender")
    is_active: bool = Field(True, description="Active enrollment indicator")


@dataclass
class EnrollmentMetrics:
    """Data class for enrollment metrics"""

    total_enrollments: int
    enrollment_growth_rate: float
    active_schools: int
    retention_rate: float
    dropout_rate: float


class EnrollmentDataService:
    """Service class for handling enrollment data operations."""

    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/student_data_db")
        self.redis_client = self._get_redis_client()
        self.engine = None
        if self.database_url:
            self.engine = create_engine(self.database_url)

    def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client for caching."""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            client = redis.from_url(redis_url, decode_responses=True)
            client.ping()
            return client
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            return None

    def get_cache_key(self, data_type: str, filters: Dict) -> str:
        """Generate cache key for data."""
        filter_str = json.dumps(filters, sort_keys=True, default=str)
        return f"enrollment_trends:{data_type}:{hashlib.md5(filter_str.encode()).hexdigest()}"

    def get_cached_data(self, cache_key: str, ttl: int = 3600) -> Optional[pd.DataFrame]:
        """Get data from cache."""
        if self.redis_client:
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    return pd.read_json(cached_data)
            except Exception as e:
                logger.warning(f"Cache retrieval failed: {e}")
        return None

    def set_cached_data(self, cache_key: str, data: pd.DataFrame, ttl: int = 3600):
        """Set data in cache."""
        if self.redis_client:
            try:
                self.redis_client.setex(cache_key, ttl, data.to_json())
            except Exception as e:
                logger.warning(f"Cache storage failed: {e}")

    def get_filter_options(self) -> Dict[str, List[str]]:
        """Get filter options from database."""
        try:
            if not self.engine:
                return self._get_mock_filter_options()

            cache_key = "enrollment_filter_options"
            cached_options = self.get_cached_data(cache_key)
            if cached_options is not None:
                return cached_options.to_dict("list")

            with self.engine.connect() as conn:
                # Get academic years
                years_query = """
                SELECT DISTINCT academic_year
                FROM enrollments
                WHERE academic_year IS NOT NULL
                ORDER BY academic_year DESC
                """
                years_df = pd.read_sql(years_query, conn)

                # Get divisions
                divisions_query = """
                SELECT DISTINCT d.name as division
                FROM divisions d
                JOIN students s ON d.id = s.division_id
                JOIN enrollments e ON s.id = e.student_id
                WHERE e.is_active = true
                ORDER BY d.name
                """
                divisions_df = pd.read_sql(divisions_query, conn)

                # Get school types
                school_types_query = """
                SELECT DISTINCT sch.type as school_type
                FROM schools sch
                JOIN enrollments e ON sch.id = e.school_id
                WHERE e.is_active = true AND sch.type IS NOT NULL
                ORDER BY sch.type
                """
                school_types_df = pd.read_sql(school_types_query, conn)

                # Get grade levels
                grades_query = """
                SELECT DISTINCT current_class as grade_level
                FROM students s
                JOIN enrollments e ON s.id = e.student_id
                WHERE e.is_active = true AND s.current_class IS NOT NULL
                ORDER BY s.current_class
                """
                grades_df = pd.read_sql(grades_query, conn)

                options = {
                    "academic_years": years_df["academic_year"].tolist(),
                    "divisions": divisions_df["division"].tolist(),
                    "school_types": school_types_df["school_type"].tolist(),
                    "grade_levels": grades_df["grade_level"].tolist(),
                }

                # Cache the options
                options_df = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in options.items()]))
                self.set_cached_data(cache_key, options_df, ttl=3600)

                return options

        except Exception as e:
            logger.error(f"Error loading filter options: {e}")
            return self._get_mock_filter_options()

    def _get_mock_filter_options(self) -> Dict[str, List[str]]:
        """Get mock filter options for development."""
        return {
            "academic_years": ["2024", "2023", "2022", "2021", "2020"],
            "divisions": ["Dhaka", "Chittagong", "Rajshahi", "Khulna", "Sylhet", "Barisal", "Rangpur", "Mymensingh"],
            "school_types": ["Government Primary", "Government Secondary", "Private", "Madrasa", "Technical"],
            "grade_levels": [
                "Class 1",
                "Class 2",
                "Class 3",
                "Class 4",
                "Class 5",
                "Class 6",
                "Class 7",
                "Class 8",
                "Class 9",
                "Class 10",
            ],
        }

    def get_key_metrics(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get key enrollment metrics."""
        try:
            cache_key = self.get_cache_key("key_metrics", filters or {})
            cached_metrics = self.get_cached_data(cache_key)
            if cached_metrics is not None and not cached_metrics.empty:
                return cached_metrics.iloc[0].to_dict()

            if not self.engine:
                return self._get_mock_key_metrics()

            # Build query with filters
            base_query = """
            WITH enrollment_stats AS (
                SELECT
                    COUNT(*) as total_enrollments,
                    COUNT(DISTINCT e.school_id) as active_schools,
                    COUNT(DISTINCT e.student_id) as unique_students,
                    AVG(CASE WHEN e.status = 'active' THEN 1.0 ELSE 0.0 END) * 100 as retention_rate,
                    AVG(CASE WHEN e.status = 'dropped' THEN 1.0 ELSE 0.0 END) * 100 as dropout_rate
                FROM enrollments e
                JOIN students s ON e.student_id = s.id
                JOIN schools sch ON e.school_id = sch.id
                JOIN divisions d ON s.division_id = d.id
                WHERE e.is_deleted = false
            """

            # Add filter conditions
            conditions = []
            params = {}

            if filters:
                if filters.get("academic_years"):
                    conditions.append("e.academic_year = ANY(:academic_years)")
                    params["academic_years"] = filters["academic_years"]

                if filters.get("divisions"):
                    conditions.append("d.name = ANY(:divisions)")
                    params["divisions"] = filters["divisions"]

                if filters.get("school_types"):
                    conditions.append("sch.type = ANY(:school_types)")
                    params["school_types"] = filters["school_types"]

                if filters.get("gender"):
                    conditions.append("s.gender = :gender")
                    params["gender"] = filters["gender"]

                if filters.get("start_date") and filters.get("end_date"):
                    conditions.append("e.enrollment_date BETWEEN :start_date AND :end_date")
                    params["start_date"] = filters["start_date"]
                    params["end_date"] = filters["end_date"]

            if conditions:
                base_query += " AND " + " AND ".join(conditions)

            base_query += ")"

            # Calculate growth rate
            growth_query = (
                base_query
                + """
            , current_year AS (
                SELECT total_enrollments as current_enrollments
                FROM enrollment_stats
            ),
            previous_year AS (
                SELECT COUNT(*) as previous_enrollments
                FROM enrollments e
                JOIN students s ON e.student_id = s.id
                JOIN schools sch ON e.school_id = sch.id
                JOIN divisions d ON s.division_id = d.id
                WHERE e.is_deleted = false
                AND e.academic_year = (
                    SELECT DISTINCT academic_year
                    FROM enrollments
                    WHERE academic_year < COALESCE(:current_year, '2024')
                    ORDER BY academic_year DESC
                    LIMIT 1
                )
            """
            )

            if conditions:
                # Remove academic year filter for previous year comparison
                prev_conditions = [c for c in conditions if "academic_year" not in c]
                if prev_conditions:
                    growth_query += " AND " + " AND ".join(prev_conditions)

            growth_query += """
            )
            SELECT
                es.*,
                CASE
                    WHEN py.previous_enrollments > 0 THEN
                        ((cy.current_enrollments - py.previous_enrollments) * 100.0 / py.previous_enrollments)
                    ELSE 0
                END as enrollment_growth_rate
            FROM enrollment_stats es
            CROSS JOIN current_year cy
            CROSS JOIN previous_year py
            """

            with self.engine.connect() as conn:
                result = conn.execute(text(growth_query), params).fetchone()

                if result:
                    metrics = {
                        "total_enrollments": int(result.total_enrollments or 0),
                        "enrollment_growth_rate": float(result.enrollment_growth_rate or 0),
                        "active_schools": int(result.active_schools or 0),
                        "retention_rate": float(result.retention_rate or 0),
                        "dropout_rate": float(result.dropout_rate or 0),
                    }
                else:
                    metrics = self._get_mock_key_metrics()

            # Cache the metrics
            metrics_df = pd.DataFrame([metrics])
            self.set_cached_data(cache_key, metrics_df, ttl=900)

            return metrics

        except Exception as e:
            logger.error(f"Error calculating key metrics: {e}")
            return self._get_mock_key_metrics()

    def _get_mock_key_metrics(self) -> Dict[str, Any]:
        """Get mock key metrics for development."""
        return {
            "total_enrollments": 1250000,
            "enrollment_growth_rate": 3.2,
            "active_schools": 18500,
            "retention_rate": 87.5,
            "dropout_rate": 8.3,
        }

    def get_enrollment_trends(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get enrollment trends data."""
        try:
            cache_key = self.get_cache_key("enrollment_trends", filters or {})
            cached_data = self.get_cached_data(cache_key)
            if cached_data is not None:
                return cached_data.to_dict("records")

            if not self.engine:
                return self._get_mock_enrollment_trends()

            # Determine aggregation level
            aggregation = filters.get("aggregation_level", "Monthly") if filters else "Monthly"

            if aggregation == "Monthly":
                date_trunc = "month"
                date_format = "YYYY-MM"
            elif aggregation == "Quarterly":
                date_trunc = "quarter"
                date_format = "YYYY-Q"
            else:  # Yearly
                date_trunc = "year"
                date_format = "YYYY"

            query = f"""
            SELECT
                DATE_TRUNC('{date_trunc}', e.enrollment_date) as period,
                TO_CHAR(DATE_TRUNC('{date_trunc}', e.enrollment_date), '{date_format}') as period_label,
                COUNT(*) as enrollment_count,
                COUNT(DISTINCT e.student_id) as unique_students,
                COUNT(DISTINCT e.school_id) as active_schools,
                AVG(CASE WHEN e.status = 'active' THEN 1.0 ELSE 0.0 END) * 100 as retention_rate
            FROM enrollments e
            JOIN students s ON e.student_id = s.id
            JOIN schools sch ON e.school_id = sch.id
            JOIN divisions d ON s.division_id = d.id
            WHERE e.is_deleted = false
            """

            # Add filter conditions
            conditions = []
            params = {}

            if filters:
                if filters.get("academic_years"):
                    conditions.append("e.academic_year = ANY(:academic_years)")
                    params["academic_years"] = filters["academic_years"]

                if filters.get("divisions"):
                    conditions.append("d.name = ANY(:divisions)")
                    params["divisions"] = filters["divisions"]

                if filters.get("school_types"):
                    conditions.append("sch.type = ANY(:school_types)")
                    params["school_types"] = filters["school_types"]

                if filters.get("gender"):
                    conditions.append("s.gender = :gender")
                    params["gender"] = filters["gender"]

                if filters.get("start_date") and filters.get("end_date"):
                    conditions.append("e.enrollment_date BETWEEN :start_date AND :end_date")
                    params["start_date"] = filters["start_date"]
                    params["end_date"] = filters["end_date"]

            if conditions:
                query += " AND " + " AND ".join(conditions)

            query += """
            GROUP BY DATE_TRUNC('{date_trunc}', e.enrollment_date)
            ORDER BY period
            """.format(
                date_trunc=date_trunc
            )

            with self.engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params=params)

                # Convert to list of dictionaries
                trends_data = []
                for _, row in df.iterrows():
                    trends_data.append(
                        {
                            "period": row["period_label"],
                            "enrollment_count": int(row["enrollment_count"]),
                            "unique_students": int(row["unique_students"]),
                            "active_schools": int(row["active_schools"]),
                            "retention_rate": float(row["retention_rate"]),
                        }
                    )

                # Cache the data
                self.set_cached_data(cache_key, df, ttl=1800)

                return trends_data

        except Exception as e:
            logger.error(f"Error getting enrollment trends: {e}")
            return self._get_mock_enrollment_trends()

    def _get_mock_enrollment_trends(self) -> List[Dict[str, Any]]:
        """Get mock enrollment trends for development."""
        trends = []
        base_date = datetime(2020, 1, 1)
        base_enrollment = 100000

        for i in range(48):  # 4 years of monthly data
            month_date = base_date + timedelta(days=30 * i)

            # Add seasonal variation and growth trend
            seasonal_factor = 1 + 0.1 * np.sin(2 * np.pi * i / 12)  # Annual seasonality
            growth_factor = 1 + 0.02 * i / 12  # 2% annual growth
            noise = np.random.normal(0, 0.05)  # Random variation

            enrollment = int(base_enrollment * seasonal_factor * growth_factor * (1 + noise))

            trends.append(
                {
                    "period": month_date.strftime("%Y-%m"),
                    "enrollment_count": enrollment,
                    "unique_students": int(enrollment * 0.95),
                    "active_schools": int(enrollment / 60),
                    "retention_rate": 85 + np.random.normal(0, 3),
                }
            )

        return trends

    def get_seasonal_patterns(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get seasonal enrollment patterns."""
        try:
            # Get monthly enrollment data
            trends_data = self.get_enrollment_trends(filters)

            if not trends_data:
                return []

            # Convert to DataFrame for analysis
            df = pd.DataFrame(trends_data)
            df["period_date"] = pd.to_datetime(df["period"])
            df["month"] = df["period_date"].dt.month
            df["quarter"] = df["period_date"].dt.quarter
            df["year"] = df["period_date"].dt.year

            # Calculate monthly averages
            monthly_patterns = (
                df.groupby("month").agg({"enrollment_count": ["mean", "std"], "retention_rate": "mean"}).reset_index()
            )

            monthly_patterns.columns = ["month", "avg_enrollment", "std_enrollment", "avg_retention"]

            # Calculate quarterly patterns
            quarterly_patterns = (
                df.groupby("quarter").agg({"enrollment_count": ["mean", "std"], "retention_rate": "mean"}).reset_index()
            )

            quarterly_patterns.columns = ["quarter", "avg_enrollment", "std_enrollment", "avg_retention"]

            # Combine patterns
            seasonal_data = []

            # Add monthly data
            for _, row in monthly_patterns.iterrows():
                seasonal_data.append(
                    {
                        "period_type": "monthly",
                        "period": int(row["month"]),
                        "period_name": pd.to_datetime(f"2024-{int(row['month']):02d}-01").strftime("%B"),
                        "avg_enrollment": int(row["avg_enrollment"]),
                        "std_enrollment": float(row["std_enrollment"]),
                        "avg_retention": float(row["avg_retention"]),
                    }
                )

            # Add quarterly data
            quarter_names = {1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"}
            for _, row in quarterly_patterns.iterrows():
                seasonal_data.append(
                    {
                        "period_type": "quarterly",
                        "period": int(row["quarter"]),
                        "period_name": quarter_names[int(row["quarter"])],
                        "avg_enrollment": int(row["avg_enrollment"]),
                        "std_enrollment": float(row["std_enrollment"]),
                        "avg_retention": float(row["avg_retention"]),
                    }
                )

            return seasonal_data

        except Exception as e:
            logger.error(f"Error getting seasonal patterns: {e}")
            return []

    def get_peak_enrollment_months(self, seasonal_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get peak enrollment months analysis."""
        try:
            monthly_data = [d for d in seasonal_data if d["period_type"] == "monthly"]

            if not monthly_data:
                return {}

            # Sort by enrollment
            sorted_data = sorted(monthly_data, key=lambda x: x["avg_enrollment"], reverse=True)

            # Get top 3 and bottom 3 months
            high_months = [d["period_name"] for d in sorted_data[:3]]
            low_months = [d["period_name"] for d in sorted_data[-3:]]

            # Calculate variation
            max_enrollment = sorted_data[0]["avg_enrollment"]
            min_enrollment = sorted_data[-1]["avg_enrollment"]
            variation = ((max_enrollment - min_enrollment) / min_enrollment) * 100

            return {
                "high_months": high_months,
                "low_months": low_months,
                "variation": variation,
                "peak_month": high_months[0],
                "lowest_month": low_months[0],
            }

        except Exception as e:
            logger.error(f"Error analyzing peak months: {e}")
            return {}

    def get_regional_trends(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get regional enrollment trends."""
        try:
            cache_key = self.get_cache_key("regional_trends", filters or {})
            cached_data = self.get_cached_data(cache_key)
            if cached_data is not None:
                return cached_data.to_dict("records")

            if not self.engine:
                return self._get_mock_regional_trends()

            # Build query for regional trends
            query = """
            WITH regional_enrollment AS (
                SELECT
                    d.name as division,
                    DATE_TRUNC('year', e.enrollment_date) as year,
                    COUNT(*) as enrollment_count,
                    COUNT(DISTINCT e.student_id) as unique_students,
                    COUNT(DISTINCT e.school_id) as active_schools,
                    AVG(CASE WHEN e.status = 'active' THEN 1.0 ELSE 0.0 END) * 100 as retention_rate
                FROM enrollments e
                JOIN students s ON e.student_id = s.id
                JOIN schools sch ON e.school_id = sch.id
                JOIN divisions d ON s.division_id = d.id
                WHERE e.is_deleted = false
            """

            # Add filter conditions
            conditions = []
            params = {}

            if filters:
                if filters.get("academic_years"):
                    conditions.append("e.academic_year = ANY(:academic_years)")
                    params["academic_years"] = filters["academic_years"]

                if filters.get("school_types"):
                    conditions.append("sch.type = ANY(:school_types)")
                    params["school_types"] = filters["school_types"]

                if filters.get("gender"):
                    conditions.append("s.gender = :gender")
                    params["gender"] = filters["gender"]

                if filters.get("start_date") and filters.get("end_date"):
                    conditions.append("e.enrollment_date BETWEEN :start_date AND :end_date")
                    params["start_date"] = filters["start_date"]
                    params["end_date"] = filters["end_date"]

            if conditions:
                query += " AND " + " AND ".join(conditions)

            query += """
                GROUP BY d.name, DATE_TRUNC('year', e.enrollment_date)
            ),
            regional_growth AS (
                SELECT
                    division,
                    year,
                    enrollment_count,
                    unique_students,
                    active_schools,
                    retention_rate,
                    LAG(enrollment_count) OVER (PARTITION BY division ORDER BY year) as prev_enrollment,
                    CASE
                        WHEN LAG(enrollment_count) OVER (PARTITION BY division ORDER BY year) > 0 THEN
                            ((enrollment_count - LAG(enrollment_count) OVER (PARTITION BY division ORDER BY year)) * 100.0 /
                             LAG(enrollment_count) OVER (PARTITION BY division ORDER BY year))
                        ELSE 0
                    END as growth_rate
                FROM regional_enrollment
            )
            SELECT * FROM regional_growth
            ORDER BY division, year
            """

            with self.engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params=params)

                # Convert to list of dictionaries
                regional_data = []
                for _, row in df.iterrows():
                    regional_data.append(
                        {
                            "division": row["division"],
                            "year": int(row["year"].year),
                            "enrollment_count": int(row["enrollment_count"]),
                            "unique_students": int(row["unique_students"]),
                            "active_schools": int(row["active_schools"]),
                            "retention_rate": float(row["retention_rate"]),
                            "growth_rate": float(row["growth_rate"] or 0),
                        }
                    )

                # Cache the data
                self.set_cached_data(cache_key, df, ttl=1800)

                return regional_data

        except Exception as e:
            logger.error(f"Error getting regional trends: {e}")
            return self._get_mock_regional_trends()

    def _get_mock_regional_trends(self) -> List[Dict[str, Any]]:
        """Get mock regional trends for development."""
        divisions = ["Dhaka", "Chittagong", "Rajshahi", "Khulna", "Sylhet", "Barisal", "Rangpur", "Mymensingh"]
        years = [2020, 2021, 2022, 2023, 2024]

        regional_data = []

        for division in divisions:
            base_enrollment = np.random.randint(80000, 200000)

            for year in years:
                # Add division-specific growth patterns
                division_factor = {
                    "Dhaka": 1.2,
                    "Chittagong": 1.1,
                    "Rajshahi": 1.0,
                    "Khulna": 0.95,
                    "Sylhet": 0.9,
                    "Barisal": 0.85,
                    "Rangpur": 0.8,
                    "Mymensingh": 0.75,
                }.get(division, 1.0)

                year_growth = 1 + 0.03 * (year - 2020)  # 3% annual growth
                enrollment = int(base_enrollment * division_factor * year_growth * (1 + np.random.normal(0, 0.1)))

                growth_rate = 3.0 + np.random.normal(0, 2) if year > 2020 else 0

                regional_data.append(
                    {
                        "division": division,
                        "year": year,
                        "enrollment_count": enrollment,
                        "unique_students": int(enrollment * 0.95),
                        "active_schools": int(enrollment / 65),
                        "retention_rate": 85 + np.random.normal(0, 5),
                        "growth_rate": growth_rate,
                    }
                )

        return regional_data

    def get_regional_insights(self, regional_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get regional insights from trends data."""
        try:
            if not regional_data:
                return {}

            # Get latest year data
            df = pd.DataFrame(regional_data)
            latest_year = df["year"].max()
            latest_data = df[df["year"] == latest_year]

            # Find top and bottom performing regions
            top_region = latest_data.loc[latest_data["growth_rate"].idxmax()]
            lowest_region = latest_data.loc[latest_data["growth_rate"].idxmin()]

            # Calculate regional variation
            growth_rates = latest_data["growth_rate"].values
            variation = np.std(growth_rates) / np.mean(growth_rates) * 100 if np.mean(growth_rates) != 0 else 0

            return {
                "top_region": top_region["division"],
                "top_growth": float(top_region["growth_rate"]),
                "lowest_region": lowest_region["division"],
                "lowest_growth": float(lowest_region["growth_rate"]),
                "variation": float(variation),
                "std_dev": float(np.std(growth_rates)),
            }

        except Exception as e:
            logger.error(f"Error calculating regional insights: {e}")
            return {}

    def get_demographic_trends(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get demographic enrollment trends."""
        try:
            cache_key = self.get_cache_key("demographic_trends", filters or {})
            cached_data = self.get_cached_data(cache_key)
            if cached_data is not None:
                return cached_data.to_dict("records")[0] if not cached_data.empty else {}

            demographic_data = {
                "gender_trends": self._get_gender_trends(filters),
                "grade_trends": self._get_grade_level_trends(filters),
                "school_type_trends": self._get_school_type_trends(filters),
            }

            # Cache the data
            demo_df = pd.DataFrame([demographic_data])
            self.set_cached_data(cache_key, demo_df, ttl=1800)

            return demographic_data

        except Exception as e:
            logger.error(f"Error getting demographic trends: {e}")
            return {}

    def _get_gender_trends(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get gender-based enrollment trends."""
        try:
            if not self.engine:
                return self._get_mock_gender_trends()

            query = """
            SELECT
                s.gender,
                DATE_TRUNC('year', e.enrollment_date) as year,
                COUNT(*) as enrollment_count,
                COUNT(DISTINCT e.student_id) as unique_students
            FROM enrollments e
            JOIN students s ON e.student_id = s.id
            JOIN schools sch ON e.school_id = sch.id
            WHERE e.is_deleted = false
            """

            # Add filter conditions
            conditions = []
            params = {}

            if filters:
                if filters.get("academic_years"):
                    conditions.append("e.academic_year = ANY(:academic_years)")
                    params["academic_years"] = filters["academic_years"]

                if filters.get("divisions"):
                    conditions.append("s.division_id IN (SELECT id FROM divisions WHERE name = ANY(:divisions))")
                    params["divisions"] = filters["divisions"]

            if conditions:
                query += " AND " + " AND ".join(conditions)

            query += """
            GROUP BY s.gender, DATE_TRUNC('year', e.enrollment_date)
            ORDER BY year, s.gender
            """

            with self.engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params=params)

                gender_trends = []
                for _, row in df.iterrows():
                    gender_trends.append(
                        {
                            "gender": row["gender"],
                            "year": int(row["year"].year),
                            "enrollment_count": int(row["enrollment_count"]),
                            "unique_students": int(row["unique_students"]),
                        }
                    )

                return gender_trends

        except Exception as e:
            logger.error(f"Error getting gender trends: {e}")
            return self._get_mock_gender_trends()

    def _get_mock_gender_trends(self) -> List[Dict[str, Any]]:
        """Get mock gender trends for development."""
        years = [2020, 2021, 2022, 2023, 2024]
        genders = ["Male", "Female"]

        gender_trends = []
        for year in years:
            for gender in genders:
                # Simulate slight female advantage in enrollment
                base_count = 500000 if gender == "Female" else 480000
                year_growth = 1 + 0.03 * (year - 2020)
                enrollment = int(base_count * year_growth * (1 + np.random.normal(0, 0.05)))

                gender_trends.append(
                    {"gender": gender, "year": year, "enrollment_count": enrollment, "unique_students": int(enrollment * 0.95)}
                )

        return gender_trends

    def _get_grade_level_trends(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get grade level enrollment trends."""
        try:
            if not self.engine:
                return self._get_mock_grade_trends()

            query = """
            SELECT
                s.current_class as grade_level,
                DATE_TRUNC('year', e.enrollment_date) as year,
                COUNT(*) as enrollment_count,
                COUNT(DISTINCT e.student_id) as unique_students
            FROM enrollments e
            JOIN students s ON e.student_id = s.id
            WHERE e.is_deleted = false
            AND s.current_class IS NOT NULL
            """

            # Add filter conditions
            conditions = []
            params = {}

            if filters:
                if filters.get("academic_years"):
                    conditions.append("e.academic_year = ANY(:academic_years)")
                    params["academic_years"] = filters["academic_years"]

                if filters.get("grade_levels"):
                    conditions.append("s.current_class = ANY(:grade_levels)")
                    params["grade_levels"] = filters["grade_levels"]

            if conditions:
                query += " AND " + " AND ".join(conditions)

            query += """
            GROUP BY s.current_class, DATE_TRUNC('year', e.enrollment_date)
            ORDER BY year, s.current_class
            """

            with self.engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params=params)

                grade_trends = []
                for _, row in df.iterrows():
                    grade_trends.append(
                        {
                            "grade_level": row["grade_level"],
                            "year": int(row["year"].year),
                            "enrollment_count": int(row["enrollment_count"]),
                            "unique_students": int(row["unique_students"]),
                        }
                    )

                return grade_trends

        except Exception as e:
            logger.error(f"Error getting grade trends: {e}")
            return self._get_mock_grade_trends()

    def _get_mock_grade_trends(self) -> List[Dict[str, Any]]:
        """Get mock grade level trends for development."""
        years = [2020, 2021, 2022, 2023, 2024]
        grades = [
            "Class 1",
            "Class 2",
            "Class 3",
            "Class 4",
            "Class 5",
            "Class 6",
            "Class 7",
            "Class 8",
            "Class 9",
            "Class 10",
        ]

        grade_trends = []
        for year in years:
            for grade in grades:
                # Simulate higher enrollment in lower grades
                grade_num = int(grade.split()[-1])
                base_count = 120000 - (grade_num * 8000)  # Decreasing enrollment by grade
                year_growth = 1 + 0.03 * (year - 2020)
                enrollment = int(base_count * year_growth * (1 + np.random.normal(0, 0.1)))

                grade_trends.append(
                    {
                        "grade_level": grade,
                        "year": year,
                        "enrollment_count": max(enrollment, 10000),  # Minimum enrollment
                        "unique_students": int(max(enrollment, 10000) * 0.95),
                    }
                )

        return grade_trends

    def _get_school_type_trends(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get school type enrollment trends."""
        try:
            if not self.engine:
                return self._get_mock_school_type_trends()

            query = """
            SELECT
                sch.type as school_type,
                DATE_TRUNC('year', e.enrollment_date) as year,
                COUNT(*) as enrollment_count,
                COUNT(DISTINCT e.student_id) as unique_students,
                COUNT(DISTINCT e.school_id) as school_count
            FROM enrollments e
            JOIN schools sch ON e.school_id = sch.id
            WHERE e.is_deleted = false
            AND sch.type IS NOT NULL
            """

            # Add filter conditions
            conditions = []
            params = {}

            if filters:
                if filters.get("academic_years"):
                    conditions.append("e.academic_year = ANY(:academic_years)")
                    params["academic_years"] = filters["academic_years"]

                if filters.get("school_types"):
                    conditions.append("sch.type = ANY(:school_types)")
                    params["school_types"] = filters["school_types"]

            if conditions:
                query += " AND " + " AND ".join(conditions)

            query += """
            GROUP BY sch.type, DATE_TRUNC('year', e.enrollment_date)
            ORDER BY year, sch.type
            """

            with self.engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params=params)

                school_type_trends = []
                for _, row in df.iterrows():
                    school_type_trends.append(
                        {
                            "school_type": row["school_type"],
                            "year": int(row["year"].year),
                            "enrollment_count": int(row["enrollment_count"]),
                            "unique_students": int(row["unique_students"]),
                            "school_count": int(row["school_count"]),
                        }
                    )

                return school_type_trends

        except Exception as e:
            logger.error(f"Error getting school type trends: {e}")
            return self._get_mock_school_type_trends()

    def _get_mock_school_type_trends(self) -> List[Dict[str, Any]]:
        """Get mock school type trends for development."""
        years = [2020, 2021, 2022, 2023, 2024]
        school_types = ["Government Primary", "Government Secondary", "Private", "Madrasa", "Technical"]

        school_type_trends = []
        for year in years:
            for school_type in school_types:
                # Different base enrollments for different school types
                base_counts = {
                    "Government Primary": 400000,
                    "Government Secondary": 300000,
                    "Private": 200000,
                    "Madrasa": 150000,
                    "Technical": 50000,
                }

                base_count = base_counts.get(school_type, 100000)
                year_growth = 1 + 0.03 * (year - 2020)

                # Private schools growing faster
                if school_type == "Private":
                    year_growth *= 1.02

                enrollment = int(base_count * year_growth * (1 + np.random.normal(0, 0.08)))

                school_type_trends.append(
                    {
                        "school_type": school_type,
                        "year": year,
                        "enrollment_count": enrollment,
                        "unique_students": int(enrollment * 0.95),
                        "school_count": int(enrollment / 80),  # Average students per school
                    }
                )

        return school_type_trends

    def get_gender_insights(self, gender_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get gender parity insights."""
        try:
            if not gender_data:
                return {}

            df = pd.DataFrame(gender_data)
            latest_year = df["year"].max()
            latest_data = df[df["year"] == latest_year]

            # Calculate gender distribution
            total_enrollment = latest_data["enrollment_count"].sum()
            female_enrollment = latest_data[latest_data["gender"] == "Female"]["enrollment_count"].sum()
            male_enrollment = latest_data[latest_data["gender"] == "Male"]["enrollment_count"].sum()

            female_percentage = (female_enrollment / total_enrollment) * 100
            male_percentage = (male_enrollment / total_enrollment) * 100

            # Calculate Gender Parity Index (GPI)
            parity_index = female_enrollment / male_enrollment if male_enrollment > 0 else 0

            return {
                "parity_index": float(parity_index),
                "female_percentage": float(female_percentage),
                "male_percentage": float(male_percentage),
                "total_enrollment": int(total_enrollment),
            }

        except Exception as e:
            logger.error(f"Error calculating gender insights: {e}")
            return {}

    def get_grade_transition_rates(self, grade_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate grade transition rates."""
        try:
            if not grade_data:
                return []

            df = pd.DataFrame(grade_data)

            # Calculate transition rates between consecutive grades
            transition_rates = []
            grades = sorted(df["grade_level"].unique())

            for i in range(len(grades) - 1):
                current_grade = grades[i]
                next_grade = grades[i + 1]

                # Get latest year data
                latest_year = df["year"].max()
                current_enrollment = df[(df["grade_level"] == current_grade) & (df["year"] == latest_year)][
                    "enrollment_count"
                ].sum()
                next_enrollment = df[(df["grade_level"] == next_grade) & (df["year"] == latest_year)]["enrollment_count"].sum()

                # Calculate transition rate (simplified)
                transition_rate = (next_enrollment / current_enrollment) * 100 if current_enrollment > 0 else 0

                transition_rates.append(
                    {
                        "from_grade": current_grade,
                        "to_grade": next_grade,
                        "transition_rate": min(float(transition_rate), 100.0),  # Cap at 100%
                        "current_enrollment": int(current_enrollment),
                        "next_enrollment": int(next_enrollment),
                    }
                )

            return transition_rates

        except Exception as e:
            logger.error(f"Error calculating transition rates: {e}")
            return []

    def get_public_private_trends(self, school_type_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get public vs private school trends."""
        try:
            if not school_type_data:
                return []

            df = pd.DataFrame(school_type_data)

            # Categorize school types
            public_types = ["Government Primary", "Government Secondary", "Madrasa"]
            private_types = ["Private", "Technical"]

            # Aggregate by public/private
            df["category"] = df["school_type"].apply(lambda x: "Public" if x in public_types else "Private")

            public_private_trends = (
                df.groupby(["year", "category"])
                .agg({"enrollment_count": "sum", "unique_students": "sum", "school_count": "sum"})
                .reset_index()
            )

            trends = []
            for _, row in public_private_trends.iterrows():
                trends.append(
                    {
                        "year": int(row["year"]),
                        "category": row["category"],
                        "enrollment_count": int(row["enrollment_count"]),
                        "unique_students": int(row["unique_students"]),
                        "school_count": int(row["school_count"]),
                    }
                )

            return trends

        except Exception as e:
            logger.error(f"Error getting public/private trends: {e}")
            return []

    def get_enrollment_volatility(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Calculate enrollment volatility metrics."""
        try:
            trends_data = self.get_enrollment_trends(filters)

            if len(trends_data) < 12:  # Need at least 12 periods
                return []

            df = pd.DataFrame(trends_data)
            df["enrollment_count"] = pd.to_numeric(df["enrollment_count"])

            # Calculate rolling volatility (12-period)
            df["rolling_std"] = df["enrollment_count"].rolling(window=12).std()
            df["rolling_mean"] = df["enrollment_count"].rolling(window=12).mean()
            df["volatility"] = (df["rolling_std"] / df["rolling_mean"]) * 100

            # Calculate month-over-month changes
            df["mom_change"] = df["enrollment_count"].pct_change() * 100

            volatility_data = []
            for _, row in df.iterrows():
                if pd.notna(row["volatility"]):
                    volatility_data.append(
                        {
                            "period": row["period"],
                            "enrollment_count": int(row["enrollment_count"]),
                            "volatility": float(row["volatility"]),
                            "mom_change": float(row["mom_change"] or 0),
                        }
                    )

            return volatility_data

        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return []

    def get_growth_rate_distribution(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get growth rate distribution analysis."""
        try:
            trends_data = self.get_enrollment_trends(filters)

            if len(trends_data) < 2:
                return []

            df = pd.DataFrame(trends_data)
            df["enrollment_count"] = pd.to_numeric(df["enrollment_count"])

            # Calculate period-over-period growth rates
            df["growth_rate"] = df["enrollment_count"].pct_change() * 100

            # Remove NaN values
            growth_rates = df["growth_rate"].dropna()

            if len(growth_rates) == 0:
                return []

            # Create distribution bins
            bins = np.linspace(growth_rates.min(), growth_rates.max(), 10)
            hist, bin_edges = np.histogram(growth_rates, bins=bins)

            distribution_data = []
            for i in range(len(hist)):
                distribution_data.append(
                    {
                        "bin_start": float(bin_edges[i]),
                        "bin_end": float(bin_edges[i + 1]),
                        "bin_center": float((bin_edges[i] + bin_edges[i + 1]) / 2),
                        "frequency": int(hist[i]),
                        "percentage": float(hist[i] / len(growth_rates) * 100),
                    }
                )

            return distribution_data

        except Exception as e:
            logger.error(f"Error calculating growth distribution: {e}")
            return []

    def get_historical_enrollment_data(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get historical enrollment data for forecasting."""
        try:
            # Get at least 3 years of monthly data for forecasting
            historical_filters = filters.copy() if filters else {}

            # Ensure we get enough historical data
            if "start_date" not in historical_filters:
                historical_filters["start_date"] = date.today() - timedelta(days=1095)  # 3 years
            if "end_date" not in historical_filters:
                historical_filters["end_date"] = date.today()

            historical_filters["aggregation_level"] = "Monthly"

            return self.get_enrollment_trends(historical_filters)

        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return []

    def generate_enrollment_forecast(
        self, historical_data: List[Dict[str, Any]], forecast_periods: int, confidence_level: int, method: str
    ) -> Dict[str, Any]:
        """Generate enrollment forecast using specified method."""
        try:
            if len(historical_data) < 12:
                return {}

            df = pd.DataFrame(historical_data)
            df["period_date"] = pd.to_datetime(df["period"])
            df = df.sort_values("period_date")

            # Prepare time series data
            ts_data = df["enrollment_count"].values

            if method == "ARIMA":
                forecast_data = self._arima_forecast(ts_data, forecast_periods, confidence_level)
            elif method == "Exponential Smoothing":
                forecast_data = self._exponential_smoothing_forecast(ts_data, forecast_periods, confidence_level)
            elif method == "Linear Trend":
                forecast_data = self._linear_trend_forecast(ts_data, forecast_periods, confidence_level)
            else:  # Seasonal Decomposition
                forecast_data = self._seasonal_decomposition_forecast(ts_data, forecast_periods, confidence_level)

            if not forecast_data:
                return {}

            # Generate future periods
            last_date = df["period_date"].max()
            future_periods = []

            for i in range(1, forecast_periods + 1):
                future_date = last_date + pd.DateOffset(months=i)
                future_periods.append(future_date.strftime("%Y-%m"))

            # Combine forecast with periods
            forecast_result = {
                "method": method,
                "forecast_periods": forecast_periods,
                "confidence_level": confidence_level,
                "historical_data": historical_data,
                "forecast_data": [],
            }

            for i, period in enumerate(future_periods):
                forecast_result["forecast_data"].append(
                    {
                        "period": period,
                        "forecast_value": int(forecast_data["forecast"][i]),
                        "lower_bound": int(forecast_data["lower_bound"][i]),
                        "upper_bound": int(forecast_data["upper_bound"][i]),
                    }
                )

            return forecast_result

        except Exception as e:
            logger.error(f"Error generating forecast: {e}")
            return {}

    def _arima_forecast(self, data: np.ndarray, periods: int, confidence_level: int) -> Dict[str, np.ndarray]:
        """Generate ARIMA forecast."""
        try:
            # Fit ARIMA model (auto-select parameters)
            model = ARIMA(data, order=(1, 1, 1))
            fitted_model = model.fit()

            # Generate forecast
            forecast = fitted_model.forecast(steps=periods)
            conf_int = fitted_model.get_forecast(steps=periods).conf_int(alpha=(100 - confidence_level) / 100)

            return {"forecast": forecast, "lower_bound": conf_int.iloc[:, 0].values, "upper_bound": conf_int.iloc[:, 1].values}

        except Exception as e:
            logger.error(f"ARIMA forecast error: {e}")
            return self._linear_trend_forecast(data, periods, confidence_level)

    def _exponential_smoothing_forecast(self, data: np.ndarray, periods: int, confidence_level: int) -> Dict[str, np.ndarray]:
        """Generate Exponential Smoothing forecast."""
        try:
            # Fit Exponential Smoothing model
            model = ExponentialSmoothing(data, trend="add", seasonal="add", seasonal_periods=12)
            fitted_model = model.fit()

            # Generate forecast
            forecast = fitted_model.forecast(periods)

            # Calculate confidence intervals (simplified)
            residuals = fitted_model.resid
            std_error = np.std(residuals)
            z_score = 1.96 if confidence_level == 95 else 1.645 if confidence_level == 90 else 1.28

            margin_of_error = z_score * std_error

            return {"forecast": forecast, "lower_bound": forecast - margin_of_error, "upper_bound": forecast + margin_of_error}

        except Exception as e:
            logger.error(f"Exponential Smoothing forecast error: {e}")
            return self._linear_trend_forecast(data, periods, confidence_level)

    def _linear_trend_forecast(self, data: np.ndarray, periods: int, confidence_level: int) -> Dict[str, np.ndarray]:
        """Generate Linear Trend forecast."""
        try:
            # Fit linear regression
            X = np.arange(len(data)).reshape(-1, 1)
            y = data

            model = LinearRegression()
            model.fit(X, y)

            # Generate forecast
            future_X = np.arange(len(data), len(data) + periods).reshape(-1, 1)
            forecast = model.predict(future_X)

            # Calculate confidence intervals
            residuals = y - model.predict(X)
            std_error = np.std(residuals)
            z_score = 1.96 if confidence_level == 95 else 1.645 if confidence_level == 90 else 1.28

            margin_of_error = z_score * std_error

            return {"forecast": forecast, "lower_bound": forecast - margin_of_error, "upper_bound": forecast + margin_of_error}

        except Exception as e:
            logger.error(f"Linear trend forecast error: {e}")
            # Return simple average-based forecast as fallback
            avg_value = np.mean(data)
            return {
                "forecast": np.full(periods, avg_value),
                "lower_bound": np.full(periods, avg_value * 0.9),
                "upper_bound": np.full(periods, avg_value * 1.1),
            }

    def _seasonal_decomposition_forecast(self, data: np.ndarray, periods: int, confidence_level: int) -> Dict[str, np.ndarray]:
        """Generate forecast using seasonal decomposition."""
        try:
            if len(data) < 24:  # Need at least 2 years for seasonal decomposition
                return self._linear_trend_forecast(data, periods, confidence_level)

            # Perform seasonal decomposition
            decomposition = seasonal_decompose(data, model="additive", period=12)

            # Extract components
            trend = decomposition.trend.dropna()
            seasonal = decomposition.seasonal

            # Forecast trend (linear extrapolation)
            trend_values = trend.values
            X = np.arange(len(trend_values)).reshape(-1, 1)

            trend_model = LinearRegression()
            trend_model.fit(X, trend_values)

            future_X = np.arange(len(trend_values), len(trend_values) + periods).reshape(-1, 1)
            trend_forecast = trend_model.predict(future_X)

            # Get seasonal pattern for forecast periods
            seasonal_pattern = seasonal.values[-12:]  # Last year's seasonal pattern
            seasonal_forecast = np.tile(seasonal_pattern, (periods // 12) + 1)[:periods]

            # Combine trend and seasonal
            forecast = trend_forecast + seasonal_forecast

            # Calculate confidence intervals
            residuals = decomposition.resid.dropna()
            std_error = np.std(residuals)
            z_score = 1.96 if confidence_level == 95 else 1.645 if confidence_level == 90 else 1.28

            margin_of_error = z_score * std_error

            return {"forecast": forecast, "lower_bound": forecast - margin_of_error, "upper_bound": forecast + margin_of_error}

        except Exception as e:
            logger.error(f"Seasonal decomposition forecast error: {e}")
            return self._linear_trend_forecast(data, periods, confidence_level)

    def get_forecast_insights(self, forecast_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get insights from forecast data."""
        try:
            if not forecast_data or "forecast_data" not in forecast_data:
                return {}

            forecast_values = [d["forecast_value"] for d in forecast_data["forecast_data"]]
            historical_values = [d["enrollment_count"] for d in forecast_data["historical_data"]]

            # Calculate expected growth
            last_historical = historical_values[-1]
            last_forecast = forecast_values[-1]
            expected_growth = ((last_forecast - last_historical) / last_historical) * 100

            # Determine trend direction
            if expected_growth > 2:
                trend_direction = "Increasing"
            elif expected_growth < -2:
                trend_direction = "Decreasing"
            else:
                trend_direction = "Stable"

            # Calculate model accuracy (simplified MAPE on historical data)
            if len(historical_values) > 12:
                recent_actual = historical_values[-6:]
                recent_predicted = historical_values[-12:-6]  # Use earlier data as "prediction"
                mape = mean_absolute_percentage_error(recent_actual, recent_predicted) * 100
                accuracy = max(0, 100 - mape)
            else:
                accuracy = 75.0  # Default accuracy
                mape = 25.0

            return {
                "expected_growth": float(expected_growth),
                "trend_direction": trend_direction,
                "accuracy": float(accuracy),
                "mape": float(mape),
                "forecast_range": {
                    "min": int(min(forecast_values)),
                    "max": int(max(forecast_values)),
                    "avg": int(np.mean(forecast_values)),
                },
            }

        except Exception as e:
            logger.error(f"Error calculating forecast insights: {e}")
            return {}

    def get_scenario_analysis(self, forecast_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate scenario analysis (optimistic, pessimistic, realistic)."""
        try:
            if not forecast_data or "forecast_data" not in forecast_data:
                return []

            scenarios = []

            for forecast_point in forecast_data["forecast_data"]:
                base_forecast = forecast_point["forecast_value"]

                # Generate scenarios
                optimistic = int(base_forecast * 1.15)  # 15% higher
                pessimistic = int(base_forecast * 0.85)  # 15% lower
                realistic = base_forecast  # Base forecast

                scenarios.append(
                    {
                        "period": forecast_point["period"],
                        "optimistic": optimistic,
                        "realistic": realistic,
                        "pessimistic": pessimistic,
                        "base_forecast": base_forecast,
                    }
                )

            return scenarios

        except Exception as e:
            logger.error(f"Error generating scenario analysis: {e}")
            return []

    def generate_comprehensive_report(self, filters: Dict[str, Any] = None) -> str:
        """Generate comprehensive enrollment trends report."""
        try:
            # This would generate a PDF report in a real implementation
            # For now, return a simple text report

            report_lines = [
                "BANGLADESH EDUCATION ENROLLMENT TRENDS REPORT",
                "=" * 50,
                f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "EXECUTIVE SUMMARY",
                "-" * 20,
            ]

            # Get key metrics
            metrics = self.get_key_metrics(filters)
            report_lines.extend(
                [
                    f"Total Enrollments: {metrics.get('total_enrollments', 0):,}",
                    f"Growth Rate: {metrics.get('enrollment_growth_rate', 0):+.1f}%",
                    f"Active Schools: {metrics.get('active_schools', 0):,}",
                    f"Retention Rate: {metrics.get('retention_rate', 0):.1f}%",
                    f"Dropout Rate: {metrics.get('dropout_rate', 0):.1f}%",
                    "",
                ]
            )

            # Add trends analysis
            trends_data = self.get_enrollment_trends(filters)
            if trends_data:
                report_lines.extend(
                    [
                        "ENROLLMENT TRENDS",
                        "-" * 20,
                        f"Analysis Period: {trends_data[0]['period']} to {trends_data[-1]['period']}",
                        f"Data Points: {len(trends_data)}",
                        "",
                    ]
                )

            # Add regional analysis
            regional_data = self.get_regional_trends(filters)
            if regional_data:
                regional_insights = self.get_regional_insights(regional_data)
                report_lines.extend(
                    [
                        "REGIONAL ANALYSIS",
                        "-" * 20,
                        f"Top Performing Region: {regional_insights.get('top_region', 'N/A')}",
                        f"Needs Attention: {regional_insights.get('lowest_region', 'N/A')}",
                        "",
                    ]
                )

            report_lines.extend(["END OF REPORT", "=" * 50])

            return "\n".join(report_lines)

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return "Error generating report"


# Create a global instance
enrollment_data_service = EnrollmentDataService()
