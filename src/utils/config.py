"""
Configuration management for Company Data Synchronization System
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings

from .exceptions import ConfigurationException


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Application Configuration
    app_host: str = Field(default="0.0.0.0", env="APP_HOST")
    app_port: int = Field(default=8000, env="APP_PORT")
    app_log_level: str = Field(default="INFO", env="APP_LOG_LEVEL")
    log_file: Optional[str] = Field(default="logs/app.log", env="LOG_FILE")

    # Database Configuration
    database_url: str = Field(default="sqlite:///./data/companies.db", env="DATABASE_URL")
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_pool_max_overflow: int = Field(default=20, env="DATABASE_POOL_MAX_OVERFLOW")

    # External API Configuration
    external_api_base_url: str = Field(
        default="https://kaifazhe.fun/prod-api",
        env="EXTERNAL_API_BASE_URL"
    )
    external_api_timeout: int = Field(default=30, env="EXTERNAL_API_TIMEOUT")
    external_api_max_concurrent: int = Field(default=200, env="EXTERNAL_API_MAX_CONCURRENT")
    external_api_user_agent: str = Field(
        default="CC-Company-Sync/1.0",
        env="EXTERNAL_API_USER_AGENT"
    )

    # Sync Configuration
    default_page_size: int = Field(default=50, env="DEFAULT_PAGE_SIZE")
    sync_batch_size: int = Field(default=1000, env="SYNC_BATCH_SIZE")
    sync_retry_attempts: int = Field(default=3, env="SYNC_RETRY_ATTEMPTS")
    sync_retry_delay: float = Field(default=1.0, env="SYNC_RETRY_DELAY")
    sync_progress_update_interval: int = Field(default=10, env="SYNC_PROGRESS_UPDATE_INTERVAL")

    # Security Configuration
    cors_origins: list[str] = Field(default=["http://localhost:3000", "http://localhost:8080"], env="CORS_ORIGINS")
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: list[str] = Field(default=["GET", "POST", "PUT", "DELETE"], env="CORS_ALLOW_METHODS")
    cors_allow_headers: list[str] = Field(default=["*"], env="CORS_ALLOW_HEADERS")

    # Performance Configuration
    max_search_results: int = Field(default=1000, env="MAX_SEARCH_RESULTS")
    search_timeout: int = Field(default=5, env="SEARCH_TIMEOUT")
    cache_ttl: int = Field(default=300, env="CACHE_TTL")  # 5 minutes

    # Development Configuration
    debug: bool = Field(default=False, env="DEBUG")
    reload: bool = Field(default=False, env="RELOAD")
    workers: int = Field(default=1, env="WORKERS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def __post_init__(self) -> None:
        """Validate configuration after initialization"""
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate critical configuration values"""
        # Validate port range
        if not (1 <= self.app_port <= 65535):
            raise ConfigurationException(f"Invalid port number: {self.app_port}")

        # Validate API timeout
        if self.external_api_timeout <= 0:
            raise ConfigurationException("API timeout must be positive")

        # Validate batch size
        if self.sync_batch_size <= 0:
            raise ConfigurationException("Sync batch size must be positive")

        # Validate retry configuration
        if self.sync_retry_attempts < 0:
            raise ConfigurationException("Retry attempts cannot be negative")
        if self.sync_retry_delay < 0:
            raise ConfigurationException("Retry delay cannot be negative")

        # Validate database URL
        if not self.database_url:
            raise ConfigurationException("Database URL is required")

    @property
    def database_path(self) -> Path:
        """Get the database file path"""
        if self.database_url.startswith("sqlite:///"):
            return Path(self.database_url[10:])
        raise ConfigurationException(f"Unsupported database URL format: {self.database_url}")

    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.debug or self.reload

    @property
    def external_api_endpoints(self) -> dict[str, str]:
        """Get external API endpoints"""
        base_url = self.external_api_base_url.rstrip("/")
        return {
            "companies": f"{base_url}/system/softwareCompany/list",
            "health": f"{base_url}/health"
        }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


def validate_environment() -> None:
    """Validate that required environment variables are set"""
    required_vars = []

    # Check for critical missing environment variables
    settings = get_settings()

    # Validate database directory is writable
    try:
        db_path = settings.database_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        if not os.access(db_path.parent, os.W_OK):
            raise ConfigurationException(f"Database directory is not writable: {db_path.parent}")
    except Exception as e:
        raise ConfigurationException(f"Database configuration error: {e}")

    # Validate log directory is writable
    if settings.log_file:
        try:
            log_path = Path(settings.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            if not os.access(log_path.parent, os.W_OK):
                raise ConfigurationException(f"Log directory is not writable: {log_path.parent}")
        except Exception as e:
            raise ConfigurationException(f"Log configuration error: {e}")


# Initialize settings on import
try:
    settings = get_settings()
    validate_environment()
except Exception as e:
    import sys
    print(f"Configuration error: {e}")
    sys.exit(1)