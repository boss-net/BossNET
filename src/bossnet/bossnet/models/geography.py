"""
Geography models for Bangladesh administrative divisions.
"""

from sqlalchemy import JSON, Boolean, Column, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from .base import Base


class DivisionModel(Base):
    """Bangladesh administrative divisions model."""

    __tablename__ = "divisions"

    # Basic Information
    name = Column(String(100), nullable=False, unique=True)
    name_bn = Column(String(100), nullable=True)  # Bengali name
    code = Column(String(10), unique=True, nullable=False, index=True)

    # Geographic Information
    area_sq_km = Column(Numeric(10, 2), nullable=True)
    population = Column(Integer, nullable=True)

    # Coordinates for mapping
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Additional Information
    description = Column(Text, nullable=True)

    # Relationships
    districts = relationship("DistrictModel", back_populates="division", lazy="dynamic")
    schools = relationship("SchoolModel", back_populates="division", lazy="dynamic")
    students = relationship("StudentModel", back_populates="division", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Division(name='{self.name}', code='{self.code}')>"


class DistrictModel(Base):
    """Bangladesh districts model."""

    __tablename__ = "districts"

    # Basic Information
    name = Column(String(100), nullable=False)
    name_bn = Column(String(100), nullable=True)
    code = Column(String(10), nullable=False, index=True)

    # Relationships
    division_id = Column(Integer, ForeignKey("divisions.id"), nullable=False)

    # Geographic Information
    area_sq_km = Column(Numeric(10, 2), nullable=True)
    population = Column(Integer, nullable=True)

    # Coordinates
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    division = relationship("DivisionModel", back_populates="districts")
    upazilas = relationship("UpazilaModel", back_populates="district", lazy="dynamic")
    schools = relationship("SchoolModel", back_populates="district", lazy="dynamic")
    students = relationship("StudentModel", back_populates="district", lazy="dynamic")

    # Indexes
    __table_args__ = (Index("ix_districts_division_name", "division_id", "name"),)

    def __repr__(self) -> str:
        return f"<District(name='{self.name}', division='{self.division.name if self.division else None}')>"


class UpazilaModel(Base):
    """Bangladesh upazilas/sub-districts model."""

    __tablename__ = "upazilas"

    # Basic Information
    name = Column(String(100), nullable=False)
    name_bn = Column(String(100), nullable=True)
    code = Column(String(10), nullable=False, index=True)

    # Relationships
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)

    # Geographic Information
    area_sq_km = Column(Numeric(10, 2), nullable=True)
    population = Column(Integer, nullable=True)

    # Coordinates
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    district = relationship("DistrictModel", back_populates="upazilas")
    schools = relationship("SchoolModel", back_populates="upazila", lazy="dynamic")
    students = relationship("StudentModel", back_populates="upazila", lazy="dynamic")

    # Indexes
    __table_args__ = (Index("ix_upazilas_district_name", "district_id", "name"),)

    @property
    def division(self):
        """Get division through district relationship."""
        return self.district.division if self.district else None

    def __repr__(self) -> str:
        return f"<Upazila(name='{self.name}', district='{self.district.name if self.district else None}')>"
