"""
Student-related models.
"""

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl
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
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Gender(str, Enum):
    """Gender enumeration."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class BloodGroup(str, Enum):
    """Blood group enumeration."""

    A_POSITIVE = "A+"
    A_NEGATIVE = "A-"
    B_POSITIVE = "B+"
    B_NEGATIVE = "B-"
    AB_POSITIVE = "AB+"
    AB_NEGATIVE = "AB-"
    O_POSITIVE = "O+"
    O_NEGATIVE = "O-"


class Religion(str, Enum):
    """Religion enumeration."""

    ISLAM = "islam"
    HINDUISM = "hinduism"
    BUDDHISM = "buddhism"
    CHRISTIANITY = "christianity"
    OTHER = "other"


class StudentStatus(str, Enum):
    """Student status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    GRADUATED = "graduated"
    TRANSFERRED = "transferred"
    DROPPED_OUT = "dropped_out"
    SUSPENDED = "suspended"


class StudentModel(Base):
    """Student model with comprehensive information."""

    __tablename__ = "students"

    # Identification
    student_id = Column(String(50), unique=True, nullable=False, index=True)
    national_id = Column(String(20), unique=True, nullable=True, index=True)  # NID for adults
    birth_certificate_no = Column(String(30), unique=True, nullable=True, index=True)

    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    first_name_bn = Column(String(100), nullable=True)  # Bengali name
    last_name_bn = Column(String(100), nullable=True)  # Bengali name

    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(10), nullable=False)
    blood_group = Column(String(5), nullable=True)
    religion = Column(String(20), nullable=True)

    # Contact Information
    email = Column(String(255), unique=True, nullable=True, index=True)
    phone = Column(String(20), nullable=True)
    emergency_contact = Column(String(20), nullable=True)

    # Address Information
    present_address = Column(Text, nullable=True)
    permanent_address = Column(Text, nullable=True)

    # Geographic Information
    division_id = Column(Integer, ForeignKey("divisions.id"), nullable=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=True)
    upazila_id = Column(Integer, ForeignKey("upazilas.id"), nullable=True)

    # Family Information
    father_name = Column(String(200), nullable=True)
    father_name_bn = Column(String(200), nullable=True)
    father_occupation = Column(String(100), nullable=True)
    father_phone = Column(String(20), nullable=True)
    father_nid = Column(String(20), nullable=True)

    mother_name = Column(String(200), nullable=True)
    mother_name_bn = Column(String(200), nullable=True)
    mother_occupation = Column(String(100), nullable=True)
    mother_phone = Column(String(20), nullable=True)
    mother_nid = Column(String(20), nullable=True)

    # Guardian Information (if different from parents)
    guardian_name = Column(String(200), nullable=True)
    guardian_relation = Column(String(50), nullable=True)
    guardian_phone = Column(String(20), nullable=True)
    guardian_address = Column(Text, nullable=True)

    # Academic Information
    admission_date = Column(Date, nullable=True)
    current_class = Column(String(20), nullable=True)
    current_section = Column(String(10), nullable=True)
    roll_number = Column(String(20), nullable=True)

    # Status and Flags
    status = Column(String(20), default=StudentStatus.ACTIVE.value, nullable=False)
    is_scholarship_recipient = Column(Boolean, default=False, nullable=False)
    is_special_needs = Column(Boolean, default=False, nullable=False)
    special_needs_details = Column(Text, nullable=True)

    # Financial Information
    monthly_family_income = Column(Numeric(10, 2), nullable=True)
    fee_waiver_percentage = Column(Integer, default=0, nullable=False)

    # Additional Information
    photo_url = Column(String(500), nullable=True)
    documents = Column(JSON, nullable=True)  # Store document URLs and metadata
    medical_info = Column(JSON, nullable=True)  # Medical conditions, allergies, etc.
    extra_curricular = Column(JSON, nullable=True)  # Sports, clubs, activities

    # Metadata
    notes = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict, nullable=True)

    # Relationships
    division = relationship("DivisionModel", back_populates="students")
    district = relationship("DistrictModel", back_populates="students")
    upazila = relationship("UpazilaModel", back_populates="students")

    enrollments = relationship("EnrollmentModel", back_populates="student", lazy="dynamic")
    attendances = relationship("AttendanceModel", back_populates="student", lazy="dynamic")
    assessment_results = relationship("AssessmentResultModel", back_populates="student", lazy="dynamic")
    performance_records = relationship("StudentPerformanceModel", back_populates="student", lazy="dynamic")

    # Indexes
    __table_args__ = (
        Index("ix_students_name", "first_name", "last_name"),
        Index("ix_students_location", "division_id", "district_id", "upazila_id"),
        Index("ix_students_status_class", "status", "current_class"),
        Index("ix_students_admission_date", "admission_date"),
        UniqueConstraint("student_id", name="uq_students_student_id"),
    )

    @property
    def full_name(self) -> str:
        """Get student's full name."""
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def full_name_bn(self) -> Optional[str]:
        """Get student's full Bengali name."""
        if self.first_name_bn and self.last_name_bn:
            return f"{self.first_name_bn} {self.last_name_bn}".strip()
        return None

    @property
    def age(self) -> Optional[int]:
        """Calculate student's age."""
        if self.date_of_birth:
            today = date.today()
            return (
                today.year
                - self.date_of_birth.year
                - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
            )
        return None

    @property
    def current_enrollment(self):
        """Get current active enrollment."""
        return self.enrollments.filter_by(is_active=True).first()

    @property
    def current_school(self):
        """Get current school through active enrollment."""
        enrollment = self.current_enrollment
        return enrollment.school if enrollment else None

    def __repr__(self) -> str:
        return f"<Student(id='{self.student_id}', name='{self.full_name}')>"


class GuardianModel(Base):
    """Guardian/Parent model for students."""

    __tablename__ = "guardians"

    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    first_name_bn = Column(String(100), nullable=True)
    last_name_bn = Column(String(100), nullable=True)

    # Identification
    national_id = Column(String(20), unique=True, nullable=True, index=True)

    # Contact Information
    email = Column(String(255), unique=True, nullable=True, index=True)
    phone = Column(String(20), nullable=False)
    alternative_phone = Column(String(20), nullable=True)

    # Address
    address = Column(Text, nullable=True)

    # Professional Information
    occupation = Column(String(100), nullable=True)
    workplace = Column(String(200), nullable=True)
    monthly_income = Column(Numeric(10, 2), nullable=True)

    # Relationship to students
    relation_type = Column(String(20), nullable=False)  # father, mother, guardian, etc.

    # Status
    is_primary_contact = Column(Boolean, default=False, nullable=False)
    is_emergency_contact = Column(Boolean, default=False, nullable=False)

    # Metadata
    notes = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Guardian(name='{self.first_name} {self.last_name}', relation='{self.relation_type}')>"


# Association table for student-guardian relationships
student_guardian_table = Table(
    "student_guardians",
    Base.metadata,
    Column("student_id", Integer, ForeignKey("students.id"), primary_key=True),
    Column("guardian_id", Integer, ForeignKey("guardians.id"), primary_key=True),
    Column("relationship_type", String(20), nullable=False),  # father, mother, guardian
    Column("is_primary", Boolean, default=False, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    UniqueConstraint("student_id", "guardian_id", name="uq_student_guardian"),
)

# Add relationship to StudentModel
StudentModel.guardians = relationship("GuardianModel", secondary=student_guardian_table, backref="students", lazy="selectin")


class StudentBase(BaseModel):
    student_id: str = Field(..., description="Unique identifier for the student")
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    date_of_birth: date
    gender: Gender
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    address: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    division: Optional[str] = None
    postal_code: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "student_id": "STU20230001",
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "2005-01-15",
                "gender": "male",
                "email": "john.doe@example.com",
                "phone": "+8801712345678",
                "address": "123 Main Road",
                "city": "Dhaka",
                "district": "Dhaka",
                "division": "Dhaka",
                "postal_code": "1207",
            }
        }


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    address: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    division: Optional[str] = None
    postal_code: Optional[str] = None


class StudentInDB(StudentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class StudentResponse(StudentInDB):
    pass


class PaginatedStudentResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[StudentResponse]
