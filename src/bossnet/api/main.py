"""
Main FastAPI application for Bangladesh Student Data API
"""

import logging
import os
from typing import Any, Dict, List, Optional

# Import all routers
from api.endpoints import auth, students
from auth.service import AuthService
from config.security import security_settings
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from middleware.request_validation import RequestValidationMiddleware

# Import security middleware
from middleware.security_headers import SecurityHeadersMiddleware, setup_security_middleware

from config import settings
from database.base import Base, engine, get_db

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("app.log")],
)
logger = logging.getLogger(__name__)

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    logger.error(f"Error creating database tables: {str(e)}")
    raise

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize auth service
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token", auto_error=False)

auth_service = AuthService(secret_key=settings.SECRET_KEY, algorithm=settings.ALGORITHM)

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="REST API for managing and analyzing student data in Bangladesh",
    version="1.0.0",
    docs_url=None,  # We'll serve custom docs
    redoc_url=None,  # We'll serve custom ReDoc
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    debug=settings.DEBUG,
)

# Configure static files
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=security_settings.CORS_ORIGINS,
    allow_credentials=security_settings.CORS_CREDENTIALS,
    allow_methods=security_settings.CORS_METHODS,
    allow_headers=security_settings.CORS_HEADERS,
    expose_headers=["Content-Disposition"],
)

# Add security middleware
if security_settings.ENABLE_SECURITY_HEADERS:
    app.add_middleware(SecurityHeadersMiddleware)

if security_settings.ENABLE_REQUEST_VALIDATION:
    app.add_middleware(RequestValidationMiddleware)

# Setup additional security middleware
setup_security_middleware(app)

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(students.router, prefix=settings.API_V1_STR)


# Custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors and return a clean error response"""
    logger.warning(f"Validation error: {exc.errors()}")

    errors = []
    for error in exc.errors():
        # Don't expose internal field names in error messages
        field = ".".join(str(loc) for loc in error["loc"] if loc not in ("body", "query"))

        # Sanitize error messages to prevent information leakage
        msg = error["msg"]
        if "ensure this value" in msg and "type=" in msg:
            msg = f"Invalid value for field '{field}': {error['type']}"

        errors.append({"field": field, "message": msg, "type": error["type"]})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": "Validation error", "errors": errors}
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions and ensure security headers are included"""
    if exc.status_code == 404:
        return JSONResponse(status_code=404, content={"detail": "Not Found"}, headers={"X-Content-Type-Options": "nosniff"})

    response = JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers or {})

    # Add security headers
    for header, value in security_settings.SECURITY_HEADERS.items():
        response.headers[header] = value

    return response


# Custom docs endpoint
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=app.title + " - Swagger UI",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )


# Custom OpenAPI schema
@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_endpoint():
    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Bangladesh Student Data API",
        "version": "1.0.0",
        "docs": "/docs",
        "description": "REST API for managing and analyzing student data in Bangladesh",
    }
