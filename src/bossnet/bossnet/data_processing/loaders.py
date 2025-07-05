"""
Data Loaders
============
Load transformed data into the database with validation and error handling
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from pydantic import BaseModel
from sqlalchemy import insert, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.persistence.sqlalchemy.database import get_async_session
from src.infrastructure.persistence.sqlalchemy.models.student import Enrollment, School, Student
from src.infrastructure.persistence.sqlalchemy.models.user import User

logger = logging.getLogger(__name__)


class LoadResult(BaseModel):
    """Result of data loading operation"""

    success: bool
    records_processed: int
    records_inserted: int
    records_updated: int
    records_failed: int
    errors: List[str] = []
    warnings: List[str] = []


class BaseLoader(ABC):
    """Abstract base class for data loaders"""

    def __init__(self, target_table: str):
        self.target_table = target_table
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def load(self, data: pd.DataFrame) -> LoadResult:
        """Load data into the target destination"""
        pass

    @abstractmethod
    async def validate_data(self, data: pd.DataFrame) -> List[str]:
        """Validate data before loading"""
        pass


class DatabaseLoader(BaseLoader):
    """Load data into PostgreSQL database"""

    def __init__(self, target_table: str, **kwargs):
        super().__init__(target_table)
        self.batch_size = kwargs.get("batch_size", 1000)
        self.on_conflict = kwargs.get("on_conflict", "update")  # update, ignore, error
        self.upsert_columns = kwargs.get("upsert_columns", [])

    async def validate_data(self, data: pd.DataFrame) -> List[str]:
        """Validate data structure and content"""
        errors = []

        if data.empty:
            errors.append("DataFrame is empty")
            return errors

        # Get table model
        model_class = self._get_model_class()
        if not model_class:
            errors.append(f"No model found for table: {self.target_table}")
            return errors

        # Check required columns
        required_columns = self._get_required_columns(model_class)
        missing_columns = set(required_columns) - set(data.columns)

        if missing_columns:
            errors.append(f"Missing required columns: {list(missing_columns)}")

        # Check data types and constraints
        for column in data.columns:
            if hasattr(model_class, column):
                column_attr = getattr(model_class, column)
                if hasattr(column_attr.property, "columns"):
                    db_column = column_attr.property.columns[0]

                    # Check for null values in non-nullable columns
                    if not db_column.nullable and data[column].isnull().any():
                        null_count = data[column].isnull().sum()
                        errors.append(f"Column '{column}' has {null_count} null values but is not nullable")

                    # Check string length constraints
                    if hasattr(db_column.type, "length") and db_column.type.length:
                        max_length = db_column.type.length
                        long_values = data[column].astype(str).str.len() > max_length
                        if long_values.any():
                            long_count = long_values.sum()
                            errors.append(f"Column '{column}' has {long_count} values exceeding max length {max_length}")

        return errors

    async def load(self, data: pd.DataFrame) -> LoadResult:
        """Load data into database table"""
        result = LoadResult(
            success=False, records_processed=len(data), records_inserted=0, records_updated=0, records_failed=0
        )

        try:
            # Validate data first
            validation_errors = await self.validate_data(data)
            if validation_errors:
                result.errors.extend(validation_errors)
                if any("required" in error.lower() for error in validation_errors):
                    # Critical validation errors - don't proceed
                    return result
                else:
                    # Non-critical errors - log as warnings and continue
                    result.warnings.extend(validation_errors)

            # Get model class
            model_class = self._get_model_class()
            if not model_class:
                result.errors.append(f"No model found for table: {self.target_table}")
                return result

            # Process data in batches
            total_inserted = 0
            total_updated = 0
            total_failed = 0

            async with get_async_session() as session:
                for i in range(0, len(data), self.batch_size):
                    batch = data.iloc[i : i + self.batch_size]
                    batch_result = await self._load_batch(session, batch, model_class)

                    total_inserted += batch_result["inserted"]
                    total_updated += batch_result["updated"]
                    total_failed += batch_result["failed"]

                    if batch_result["errors"]:
                        result.errors.extend(batch_result["errors"])

                await session.commit()

            result.records_inserted = total_inserted
            result.records_updated = total_updated
            result.records_failed = total_failed
            result.success = total_failed == 0

            self.logger.info(f"Load completed: {total_inserted} inserted, " f"{total_updated} updated, {total_failed} failed")

            return result

        except Exception as e:
            self.logger.error(f"Error loading data: {str(e)}")
            result.errors.append(str(e))
            return result

    async def _load_batch(self, session: AsyncSession, batch: pd.DataFrame, model_class) -> Dict[str, Any]:
        """Load a single batch of data"""
        inserted = updated = failed = 0
        errors = []

        try:
            # Convert DataFrame to list of dictionaries
            records = batch.to_dict("records")

            if self.on_conflict == "update" and self.upsert_columns:
                # Use PostgreSQL UPSERT (ON CONFLICT DO UPDATE)
                stmt = pg_insert(model_class.__table__)

                # Define the conflict resolution
                update_dict = {
                    col.name: stmt.excluded[col.name]
                    for col in model_class.__table__.columns
                    if col.name not in self.upsert_columns
                }

                stmt = stmt.on_conflict_do_update(index_elements=self.upsert_columns, set_=update_dict)

                result = await session.execute(stmt, records)
                inserted = len(records)  # PostgreSQL doesn't distinguish in UPSERT

            elif self.on_conflict == "ignore":
                # Use PostgreSQL ON CONFLICT DO NOTHING
                stmt = pg_insert(model_class.__table__).on_conflict_do_nothing()
                await session.execute(stmt, records)
                inserted = len(records)

            else:
                # Regular insert - will fail on conflicts
                stmt = insert(model_class.__table__)
                await session.execute(stmt, records)
                inserted = len(records)

        except Exception as e:
            self.logger.error(f"Batch load error: {str(e)}")
            errors.append(str(e))
            failed = len(batch)

        return {"inserted": inserted, "updated": updated, "failed": failed, "errors": errors}

    def _get_model_class(self):
        """Get SQLAlchemy model class for the target table"""
        model_mapping = {"users": User, "students": Student, "schools": School, "enrollments": Enrollment}

        return model_mapping.get(self.target_table.lower())

    def _get_required_columns(self, model_class) -> List[str]:
        """Get required columns for the model"""
        required_columns = []

        for column in model_class.__table__.columns:
            if not column.nullable and column.default is None and column.server_default is None:
                required_columns.append(column.name)

        return required_columns


class ValidationLoader(DatabaseLoader):
    """Loader with enhanced data validation"""

    def __init__(self, target_table: str, **kwargs):
        super().__init__(target_table, **kwargs)
        self.strict_validation = kwargs.get("strict_validation", True)
        self.custom_validators = kwargs.get("custom_validators", {})

    async def validate_data(self, data: pd.DataFrame) -> List[str]:
        """Enhanced data validation"""
        errors = await super().validate_data(data)

        # Apply custom validators
        for column, validator_func in self.custom_validators.items():
            if column in data.columns:
                try:
                    validation_result = validator_func(data[column])
                    if not validation_result["valid"]:
                        errors.extend(validation_result["errors"])
                except Exception as e:
                    errors.append(f"Custom validation failed for column '{column}': {str(e)}")

        # Business logic validation
        errors.extend(await self._validate_business_rules(data))

        return errors

    async def _validate_business_rules(self, data: pd.DataFrame) -> List[str]:
        """Validate business-specific rules"""
        errors = []

        if self.target_table.lower() == "students":
            errors.extend(self._validate_student_rules(data))
        elif self.target_table.lower() == "schools":
            errors.extend(self._validate_school_rules(data))
        elif self.target_table.lower() == "enrollments":
            errors.extend(self._validate_enrollment_rules(data))

        return errors

    def _validate_student_rules(self, data: pd.DataFrame) -> List[str]:
        """Validate student-specific business rules"""
        errors = []

        # Check age constraints
        if "age" in data.columns:
            invalid_ages = (data["age"] < 3) | (data["age"] > 25)
            if invalid_ages.any():
                count = invalid_ages.sum()
                errors.append(f"{count} students have invalid ages (must be between 3-25)")

        # Check gender values
        if "gender" in data.columns:
            valid_genders = ["Male", "Female", "Other", "Unknown"]
            invalid_genders = ~data["gender"].isin(valid_genders)
            if invalid_genders.any():
                count = invalid_genders.sum()
                errors.append(f"{count} students have invalid gender values")

        # Check phone number format
        if "phone_number" in data.columns:
            phone_pattern = r"^\+880\d{10}$"
            valid_phones = data["phone_number"].str.match(phone_pattern, na=True)
            invalid_phones = ~valid_phones & data["phone_number"].notna()
            if invalid_phones.any():
                count = invalid_phones.sum()
                errors.append(f"{count} students have invalid phone number format")

        return errors

    def _validate_school_rules(self, data: pd.DataFrame) -> List[str]:
        """Validate school-specific business rules"""
        errors = []

        # Check school type values
        if "school_type" in data.columns:
            valid_types = ["Government", "Private", "NGO", "Madrasa", "Technical", "Other"]
            invalid_types = ~data["school_type"].isin(valid_types)
            if invalid_types.any():
                count = invalid_types.sum()
                errors.append(f"{count} schools have invalid school type values")

        # Check education level values
        if "education_level" in data.columns:
            valid_levels = ["Primary", "Secondary", "Higher Secondary", "Technical", "Madrasa", "Other"]
            invalid_levels = ~data["education_level"].isin(valid_levels)
            if invalid_levels.any():
                count = invalid_levels.sum()
                errors.append(f"{count} schools have invalid education level values")

        return errors

    def _validate_enrollment_rules(self, data: pd.DataFrame) -> List[str]:
        """Validate enrollment-specific business rules"""
        errors = []

        # Check academic year format
        if "academic_year" in data.columns:
            year_pattern = r"^\d{4}$"
            valid_years = data["academic_year"].str.match(year_pattern)
            invalid_years = ~valid_years
            if invalid_years.any():
                count = invalid_years.sum()
                errors.append(f"{count} enrollments have invalid academic year format")

        # Check grade level values
        if "grade_level" in data.columns:
            valid_grades = [str(i) for i in range(1, 13)] + ["KG", "Nursery"]
            invalid_grades = ~data["grade_level"].isin(valid_grades)
            if invalid_grades.any():
                count = invalid_grades.sum()
                errors.append(f"{count} enrollments have invalid grade level values")

        return errors


class CSVLoader(BaseLoader):
    """Load data to CSV files (for backup/export)"""

    def __init__(self, target_path: str, **kwargs):
        super().__init__(target_path)
        self.target_path = target_path
        self.append_mode = kwargs.get("append_mode", False)
        self.include_index = kwargs.get("include_index", False)

    async def validate_data(self, data: pd.DataFrame) -> List[str]:
        """Basic validation for CSV export"""
        errors = []

        if data.empty:
            errors.append("DataFrame is empty")

        return errors

    async def load(self, data: pd.DataFrame) -> LoadResult:
        """Save data to CSV file"""
        result = LoadResult(
            success=False, records_processed=len(data), records_inserted=0, records_updated=0, records_failed=0
        )

        try:
            # Validate data
            validation_errors = await self.validate_data(data)
            if validation_errors:
                result.errors.extend(validation_errors)
                return result

            # Save to CSV
            mode = "a" if self.append_mode else "w"
            header = not self.append_mode or not Path(self.target_path).exists()

            data.to_csv(self.target_path, mode=mode, header=header, index=self.include_index)

            result.records_inserted = len(data)
            result.success = True

            self.logger.info(f"Successfully saved {len(data)} records to {self.target_path}")

        except Exception as e:
            self.logger.error(f"Error saving to CSV: {str(e)}")
            result.errors.append(str(e))

        return result


# Factory function to create loaders
def create_loader(loader_type: str, target: str, **kwargs) -> BaseLoader:
    """Factory function to create appropriate loader"""
    loaders = {"database": DatabaseLoader, "validation": ValidationLoader, "csv": CSVLoader}

    if loader_type not in loaders:
        raise ValueError(f"Unsupported loader type: {loader_type}")

    return loaders[loader_type](target, **kwargs)
