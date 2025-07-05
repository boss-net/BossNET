"""
Performance tracking and analytics models.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class PerformanceMetricType(str, Enum):
    """Performance metric type enumeration."""

    ACADEMIC = "academic"
    ATTENDANCE = "attendance"
    BEHAVIOR = "behavior"
    PARTICIPATION = "participation"
    ASSIGNMENT = "assignment"
    EXAM = "exam"


class TrendDirection(str, Enum):
    """Trend direction enumeration."""

    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    FLUCTUATING = "fluctuating"


class StudentPerformanceModel(Base):
    """Student performance tracking model."""

    __tablename__ = "student_performances"

    # Relationships
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)

    # Time Period
    academic_year = Column(String(20), nullable=False)
    term = Column(String(20), nullable=True)
    month = Column(Integer, nullable=True)  # 1-12
    week = Column(Integer, nullable=True)  # Week of year

    # Performance Metrics
    overall_percentage = Column(Numeric(5, 2), nullable=True)
    overall_grade = Column(String(5), nullable=True)
    overall_gpa = Column(Numeric(3, 2), nullable=True)

    # Subject-specific Performance
    subject_percentage = Column(Numeric(5, 2), nullable=True)
    subject_grade = Column(String(5), nullable=True)
    subject_gpa = Column(Numeric(3, 2), nullable=True)

    # Attendance Metrics
    attendance_percentage = Column(Numeric(5, 2), nullable=True)
    total_days = Column(Integer, nullable=True)
    present_days = Column(Integer, nullable=True)
    absent_days = Column(Integer, nullable=True)

    # Assignment and Homework
    assignments_completed = Column(Integer, default=0, nullable=False)
    assignments_total = Column(Integer, default=0, nullable=False)
    assignment_completion_rate = Column(Numeric(5, 2), nullable=True)

    # Behavioral Metrics
    discipline_score = Column(Numeric(3, 2), nullable=True)  # Out of 5
    participation_score = Column(Numeric(3, 2), nullable=True)  # Out of 5

    # Rankings
    class_rank = Column(Integer, nullable=True)
    school_rank = Column(Integer, nullable=True)
    district_rank = Column(Integer, nullable=True)

    # Trend Analysis
    trend_direction = Column(String(20), nullable=True)
    improvement_rate = Column(Numeric(5, 2), nullable=True)  # Percentage change

    # Predictions
    predicted_final_grade = Column(String(5), nullable=True)
    risk_level = Column(String(20), nullable=True)  # low, medium, high

    # Additional Metrics
    extra_curricular_score = Column(Numeric(3, 2), nullable=True)
    leadership_score = Column(Numeric(3, 2), nullable=True)

    # Metadata
    metrics_data = Column(JSON, nullable=True)  # Additional performance data
    notes = Column(Text, nullable=True)

    # Relationships
    student = relationship("StudentModel", back_populates="performance_records")
    enrollment = relationship("EnrollmentModel", backref="performance_records")
    subject = relationship("SubjectModel", backref="performance_records")

    # Indexes
    __table_args__ = (
        Index("ix_student_performance_student_year", "student_id", "academic_year"),
        Index("ix_student_performance_enrollment_term", "enrollment_id", "term"),
        Index("ix_student_performance_subject_year", "subject_id", "academic_year"),
        Index("ix_student_performance_rankings", "class_rank", "school_rank"),
    )

    @property
    def attendance_rate(self) -> Optional[float]:
        """Calculate attendance rate."""
        if self.total_days and self.total_days > 0:
            return (self.present_days / self.total_days) * 100
        return None

    @property
    def assignment_completion_percentage(self) -> Optional[float]:
        """Calculate assignment completion percentage."""
        if self.assignments_total and self.assignments_total > 0:
            return (self.assignments_completed / self.assignments_total) * 100
        return None

    def __repr__(self) -> str:
        return f"<StudentPerformance(student_id={self.student_id}, year='{self.academic_year}', grade='{self.overall_grade}')>"


class SchoolPerformanceModel(Base):
    """School performance tracking model."""

    __tablename__ = "school_performances"

    # Relationships
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)

    # Time Period
    academic_year = Column(String(20), nullable=False)
    term = Column(String(20), nullable=True)

    # Overall Performance
    overall_pass_rate = Column(Numeric(5, 2), nullable=True)
    overall_attendance_rate = Column(Numeric(5, 2), nullable=True)
    average_grade = Column(String(5), nullable=True)
    average_gpa = Column(Numeric(3, 2), nullable=True)

    # Student Metrics
    total_students = Column(Integer, nullable=False)
    students_passed = Column(Integer, nullable=True)
    students_failed = Column(Integer, nullable=True)
    dropout_count = Column(Integer, default=0, nullable=False)

    # Grade Distribution
    grade_a_plus_count = Column(Integer, default=0, nullable=False)
    grade_a_count = Column(Integer, default=0, nullable=False)
    grade_b_count = Column(Integer, default=0, nullable=False)
    grade_c_count = Column(Integer, default=0, nullable=False)
    grade_d_count = Column(Integer, default=0, nullable=False)
    grade_f_count = Column(Integer, default=0, nullable=False)

    # Subject-wise Performance
    subject_performances = Column(JSON, nullable=True)  # Subject-wise statistics

    # Teacher Performance
    total_teachers = Column(Integer, nullable=False)
    teacher_student_ratio = Column(Numeric(5, 2), nullable=True)

    # Infrastructure Utilization
    classroom_utilization = Column(Numeric(5, 2), nullable=True)

    # Rankings and Comparisons
    district_rank = Column(Integer, nullable=True)
    division_rank = Column(Integer, nullable=True)
    national_rank = Column(Integer, nullable=True)

    # Improvement Metrics
    improvement_from_previous_year = Column(Numeric(5, 2), nullable=True)
    trend_direction = Column(String(20), nullable=True)

    # Additional Metrics
    extracurricular_participation = Column(Numeric(5, 2), nullable=True)
    parent_satisfaction_score = Column(Numeric(3, 2), nullable=True)

    # Metadata
    performance_data = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    school = relationship("SchoolModel", back_populates="performance_records")

    # Indexes
    __table_args__ = (
        Index("ix_school_performance_school_year", "school_id", "academic_year"),
        Index("ix_school_performance_rankings", "district_rank", "division_rank"),
        Index("ix_school_performance_pass_rate", "overall_pass_rate"),
        UniqueConstraint("school_id", "academic_year", "term", name="uq_school_performance_year_term"),
    )

    @property
    def pass_percentage(self) -> Optional[float]:
        """Calculate pass percentage."""
        if self.total_students > 0 and self.students_passed is not None:
            return (self.students_passed / self.total_students) * 100
        return None

    @property
    def dropout_rate(self) -> Optional[float]:
        """Calculate dropout rate."""
        if self.total_students > 0:
            return (self.dropout_count / self.total_students) * 100
        return None

    def __repr__(self) -> str:
        return f"<SchoolPerformance(school_id={self.school_id}, year='{self.academic_year}', pass_rate={self.overall_pass_rate}%)>"


class PerformanceMetricModel(Base):
    """Generic performance metric model for flexible tracking."""

    __tablename__ = "performance_metrics"

    # Entity References (flexible - can reference student, school, teacher, etc.)
    entity_type = Column(String(50), nullable=False)  # student, school, teacher, class
    entity_id = Column(Integer, nullable=False)

    # Metric Information
    metric_name = Column(String(100), nullable=False)
    metric_type = Column(String(30), nullable=False)  # PerformanceMetricType
    metric_category = Column(String(50), nullable=True)

    # Time Period
    academic_year = Column(String(20), nullable=False)
    term = Column(String(20), nullable=True)
    date_recorded = Column(Date, nullable=False)

    # Metric Values
    numeric_value = Column(Numeric(10, 4), nullable=True)
    text_value = Column(String(255), nullable=True)
    json_value = Column(JSON, nullable=True)

    # Context
    unit = Column(String(20), nullable=True)  # percentage, points, count, etc.
    max_value = Column(Numeric(10, 4), nullable=True)
    min_value = Column(Numeric(10, 4), nullable=True)

    # Comparison and Benchmarking
    benchmark_value = Column(Numeric(10, 4), nullable=True)
    percentile = Column(Integer, nullable=True)  # 1-100

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Metadata
    source = Column(String(100), nullable=True)  # Where this metric came from
    calculation_method = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Indexes
    __table_args__ = (
        Index("ix_performance_metrics_entity", "entity_type", "entity_id"),
        Index("ix_performance_metrics_name_year", "metric_name", "academic_year"),
        Index("ix_performance_metrics_type_date", "metric_type", "date_recorded"),
        Index("ix_performance_metrics_value", "numeric_value"),
    )

    @property
    def percentage_of_max(self) -> Optional[float]:
        """Calculate percentage of maximum value."""
        if self.numeric_value is not None and self.max_value and self.max_value > 0:
            return (float(self.numeric_value) / float(self.max_value)) * 100
        return None

    @property
    def performance_level(self) -> str:
        """Determine performance level based on percentile."""
        if self.percentile is None:
            return "Unknown"
        elif self.percentile >= 90:
            return "Excellent"
        elif self.percentile >= 75:
            return "Good"
        elif self.percentile >= 50:
            return "Average"
        elif self.percentile >= 25:
            return "Below Average"
        else:
            return "Poor"

    def __repr__(self) -> str:
        return f"<PerformanceMetric(entity={self.entity_type}:{self.entity_id}, metric='{self.metric_name}', value={self.numeric_value})>"
