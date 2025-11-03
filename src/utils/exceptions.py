"""
Custom exceptions for Company Data Synchronization System
"""

from typing import Optional


class CompanySyncException(Exception):
    """Base exception for company synchronization errors"""
    pass


class APIException(CompanySyncException):
    """Exception raised when API requests fail"""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class DatabaseException(CompanySyncException):
    """Exception raised when database operations fail"""
    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(message)
        self.operation = operation


class ValidationException(CompanySyncException):
    """Exception raised when data validation fails"""
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[str] = None):
        super().__init__(message)
        self.field = field
        self.value = value


class SyncInProgressException(CompanySyncException):
    """Exception raised when sync is already in progress"""
    pass


class ConfigurationException(CompanySyncException):
    """Exception raised when configuration is invalid"""
    pass