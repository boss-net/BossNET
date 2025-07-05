"""
SQLAlchemy Student model
"""

import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.infrastructure.persistence.sqlalchemy.database import Base


class GenderEnum(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class StudentModel(Base):
    """SQLAlchemy Student model"""

    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(50), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(Enum(GenderEnum), nullable=False)
    email = Column(String(255), unique=True, index=True)
    phone = Column(String(20))
    address = Column(Text)

    # Geographic information
    division = Column(String(100))
    district = Column(String(100))
    upazila = Column(String(100))

    # Academic information
    current_grade = Column(String(20))
    enrollment_date = Column(Date)
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Student(id={self.id}, student_id='{self.student_id}', name='{self.first_name} {self.last_name}')>"


class SchoolModel(Base):
    """SQLAlchemy School model"""

    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, index=True)
    school_code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(50))  # Primary, Secondary, Higher Secondary
    address = Column(Text)

    # Geographic information
    division = Column(String(100))
    district = Column(String(100))
    upazila = Column(String(100))

    # Contact information
    phone = Column(String(20))
    email = Column(String(255))

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<School(id={self.id}, code='{self.school_code}', name='{self.name}')>"


class EnrollmentModel(Base):
    """SQLAlchemy Enrollment model"""

    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    grade = Column(String(20), nullable=False)
    academic_year = Column(String(20), nullable=False)
    enrollment_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    student = relationship("StudentModel", backref="enrollments")
    school = relationship("SchoolModel", backref="enrollments")

    def __repr__(self) -> str:
        return f"<Enrollment(id={self.id}, student_id={self.student_id}, school_id={self.school_id}, grade='{self.grade}')>"
