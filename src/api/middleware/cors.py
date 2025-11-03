"""
CORS middleware configuration for Company Data Synchronization System
"""

from typing import Sequence

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ...utils.config import get_settings
from ...utils.logging import get_logger

logger = get_logger(__name__)


def setup_cors(app: FastAPI) -> None:
    """Setup CORS middleware for the FastAPI application"""
    settings = get_settings()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    logger.info(f"CORS middleware configured with origins: {settings.cors_origins}")