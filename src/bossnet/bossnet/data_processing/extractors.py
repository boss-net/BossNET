"""
Data Extractors
===============
Extract data from various sources (CSV, Excel, Database, APIs)
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiofiles
import aiohttp
import openpyxl
import pandas as pd
from pydantic import BaseModel, Field, validator
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

logger = logging.getLogger(__name__)


class ExtractionResult(BaseModel):
    """Result of data extraction"""

    success: bool
    records_count: int
    columns: List[str]
    errors: List[str] = []
    metadata: Dict[str, Any] = {}


class BaseExtractor(ABC):
    """Abstract base class for data extractors"""

    def __init__(self, source_config: Dict[str, Any]):
        self.source_config = source_config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def extract(self) -> pd.DataFrame:
        """Extract data and return as DataFrame"""
        pass

    @abstractmethod
    async def validate_source(self) -> bool:
        """Validate that the data source is accessible"""
        pass


class CSVExtractor(BaseExtractor):
    """Extract data from CSV files"""

    def __init__(self, file_path: str, **kwargs):
        super().__init__({"file_path": file_path, **kwargs})
        self.file_path = Path(file_path)
        self.encoding = kwargs.get("encoding", "utf-8")
        self.delimiter = kwargs.get("delimiter", ",")
        self.skip_rows = kwargs.get("skip_rows", 0)
        self.chunk_size = kwargs.get("chunk_size", 10000)

    async def validate_source(self) -> bool:
        """Check if CSV file exists and is readable"""
        try:
            if not self.file_path.exists():
                self.logger.error(f"CSV file not found: {self.file_path}")
                return False

            if not self.file_path.is_file():
                self.logger.error(f"Path is not a file: {self.file_path}")
                return False

            # Try to read first few lines
            async with aiofiles.open(self.file_path, "r", encoding=self.encoding) as f:
                first_line = await f.readline()
                if not first_line.strip():
                    self.logger.error("CSV file appears to be empty")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating CSV source: {str(e)}")
            return False

    async def extract(self) -> pd.DataFrame:
        """Extract data from CSV file"""
        try:
            if not await self.validate_source():
                raise ValueError(f"Invalid CSV source: {self.file_path}")

            self.logger.info(f"Extracting data from CSV: {self.file_path}")

            # Read CSV in chunks for large files
            chunks = []
            chunk_count = 0

            for chunk in pd.read_csv(
                self.file_path,
                encoding=self.encoding,
                delimiter=self.delimiter,
                skiprows=self.skip_rows,
                chunksize=self.chunk_size,
                low_memory=False,
            ):
                chunks.append(chunk)
                chunk_count += 1
                self.logger.debug(f"Read chunk {chunk_count} with {len(chunk)} records")

            # Combine all chunks
            if chunks:
                df = pd.concat(chunks, ignore_index=True)
                self.logger.info(f"Successfully extracted {len(df)} records from CSV")
                return df
            else:
                self.logger.warning("No data found in CSV file")
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Error extracting from CSV: {str(e)}")
            raise


class ExcelExtractor(BaseExtractor):
    """Extract data from Excel files"""

    def __init__(self, file_path: str, **kwargs):
        super().__init__({"file_path": file_path, **kwargs})
        self.file_path = Path(file_path)
        self.sheet_name = kwargs.get("sheet_name", 0)  # First sheet by default
        self.header_row = kwargs.get("header_row", 0)
        self.skip_rows = kwargs.get("skip_rows", 0)

    async def validate_source(self) -> bool:
        """Check if Excel file exists and is readable"""
        try:
            if not self.file_path.exists():
                self.logger.error(f"Excel file not found: {self.file_path}")
                return False

            if not self.file_path.suffix.lower() in [".xlsx", ".xls"]:
                self.logger.error(f"File is not an Excel file: {self.file_path}")
                return False

            # Try to open the file
            try:
                workbook = openpyxl.load_workbook(self.file_path, read_only=True)
                workbook.close()
                return True
            except Exception as e:
                self.logger.error(f"Cannot open Excel file: {str(e)}")
                return False

        except Exception as e:
            self.logger.error(f"Error validating Excel source: {str(e)}")
            return False

    async def extract(self) -> pd.DataFrame:
        """Extract data from Excel file"""
        try:
            if not await self.validate_source():
                raise ValueError(f"Invalid Excel source: {self.file_path}")

            self.logger.info(f"Extracting data from Excel: {self.file_path}")

            # Read Excel file
            df = pd.read_excel(self.file_path, sheet_name=self.sheet_name, header=self.header_row, skiprows=self.skip_rows)

            self.logger.info(f"Successfully extracted {len(df)} records from Excel")
            return df

        except Exception as e:
            self.logger.error(f"Error extracting from Excel: {str(e)}")
            raise


class DatabaseExtractor(BaseExtractor):
    """Extract data from database sources"""

    def __init__(self, connection_config: Dict[str, Any]):
        super().__init__(connection_config)
        self.connection_string = connection_config.get("connection_string")
        self.query = connection_config.get("query")
        self.table_name = connection_config.get("table_name")
        self.chunk_size = connection_config.get("chunk_size", 10000)

        if not self.connection_string:
            raise ValueError("Database connection string is required")

        if not (self.query or self.table_name):
            raise ValueError("Either query or table_name must be provided")

    async def validate_source(self) -> bool:
        """Test database connection"""
        try:
            engine = create_async_engine(self.connection_string)

            async with engine.begin() as conn:
                # Test connection with simple query
                result = await conn.execute(text("SELECT 1"))
                await result.fetchone()

            await engine.dispose()
            return True

        except Exception as e:
            self.logger.error(f"Database connection failed: {str(e)}")
            return False

    async def extract(self) -> pd.DataFrame:
        """Extract data from database"""
        try:
            if not await self.validate_source():
                raise ValueError("Invalid database source")

            # Build query
            if self.query:
                query = self.query
            else:
                query = f"SELECT * FROM {self.table_name}"

            self.logger.info(f"Extracting data from database with query: {query[:100]}...")

            # Use synchronous engine for pandas compatibility
            sync_connection_string = self.connection_string.replace("+asyncpg", "")
            engine = create_engine(sync_connection_string)

            # Read data in chunks
            chunks = []
            for chunk in pd.read_sql(query, engine, chunksize=self.chunk_size):
                chunks.append(chunk)
                self.logger.debug(f"Read chunk with {len(chunk)} records")

            engine.dispose()

            # Combine chunks
            if chunks:
                df = pd.concat(chunks, ignore_index=True)
                self.logger.info(f"Successfully extracted {len(df)} records from database")
                return df
            else:
                self.logger.warning("No data found in database query")
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Error extracting from database: {str(e)}")
            raise


class APIExtractor(BaseExtractor):
    """Extract data from REST APIs"""

    def __init__(self, api_config: Dict[str, Any]):
        super().__init__(api_config)
        self.base_url = api_config.get("base_url")
        self.endpoints = api_config.get("endpoints", [])
        self.headers = api_config.get("headers", {})
        self.auth_token = api_config.get("auth_token")
        self.timeout = api_config.get("timeout", 30)
        self.rate_limit = api_config.get("rate_limit", 10)  # requests per second

        if self.auth_token:
            self.headers["Authorization"] = f"Bearer {self.auth_token}"

    async def validate_source(self) -> bool:
        """Test API connectivity"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                # Test with a simple health check or first endpoint
                test_url = f"{self.base_url}/health" if self.base_url else self.endpoints[0]

                async with session.get(test_url, headers=self.headers) as response:
                    return response.status < 400

        except Exception as e:
            self.logger.error(f"API connection failed: {str(e)}")
            return False

    async def extract(self) -> pd.DataFrame:
        """Extract data from API endpoints"""
        try:
            if not await self.validate_source():
                raise ValueError("Invalid API source")

            all_data = []

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                for endpoint in self.endpoints:
                    url = f"{self.base_url}{endpoint}" if self.base_url else endpoint
                    self.logger.info(f"Extracting data from API: {url}")

                    try:
                        async with session.get(url, headers=self.headers) as response:
                            if response.status == 200:
                                data = await response.json()

                                # Handle different response formats
                                if isinstance(data, list):
                                    all_data.extend(data)
                                elif isinstance(data, dict):
                                    if "data" in data:
                                        all_data.extend(data["data"])
                                    elif "results" in data:
                                        all_data.extend(data["results"])
                                    else:
                                        all_data.append(data)

                            else:
                                self.logger.error(f"API request failed: {response.status}")

                    except Exception as e:
                        self.logger.error(f"Error fetching from {url}: {str(e)}")

                    # Rate limiting
                    await asyncio.sleep(1.0 / self.rate_limit)

            if all_data:
                df = pd.DataFrame(all_data)
                self.logger.info(f"Successfully extracted {len(df)} records from API")
                return df
            else:
                self.logger.warning("No data found from API endpoints")
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Error extracting from API: {str(e)}")
            raise


# Factory function to create extractors
def create_extractor(source_type: str, **kwargs) -> BaseExtractor:
    """Factory function to create appropriate extractor"""
    extractors = {"csv": CSVExtractor, "excel": ExcelExtractor, "database": DatabaseExtractor, "api": APIExtractor}

    if source_type not in extractors:
        raise ValueError(f"Unsupported extractor type: {source_type}")

    return extractors[source_type](**kwargs)
