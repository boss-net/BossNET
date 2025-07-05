"""
Main ETL Pipeline Implementation
===============================
Orchestrates the complete data processing workflow
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from celery import Celery
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.settings import settings
from src.data_processing.extractors import CSVExtractor, DatabaseExtractor, ExcelExtractor
from src.data_processing.loaders import DatabaseLoader, ValidationLoader
from src.data_processing.transformers import SchoolDataTransformer, StudentDataTransformer
from src.data_processing.validators import DataQualityValidator
from src.infrastructure.persistence.sqlalchemy.database import get_async_session

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery(
    "education_etl", broker=settings.REDIS_URL, backend=settings.REDIS_URL, include=["src.data_processing.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Dhaka",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)


class PipelineConfig(BaseModel):
    """Configuration for ETL pipeline execution"""

    source_type: str = Field(..., description="Type of data source (csv, excel, database)")
    source_path: Optional[str] = Field(None, description="Path to source file")
    source_config: Optional[Dict[str, Any]] = Field(None, description="Database connection config")
    target_table: str = Field(..., description="Target database table")
    batch_size: int = Field(1000, description="Processing batch size")
    validate_data: bool = Field(True, description="Enable data validation")
    skip_duplicates: bool = Field(True, description="Skip duplicate records")
    dry_run: bool = Field(False, description="Run without committing changes")

    @validator("source_type")
    def validate_source_type(cls, v):
        valid_types = ["csv", "excel", "database", "api"]
        if v not in valid_types:
            raise ValueError(f"source_type must be one of {valid_types}")
        return v


class PipelineResult(BaseModel):
    """Result of pipeline execution"""

    pipeline_id: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    records_processed: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_failed: int = 0
    validation_errors: List[str] = []
    processing_errors: List[str] = []
    execution_time_seconds: Optional[float] = None


class DataPipeline:
    """Main ETL Pipeline orchestrator"""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.pipeline_id = f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.result = PipelineResult(pipeline_id=self.pipeline_id, status="initialized", start_time=datetime.now())

        # Initialize components
        self.extractor = self._get_extractor()
        self.transformer = self._get_transformer()
        self.loader = self._get_loader()
        self.validator = DataQualityValidator()

    def _get_extractor(self):
        """Get appropriate data extractor based on source type"""
        if self.config.source_type == "csv":
            return CSVExtractor(self.config.source_path)
        elif self.config.source_type == "excel":
            return ExcelExtractor(self.config.source_path)
        elif self.config.source_type == "database":
            return DatabaseExtractor(self.config.source_config)
        else:
            raise ValueError(f"Unsupported source type: {self.config.source_type}")

    def _get_transformer(self):
        """Get appropriate data transformer based on target table"""
        if "student" in self.config.target_table.lower():
            return StudentDataTransformer()
        elif "school" in self.config.target_table.lower():
            return SchoolDataTransformer()
        else:
            # Generic transformer for other tables
            return StudentDataTransformer()  # Default

    def _get_loader(self):
        """Get appropriate data loader"""
        if self.config.validate_data:
            return ValidationLoader(self.config.target_table)
        else:
            return DatabaseLoader(self.config.target_table)

    async def execute(self) -> PipelineResult:
        """Execute the complete ETL pipeline"""
        logger.info(f"Starting pipeline {self.pipeline_id}")
        self.result.status = "running"

        try:
            # Step 1: Extract data
            logger.info("Step 1: Extracting data")
            raw_data = await self.extractor.extract()
            logger.info(f"Extracted {len(raw_data)} records")

            if raw_data.empty:
                self.result.status = "completed"
                self.result.end_time = datetime.now()
                logger.warning("No data to process")
                return self.result

            # Step 2: Transform data
            logger.info("Step 2: Transforming data")
            transformed_data = await self.transformer.transform(raw_data)
            logger.info(f"Transformed {len(transformed_data)} records")

            # Step 3: Validate data (if enabled)
            if self.config.validate_data:
                logger.info("Step 3: Validating data quality")
                validation_result = await self.validator.validate(transformed_data)

                if not validation_result.is_valid:
                    self.result.validation_errors = validation_result.errors
                    logger.error(f"Data validation failed: {validation_result.errors}")

                    if validation_result.critical_errors:
                        self.result.status = "failed"
                        self.result.end_time = datetime.now()
                        return self.result

            # Step 4: Load data in batches
            logger.info("Step 4: Loading data to database")
            load_result = await self._load_in_batches(transformed_data)

            # Update results
            self.result.records_processed = len(raw_data)
            self.result.records_inserted = load_result.get("inserted", 0)
            self.result.records_updated = load_result.get("updated", 0)
            self.result.records_failed = load_result.get("failed", 0)
            self.result.processing_errors = load_result.get("errors", [])

            self.result.status = "completed"
            self.result.end_time = datetime.now()
            self.result.execution_time_seconds = (self.result.end_time - self.result.start_time).total_seconds()

            logger.info(f"Pipeline {self.pipeline_id} completed successfully")
            return self.result

        except Exception as e:
            logger.error(f"Pipeline {self.pipeline_id} failed: {str(e)}")
            self.result.status = "failed"
            self.result.end_time = datetime.now()
            self.result.processing_errors.append(str(e))
            return self.result

    async def _load_in_batches(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Load data in batches to avoid memory issues"""
        batch_size = self.config.batch_size
        total_records = len(data)
        inserted = updated = failed = 0
        errors = []

        for i in range(0, total_records, batch_size):
            batch = data.iloc[i : i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_records + batch_size - 1) // batch_size

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} records)")

            try:
                if not self.config.dry_run:
                    batch_result = await self.loader.load(batch)
                    inserted += batch_result.get("inserted", 0)
                    updated += batch_result.get("updated", 0)
                    failed += batch_result.get("failed", 0)
                else:
                    logger.info(f"DRY RUN: Would process {len(batch)} records")

            except Exception as e:
                error_msg = f"Batch {batch_num} failed: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                failed += len(batch)

        return {"inserted": inserted, "updated": updated, "failed": failed, "errors": errors}


# Celery task for async pipeline execution
@celery_app.task(bind=True)
def run_pipeline_task(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Celery task to run ETL pipeline asynchronously"""
    try:
        config = PipelineConfig(**config_dict)
        pipeline = DataPipeline(config)

        # Run the async pipeline in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(pipeline.execute())
            return result.dict()
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Pipeline task failed: {str(e)}")
        return {
            "pipeline_id": f"failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "status": "failed",
            "start_time": datetime.now().isoformat(),
            "end_time": datetime.now().isoformat(),
            "processing_errors": [str(e)],
        }


# Convenience functions
async def run_student_data_pipeline(source_path: str, source_type: str = "csv") -> PipelineResult:
    """Run pipeline for student data"""
    config = PipelineConfig(
        source_type=source_type, source_path=source_path, target_table="students", batch_size=500, validate_data=True
    )

    pipeline = DataPipeline(config)
    return await pipeline.execute()


async def run_school_data_pipeline(source_path: str, source_type: str = "csv") -> PipelineResult:
    """Run pipeline for school data"""
    config = PipelineConfig(
        source_type=source_type, source_path=source_path, target_table="schools", batch_size=1000, validate_data=True
    )

    pipeline = DataPipeline(config)
    return await pipeline.execute()


def schedule_pipeline(config: PipelineConfig) -> str:
    """Schedule pipeline to run asynchronously with Celery"""
    task = run_pipeline_task.delay(config.dict())
    return task.id
