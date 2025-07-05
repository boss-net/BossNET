"""
School and teacher-related models.
"""

from datetime import date, datetime
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


class SchoolType(str, Enum):
    """School type enumeration."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    HIGHER_SECONDARY = "higher_secondary"
    MADRASA = "madrasa"
    TECHNICAL = "technical"
    KINDERGARTEN = "kindergarten"


class SchoolCategory(str, Enum):
    """School category enumeration."""

    GOVERNMENT = "government"
    NON_GOVERNMENT = "non_government"
    PRIVATE = "private"
    INTERNATIONAL = "international"
    NGO = "ngo"


class SchoolShift(str, Enum):
    """School shift enumeration."""

    MORNING = "morning"
    DAY = "day"
    EVENING = "evening"
    NIGHT = "night"


class TeacherStatus(str, Enum):
    """Teacher status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"
    TRANSFERRED = "transferred"
    RETIRED = "retired"
    TERMINATED = "terminated"


class SchoolModel(Base):
    """School model with comprehensive information."""

    __tablename__ = "schools"

    # Identification
    school_code = Column(String(50), unique=True, nullable=False, index=True)
    eiin = Column(String(20), unique=True, nullable=True, index=True)  # Educational Institution Identification Number

    # Basic Information
    name = Column(String(255), nullable=False)
    name_bn = Column(String(255), nullable=True)  # Bengali name

    # Classification
    type = Column(String(30), nullable=False)  # SchoolType
    category = Column(String(30), nullable=False)  # SchoolCategory
    level = Column(String(50), nullable=True)  # Pre-primary, Primary, Secondary, etc.

    # Contact Information
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    fax = Column(String(20), nullable=True)
    website = Column(String(255), nullable=True)

    # Address Information
    address = Column(Text, nullable=True)
    postal_code = Column(String(10), nullable=True)

    # Geographic Information
    division_id = Column(Integer, ForeignKey("divisions.id"), nullable=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=True)
    upazila_id = Column(Integer, ForeignKey("upazilas.id"), nullable=True)

    # Coordinates for mapping
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)

    # Establishment Information
    establishment_date = Column(Date, nullable=True)
    recognition_date = Column(Date, nullable=True)

    # Infrastructure
    total_classrooms = Column(Integer, default=0, nullable=False)
    total_labs = Column(Integer, default=0, nullable=False)
    library_available = Column(Boolean, default=False, nullable=False)
    computer_lab_available = Column(Boolean, default=False, nullable=False)
    science_lab_available = Column(Boolean, default=False, nullable=False)
    playground_available = Column(Boolean, default=False, nullable=False)

    # Utilities
    electricity_available = Column(Boolean, default=False, nullable=False)
    internet_available = Column(Boolean, default=False, nullable=False)
    water_supply_available = Column(Boolean, default=False, nullable=False)
    toilet_facilities = Column(JSON, nullable=True)  # Details about toilet facilities

    # Academic Information
    shifts = Column(JSON, nullable=True)  # List of shifts (morning, day, evening)
    medium_of_instruction = Column(JSON, nullable=True)  # Bengali, English, etc.
    grades_offered = Column(JSON, nullable=True)  # List of grades/classes offered

    # Capacity and Enrollment
    total_capacity = Column(Integer, nullable=True)
    current_enrollment = Column(Integer, default=0, nullable=False)

    # Staff Information
    total_teachers = Column(Integer, default=0, nullable=False)
    total_staff = Column(Integer, default=0, nullable=False)

    # Financial Information
    monthly_fee_range = Column(JSON, nullable=True)  # {"min": 0, "max": 1000}
    scholarship_available = Column(Boolean, default=False, nullable=False)

    # Accreditation and Recognition
    accreditation_status = Column(String(50), nullable=True)
    recognition_authority = Column(String(100), nullable=True)

    # Performance Metrics
    pass_rate = Column(Numeric(5, 2), nullable=True)  # Percentage
    attendance_rate = Column(Numeric(5, 2), nullable=True)  # Percentage

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_co_educational = Column(Boolean, default=True, nullable=False)

    # Additional Information
    facilities = Column(JSON, nullable=True)  # List of additional facilities
    achievements = Column(JSON, nullable=True)  # School achievements and awards

    # Metadata
    notes = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict, nullable=True)

    # Relationships
    division = relationship("DivisionModel", back_populates="schools")
    district = relationship("DistrictModel", back_populates="schools")
    upazila = relationship("UpazilaModel", back_populates="schools")

    teachers = relationship("TeacherModel", back_populates="school", lazy="dynamic")
    classrooms = relationship("ClassroomModel", back_populates="school", lazy="dynamic")
    enrollments = relationship("EnrollmentModel", back_populates="school", lazy="dynamic")
    assessments = relationship("AssessmentModel", back_populates="school", lazy="dynamic")
    performance_records = relationship("SchoolPerformanceModel", back_populates="school", lazy="dynamic")

    # Indexes
    __table_args__ = (
        Index("ix_schools_location", "division_id", "district_id", "upazila_id"),
        Index("ix_schools_type_category", "type", "category"),
        Index("ix_schools_name", "name"),
        UniqueConstraint("school_code", name="uq_schools_school_code"),
    )

    @property
    def full_address(self) -> str:
        """Get full address including administrative divisions."""
        parts = []
        if self.address:
            parts.append(self.address)
        if self.upazila:
            parts.append(self.upazila.name)
        if self.district:
            parts.append(self.district.name)
        if self.division:
            parts.append(self.division.name)
        return ", ".join(parts)

    @property
    def enrollment_percentage(self) -> Optional[float]:
        """Calculate enrollment percentage of capacity."""
        if self.total_capacity and self.total_capacity > 0:
            return (self.current_enrollment / self.total_capacity) * 100
        return None

    @property
    def teacher_student_ratio(self) -> Optional[float]:
        """Calculate teacher to student ratio."""
        if self.total_teachers and self.total_teachers > 0:
            return self.current_enrollment / self.total_teachers
        return None

    def __repr__(self) -> str:
        return f"<School(code='{self.school_code}', name='{self.name}')>"


class TeacherModel(Base):
    """Teacher model with comprehensive information."""

    __tablename__ = "teachers"

    # Identification
    teacher_id = Column(String(50), unique=True, nullable=False, index=True)
    national_id = Column(String(20), unique=True, nullable=True, index=True)

    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    first_name_bn = Column(String(100), nullable=True)
    last_name_bn = Column(String(100), nullable=True)

    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(10), nullable=False)
    religion = Column(String(20), nullable=True)

    # Contact Information
    email = Column(String(255), unique=True, nullable=True, index=True)
    phone = Column(String(20), nullable=False)
    emergency_contact = Column(String(20), nullable=True)

    # Address
    present_address = Column(Text, nullable=True)
    permanent_address = Column(Text, nullable=True)

    # Professional Information
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    employee_id = Column(String(50), nullable=True)
    designation = Column(String(100), nullable=False)
    department = Column(String(100), nullable=True)

    # Employment Details
    joining_date = Column(Date, nullable=False)
    employment_type = Column(String(30), nullable=False)  # permanent, temporary, contract
    salary = Column(Numeric(10, 2), nullable=True)

    # Educational Qualifications
    highest_qualification = Column(String(100), nullable=True)
    qualifications = Column(JSON, nullable=True)  # List of qualifications
    certifications = Column(JSON, nullable=True)  # Professional certifications

    # Teaching Information
    subjects_taught = Column(JSON, nullable=True)  # List of subjects
    classes_taught = Column(JSON, nullable=True)  # List of classes/grades
    teaching_experience_years = Column(Integer, default=0, nullable=False)

    # Performance
    performance_rating = Column(Numeric(3, 2), nullable=True)  # Out of 5.00
    last_evaluation_date = Column(Date, nullable=True)

    # Status
    status = Column(String(20), default=TeacherStatus.ACTIVE.value, nullable=False)
    is_head_teacher = Column(Boolean, default=False, nullable=False)
    is_class_teacher = Column(Boolean, default=False, nullable=False)

    # Additional Information
    photo_url = Column(String(500), nullable=True)
    documents = Column(JSON, nullable=True)

    # Metadata
    notes = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict, nullable=True)

    # Relationships
    school = relationship("SchoolModel", back_populates="teachers")
    assessments = relationship("AssessmentModel", back_populates="teacher", lazy="dynamic")

    # Indexes
    __table_args__ = (
        Index("ix_teachers_school_status", "school_id", "status"),
        Index("ix_teachers_name", "first_name", "last_name"),
        Index("ix_teachers_designation", "designation"),
        UniqueConstraint("teacher_id", name="uq_teachers_teacher_id"),
    )

    @property
    def full_name(self) -> str:
        """Get teacher's full name."""
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def age(self) -> Optional[int]:
        """Calculate teacher's age."""
        if self.date_of_birth:
            today = date.today()
            return (
                today.year
                - self.date_of_birth.year
                - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
            )
        return None

    @property
    def years_at_school(self) -> int:
        """Calculate years at current school."""
        if self.joining_date:
            today = date.today()
            return today.year - self.joining_date.year
        return 0

    def __repr__(self) -> str:
        return f"<Teacher(id='{self.teacher_id}', name='{self.full_name}')>"


class ClassroomModel(Base):
    """Classroom model for school infrastructure."""

    __tablename__ = "classrooms"

    # Basic Information
    room_number = Column(String(20), nullable=False)
    name = Column(String(100), nullable=True)

    # School Relationship
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)

    # Physical Information
    floor = Column(Integer, nullable=True)
    capacity = Column(Integer, nullable=False)
    area_sq_meters = Column(Numeric(8, 2), nullable=True)

    # Facilities
    has_projector = Column(Boolean, default=False, nullable=False)
    has_computer = Column(Boolean, default=False, nullable=False)
    has_internet = Column(Boolean, default=False, nullable=False)
    has_ac = Column(Boolean, default=False, nullable=False)
    has_fan = Column(Boolean, default=False, nullable=False)

    # Usage
    primary_grade = Column(String(20), nullable=True)  # Primary grade using this room
    subjects_taught = Column(JSON, nullable=True)  # Subjects taught in this room

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    condition = Column(String(20), default="good", nullable=False)  # excellent, good, fair, poor

    # Metadata
    notes = Column(Text, nullable=True)

    # Relationships
    school = relationship("SchoolModel", back_populates="classrooms")

    # Indexes
    __table_args__ = (
        Index("ix_classrooms_school_room", "school_id", "room_number"),
        UniqueConstraint("school_id", "room_number", name="uq_classrooms_school_room"),
    )

    def __repr__(self) -> str:
        return f"<Classroom(school_id={self.school_id}, room='{self.room_number}')>"
