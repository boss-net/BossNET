"""
Data Service for Student Performance Dashboard
Handles database connectivity, caching, and data validation.
"""

import asyncio
import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import asyncpg
import pandas as pd
import redis
from pydantic import BaseModel, Field, validator
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StudentPerformanceData(BaseModel):
    """Data model for student performance records."""

    student_id: str = Field(..., description="Unique student identifier")
    student_name: str = Field(..., description="Full name of the student")
    school_name: str = Field(..., description="Name of the school")
    division: str = Field(..., description="Administrative division")
    district: str = Field(..., description="District name")
    upazila: str = Field(..., description="Upazila/Sub-district name")
    gender: str = Field(..., description="Student gender")
    age_group: str = Field(..., description="Age group category")
    socioeconomic_status: Optional[str] = Field(None, description="Socioeconomic status")
    has_disability: bool = Field(False, description="Disability indicator")
    academic_year: str = Field(..., description="Academic year")
    term: str = Field(..., description="Academic term")
    subject_name: str = Field(..., description="Subject name")
    assessment_type: str = Field(..., description="Type of assessment")
    marks_obtained: float = Field(..., ge=0, description="Marks obtained")
    max_marks: float = Field(..., gt=0, description="Maximum possible marks")
    percentage: float = Field(..., ge=0, le=100, description="Percentage score")
    grade_letter: str = Field(..., description="Letter grade")
    is_passed: bool = Field(..., description="Pass/fail indicator")
    assessment_date: datetime = Field(..., description="Date of assessment")

    @validator("percentage")
    def validate_percentage(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Percentage must be between 0 and 100")
        return v

    @validator("gender")
    def validate_gender(cls, v):
        valid_genders = ["Male", "Female", "Other", "Unknown"]
        if v not in valid_genders:
            raise ValueError(f"Gender must be one of {valid_genders}")
        return v


class DashboardFilters(BaseModel):
    """Model for dashboard filters."""

    academic_year: Optional[str] = None
    term: Optional[str] = None
    division: Optional[str] = None
    district: Optional[str] = None
    upazila: Optional[str] = None
    school_name: Optional[str] = None
    subject_name: Optional[str] = None
    gender: Optional[str] = None
    age_group: Optional[str] = None
    socioeconomic_status: Optional[str] = None
    has_disability: Optional[bool] = None
    min_percentage: float = Field(0, ge=0, le=100)
    max_percentage: float = Field(100, ge=0, le=100)
    assessment_type: Optional[str] = None


@dataclass
class PerformanceMetrics:
    """Data class for performance metrics"""

    total_students: int
    avg_performance: float
    attendance_rate: float
    total_schools: int


class DataService:
    """Service class for handling data operations."""

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
            # Test connection
            client.ping()
            return client
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            return None

    def get_cache_key(self, data_type: str, filters: Dict) -> str:
        """Generate cache key for data."""
        filter_str = json.dumps(filters, sort_keys=True, default=str)
        return f"student_performance:{data_type}:{hashlib.md5(filter_str.encode()).hexdigest()}"

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

    def load_performance_data(self, filters: Dict = None) -> pd.DataFrame:
        """Load student performance data from the database."""
        try:
            if not self.engine:
                logger.error("Database engine not initialized")
                return pd.DataFrame()

            # Check cache first
            cache_key = self.get_cache_key("performance_data", filters or {})
            cached_df = self.get_cached_data(cache_key)
            if cached_df is not None:
                logger.info("Returning cached performance data")
                return cached_df

            # Build dynamic query based on filters
            query = """
            WITH performance_data AS (
                SELECT
                    -- Student information
                    s.id as student_id,
                    s.student_id as student_code,
                    s.first_name || ' ' || s.last_name as student_name,
                    s.gender,
                    s.current_class,
                    s.status,
                    EXTRACT(YEAR FROM AGE(s.date_of_birth)) as age,
                    CASE
                        WHEN EXTRACT(YEAR FROM AGE(s.date_of_birth)) < 6 THEN 'Under 6'
                        WHEN EXTRACT(YEAR FROM AGE(s.date_of_birth)) BETWEEN 6 AND 8 THEN '6-8'
                        WHEN EXTRACT(YEAR FROM AGE(s.date_of_birth)) BETWEEN 9 AND 11 THEN '9-11'
                        WHEN EXTRACT(YEAR FROM AGE(s.date_of_birth)) BETWEEN 12 AND 14 THEN '12-14'
                        WHEN EXTRACT(YEAR FROM AGE(s.date_of_birth)) BETWEEN 15 AND 17 THEN '15-17'
                        ELSE '18+'
                    END as age_group,

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
                    e.enrollment_date,
                    e.final_percentage,
                    e.final_grade,
                    e.final_result,

                    -- Assessment information
                    ar.marks_obtained,
                    ar.total_marks,
                    ar.percentage as assessment_percentage,
                    ar.letter_grade,
                    ar.is_pass,
                    ar.rank_in_class,
                    ar.rank_in_school,
                    ar.created_at as assessment_date,

                    -- Subject information
                    sub.name as subject_name,
                    sub.category as subject_category,

                    -- Assessment details
                    a.name as assessment_name,
                    a.type as assessment_type,
                    a.term,
                    a.scheduled_date

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
                AND s.status = 'active'
                AND (e.is_deleted = false OR e.id IS NULL)
                AND (sch.is_deleted = false OR sch.id IS NULL)
            )
            SELECT * FROM performance_data
            WHERE student_id IS NOT NULL
            """

            # Add filter conditions
            conditions = []
            params = {}

            if filters:
                if filters.get("academic_year"):
                    conditions.append("academic_year = :academic_year")
                    params["academic_year"] = filters["academic_year"]

                if filters.get("term"):
                    conditions.append("term = :term")
                    params["term"] = filters["term"]

                if filters.get("division") and filters["division"] != "all":
                    conditions.append("division = :division")
                    params["division"] = filters["division"]

                if filters.get("district"):
                    conditions.append("district = :district")
                    params["district"] = filters["district"]

                if filters.get("upazila"):
                    conditions.append("upazila = :upazila")
                    params["upazila"] = filters["upazila"]

                if filters.get("school_name"):
                    conditions.append("school_name ILIKE :school_name")
                    params["school_name"] = f"%{filters['school_name']}%"

                if filters.get("subject_name"):
                    conditions.append("subject_name ILIKE :subject_name")
                    params["subject_name"] = f"%{filters['subject_name']}%"

                if filters.get("gender"):
                    conditions.append("gender = :gender")
                    params["gender"] = filters["gender"]

                if filters.get("age_group"):
                    conditions.append("age_group = :age_group")
                    params["age_group"] = filters["age_group"]

                if filters.get("assessment_type"):
                    conditions.append("assessment_type = :assessment_type")
                    params["assessment_type"] = filters["assessment_type"]

                if filters.get("grade") and filters["grade"] != "all":
                    conditions.append("current_class = :current_class")
                    params["current_class"] = f"Class {filters['grade']}"

                if filters.get("school_type") and filters["school_type"] != "all":
                    conditions.append("school_type = :school_type")
                    params["school_type"] = filters["school_type"]

            if conditions:
                query += " AND " + " AND ".join(conditions)

            query += " ORDER BY assessment_date DESC, student_name LIMIT 10000"

            # Execute query
            with self.engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params=params)

            # Cache the results
            self.set_cached_data(cache_key, df, ttl=1800)  # Cache for 30 minutes

            logger.info(f"Loaded {len(df)} performance records from database")
            return df

        except SQLAlchemyError as e:
            logger.error(f"Database error: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Data loading error: {e}")
            return pd.DataFrame()

    def get_filter_options(self) -> Dict[str, List[str]]:
        """Get filter options from database."""
        try:
            if not self.engine:
                return {}

            # Check cache first
            cache_key = "filter_options"
            cached_options = self.get_cached_data(cache_key)
            if cached_options is not None:
                return cached_options.to_dict("list")

            with self.engine.connect() as conn:
                # Get academic years
                years_query = """
                SELECT DISTINCT academic_year
                FROM enrollments
                WHERE is_active = true AND academic_year IS NOT NULL
                ORDER BY academic_year DESC
                """
                years_df = pd.read_sql(years_query, conn)

                # Get divisions
                divisions_query = """
                SELECT DISTINCT d.name as division
                FROM divisions d
                JOIN students s ON d.id = s.division_id
                WHERE s.is_deleted = false AND s.status = 'active'
                ORDER BY d.name
                """
                divisions_df = pd.read_sql(divisions_query, conn)

                # Get subjects
                subjects_query = """
                SELECT DISTINCT sub.name as subject_name
                FROM subjects sub
                JOIN assessment_results ar ON sub.id = ar.subject_id
                WHERE sub.name IS NOT NULL
                ORDER BY sub.name
                """
                subjects_df = pd.read_sql(subjects_query, conn)

                # Get school types
                school_types_query = """
                SELECT DISTINCT type as school_type
                FROM schools
                WHERE is_deleted = false AND type IS NOT NULL
                ORDER BY type
                """
                school_types_df = pd.read_sql(school_types_query, conn)

                options = {
                    "academic_years": years_df["academic_year"].tolist(),
                    "divisions": divisions_df["division"].tolist(),
                    "subjects": subjects_df["subject_name"].tolist(),
                    "school_types": school_types_df["school_type"].tolist(),
                }

                # Cache the options
                options_df = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in options.items()]))
                self.set_cached_data(cache_key, options_df, ttl=3600)  # Cache for 1 hour

                return options

        except Exception as e:
            logger.error(f"Error loading filter options: {e}")
            return {}

    def get_key_metrics(self, filters: Dict = None) -> Dict[str, Any]:
        """Get key performance metrics"""
        try:
            # Check cache first
            cache_key = self.get_cache_key("key_metrics", filters or {})
            cached_metrics = self.get_cached_data(cache_key)
            if cached_metrics is not None and not cached_metrics.empty:
                return cached_metrics.iloc[0].to_dict()

            df = self.load_performance_data(filters)

            if df.empty:
                metrics = {
                    "total_students": 0,
                    "avg_performance": 0,
                    "pass_rate": 0,
                    "total_schools": 0,
                    "total_assessments": 0,
                }
            else:
                # Calculate metrics
                total_students = df["student_id"].nunique()
                avg_performance = df["assessment_percentage"].mean() if "assessment_percentage" in df.columns else 0
                pass_rate = (df["is_pass"].sum() / len(df) * 100) if "is_pass" in df.columns and len(df) > 0 else 0
                total_schools = df["school_name"].nunique() if "school_name" in df.columns else 0
                total_assessments = df["assessment_name"].nunique() if "assessment_name" in df.columns else 0

                metrics = {
                    "total_students": total_students,
                    "avg_performance": round(avg_performance, 1),
                    "pass_rate": round(pass_rate, 1),
                    "total_schools": total_schools,
                    "total_assessments": total_assessments,
                }

            # Cache the metrics
            metrics_df = pd.DataFrame([metrics])
            self.set_cached_data(cache_key, metrics_df, ttl=900)  # Cache for 15 minutes

            return metrics

        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {"total_students": 0, "avg_performance": 0, "pass_rate": 0, "total_schools": 0, "total_assessments": 0}


# Create a global instance
data_service = DataService()
