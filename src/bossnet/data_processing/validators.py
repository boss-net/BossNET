"""
Data Quality Validators
======================
Comprehensive data validation using Great Expectations and custom rules
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union

import great_expectations as ge
import numpy as np
import pandas as pd
from great_expectations.checkpoint import SimpleCheckpoint
from great_expectations.core.batch import RuntimeBatchRequest
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ValidationRule(BaseModel):
    """Configuration for a validation rule"""

    rule_name: str
    rule_type: str  # completeness, uniqueness, validity, consistency, accuracy
    column: Optional[str] = None
    parameters: Dict[str, Any] = {}
    severity: str = "error"  # error, warning, info
    description: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of data validation"""

    is_valid: bool
    total_records: int
    valid_records: int
    invalid_records: int
    errors: List[str] = []
    warnings: List[str] = []
    critical_errors: List[str] = []
    validation_details: Dict[str, Any] = {}
    execution_time_seconds: Optional[float] = None


class DataQualityValidator:
    """Comprehensive data quality validator"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self.validation_rules: List[ValidationRule] = []
        self.ge_context = None
        self._initialize_great_expectations()

    def _initialize_great_expectations(self):
        """Initialize Great Expectations context"""
        try:
            self.ge_context = ge.get_context()
            self.logger.info("Great Expectations context initialized")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Great Expectations: {str(e)}")
            self.ge_context = None

    def add_validation_rule(self, rule: ValidationRule):
        """Add a validation rule"""
        self.validation_rules.append(rule)
        self.logger.debug(f"Added validation rule: {rule.rule_name}")

    async def validate(self, data: pd.DataFrame, table_name: str = "data") -> ValidationResult:
        """Perform comprehensive data validation"""
        start_time = datetime.now()

        result = ValidationResult(is_valid=True, total_records=len(data), valid_records=0, invalid_records=0)

        try:
            self.logger.info(f"Starting validation of {len(data)} records")

            # Basic data structure validation
            structure_errors = self._validate_data_structure(data)
            if structure_errors:
                result.errors.extend(structure_errors)
                result.is_valid = False

            # Apply custom validation rules
            custom_errors, custom_warnings = await self._apply_custom_rules(data)
            result.errors.extend(custom_errors)
            result.warnings.extend(custom_warnings)

            # Great Expectations validation
            if self.ge_context:
                ge_result = await self._run_great_expectations(data, table_name)
                result.validation_details["great_expectations"] = ge_result

                if not ge_result.get("success", True):
                    result.errors.extend(ge_result.get("errors", []))
                    result.is_valid = False

            # Statistical validation
            stats_result = self._validate_statistics(data)
            result.validation_details["statistics"] = stats_result
            result.warnings.extend(stats_result.get("warnings", []))

            # Business rule validation
            business_errors = await self._validate_business_rules(data, table_name)
            result.errors.extend(business_errors)

            # Calculate final results
            if result.errors:
                result.is_valid = False
                result.critical_errors = [e for e in result.errors if "critical" in e.lower()]

            result.invalid_records = len(data) - result.valid_records if result.valid_records == 0 else result.invalid_records
            result.valid_records = len(data) - result.invalid_records

            # Execution time
            end_time = datetime.now()
            result.execution_time_seconds = (end_time - start_time).total_seconds()

            self.logger.info(
                f"Validation completed: {result.valid_records}/{result.total_records} valid records, "
                f"{len(result.errors)} errors, {len(result.warnings)} warnings"
            )

            return result

        except Exception as e:
            self.logger.error(f"Validation failed: {str(e)}")
            result.errors.append(f"Validation process failed: {str(e)}")
            result.is_valid = False
            return result

    def _validate_data_structure(self, data: pd.DataFrame) -> List[str]:
        """Validate basic data structure"""
        errors = []

        if data.empty:
            errors.append("CRITICAL: DataFrame is empty")
            return errors

        # Check for completely empty columns
        empty_columns = data.columns[data.isnull().all()].tolist()
        if empty_columns:
            errors.append(f"Columns are completely empty: {empty_columns}")

        # Check for duplicate column names
        duplicate_columns = data.columns[data.columns.duplicated()].tolist()
        if duplicate_columns:
            errors.append(f"CRITICAL: Duplicate column names found: {duplicate_columns}")

        # Check for unnamed columns
        unnamed_columns = [col for col in data.columns if str(col).startswith("Unnamed:")]
        if unnamed_columns:
            errors.append(f"Unnamed columns found: {unnamed_columns}")

        return errors

    async def _apply_custom_rules(self, data: pd.DataFrame) -> tuple[List[str], List[str]]:
        """Apply custom validation rules"""
        errors = []
        warnings = []

        for rule in self.validation_rules:
            try:
                rule_result = await self._execute_validation_rule(data, rule)

                if rule.severity == "error" and not rule_result["passed"]:
                    errors.extend(rule_result["messages"])
                elif rule.severity == "warning" and not rule_result["passed"]:
                    warnings.extend(rule_result["messages"])

            except Exception as e:
                errors.append(f"Rule '{rule.rule_name}' execution failed: {str(e)}")

        return errors, warnings

    async def _execute_validation_rule(self, data: pd.DataFrame, rule: ValidationRule) -> Dict[str, Any]:
        """Execute a single validation rule"""
        result = {"passed": True, "messages": []}

        if rule.rule_type == "completeness":
            result = self._check_completeness(data, rule)
        elif rule.rule_type == "uniqueness":
            result = self._check_uniqueness(data, rule)
        elif rule.rule_type == "validity":
            result = self._check_validity(data, rule)
        elif rule.rule_type == "consistency":
            result = self._check_consistency(data, rule)
        elif rule.rule_type == "accuracy":
            result = self._check_accuracy(data, rule)
        else:
            result["passed"] = False
            result["messages"] = [f"Unknown rule type: {rule.rule_type}"]

        return result

    def _check_completeness(self, data: pd.DataFrame, rule: ValidationRule) -> Dict[str, Any]:
        """Check data completeness"""
        column = rule.column
        threshold = rule.parameters.get("threshold", 0.95)  # 95% completeness by default

        if column not in data.columns:
            return {"passed": False, "messages": [f"Column '{column}' not found"]}

        completeness_ratio = 1 - (data[column].isnull().sum() / len(data))

        if completeness_ratio < threshold:
            return {
                "passed": False,
                "messages": [f"Column '{column}' completeness {completeness_ratio:.2%} below threshold {threshold:.2%}"],
            }

        return {"passed": True, "messages": []}

    def _check_uniqueness(self, data: pd.DataFrame, rule: ValidationRule) -> Dict[str, Any]:
        """Check data uniqueness"""
        columns = rule.parameters.get("columns", [rule.column])

        if not all(col in data.columns for col in columns):
            missing = [col for col in columns if col not in data.columns]
            return {"passed": False, "messages": [f"Columns not found: {missing}"]}

        duplicates = data.duplicated(subset=columns).sum()

        if duplicates > 0:
            return {"passed": False, "messages": [f"Found {duplicates} duplicate records in columns: {columns}"]}

        return {"passed": True, "messages": []}

    def _check_validity(self, data: pd.DataFrame, rule: ValidationRule) -> Dict[str, Any]:
        """Check data validity"""
        column = rule.column
        valid_values = rule.parameters.get("valid_values", [])
        pattern = rule.parameters.get("pattern")
        min_value = rule.parameters.get("min_value")
        max_value = rule.parameters.get("max_value")

        if column not in data.columns:
            return {"passed": False, "messages": [f"Column '{column}' not found"]}

        messages = []

        # Check valid values
        if valid_values:
            invalid_mask = ~data[column].isin(valid_values) & data[column].notna()
            invalid_count = invalid_mask.sum()
            if invalid_count > 0:
                messages.append(f"Column '{column}' has {invalid_count} invalid values")

        # Check pattern
        if pattern:
            invalid_pattern = ~data[column].astype(str).str.match(pattern, na=True)
            invalid_pattern_count = invalid_pattern.sum()
            if invalid_pattern_count > 0:
                messages.append(f"Column '{column}' has {invalid_pattern_count} values not matching pattern")

        # Check numeric ranges
        if min_value is not None:
            below_min = (data[column] < min_value) & data[column].notna()
            below_min_count = below_min.sum()
            if below_min_count > 0:
                messages.append(f"Column '{column}' has {below_min_count} values below minimum {min_value}")

        if max_value is not None:
            above_max = (data[column] > max_value) & data[column].notna()
            above_max_count = above_max.sum()
            if above_max_count > 0:
                messages.append(f"Column '{column}' has {above_max_count} values above maximum {max_value}")

        return {"passed": len(messages) == 0, "messages": messages}

    def _check_consistency(self, data: pd.DataFrame, rule: ValidationRule) -> Dict[str, Any]:
        """Check data consistency"""
        # Example: Check if enrollment_date is before graduation_date
        date_columns = rule.parameters.get("date_columns", [])

        if len(date_columns) != 2:
            return {"passed": False, "messages": ["Consistency check requires exactly 2 date columns"]}

        col1, col2 = date_columns
        if col1 not in data.columns or col2 not in data.columns:
            return {"passed": False, "messages": [f"Date columns not found: {date_columns}"]}

        # Convert to datetime
        try:
            date1 = pd.to_datetime(data[col1], errors="coerce")
            date2 = pd.to_datetime(data[col2], errors="coerce")

            # Check if first date is before second date
            inconsistent = (date1 > date2) & date1.notna() & date2.notna()
            inconsistent_count = inconsistent.sum()

            if inconsistent_count > 0:
                return {"passed": False, "messages": [f"{inconsistent_count} records have {col1} after {col2}"]}

        except Exception as e:
            return {"passed": False, "messages": [f"Date consistency check failed: {str(e)}"]}

        return {"passed": True, "messages": []}

    def _check_accuracy(self, data: pd.DataFrame, rule: ValidationRule) -> Dict[str, Any]:
        """Check data accuracy using reference data"""
        # This would typically involve checking against external reference data
        # For now, implement basic accuracy checks

        column = rule.column
        reference_values = rule.parameters.get("reference_values", {})

        if column not in data.columns:
            return {"passed": False, "messages": [f"Column '{column}' not found"]}

        # Example: Check if division names are accurate
        if reference_values:
            inaccurate_mask = ~data[column].isin(reference_values) & data[column].notna()
            inaccurate_count = inaccurate_mask.sum()

            if inaccurate_count > 0:
                return {
                    "passed": False,
                    "messages": [f"Column '{column}' has {inaccurate_count} potentially inaccurate values"],
                }

        return {"passed": True, "messages": []}

    async def _run_great_expectations(self, data: pd.DataFrame, table_name: str) -> Dict[str, Any]:
        """Run Great Expectations validation"""
        if not self.ge_context:
            return {"success": True, "message": "Great Expectations not available"}

        try:
            # Create a batch request
            batch_request = RuntimeBatchRequest(
                datasource_name="pandas_datasource",
                data_connector_name="default_runtime_data_connector_name",
                data_asset_name=table_name,
                runtime_parameters={"batch_data": data},
                batch_identifiers={"default_identifier_name": "default_identifier"},
            )

            # Get or create expectation suite
            suite_name = f"{table_name}_suite"
            try:
                suite = self.ge_context.get_expectation_suite(suite_name)
            except:
                suite = self.ge_context.create_expectation_suite(suite_name)
                self._add_default_expectations(suite, data)

            # Run validation
            checkpoint_config = {
                "name": f"{table_name}_checkpoint",
                "config_version": 1.0,
                "template_name": None,
                "module_name": "great_expectations.checkpoint",
                "class_name": "SimpleCheckpoint",
                "run_name_template": "%Y%m%d-%H%M%S-my-run-name-template",
                "expectation_suite_name": suite_name,
                "batch_request": batch_request,
                "action_list": [
                    {
                        "name": "store_validation_result",
                        "action": {"class_name": "StoreValidationResultAction"},
                    }
                ],
            }

            checkpoint = SimpleCheckpoint(f"{table_name}_checkpoint", self.ge_context, **checkpoint_config)

            checkpoint_result = checkpoint.run()

            # Extract results
            validation_result = checkpoint_result.list_validation_results()[0]

            return {
                "success": validation_result.success,
                "statistics": validation_result.statistics,
                "results": [
                    {
                        "expectation_type": result.expectation_config.expectation_type,
                        "success": result.success,
                        "result": result.result,
                    }
                    for result in validation_result.results
                ],
                "errors": [
                    f"Expectation failed: {result.expectation_config.expectation_type}"
                    for result in validation_result.results
                    if not result.success
                ],
            }

        except Exception as e:
            self.logger.error(f"Great Expectations validation failed: {str(e)}")
            return {"success": False, "error": str(e), "errors": [str(e)]}

    def _add_default_expectations(self, suite, data: pd.DataFrame):
        """Add default expectations for common data quality checks"""
        try:
            # Table-level expectations
            suite.expect_table_row_count_to_be_between(min_value=1)
            suite.expect_table_columns_to_match_ordered_list(column_list=data.columns.tolist())

            # Column-level expectations
            for column in data.columns:
                # Basic existence
                suite.expect_column_to_exist(column)

                # Type-specific expectations
                if data[column].dtype in ["object", "string"]:
                    # String columns
                    if data[column].notna().any():
                        suite.expect_column_values_to_not_be_null(column)
                        suite.expect_column_value_lengths_to_be_between(column, min_value=1, max_value=1000)

                elif data[column].dtype in ["int64", "float64"]:
                    # Numeric columns
                    if data[column].notna().any():
                        min_val = data[column].min()
                        max_val = data[column].max()
                        suite.expect_column_values_to_be_between(column, min_value=min_val, max_value=max_val)

                elif "datetime" in str(data[column].dtype):
                    # Date columns
                    suite.expect_column_values_to_be_of_type(column, "datetime64")

        except Exception as e:
            self.logger.warning(f"Failed to add default expectations: {str(e)}")

    def _validate_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Validate statistical properties of the data"""
        stats = {
            "warnings": [],
            "row_count": len(data),
            "column_count": len(data.columns),
            "memory_usage_mb": data.memory_usage(deep=True).sum() / 1024 / 1024,
            "null_percentages": {},
            "outliers": {},
        }

        # Check null percentages
        for column in data.columns:
            null_pct = (data[column].isnull().sum() / len(data)) * 100
            stats["null_percentages"][column] = null_pct

            if null_pct > 50:
                stats["warnings"].append(f"Column '{column}' has {null_pct:.1f}% null values")

        # Check for outliers in numeric columns
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        for column in numeric_columns:
            if data[column].notna().any():
                Q1 = data[column].quantile(0.25)
                Q3 = data[column].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR

                outliers = ((data[column] < lower_bound) | (data[column] > upper_bound)) & data[column].notna()
                outlier_count = outliers.sum()
                outlier_pct = (outlier_count / len(data)) * 100

                stats["outliers"][column] = {"count": int(outlier_count), "percentage": outlier_pct}

                if outlier_pct > 5:  # More than 5% outliers
                    stats["warnings"].append(f"Column '{column}' has {outlier_pct:.1f}% outliers")

        return stats

    async def _validate_business_rules(self, data: pd.DataFrame, table_name: str) -> List[str]:
        """Validate business-specific rules"""
        errors = []

        if table_name.lower() == "students":
            errors.extend(self._validate_student_business_rules(data))
        elif table_name.lower() == "schools":
            errors.extend(self._validate_school_business_rules(data))
        elif table_name.lower() == "enrollments":
            errors.extend(self._validate_enrollment_business_rules(data))

        return errors

    def _validate_student_business_rules(self, data: pd.DataFrame) -> List[str]:
        """Validate student-specific business rules"""
        errors = []

        # Age validation
        if "age" in data.columns:
            invalid_ages = (data["age"] < 3) | (data["age"] > 25)
            if invalid_ages.any():
                count = invalid_ages.sum()
                errors.append(f"BUSINESS RULE VIOLATION: {count} students have unrealistic ages")

        # Date of birth vs enrollment date
        if "date_of_birth" in data.columns and "enrollment_date" in data.columns:
            try:
                dob = pd.to_datetime(data["date_of_birth"], errors="coerce")
                enrollment = pd.to_datetime(data["enrollment_date"], errors="coerce")

                # Check if enrollment is before birth
                invalid_dates = (enrollment < dob) & dob.notna() & enrollment.notna()
                if invalid_dates.any():
                    count = invalid_dates.sum()
                    errors.append(f"BUSINESS RULE VIOLATION: {count} students enrolled before birth date")

            except Exception as e:
                errors.append(f"Date validation failed: {str(e)}")

        return errors

    def _validate_school_business_rules(self, data: pd.DataFrame) -> List[str]:
        """Validate school-specific business rules"""
        errors = []

        # Check for valid Bangladesh divisions
        if "division" in data.columns:
            valid_divisions = ["Dhaka", "Chittagong", "Rajshahi", "Khulna", "Barisal", "Sylhet", "Rangpur", "Mymensingh"]
            invalid_divisions = ~data["division"].isin(valid_divisions) & data["division"].notna()
            if invalid_divisions.any():
                count = invalid_divisions.sum()
                errors.append(f"BUSINESS RULE VIOLATION: {count} schools have invalid division names")

        return errors

    def _validate_enrollment_business_rules(self, data: pd.DataFrame) -> List[str]:
        """Validate enrollment-specific business rules"""
        errors = []

        # Check academic year format and validity
        if "academic_year" in data.columns:
            current_year = datetime.now().year
            try:
                years = pd.to_numeric(data["academic_year"], errors="coerce")
                invalid_years = (years < 2000) | (years > current_year + 1)
                if invalid_years.any():
                    count = invalid_years.sum()
                    errors.append(f"BUSINESS RULE VIOLATION: {count} enrollments have invalid academic years")
            except Exception:
                errors.append("Academic year validation failed - non-numeric values found")

        return errors


# Predefined validation rule sets
def get_student_validation_rules() -> List[ValidationRule]:
    """Get standard validation rules for student data"""
    return [
        ValidationRule(
            rule_name="student_id_completeness",
            rule_type="completeness",
            column="student_id",
            parameters={"threshold": 1.0},
            severity="error",
            description="Student ID must be present for all records",
        ),
        ValidationRule(
            rule_name="student_id_uniqueness",
            rule_type="uniqueness",
            column="student_id",
            severity="error",
            description="Student ID must be unique",
        ),
        ValidationRule(
            rule_name="gender_validity",
            rule_type="validity",
            column="gender",
            parameters={"valid_values": ["Male", "Female", "Other", "Unknown"]},
            severity="error",
            description="Gender must be one of the valid values",
        ),
        ValidationRule(
            rule_name="age_range",
            rule_type="validity",
            column="age",
            parameters={"min_value": 3, "max_value": 25},
            severity="warning",
            description="Age should be between 3 and 25 years",
        ),
        ValidationRule(
            rule_name="phone_format",
            rule_type="validity",
            column="phone_number",
            parameters={"pattern": r"^\+880\d{10}$"},
            severity="warning",
            description="Phone number should follow Bangladesh format",
        ),
    ]


def get_school_validation_rules() -> List[ValidationRule]:
    """Get standard validation rules for school data"""
    return [
        ValidationRule(
            rule_name="school_id_completeness",
            rule_type="completeness",
            column="school_id",
            parameters={"threshold": 1.0},
            severity="error",
            description="School ID must be present for all records",
        ),
        ValidationRule(
            rule_name="school_name_completeness",
            rule_type="completeness",
            column="school_name",
            parameters={"threshold": 1.0},
            severity="error",
            description="School name must be present for all records",
        ),
        ValidationRule(
            rule_name="division_validity",
            rule_type="accuracy",
            column="division",
            parameters={
                "reference_values": ["Dhaka", "Chittagong", "Rajshahi", "Khulna", "Barisal", "Sylhet", "Rangpur", "Mymensingh"]
            },
            severity="error",
            description="Division must be a valid Bangladesh division",
        ),
    ]
