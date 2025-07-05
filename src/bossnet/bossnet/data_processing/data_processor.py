#!/usr/bin/env python3
"""Data Processing Module for Bangladesh Student Data Analysis.

This module provides core functionality for processing educational data from various sources
including BANBEIS, Education Board, and other institutional data sources.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class DataProcessor:
    """Core class for processing educational data."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the DataProcessor.

        Args:
            config_path (str, optional): Path to configuration file
        """
        self.raw_data_path = Path("raw_data")
        self.processed_data_path = Path("processed_data")
        self.logger = logging.getLogger(__name__)

        # Ensure required directories exist
        self.processed_data_path.mkdir(exist_ok=True)
        self.raw_data_path.mkdir(exist_ok=True)

    def load_student_data(self, source: str) -> pd.DataFrame:
        """Load student data from specified source.

        Args:
            source (str): Data source identifier ('banbeis', 'education_board', etc.)

        Returns:
            pd.DataFrame: Loaded student data
        """
        source_path = self.raw_data_path / source
        if not source_path.exists():
            raise FileNotFoundError(f"Data source directory not found: {source_path}")

        dfs = []
        for file in source_path.glob("*.csv"):
            try:
                df = pd.read_csv(file)
                dfs.append(df)
            except Exception as e:
                self.logger.error(f"Error loading file {file}: {str(e)}")

        if not dfs:
            raise ValueError(f"No valid data files found in {source_path}")

        return pd.concat(dfs, ignore_index=True)

    def clean_student_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and preprocess student data.

        Args:
            df (pd.DataFrame): Raw student data

        Returns:
            pd.DataFrame: Cleaned student data
        """
        # Create copy to avoid modifying original data
        cleaned_df = df.copy()

        # Basic cleaning operations
        cleaned_df = cleaned_df.dropna(subset=["student_id"])  # Remove rows with missing student IDs
        cleaned_df = cleaned_df.drop_duplicates(subset=["student_id"])  # Remove duplicate students

        # Standardize column names
        cleaned_df.columns = cleaned_df.columns.str.lower().str.replace(" ", "_")

        # Convert date columns
        date_columns = ["date_of_birth", "enrollment_date"]
        for col in date_columns:
            if col in cleaned_df.columns:
                cleaned_df[col] = pd.to_datetime(cleaned_df[col], errors="coerce")

        # Standardize geographic information
        if "division" in cleaned_df.columns:
            cleaned_df["division"] = cleaned_df["division"].str.title()
        if "district" in cleaned_df.columns:
            cleaned_df["district"] = cleaned_df["district"].str.title()

        return cleaned_df

    def calculate_performance_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate academic performance metrics.

        Args:
            df (pd.DataFrame): Student data with academic information

        Returns:
            pd.DataFrame: Data with calculated performance metrics
        """
        metrics_df = df.copy()

        # Calculate GPA if not present
        if "gpa" not in metrics_df.columns and "subject_grades" in metrics_df.columns:
            # Example GPA calculation (modify according to your grading system)
            metrics_df["gpa"] = metrics_df["subject_grades"].apply(self._calculate_gpa)

        # Calculate attendance rate
        if all(col in metrics_df.columns for col in ["days_present", "total_school_days"]):
            metrics_df["attendance_rate"] = (metrics_df["days_present"] / metrics_df["total_school_days"]).round(3)

        # Add performance indicators
        if "gpa" in metrics_df.columns:
            metrics_df["performance_level"] = metrics_df["gpa"].apply(self._get_performance_level)

        return metrics_df

    @staticmethod
    def _calculate_gpa(grades: Union[str, List]) -> float:
        """Calculate GPA from subject grades."""
        # Implement your GPA calculation logic here
        # This is a placeholder implementation
        return 4.0

    @staticmethod
    def _get_performance_level(gpa: float) -> str:
        """Determine performance level based on GPA."""
        if gpa >= 4.0:
            return "Excellent"
        elif gpa >= 3.5:
            return "Very Good"
        elif gpa >= 3.0:
            return "Good"
        elif gpa >= 2.0:
            return "Average"
        else:
            return "Needs Improvement"

    def process_institutional_data(self, institution_id: str) -> Dict:
        """Process data for a specific institution.

        Args:
            institution_id (str): Unique identifier for the institution

        Returns:
            Dict: Processed institutional metrics
        """
        try:
            # Load institution-specific data
            student_data = self.load_student_data(f"institution_{institution_id}")
            cleaned_data = self.clean_student_data(student_data)
            performance_data = self.calculate_performance_metrics(cleaned_data)

            # Calculate institutional metrics
            metrics = {
                "total_students": len(performance_data),
                "average_gpa": performance_data["gpa"].mean(),
                "attendance_rate": performance_data["attendance_rate"].mean(),
                "performance_distribution": performance_data["performance_level"].value_counts().to_dict(),
                "processed_date": datetime.now().isoformat(),
            }

            return metrics

        except Exception as e:
            self.logger.error(f"Error processing institution {institution_id}: {str(e)}")
            raise


def main():
    """Main function to demonstrate usage."""
    try:
        # Initialize processor
        processor = DataProcessor()

        # Example: Process data for a specific institution
        institution_id = "12345"
        metrics = processor.process_institutional_data(institution_id)

        # Log results
        logger.info(f"Processed metrics for institution {institution_id}:")
        logger.info(metrics)

    except Exception as e:
        logger.error(f"Error in main processing: {str(e)}")
        raise


if __name__ == "__main__":
    main()
