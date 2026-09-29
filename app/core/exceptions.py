"""
app/core/exceptions.py
Global FastAPI exception handlers: 401, 403, 404, 422.
Implemented in: Task 3.3
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Registers global exception handlers to standardize error responses
    and prevent sensitive data leakage (e.g. database queries).
    """

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """
        Handles standard HTTP exceptions (401, 403, 404, etc.)
        raised using fastapi.HTTPException.
        """
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """
        Handles Pydantic schema validation failures.
        Returns a standardized 422 Unprocessable Entity response.
        """
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation error",
                "errors": exc.errors(),
            },
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(
        request: Request, exc: IntegrityError
    ) -> JSONResponse:
        """
        Handles database constraint violations (e.g. unique constraint).
        Returns 409 Conflict without exposing SQL queries.
        """
        logger.error(f"Database Integrity Error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "Data conflict or resource already exists"},
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        """
        Handles all other raw database errors.
        Returns 500 Internal Server Error without exposing SQL queries.
        """
        logger.error(f"Database Error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """
        Catch-all for unhandled runtime exceptions.
        """
        logger.error(f"Unhandled Exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )
