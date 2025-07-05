"""
Request validation middleware for FastAPI application.
Implements request validation and sanitization.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Pattern

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for validating and sanitizing incoming requests."""

    def __init__(self, app, **kwargs):
        super().__init__(app)

        # Common malicious patterns to block
        self.malicious_patterns: List[Pattern] = [
            re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),  # XSS
            re.compile(
                r"\b(?:select|insert|update|delete|drop|truncate|--|/\*|\*/|@@|@|char\(|or\s+1=1|waitfor\s+delay)\b",
                re.IGNORECASE,
            ),  # SQL Injection
            re.compile(r"\b(?:document\.cookie|eval\(|alert\(|onload=|onerror=|onclick=)", re.IGNORECASE),  # XSS
            re.compile(r"\b(?:union\s+select|exec\s*\(|sp_|xp_|;--|/\*!|@@version)\b", re.IGNORECASE),  # More SQLi
        ]

        # File upload restrictions
        self.allowed_file_types = {
            "image/jpeg",
            "image/png",
            "image/gif",
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        self.max_file_size = 10 * 1024 * 1024  # 10MB

    async def dispatch(self, request: Request, call_next):
        # Skip validation for certain paths
        if request.url.path.startswith("/docs") or request.url.path.startswith("/openapi.json"):
            return await call_next(request)

        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_file_size:
            return JSONResponse(
                status_code=413, content={"detail": f"File size exceeds maximum allowed size of {self.max_file_size} bytes"}
            )

        # Check content type for file uploads
        content_type = request.headers.get("content-type", "").lower()
        if "multipart/form-data" in content_type:
            if not await self._validate_file_upload(request):
                return JSONResponse(status_code=400, content={"detail": "Invalid file type or content"})

        # Check for malicious input in query params and JSON body
        try:
            # Check query parameters
            for param, value in request.query_params.items():
                if self._is_malicious(str(value)):
                    logger.warning(f"Potential malicious input detected in query param {param}")
                    raise HTTPException(status_code=400, detail="Invalid input detected")

            # Check JSON body
            if request.method in ("POST", "PUT", "PATCH"):
                if "application/json" in content_type:
                    try:
                        body = await request.json()
                        if self._check_dict_for_malicious_input(body):
                            logger.warning("Potential malicious input detected in request body")
                            raise HTTPException(status_code=400, detail="Invalid input detected")
                    except json.JSONDecodeError:
                        pass  # Not JSON, skip

            return await call_next(request)

        except HTTPException as e:
            return JSONResponse(status_code=e.status_code, content={"detail": str(e.detail)})
        except Exception as e:
            logger.error(f"Error during request validation: {str(e)}")
            return JSONResponse(status_code=500, content={"detail": "Internal server error during request validation"})

    async def _validate_file_upload(self, request: Request) -> bool:
        """Validate file uploads for type and content."""
        try:
            form_data = await request.form()
            for _, file in form_data.multi_items():
                if hasattr(file, "content_type") and file.content_type:
                    if file.content_type not in self.allowed_file_types:
                        return False

                    # Read first few bytes to validate file type
                    content = await file.read(1024)
                    if not self._is_valid_file_content(content, file.content_type):
                        return False

                    # Reset file pointer
                    await file.seek(0)

            return True
        except Exception as e:
            logger.error(f"Error validating file upload: {str(e)}")
            return False

    def _is_valid_file_content(self, content: bytes, content_type: str) -> bool:
        """Validate file content based on its type."""
        if not content:
            return False

        # Add more specific validations based on file type
        if content_type == "application/pdf" and not content.startswith(b"%PDF-"):
            return False

        # Add more file type validations as needed
        return True

    def _check_dict_for_malicious_input(self, data: Any) -> bool:
        """Recursively check dictionary for malicious input."""
        if isinstance(data, dict):
            return any(
                self._is_malicious(str(key)) or self._check_dict_for_malicious_input(value) for key, value in data.items()
            )
        elif isinstance(data, (list, tuple)):
            return any(self._check_dict_for_malicious_input(item) for item in data)
        elif isinstance(data, str):
            return self._is_malicious(data)
        return False

    def _is_malicious(self, input_str: str) -> bool:
        """Check if input contains malicious patterns."""
        if not input_str:
            return False

        input_lower = input_str.lower()

        # Check for common attack patterns
        for pattern in self.malicious_patterns:
            if pattern.search(input_lower):
                return True

        # Check for suspicious URL schemes
        if re.search(r"\b(?:javascript|data|vbscript):", input_lower):
            return True

        # Check for suspicious HTML/JavaScript events
        if re.search(r"\bon\w+\s*=", input_lower):
            return True

        return False
