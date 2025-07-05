"""
Tests for Data Processing Pipeline
=================================
Comprehensive tests for ETL pipeline components
"""

import asyncio
import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest
from src.data_processing.extractors import CSVExtractor, DatabaseExtractor, ExcelExtractor
from src.data_processing.loaders import DatabaseLoader, ValidationLoader
from src.data_processing.pipeline import DataPipeline, PipelineConfig, PipelineResult
from src.data_processing.transformers import SchoolDataTransformer, StudentDataTransformer
from src.data_processing.validators import DataQualityValidator, ValidationRule


class TestDataPipeline:
    """Test the main ETL pipeline"""

    @pytest.fixture
    def sample_student_data(self):
        """Sample student data for testing"""
        return pd.DataFrame(
            {
                "student_id": ["STU001", "STU002", "STU003"],
                "name": ["Ahmed Rahman", "Fatima Khan", "Mohammad Ali"],
                "gender": ["M", "F", "M"],
                "dob": ["2010-01-15", "2009-05-20", "2011-03-10"],
                "division": ["dhaka", "chittagong", "rajshahi"],
                "phone": ["01712345678", "01823456789", "01934567890"],
            }
        )

    @pytest.fixture
    def pipeline_config(self):
        """Basic pipeline configuration"""
        return PipelineConfig(
            source_type="csv",
            source_path="/tmp/test_data.csv",
            target_table="students",
            batch_size=100,
            validate_data=True,
            dry_run=True,
        )

    def test_pipeline_config_validation(self):
        """Test pipeline configuration validation"""
        # Valid config
        config = PipelineConfig(source_type="csv", source_path="/tmp/test.csv", target_table="students")
        assert config.source_type == "csv"
        assert config.batch_size == 1000  # default

        # Invalid source type
        with pytest.raises(ValueError):
            PipelineConfig(source_type="invalid", source_path="/tmp/test.csv", target_table="students")

    @pytest.mark.asyncio
    async def test_pipeline_execution_success(self, pipeline_config, sample_student_data):
        """Test successful pipeline execution"""
        with patch("src.data_processing.pipeline.CSVExtractor") as mock_extractor_class:
            with patch("src.data_processing.pipeline.StudentDataTransformer") as mock_transformer_class:
                with patch("src.data_processing.pipeline.ValidationLoader") as mock_loader_class:
                    # Setup mocks
                    mock_extractor = Mock()
                    mock_extractor.extract = AsyncMock(return_value=sample_student_data)
                    mock_extractor_class.return_value = mock_extractor

                    mock_transformer = Mock()
                    mock_transformer.transform = AsyncMock(return_value=sample_student_data)
                    mock_transformer_class.return_value = mock_transformer

                    mock_loader = Mock()
                    mock_loader.load = AsyncMock(return_value={"inserted": 3, "updated": 0, "failed": 0, "errors": []})
                    mock_loader_class.return_value = mock_loader

                    # Execute pipeline
                    pipeline = DataPipeline(pipeline_config)
                    result = await pipeline.execute()

                    # Assertions
                    assert result.status == "completed"
                    assert result.records_processed == 3
                    assert result.records_inserted == 3
                    assert result.records_failed == 0
                    assert len(result.processing_errors) == 0

    @pytest.mark.asyncio
    async def test_pipeline_execution_failure(self, pipeline_config):
        """Test pipeline execution with failure"""
        with patch("src.data_processing.pipeline.CSVExtractor") as mock_extractor_class:
            # Setup mock to raise exception
            mock_extractor = Mock()
            mock_extractor.extract = AsyncMock(side_effect=Exception("File not found"))
            mock_extractor_class.return_value = mock_extractor

            # Execute pipeline
            pipeline = DataPipeline(pipeline_config)
            result = await pipeline.execute()

            # Assertions
            assert result.status == "failed"
            assert len(result.processing_errors) > 0
            assert "File not found" in result.processing_errors[0]


class TestExtractors:
    """Test data extractors"""

    @pytest.fixture
    def sample_csv_file(self):
        """Create a temporary CSV file for testing"""
        data = pd.DataFrame({"id": [1, 2, 3], "name": ["Alice", "Bob", "Charlie"], "age": [25, 30, 35]})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            data.to_csv(f.name, index=False)
            yield f.name

        # Cleanup
        os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_csv_extractor_success(self, sample_csv_file):
        """Test successful CSV extraction"""
        extractor = CSVExtractor(sample_csv_file)

        # Test validation
        is_valid = await extractor.validate_source()
        assert is_valid is True

        # Test extraction
        data = await extractor.extract()
        assert len(data) == 3
        assert list(data.columns) == ["id", "name", "age"]
        assert data.iloc[0]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_csv_extractor_file_not_found(self):
        """Test CSV extractor with non-existent file"""
        extractor = CSVExtractor("/nonexistent/file.csv")

        # Test validation
        is_valid = await extractor.validate_source()
        assert is_valid is False

        # Test extraction should raise exception
        with pytest.raises(ValueError):
            await extractor.extract()

    @pytest.mark.asyncio
    async def test_database_extractor_validation(self):
        """Test database extractor validation"""
        # Test with invalid connection string
        extractor = DatabaseExtractor({"connection_string": "invalid://connection", "query": "SELECT * FROM test"})

        is_valid = await extractor.validate_source()
        assert is_valid is False


class TestTransformers:
    """Test data transformers"""

    @pytest.fixture
    def raw_student_data(self):
        """Raw student data before transformation"""
        return pd.DataFrame(
            {
                "student_id": ["stu001", "STU002", " stu003 "],
                "name": ["ahmed rahman", "FATIMA KHAN", "mohammad ali"],
                "sex": ["M", "F", "MALE"],
                "dob": ["2010-01-15", "2009-05-20", "2011-03-10"],
                "division": ["DHAKA", "chittagong", "Rajshahi"],
                "mobile": ["01712345678", "880823456789", "01934567890"],
            }
        )

    @pytest.mark.asyncio
    async def test_student_transformer(self, raw_student_data):
        """Test student data transformation"""
        transformer = StudentDataTransformer()

        # Transform data
        transformed_data = await transformer.transform(raw_student_data)

        # Check transformations
        assert transformed_data["student_id"].iloc[0] == "STU001"  # Cleaned and uppercase
        assert transformed_data["full_name"].iloc[0] == "Ahmed Rahman"  # Title case
        assert transformed_data["gender"].iloc[0] == "Male"  # Standardized
        assert transformed_data["gender"].iloc[2] == "Male"  # MALE -> Male
        assert transformed_data["division"].iloc[0] == "Dhaka"  # Title case

        # Check computed columns
        assert "age" in transformed_data.columns
        assert "age_group" in transformed_data.columns
        assert "created_at" in transformed_data.columns

        # Check phone number normalization
        assert transformed_data["phone_number"].iloc[0] == "+8801712345678"
        assert transformed_data["phone_number"].iloc[1] == "+8801823456789"  # Removed 880 prefix

    @pytest.mark.asyncio
    async def test_student_transformer_missing_columns(self):
        """Test student transformer with missing required columns"""
        incomplete_data = pd.DataFrame(
            {
                "name": ["Ahmed Rahman"],
                "gender": ["M"],
                # Missing student_id, date_of_birth
            }
        )

        transformer = StudentDataTransformer()

        with pytest.raises(ValueError, match="Missing required columns"):
            await transformer.transform(incomplete_data)

    @pytest.fixture
    def raw_school_data(self):
        """Raw school data before transformation"""
        return pd.DataFrame(
            {
                "school_id": ["sch001", "SCH002"],
                "institution_name": ["dhaka high school", "CHITTAGONG COLLEGE"],
                "type": ["GOVT", "PVT"],
                "level": ["SECONDARY", "HIGHER_SECONDARY"],
                "division": ["DHAKA", "chittagong"],
                "phone": ["01712345678", "880823456789"],
            }
        )

    @pytest.mark.asyncio
    async def test_school_transformer(self, raw_school_data):
        """Test school data transformation"""
        transformer = SchoolDataTransformer()

        # Transform data
        transformed_data = await transformer.transform(raw_school_data)

        # Check transformations
        assert transformed_data["school_id"].iloc[0] == "SCH001"  # Uppercase
        assert transformed_data["school_name"].iloc[0] == "Dhaka High School"  # Title case
        assert transformed_data["school_type"].iloc[0] == "Government"  # Standardized
        assert transformed_data["school_type"].iloc[1] == "Private"  # PVT -> Private
        assert transformed_data["education_level"].iloc[0] == "Secondary"  # Standardized

        # Check computed columns
        assert "is_rural" in transformed_data.columns
        assert "operational_status" in transformed_data.columns
        assert transformed_data["operational_status"].iloc[0] == "Active"


class TestLoaders:
    """Test data loaders"""

    @pytest.fixture
    def sample_student_data(self):
        """Sample transformed student data"""
        return pd.DataFrame(
            {
                "student_id": ["STU001", "STU002"],
                "full_name": ["Ahmed Rahman", "Fatima Khan"],
                "gender": ["Male", "Female"],
                "date_of_birth": [date(2010, 1, 15), date(2009, 5, 20)],
                "age": [14, 15],
                "division": ["Dhaka", "Chittagong"],
                "created_at": [datetime.now(), datetime.now()],
                "updated_at": [datetime.now(), datetime.now()],
            }
        )

    @pytest.mark.asyncio
    async def test_database_loader_validation(self, sample_student_data):
        """Test database loader data validation"""
        loader = DatabaseLoader("students")

        # Test with valid data
        errors = await loader.validate_data(sample_student_data)
        assert len(errors) == 0

        # Test with invalid data (missing required column)
        invalid_data = sample_student_data.drop("student_id", axis=1)
        errors = await loader.validate_data(invalid_data)
        assert len(errors) > 0
        assert any("student_id" in error for error in errors)

    @pytest.mark.asyncio
    async def test_validation_loader_business_rules(self, sample_student_data):
        """Test validation loader with business rules"""
        loader = ValidationLoader("students", strict_validation=True)

        # Add invalid age
        invalid_data = sample_student_data.copy()
        invalid_data.loc[0, "age"] = 50  # Invalid age

        errors = await loader.validate_data(invalid_data)
        assert len(errors) > 0
        assert any("age" in error.lower() for error in errors)


class TestValidators:
    """Test data quality validators"""

    @pytest.fixture
    def sample_data_with_issues(self):
        """Sample data with various quality issues"""
        return pd.DataFrame(
            {
                "id": [1, 2, 3, 3, 5],  # Duplicate
                "name": ["Alice", "Bob", None, "David", ""],  # Missing values
                "age": [25, 30, 35, 150, -5],  # Outliers
                "email": ["alice@test.com", "invalid-email", "bob@test.com", "charlie@test.com", None],
                "gender": ["Male", "Female", "Other", "Invalid", "Male"],  # Invalid value
            }
        )

    @pytest.mark.asyncio
    async def test_data_quality_validator(self, sample_data_with_issues):
        """Test comprehensive data quality validation"""
        validator = DataQualityValidator()

        # Add validation rules
        validator.add_validation_rule(
            ValidationRule(rule_name="id_uniqueness", rule_type="uniqueness", column="id", severity="error")
        )

        validator.add_validation_rule(
            ValidationRule(
                rule_name="name_completeness",
                rule_type="completeness",
                column="name",
                parameters={"threshold": 0.8},
                severity="warning",
            )
        )

        validator.add_validation_rule(
            ValidationRule(
                rule_name="gender_validity",
                rule_type="validity",
                column="gender",
                parameters={"valid_values": ["Male", "Female", "Other"]},
                severity="error",
            )
        )

        # Run validation
        result = await validator.validate(sample_data_with_issues)

        # Check results
        assert result.is_valid is False  # Should fail due to errors
        assert result.total_records == 5
        assert len(result.errors) > 0
        assert len(result.warnings) > 0

        # Check specific validations
        error_messages = " ".join(result.errors)
        assert "duplicate" in error_messages.lower()
        assert "invalid" in error_messages.lower()

    @pytest.mark.asyncio
    async def test_completeness_validation(self):
        """Test completeness validation rule"""
        validator = DataQualityValidator()

        data = pd.DataFrame({"complete_col": [1, 2, 3, 4, 5], "incomplete_col": [1, None, 3, None, 5]})  # 60% complete

        # Test with 80% threshold - should fail
        rule = ValidationRule(
            rule_name="completeness_test",
            rule_type="completeness",
            column="incomplete_col",
            parameters={"threshold": 0.8},
            severity="error",
        )

        result = await validator._execute_validation_rule(data, rule)
        assert result["passed"] is False
        assert "completeness" in result["messages"][0].lower()

        # Test with 50% threshold - should pass
        rule.parameters["threshold"] = 0.5
        result = await validator._execute_validation_rule(data, rule)
        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_uniqueness_validation(self):
        """Test uniqueness validation rule"""
        validator = DataQualityValidator()

        data = pd.DataFrame({"unique_col": [1, 2, 3, 4, 5], "duplicate_col": [1, 2, 2, 4, 5]})  # Has duplicates

        # Test unique column
        rule = ValidationRule(rule_name="uniqueness_test", rule_type="uniqueness", column="unique_col", severity="error")

        result = await validator._execute_validation_rule(data, rule)
        assert result["passed"] is True

        # Test duplicate column
        rule.column = "duplicate_col"
        result = await validator._execute_validation_rule(data, rule)
        assert result["passed"] is False
        assert "duplicate" in result["messages"][0].lower()

    @pytest.mark.asyncio
    async def test_validity_validation(self):
        """Test validity validation rule"""
        validator = DataQualityValidator()

        data = pd.DataFrame({"status": ["Active", "Inactive", "Active", "Invalid", "Active"]})

        rule = ValidationRule(
            rule_name="validity_test",
            rule_type="validity",
            column="status",
            parameters={"valid_values": ["Active", "Inactive"]},
            severity="error",
        )

        result = await validator._execute_validation_rule(data, rule)
        assert result["passed"] is False
        assert "invalid values" in result["messages"][0].lower()

    def test_predefined_validation_rules(self):
        """Test predefined validation rule sets"""
        from src.data_processing.validators import get_school_validation_rules, get_student_validation_rules

        student_rules = get_student_validation_rules()
        assert len(student_rules) > 0
        assert any(rule.column == "student_id" for rule in student_rules)
        assert any(rule.rule_type == "completeness" for rule in student_rules)
        assert any(rule.rule_type == "uniqueness" for rule in student_rules)

        school_rules = get_school_validation_rules()
        assert len(school_rules) > 0
        assert any(rule.column == "school_id" for rule in school_rules)


class TestIntegration:
    """Integration tests for the complete ETL pipeline"""

    @pytest.mark.asyncio
    async def test_end_to_end_student_pipeline(self):
        """Test complete student data pipeline"""
        # Create sample CSV data
        sample_data = pd.DataFrame(
            {
                "student_id": ["STU001", "STU002"],
                "name": ["ahmed rahman", "fatima khan"],
                "gender": ["M", "F"],
                "dob": ["2010-01-15", "2009-05-20"],
                "division": ["dhaka", "chittagong"],
            }
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            sample_data.to_csv(f.name, index=False)
            csv_file = f.name

        try:
            # Configure pipeline
            config = PipelineConfig(
                source_type="csv",
                source_path=csv_file,
                target_table="students",
                batch_size=10,
                validate_data=True,
                dry_run=True,  # Don't actually insert to database
            )

            # Mock the database operations
            with patch("src.data_processing.loaders.get_async_session"):
                with patch.object(DatabaseLoader, "_get_model_class") as mock_model:
                    # Mock the model class
                    mock_model.return_value = Mock()
                    mock_model.return_value.__table__ = Mock()
                    mock_model.return_value.__table__.columns = []

                    # Execute pipeline
                    pipeline = DataPipeline(config)
                    result = await pipeline.execute()

                    # Verify results
                    assert result.status == "completed"
                    assert result.records_processed == 2

        finally:
            # Cleanup
            os.unlink(csv_file)

    @pytest.mark.asyncio
    async def test_pipeline_with_validation_errors(self):
        """Test pipeline behavior with validation errors"""
        # Create sample data with validation issues
        invalid_data = pd.DataFrame(
            {
                "student_id": ["", "STU002"],  # Empty student ID
                "name": ["Ahmed Rahman", ""],  # Empty name
                "gender": ["M", "Invalid"],  # Invalid gender
                "dob": ["2010-01-15", "invalid-date"],  # Invalid date
                "division": ["Dhaka", "InvalidDivision"],  # Invalid division
            }
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            invalid_data.to_csv(f.name, index=False)
            csv_file = f.name

        try:
            config = PipelineConfig(
                source_type="csv", source_path=csv_file, target_table="students", validate_data=True, dry_run=True
            )

            # Mock database operations
            with patch("src.data_processing.loaders.get_async_session"):
                with patch.object(DatabaseLoader, "_get_model_class") as mock_model:
                    mock_model.return_value = Mock()
                    mock_model.return_value.__table__ = Mock()
                    mock_model.return_value.__table__.columns = []

                    pipeline = DataPipeline(config)
                    result = await pipeline.execute()

                    # Should complete but with validation warnings/errors
                    assert result.status in ["completed", "failed"]
                    assert len(result.validation_errors) > 0 or len(result.processing_errors) > 0

        finally:
            os.unlink(csv_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
