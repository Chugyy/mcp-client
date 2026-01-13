#!/usr/bin/env python3
# app/api/v1/exception_handlers.py
"""
Handlers d'exceptions globaux pour mapper les exceptions métier aux codes HTTP.

Utilisé dans main.py via app.add_exception_handler().
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from datetime import datetime, timezone
from app.core.exceptions import (
    AppException,
    ValidationError,
    ConflictError,
    QuotaExceededError,
    PermissionError,
    NotFoundError,
    AuthenticationError,
    RateLimitError,
    CircuitBreakerOpenError
)
from app.core.schemas.errors import ErrorDetail, ProblemDetails
from config.logger import logger


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handler global pour toutes les exceptions métier (AppException).

    Mapping exceptions → HTTP codes:
    - ValidationError → 400 Bad Request
    - AuthenticationError → 401 Unauthorized
    - PermissionError → 403 Forbidden
    - NotFoundError → 404 Not Found
    - ConflictError → 409 Conflict
    - QuotaExceededError → 429 Too Many Requests
    - RateLimitError → 429 Too Many Requests
    - CircuitBreakerOpenError → 503 Service Unavailable
    - AppException (générique) → 500 Internal Server Error

    Args:
        request: Requête FastAPI
        exc: Exception métier

    Returns:
        JSONResponse avec le code HTTP approprié et format RFC 7807
    """
    # Mapper exception → HTTP code
    status_code = 500
    if isinstance(exc, ValidationError):
        status_code = 400
    elif isinstance(exc, AuthenticationError):
        status_code = 401
    elif isinstance(exc, PermissionError):
        status_code = 403
    elif isinstance(exc, NotFoundError):
        status_code = 404
    elif isinstance(exc, ConflictError):
        status_code = 409
    elif isinstance(exc, (QuotaExceededError, RateLimitError)):
        status_code = 429
    elif isinstance(exc, CircuitBreakerOpenError):
        status_code = 503

    # Logger avec niveau approprié selon la gravité
    if status_code >= 500:
        logger.error(f"[{exc.__class__.__name__}] {exc.message} | Path: {request.url.path}")
    else:
        logger.warning(f"[{exc.__class__.__name__}] {exc.message} | Path: {request.url.path}")

    # Construire ProblemDetails (RFC 7807)
    problem = ProblemDetails(
        type=exc.__class__.__name__,
        title=exc.__class__.__name__.replace('Error', ' Error'),
        status=status_code,
        detail=exc.message,
        instance=str(request.url),
        timestamp=datetime.now(timezone.utc).isoformat()
    )

    # Gérer les détails supplémentaires (extensions RFC 7807)
    if exc.details:
        response_data = problem.model_dump(exclude_none=True)
        response_data.update(exc.details)
        return JSONResponse(
            status_code=status_code,
            content=response_data
        )

    # Pas de détails supplémentaires
    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(exclude_none=True)
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handler for Pydantic validation errors (422).

    Transforms Pydantic error format into RFC 7807-inspired structured response
    with detailed field-level error information.

    Args:
        request: FastAPI Request object
        exc: RequestValidationError instance from Pydantic

    Returns:
        JSONResponse with structured error details
    """
    # Step 1: Extract Pydantic errors and transform to ErrorDetail format
    error_details = []
    for error in exc.errors():
        # Extract field path (ignore first element: 'body', 'query', 'path')
        loc = error.get('loc', ())
        field_path = ' → '.join(str(x) for x in loc[1:]) if len(loc) > 1 else 'unknown'

        # Extract message and value
        message = error.get('msg', 'Validation error')
        value = error.get('input')

        # Create ErrorDetail instance
        error_details.append(ErrorDetail(
            field=field_path,
            message=message,
            value=value
        ))

    # Step 2: Build ProblemDetails response
    error_count = len(error_details)
    problem = ProblemDetails(
        type="ValidationError",
        title="Validation Failed",
        status=422,
        detail=f"{error_count} validation error(s) detected",
        instance=str(request.url),
        errors=error_details,
        timestamp=datetime.now(timezone.utc).isoformat()
    )

    # Step 3: Log warning (client error, not server error)
    logger.warning(f"Validation error on {request.url.path}: {error_count} error(s)")

    # Step 4: Return JSONResponse with exclude_none to omit null fields
    return JSONResponse(
        status_code=422,
        content=problem.model_dump(exclude_none=True)
    )
