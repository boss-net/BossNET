from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Enum, Index, Integer, String
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.sql import func

from database.base import Base


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class StudentDB(Base):
    """Database model for students"""

    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(50), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(PgEnum(Gender, name="gender_enum"), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    division = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Add indexes for frequently queried fields
    __table_args__ = (
        Index("idx_student_name", "first_name", "last_name"),
        Index("idx_student_location", "division", "district", "city"),
    )

    def __repr__(self):
        return f"<Student {self.student_id}: {self.first_name} {self.last_name}>"

    def to_dict(self):
        """Convert model instance to dictionary"""
        return {
            "id": self.id,
            "student_id": self.student_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "gender": self.gender.value if self.gender else None,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
            "city": self.city,
            "district": self.district,
            "division": self.division,
            "postal_code": self.postal_code,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
