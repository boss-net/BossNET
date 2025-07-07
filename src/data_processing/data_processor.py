# src/data_processing/data_processor.py

import logging
from src.data_processing.extract_data import extract
from src.data_processing.transform_data import transform
from src.data_processing.load_data import load
from src.validation.data_quality_checks import validate_schema

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def run_etl(source_name: str = "banbeis") -> None:
    logging.info(f"🚀 Starting ETL process for source: {source_name}")

    # Extract
    raw_data = extract(source=source_name)
    logging.info("✅ Data extraction completed.")

    # Validate schema
    if not validate_schema(raw_data):
        logging.error("❌ Schema validation failed. Aborting pipeline.")
        return

    # Transform
    transformed_data = transform(raw_data)
    logging.info("🔄 Data transformation complete.")

    # Load
    load(transformed_data)
    logging.info("📦 Data loaded successfully.")

    logging.info("🎉 ETL process completed successfully.")

if __name__ == "__main__":
    run_etl()
