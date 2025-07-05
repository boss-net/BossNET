"""
Academic-related models for enrollment, attendance, assessments, etc.
"""

from datetime import date, datetime, time
from enum import Enum
from typing import List, Optional

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
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class EnrollmentStatus(str, Enum):
    """Enrollment status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    COMPLETED = "completed"
    TRANSFERRED = "transferred"
    DROPPED = "dropped"
    SUSPENDED = "suspended"


class AttendanceStatus(str, Enum):
    """Attendance status enumeration."""

    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"
    SICK = "sick"
    HOLIDAY = "holiday"


class AssessmentType(str, Enum):
    """Assessment type enumeration."""

    EXAM = "exam"
    QUIZ = "quiz"
    ASSIGNMENT = "assignment"
    PROJECT = "project"
    PRACTICAL = "practical"
    ORAL = "oral"
    CONTINUOUS = "continuous"


class GradeSystem(str, Enum):
    """Grade system enumeration."""

    PERCENTAGE = "percentage"
    GPA = "gpa"
    LETTER = "letter"
    PASS_FAIL = "pass_fail"


class SubjectModel(Base):
    """Subject model for academic subjects."""

    __tablename__ = "subjects"

    # Basic Information
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    name_bn = Column(String(100), nullable=True)

    # Classification
    category = Column(String(50), nullable=True)  # core, elective, optional
    type = Column(String(30), nullable=True)  # theory, practical, both

    # Academic Information
    credit_hours = Column(Integer, default=1, nullable=False)
    total_marks = Column(Integer, default=100, nullable=False)
    pass_marks = Column(Integer, default=40, nullable=False)

    # Applicable Levels
    applicable_grades = Column(JSON, nullable=True)  # List of grades where this subject is taught

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_mandatory = Column(Boolean, default=True, nullable=False)

    # Description
    description = Column(Text, nullable=True)

    # Relationships
    assessments = relationship("AssessmentModel", back_populates="subject", lazy="dynamic")
    assessment_results = relationship("AssessmentResultModel", back_populates="subject", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Subject(code='{self.code}', name='{self.name}')>"


class GradeModel(Base):
    """Grade/Class model for academic levels."""

    __tablename__ = "grades"

    # Basic Information
    name = Column(String(20), nullable=False, unique=True)  # Class 1, Class 2, etc.
    name_bn = Column(String(20), nullable=True)
    level = Column(Integer, nullable=False)  # Numeric level for ordering

    # Classification
    stage = Column(String(30), nullable=False)  # primary, secondary, higher_secondary

    # Academic Information
    subjects = Column(JSON, nullable=True)  # List of subject codes for this grade

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    enrollments = relationship("EnrollmentModel", back_populates="grade", lazy="dynamic")

    # Indexes
    __table_args__ = (
        Index("ix_grades_level", "level"),
        Index("ix_grades_stage", "stage"),
    )

    def __repr__(self) -> str:
        return f"<Grade(name='{self.name}', level={self.level})>"


class EnrollmentModel(Base):
    """Student enrollment model."""

    __tablename__ = "enrollments"

    # Relationships
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    grade_id = Column(Integer, ForeignKey("grades.id"), nullable=False)

    # Academic Information
    academic_year = Column(String(20), nullable=False)  # 2023-2024
    section = Column(String(10), nullable=True)  # A, B, C
    roll_number = Column(String(20), nullable=True)

    # Dates
    enrollment_date = Column(Date, nullable=False)
    completion_date = Column(Date, nullable=True)

    # Status
    status = Column(String(20), default=EnrollmentStatus.ACTIVE.value, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Financial Information
    fee_amount = Column(Numeric(10, 2), nullable=True)
    scholarship_amount = Column(Numeric(10, 2), default=0, nullable=False)
    fee_waiver_percentage = Column(Integer, default=0, nullable=False)

    # Performance Summary
    final_result = Column(String(20), nullable=True)  # pass, fail, promoted
    final_grade = Column(String(10), nullable=True)
    final_percentage = Column(Numeric(5, 2), nullable=True)

    # Metadata
    notes = Column(Text, nullable=True)

    # Relationships
    student = relationship("StudentModel", back_populates="enrollments")
    school = relationship("SchoolModel", back_populates="enrollments")
    grade = relationship("GradeModel", back_populates="enrollments")
    attendances = relationship("AttendanceModel", back_populates="enrollment", lazy="dynamic")

    # Indexes
    __table_args__ = (
        Index("ix_enrollments_student_year", "student_id", "academic_year"),
        Index("ix_enrollments_school_year", "school_id", "academic_year"),
        Index("ix_enrollments_status", "status"),
        UniqueConstraint("student_id", "school_id", "academic_year", name="uq_enrollment_student_school_year"),
    )

    @property
    def net_fee_amount(self) -> Optional[float]:
        """Calculate net fee after scholarship and waiver."""
        if self.fee_amount:
            waiver_amount = (self.fee_amount * self.fee_waiver_percentage) / 100
            return float(self.fee_amount) - float(self.scholarship_amount) - waiver_amount
        return None

    def __repr__(self) -> str:
        return f"<Enrollment(student_id={self.student_id}, school_id={self.school_id}, year='{self.academic_year}')>"


class AttendanceModel(Base):
    """Student attendance model."""

    __tablename__ = "attendances"

    # Relationships
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)  # For subject-wise attendance

    # Date and Time
    attendance_date = Column(Date, nullable=False)
    period = Column(Integer, nullable=True)  # Class period number

    # Status
    status = Column(String(20), default=AttendanceStatus.PRESENT.value, nullable=False)

    # Additional Information
    arrival_time = Column(Time, nullable=True)
    departure_time = Column(Time, nullable=True)
    remarks = Column(Text, nullable=True)

    # Recorded by
    recorded_by = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    student = relationship("StudentModel", back_populates="attendances")
    enrollment = relationship("EnrollmentModel", back_populates="attendances")
    subject = relationship("SubjectModel", backref="attendances")
    teacher = relationship("TeacherModel", backref="recorded_attendances")

    # Indexes
    __table_args__ = (
        Index("ix_attendances_student_date", "student_id", "attendance_date"),
        Index("ix_attendances_enrollment_date", "enrollment_id", "attendance_date"),
        Index("ix_attendances_date_status", "attendance_date", "status"),
        UniqueConstraint(
            "student_id", "attendance_date", "period", "subject_id", name="uq_attendance_student_date_period_subject"
        ),
    )

    def __repr__(self) -> str:
        return f"<Attendance(student_id={self.student_id}, date={self.attendance_date}, status='{self.status}')>"


class AssessmentModel(Base):
    """Assessment/Exam model."""

    __tablename__ = "assessments"

    # Basic Information
    name = Column(String(200), nullable=False)
    code = Column(String(50), nullable=True, index=True)

    # Relationships
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    grade_id = Column(Integer, ForeignKey("grades.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)

    # Assessment Details
    type = Column(String(30), nullable=False)  # AssessmentType
    academic_year = Column(String(20), nullable=False)
    term = Column(String(20), nullable=True)  # 1st term, 2nd term, final

    # Scheduling
    scheduled_date = Column(Date, nullable=True)
    start_time = Column(Time, nullable=True)
    duration_minutes = Column(Integer, nullable=True)

    # Grading
    total_marks = Column(Integer, nullable=False)
    pass_marks = Column(Integer, nullable=False)
    grade_system = Column(String(20), default=GradeSystem.PERCENTAGE.value, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_published = Column(Boolean, default=False, nullable=False)

    # Instructions and Details
    instructions = Column(Text, nullable=True)
    syllabus = Column(JSON, nullable=True)  # Topics covered

    # Metadata
    metadata_ = Column("metadata", JSON, default=dict, nullable=True)

    # Relationships
    school = relationship("SchoolModel", back_populates="assessments")
    subject = relationship("SubjectModel", back_populates="assessments")
    grade = relationship("GradeModel", backref="assessments")
    teacher = relationship("TeacherModel", back_populates="assessments")
    results = relationship("AssessmentResultModel", back_populates="assessment", lazy="dynamic")

    # Indexes
    __table_args__ = (
        Index("ix_assessments_school_year", "school_id", "academic_year"),
        Index("ix_assessments_subject_grade", "subject_id", "grade_id"),
        Index("ix_assessments_date", "scheduled_date"),
    )

    @property
    def pass_percentage(self) -> float:
        """Calculate pass percentage."""
        return (self.pass_marks / self.total_marks) * 100

    def __repr__(self) -> str:
        return f"<Assessment(name='{self.name}', school_id={self.school_id})>"


class AssessmentResultModel(Base):
    """Assessment result model for individual student results."""

    __tablename__ = "assessment_results"

    # Relationships
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False)

    # Scores
    marks_obtained = Column(Numeric(6, 2), nullable=False)
    total_marks = Column(Integer, nullable=False)
    percentage = Column(Numeric(5, 2), nullable=False)

    # Grades
    letter_grade = Column(String(5), nullable=True)  # A+, A, B+, etc.
    grade_point = Column(Numeric(3, 2), nullable=True)  # GPA

    # Status
    is_pass = Column(Boolean, nullable=False)
    is_absent = Column(Boolean, default=False, nullable=False)

    # Additional Information
    rank_in_class = Column(Integer, nullable=True)
    rank_in_school = Column(Integer, nullable=True)

    # Feedback
    teacher_comments = Column(Text, nullable=True)

    # Timestamps
    result_date = Column(Date, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    student = relationship("StudentModel", back_populates="assessment_results")
    assessment = relationship("AssessmentModel", back_populates="results")
    subject = relationship("SubjectModel", back_populates="assessment_results")
    enrollment = relationship("EnrollmentModel", backref="assessment_results")

    # Indexes
    __table_args__ = (
        Index("ix_assessment_results_student_assessment", "student_id", "assessment_id"),
        Index("ix_assessment_results_assessment_marks", "assessment_id", "marks_obtained"),
        Index("ix_assessment_results_subject_grade", "subject_id", "letter_grade"),
        UniqueConstraint("student_id", "assessment_id", "subject_id", name="uq_assessment_result_student_assessment_subject"),
    )

    @property
    def performance_level(self) -> str:
        """Determine performance level based on percentage."""
        if self.percentage >= 90:
            return "Excellent"
        elif self.percentage >= 80:
            return "Very Good"
        elif self.percentage >= 70:
            return "Good"
        elif self.percentage >= 60:
            return "Satisfactory"
        elif self.percentage >= 50:
            return "Needs Improvement"
        else:
            return "Poor"

    def __repr__(self) -> str:
        return f"<AssessmentResult(student_id={self.student_id}, assessment_id={self.assessment_id}, marks={self.marks_obtained}/{self.total_marks})>"
