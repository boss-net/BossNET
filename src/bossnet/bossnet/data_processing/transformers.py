"""
Data Transformers
================
Transform and clean extracted data for loading into the warehouse
"""

import logging
import re
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class TransformationRule(BaseModel):
    """Configuration for a single transformation rule"""

    column: str
    operation: str  # clean, normalize, validate, convert, etc.
    parameters: Dict[str, Any] = {}
    required: bool = True


class TransformationResult(BaseModel):
    """Result of data transformation"""

    success: bool
    records_processed: int
    records_valid: int
    records_invalid: int
    errors: List[str] = []
    warnings: List[str] = []
    transformation_log: List[str] = []


class BaseTransformer(ABC):
    """Abstract base class for data transformers"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.transformation_rules: List[TransformationRule] = []
        self.column_mappings: Dict[str, str] = {}
        self.required_columns: List[str] = []

    @abstractmethod
    async def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Transform the input data"""
        pass

    def add_transformation_rule(self, rule: TransformationRule):
        """Add a transformation rule"""
        self.transformation_rules.append(rule)

    def set_column_mapping(self, source_column: str, target_column: str):
        """Set column name mapping"""
        self.column_mappings[source_column] = target_column

    def _apply_column_mappings(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply column name mappings"""
        if self.column_mappings:
            df = df.rename(columns=self.column_mappings)
            self.logger.info(f"Applied column mappings: {self.column_mappings}")
        return df

    def _validate_required_columns(self, df: pd.DataFrame) -> List[str]:
        """Validate that required columns are present"""
        missing_columns = []
        for col in self.required_columns:
            if col not in df.columns:
                missing_columns.append(col)

        if missing_columns:
            self.logger.error(f"Missing required columns: {missing_columns}")

        return missing_columns

    def _clean_text_column(self, series: pd.Series, **kwargs) -> pd.Series:
        """Clean text data"""
        # Remove extra whitespace
        series = series.astype(str).str.strip()

        # Remove multiple spaces
        series = series.str.replace(r"\s+", " ", regex=True)

        # Handle case conversion
        case = kwargs.get("case", "title")
        if case == "upper":
            series = series.str.upper()
        elif case == "lower":
            series = series.str.lower()
        elif case == "title":
            series = series.str.title()

        # Remove special characters if specified
        if kwargs.get("remove_special_chars", False):
            series = series.str.replace(r"[^\w\s]", "", regex=True)

        return series

    def _normalize_phone_number(self, series: pd.Series) -> pd.Series:
        """Normalize phone numbers to standard format"""

        def clean_phone(phone):
            if pd.isna(phone):
                return None

            # Convert to string and remove all non-digits
            phone_str = re.sub(r"\D", "", str(phone))

            # Handle Bangladesh phone numbers
            if phone_str.startswith("880"):
                phone_str = phone_str[3:]  # Remove country code
            elif phone_str.startswith("0"):
                phone_str = phone_str[1:]  # Remove leading zero

            # Validate length (should be 10 digits for Bangladesh mobile)
            if len(phone_str) == 10 and phone_str.startswith("1"):
                return f"+880{phone_str}"

            return None

        return series.apply(clean_phone)

    def _parse_date_column(self, series: pd.Series, **kwargs) -> pd.Series:
        """Parse and standardize date columns"""
        date_format = kwargs.get("format", None)

        try:
            if date_format:
                return pd.to_datetime(series, format=date_format, errors="coerce")
            else:
                return pd.to_datetime(series, errors="coerce")
        except Exception as e:
            self.logger.warning(f"Date parsing error: {str(e)}")
            return pd.to_datetime(series, errors="coerce")

    def _validate_email(self, series: pd.Series) -> pd.Series:
        """Validate email addresses"""
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        def is_valid_email(email):
            if pd.isna(email):
                return None
            return email if re.match(email_pattern, str(email)) else None

        return series.apply(is_valid_email)


class StudentDataTransformer(BaseTransformer):
    """Transformer for student data"""

    def __init__(self):
        super().__init__()
        self.required_columns = ["student_id", "full_name", "gender", "date_of_birth"]

        # Common column mappings for student data
        self.column_mappings = {
            "name": "full_name",
            "dob": "date_of_birth",
            "birth_date": "date_of_birth",
            "sex": "gender",
            "phone": "phone_number",
            "mobile": "phone_number",
            "email_address": "email",
            "father_name": "father_full_name",
            "mother_name": "mother_full_name",
            "guardian_name": "guardian_full_name",
            "address": "current_address",
        }

    async def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Transform student data"""
        try:
            self.logger.info(f"Starting transformation of {len(data)} student records")

            # Apply column mappings
            df = self._apply_column_mappings(data.copy())

            # Validate required columns
            missing_cols = self._validate_required_columns(df)
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")

            # Transform individual columns
            df = await self._transform_student_columns(df)

            # Add computed columns
            df = self._add_computed_columns(df)

            # Remove duplicates
            initial_count = len(df)
            df = df.drop_duplicates(subset=["student_id"], keep="first")
            duplicates_removed = initial_count - len(df)

            if duplicates_removed > 0:
                self.logger.info(f"Removed {duplicates_removed} duplicate records")

            self.logger.info(f"Successfully transformed {len(df)} student records")
            return df

        except Exception as e:
            self.logger.error(f"Error transforming student data: {str(e)}")
            raise

    async def _transform_student_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform specific student columns"""

        # Clean student ID
        if "student_id" in df.columns:
            df["student_id"] = df["student_id"].astype(str).str.strip()
            df["student_id"] = df["student_id"].str.upper()

        # Clean full name
        if "full_name" in df.columns:
            df["full_name"] = self._clean_text_column(df["full_name"], case="title")

        # Standardize gender
        if "gender" in df.columns:
            gender_mapping = {
                "M": "Male",
                "F": "Female",
                "O": "Other",
                "MALE": "Male",
                "FEMALE": "Female",
                "OTHER": "Other",
                "1": "Male",
                "2": "Female",
                "3": "Other",
            }
            df["gender"] = df["gender"].astype(str).str.upper().map(gender_mapping)
            df["gender"] = df["gender"].fillna("Unknown")

        # Parse date of birth
        if "date_of_birth" in df.columns:
            df["date_of_birth"] = self._parse_date_column(df["date_of_birth"])

        # Clean phone numbers
        if "phone_number" in df.columns:
            df["phone_number"] = self._normalize_phone_number(df["phone_number"])

        # Validate emails
        if "email" in df.columns:
            df["email"] = self._validate_email(df["email"])

        # Clean parent/guardian names
        for col in ["father_full_name", "mother_full_name", "guardian_full_name"]:
            if col in df.columns:
                df[col] = self._clean_text_column(df[col], case="title")

        # Clean addresses
        for col in ["current_address", "permanent_address"]:
            if col in df.columns:
                df[col] = self._clean_text_column(df[col], case="title")

        # Standardize division/district names
        for col in ["division", "district", "upazila"]:
            if col in df.columns:
                df[col] = self._clean_text_column(df[col], case="title")

        return df

    def _add_computed_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add computed columns"""

        # Calculate age if date_of_birth is available
        if "date_of_birth" in df.columns:
            today = pd.Timestamp.now()
            df["age"] = (today - df["date_of_birth"]).dt.days // 365

            # Add age group
            df["age_group"] = pd.cut(
                df["age"],
                bins=[0, 5, 10, 15, 20, 25, 100],
                labels=["0-4", "5-9", "10-14", "15-19", "20-24", "25+"],
                right=False,
            )

        # Add enrollment status (default to active)
        if "enrollment_status" not in df.columns:
            df["enrollment_status"] = "Active"

        # Add created/updated timestamps
        df["created_at"] = pd.Timestamp.now()
        df["updated_at"] = pd.Timestamp.now()

        return df


class SchoolDataTransformer(BaseTransformer):
    """Transformer for school data"""

    def __init__(self):
        super().__init__()
        self.required_columns = ["school_id", "school_name", "division", "district"]

        # Common column mappings for school data
        self.column_mappings = {
            "name": "school_name",
            "institution_name": "school_name",
            "type": "school_type",
            "level": "education_level",
            "phone": "phone_number",
            "mobile": "phone_number",
            "email_address": "email",
            "head_teacher": "head_teacher_name",
            "principal": "head_teacher_name",
        }

    async def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Transform school data"""
        try:
            self.logger.info(f"Starting transformation of {len(data)} school records")

            # Apply column mappings
            df = self._apply_column_mappings(data.copy())

            # Validate required columns
            missing_cols = self._validate_required_columns(df)
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")

            # Transform individual columns
            df = await self._transform_school_columns(df)

            # Add computed columns
            df = self._add_school_computed_columns(df)

            # Remove duplicates
            initial_count = len(df)
            df = df.drop_duplicates(subset=["school_id"], keep="first")
            duplicates_removed = initial_count - len(df)

            if duplicates_removed > 0:
                self.logger.info(f"Removed {duplicates_removed} duplicate records")

            self.logger.info(f"Successfully transformed {len(df)} school records")
            return df

        except Exception as e:
            self.logger.error(f"Error transforming school data: {str(e)}")
            raise

    async def _transform_school_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform specific school columns"""

        # Clean school ID
        if "school_id" in df.columns:
            df["school_id"] = df["school_id"].astype(str).str.strip()
            df["school_id"] = df["school_id"].str.upper()

        # Clean school name
        if "school_name" in df.columns:
            df["school_name"] = self._clean_text_column(df["school_name"], case="title")

        # Standardize school type
        if "school_type" in df.columns:
            type_mapping = {
                "GOVT": "Government",
                "PVT": "Private",
                "NGO": "NGO",
                "MADRASA": "Madrasa",
                "TECHNICAL": "Technical",
            }
            df["school_type"] = df["school_type"].astype(str).str.upper()
            df["school_type"] = df["school_type"].map(type_mapping).fillna("Other")

        # Standardize education level
        if "education_level" in df.columns:
            level_mapping = {
                "PRIMARY": "Primary",
                "SECONDARY": "Secondary",
                "HIGHER_SECONDARY": "Higher Secondary",
                "TECHNICAL": "Technical",
                "MADRASA": "Madrasa",
            }
            df["education_level"] = df["education_level"].astype(str).str.upper()
            df["education_level"] = df["education_level"].map(level_mapping).fillna("Other")

        # Clean geographic information
        for col in ["division", "district", "upazila", "union"]:
            if col in df.columns:
                df[col] = self._clean_text_column(df[col], case="title")

        # Clean contact information
        if "phone_number" in df.columns:
            df["phone_number"] = self._normalize_phone_number(df["phone_number"])

        if "email" in df.columns:
            df["email"] = self._validate_email(df["email"])

        # Clean head teacher name
        if "head_teacher_name" in df.columns:
            df["head_teacher_name"] = self._clean_text_column(df["head_teacher_name"], case="title")

        return df

    def _add_school_computed_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add computed columns for schools"""

        # Determine if school is rural/urban based on district
        # This is a simplified classification - in reality, you'd use more sophisticated logic
        urban_districts = ["Dhaka", "Chittagong", "Sylhet", "Rajshahi", "Khulna", "Barisal", "Rangpur"]

        if "district" in df.columns:
            df["is_rural"] = ~df["district"].isin(urban_districts)

        # Add operational status (default to active)
        if "operational_status" not in df.columns:
            df["operational_status"] = "Active"

        # Add created/updated timestamps
        df["created_at"] = pd.Timestamp.now()
        df["updated_at"] = pd.Timestamp.now()

        return df


class EnrollmentDataTransformer(BaseTransformer):
    """Transformer for enrollment data"""

    def __init__(self):
        super().__init__()
        self.required_columns = ["student_id", "school_id", "academic_year", "grade_level"]

    async def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Transform enrollment data"""
        try:
            self.logger.info(f"Starting transformation of {len(data)} enrollment records")

            df = data.copy()

            # Validate required columns
            missing_cols = self._validate_required_columns(df)
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")

            # Clean IDs
            df["student_id"] = df["student_id"].astype(str).str.strip().str.upper()
            df["school_id"] = df["school_id"].astype(str).str.strip().str.upper()

            # Standardize academic year format
            df["academic_year"] = df["academic_year"].astype(str).str.strip()

            # Standardize grade level
            df["grade_level"] = df["grade_level"].astype(str).str.strip()

            # Parse enrollment date
            if "enrollment_date" in df.columns:
                df["enrollment_date"] = self._parse_date_column(df["enrollment_date"])
            else:
                df["enrollment_date"] = pd.Timestamp.now()

            # Add enrollment status
            if "enrollment_status" not in df.columns:
                df["enrollment_status"] = "Active"

            # Add timestamps
            df["created_at"] = pd.Timestamp.now()
            df["updated_at"] = pd.Timestamp.now()

            # Remove duplicates
            initial_count = len(df)
            df = df.drop_duplicates(subset=["student_id", "school_id", "academic_year"], keep="first")
            duplicates_removed = initial_count - len(df)

            if duplicates_removed > 0:
                self.logger.info(f"Removed {duplicates_removed} duplicate enrollment records")

            self.logger.info(f"Successfully transformed {len(df)} enrollment records")
            return df

        except Exception as e:
            self.logger.error(f"Error transforming enrollment data: {str(e)}")
            raise


# Factory function to create transformers
def create_transformer(data_type: str) -> BaseTransformer:
    """Factory function to create appropriate transformer"""
    transformers = {
        "student": StudentDataTransformer,
        "school": SchoolDataTransformer,
        "enrollment": EnrollmentDataTransformer,
    }

    if data_type not in transformers:
        raise ValueError(f"Unsupported transformer type: {data_type}")

    return transformers[data_type]()
