"""
Bangladesh Education Data API

A comprehensive data analysis system for educational data in Bangladesh,
integrating various data sources to provide insights into student performance,
demographics, and educational trends.
"""

__version__ = "0.1.0"
__author__ = "BdREN Data Analytics Team"
__email__ = "team@bdren.edu.bd"
__license__ = "MIT"

# Import key modules
from .config import settings
from .database import Base, get_db, get_async_db

# Import models to ensure they are registered with SQLAlchemy
from .models import *  # noqa: F401, F403

__all__ = [
    "settings",
    "Base",
    "get_db",
    "get_async_db",
    "__version__",
    "__author__",
    "__email__",
    "__license__",
]
