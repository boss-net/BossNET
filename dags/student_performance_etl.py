"""
Apache Airflow DAG for Student Performance ETL Pipeline
-------------------------------------------------------
Priority P0: Implement Apache Airflow DAGs for ETL workflows
"""

import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.redis.operators.redis import RedisOperator
from airflow.utils.dates import days_ago

# Configure logging
logger = logging.getLogger(__name__)

# Default arguments for the DAG
default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "start_date": days_ago(1),
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "catchup": False,
}

# DAG definition
dag = DAG(
    "student_performance_etl",
    default_args=default_args,
    description="ETL pipeline for student performance data",
    schedule_interval="0 2 * * *",  # Daily at 2 AM
    max_active_runs=1,
    tags=["education", "etl", "student-performance"],
)


def extract_student_data(**context):
    """Extract student data from various sources."""
    import os

    import pandas as pd
    from sqlalchemy import create_engine

    logger.info("Starting student data extraction...")

    try:
        # Connect to source databases
        banbeis_engine = create_engine(os.getenv("BANBEIS_DATABASE_URL"))
        education_board_engine = create_engine(os.getenv("EDUCATION_BOARD_DATABASE_URL"))

        # Extract from BANBEIS
        banbeis_query = """
        SELECT
            student_id,
            full_name,
            gender,
            date_of_birth,
            division,
            district,
            upazila,
            school_id,
            enrollment_date,
            academic_year
        FROM students
        WHERE updated_at >= CURRENT_DATE - INTERVAL '1 day'
        """

        banbeis_df = pd.read_sql(banbeis_query, banbeis_engine)
        logger.info(f"Extracted {len(banbeis_df)} records from BANBEIS")

        # Extract from Education Board
        board_query = """
        SELECT
            student_id,
            subject_name,
            marks_obtained,
            max_marks,
            assessment_date,
            academic_year,
            term,
            assessment_type
        FROM assessment_results
        WHERE assessment_date >= CURRENT_DATE - INTERVAL '7 days'
        """

        board_df = pd.read_sql(board_query, education_board_engine)
        logger.info(f"Extracted {len(board_df)} assessment records from Education Board")

        # Store extracted data for next step
        context["task_instance"].xcom_push(key="banbeis_data", value=banbeis_df.to_json())
        context["task_instance"].xcom_push(key="board_data", value=board_df.to_json())

        return "Extraction completed successfully"

    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}")
        raise


def transform_student_data(**context):
    """Transform and clean student data."""
    from datetime import datetime

    import numpy as np
    import pandas as pd

    logger.info("Starting data transformation...")

    try:
        # Get extracted data
        banbeis_json = context["task_instance"].xcom_pull(key="banbeis_data")
        board_json = context["task_instance"].xcom_pull(key="board_data")

        banbeis_df = pd.read_json(banbeis_json)
        board_df = pd.read_json(board_json)

        # Clean student data
        banbeis_df["date_of_birth"] = pd.to_datetime(banbeis_df["date_of_birth"], errors="coerce")
        banbeis_df["enrollment_date"] = pd.to_datetime(banbeis_df["enrollment_date"], errors="coerce")
        banbeis_df["division"] = banbeis_df["division"].str.title()
        banbeis_df["district"] = banbeis_df["district"].str.title()
        banbeis_df["upazila"] = banbeis_df["upazila"].str.title()

        # Calculate age
        banbeis_df["age"] = (datetime.now() - banbeis_df["date_of_birth"]).dt.days // 365
        banbeis_df["age_group"] = pd.cut(
            banbeis_df["age"], bins=[0, 5, 10, 15, 20, 25, 100], labels=["0-4", "5-9", "10-14", "15-19", "20-24", "25+"]
        )

        # Clean assessment data
        board_df["assessment_date"] = pd.to_datetime(board_df["assessment_date"], errors="coerce")
        board_df["percentage"] = (board_df["marks_obtained"] / board_df["max_marks"]) * 100
        board_df["is_passed"] = board_df["percentage"] >= 33

        # Add grade letters
        def get_grade_letter(percentage):
            if percentage >= 80:
                return "A+"
            elif percentage >= 70:
                return "A"
            elif percentage >= 60:
                return "A-"
            elif percentage >= 50:
                return "B"
            elif percentage >= 40:
                return "C"
            elif percentage >= 33:
                return "D"
            else:
                return "F"

        board_df["grade_letter"] = board_df["percentage"].apply(get_grade_letter)

        # Store transformed data
        context["task_instance"].xcom_push(key="transformed_students", value=banbeis_df.to_json())
        context["task_instance"].xcom_push(key="transformed_assessments", value=board_df.to_json())

        logger.info("Data transformation completed successfully")
        return "Transformation completed successfully"

    except Exception as e:
        logger.error(f"Transformation failed: {str(e)}")
        raise


def load_student_data(**context):
    """Load transformed data into the data warehouse."""
    import os

    import pandas as pd
    from sqlalchemy import create_engine

    logger.info("Starting data loading...")

    try:
        # Get transformed data
        students_json = context["task_instance"].xcom_pull(key="transformed_students")
        assessments_json = context["task_instance"].xcom_pull(key="transformed_assessments")

        students_df = pd.read_json(students_json)
        assessments_df = pd.read_json(assessments_json)

        # Connect to data warehouse
        dw_engine = create_engine(os.getenv("DATA_WAREHOUSE_URL"))

        # Load students dimension
        students_df.to_sql("stg_students", dw_engine, if_exists="append", index=False, method="multi")
        logger.info(f"Loaded {len(students_df)} student records")

        # Load assessment results
        assessments_df.to_sql("stg_assessment_results", dw_engine, if_exists="append", index=False, method="multi")
        logger.info(f"Loaded {len(assessments_df)} assessment records")

        return "Data loading completed successfully"

    except Exception as e:
        logger.error(f"Data loading failed: {str(e)}")
        raise


def run_dbt_models(**context):
    """Run dbt models to transform staging data."""
    logger.info("Starting dbt model execution...")

    try:
        # This would typically call dbt commands
        # For now, we'll simulate the process
        import os
        import subprocess

        # Change to dbt project directory
        os.chdir("/app/dbt")

        # Run dbt models
        result = subprocess.run(
            [
                "dbt",
                "run",
                "--models",
                "dim_students",
                "dim_schools",
                "fct_assessment_results",
                "--vars",
                '{"execution_date": "' + context["ds"] + '"}',
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise Exception(f"dbt run failed: {result.stderr}")

        logger.info("dbt models executed successfully")
        return "dbt models completed successfully"

    except Exception as e:
        logger.error(f"dbt execution failed: {str(e)}")
        raise


def validate_data_quality(**context):
    """Validate data quality using Great Expectations."""
    logger.info("Starting data quality validation...")

    try:
        import os

        import great_expectations as ge
        import pandas as pd
        from great_expectations.core.batch import RuntimeBatchRequest
        from sqlalchemy import create_engine

        # Connect to data warehouse
        dw_engine = create_engine(os.getenv("DATA_WAREHOUSE_URL"))

        # Load data for validation
        students_df = pd.read_sql("SELECT * FROM dimensions.dim_students WHERE is_current = TRUE", dw_engine)
        assessments_df = pd.read_sql(
            "SELECT * FROM facts.fct_assessment_results WHERE assessment_date >= CURRENT_DATE - INTERVAL '7 days'", dw_engine
        )

        # Initialize Great Expectations
        context = ge.get_context()

        # Validate student data
        student_batch = RuntimeBatchRequest(
            datasource_name="postgres_datasource",
            data_connector_name="default_runtime_data_connector_name",
            data_asset_name="students",
            runtime_parameters={"batch_data": students_df},
            batch_identifiers={"default_identifier_name": "default_identifier"},
        )

        # Run expectations
        results = context.run_validation_operator(
            "action_list_operator", assets_to_validate=[student_batch], expectation_suite_name="student_data_suite"
        )

        if not results.success:
            logger.error("Data quality validation failed")
            raise Exception("Data quality validation failed")

        logger.info("Data quality validation passed")
        return "Data quality validation completed successfully"

    except Exception as e:
        logger.error(f"Data quality validation failed: {str(e)}")
        raise


def clear_cache(**context):
    """Clear Redis cache for dashboard data."""
    logger.info("Clearing dashboard cache...")

    try:
        import os

        import redis

        redis_client = redis.from_url(os.getenv("REDIS_URL"))
        redis_client.flushdb()

        logger.info("Cache cleared successfully")
        return "Cache cleared successfully"

    except Exception as e:
        logger.error(f"Cache clearing failed: {str(e)}")
        raise


# Define tasks
extract_task = PythonOperator(
    task_id="extract_student_data",
    python_callable=extract_student_data,
    dag=dag,
)

transform_task = PythonOperator(
    task_id="transform_student_data",
    python_callable=transform_student_data,
    dag=dag,
)

load_task = PythonOperator(
    task_id="load_student_data",
    python_callable=load_student_data,
    dag=dag,
)

dbt_task = PythonOperator(
    task_id="run_dbt_models",
    python_callable=run_dbt_models,
    dag=dag,
)

validate_task = PythonOperator(
    task_id="validate_data_quality",
    python_callable=validate_data_quality,
    dag=dag,
)

clear_cache_task = PythonOperator(
    task_id="clear_cache",
    python_callable=clear_cache,
    dag=dag,
)

# Define task dependencies
extract_task >> transform_task >> load_task >> dbt_task >> validate_task >> clear_cache_task
