"""
Main FastAPI application for Bangladesh Student Data API
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from infrastructure.container import container
from interfaces.api.v1.api import api_router
from src.infrastructure.persistence.sqlalchemy.database import engine
from src.middleware.security_headers import SecurityHeadersMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager"""
    logger.info("Starting Bangladesh Education Data Warehouse API")

    # Initialize dependency injection container
    container = Container()
    container.wire(modules=["src.interfaces.api.v1.endpoints.auth", "src.interfaces.api.v1.endpoints.users"])
    app.container = container

    yield

    logger.info("Shutting down Bangladesh Education Data Warehouse API")
    await engine.dispose()


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="Bangladesh Education Data Warehouse API",
        description="A comprehensive data warehouse and analytics platform for Bangladesh's education system",
        version="1.0.0",
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # Add security middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )

    # Add trusted host middleware
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS])

    # Include API routes
    app.include_router(api_router, prefix="/api/v1")

    # Global exception handlers
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.status_code, "message": exc.detail, "type": "http_error"}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {"code": 422, "message": "Validation error", "type": "validation_error", "details": exc.errors()}
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": 500, "message": "Internal server error", "type": "internal_error"}},
        )

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "service": "Bangladesh Education Data Warehouse API", "version": "1.0.0"}

    return app


# Create the application instance
app = create_application()


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=settings.ENVIRONMENT == "development", log_level="info")
