"""
Error handling middleware for Company Data Synchronization System
"""

import logging
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ...utils.exceptions import CompanySyncException
from ...utils.logging import get_logger

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except CompanySyncException as e:
            logger.error(f"Company sync error: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": str(e),
                    "type": "CompanySyncException"
                }
            )
        except Exception as e:
            logger.error(f"Unhandled error: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred",
                    "type": "InternalServerError"
                }
            )


def setup_error_handlers(app) -> None:
    """Setup custom exception handlers"""

    @app.exception_handler(CompanySyncException)
    async def company_sync_exception_handler(request: Request, exc: CompanySyncException):
        logger.error(f"Company sync exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Company sync error",
                "message": str(exc),
                "type": "CompanySyncException"
            }
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        logger.warning(f"Value error: {exc}")
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid input",
                "message": str(exc),
                "type": "ValueError"
            }
        )

    @app.exception_handler(KeyError)
    async def key_error_handler(request: Request, exc: KeyError):
        logger.warning(f"Key error: {exc}")
        return JSONResponse(
            status_code=404,
            content={
                "error": "Resource not found",
                "message": f"Requested resource not found: {exc}",
                "type": "KeyError"
            }
        )