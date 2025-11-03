"""
Sync operation models for Company Data Synchronization System
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SyncLogBase(BaseModel):
    """Base sync log model"""
    status: str = Field(..., pattern=r"^(running|completed|failed|cancelled)$", description="Sync status")
    total_records: int = Field(0, ge=0, description="Total records to process")
    success_records: int = Field(0, ge=0, description="Successfully processed records")
    failed_records: int = Field(0, ge=0, description="Failed records")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    duration_ms: Optional[int] = Field(None, ge=0, description="Duration in milliseconds")


class SyncLogCreate(SyncLogBase):
    """Model for creating new sync logs"""
    start_time: datetime = Field(default_factory=datetime.now, description="Sync start time")


class SyncLogUpdate(BaseModel):
    """Model for updating existing sync logs"""
    end_time: Optional[datetime] = None
    status: Optional[str] = Field(None, pattern=r"^(running|completed|failed|cancelled)$")
    total_records: Optional[int] = Field(None, ge=0)
    success_records: Optional[int] = Field(None, ge=0)
    failed_records: Optional[int] = Field(None, ge=0)
    error_message: Optional[str] = None
    duration_ms: Optional[int] = Field(None, ge=0)


class SyncLog(SyncLogBase):
    """Complete sync log model"""
    id: int
    start_time: datetime
    end_time: Optional[datetime] = None

    class Config:
        from_attributes = True


# API Response Models
class SyncStatusResponse(SyncLog):
    """Sync status response model"""
    pass


class SyncProgressResponse(BaseModel):
    """Sync progress response model"""
    is_running: bool = Field(description="Whether sync is currently running")
    current_page: int = Field(description="Current page being processed")
    total_pages: int = Field(description="Total pages to process")
    processed_records: int = Field(description="Number of records processed")
    total_records: int = Field(description="Total records to process")
    percentage: float = Field(description="Percentage completed")
    estimated_remaining_seconds: Optional[int] = Field(None, description="Estimated remaining time")
    current_operation: Optional[str] = Field(None, description="Current operation description")


class SyncStartResponse(BaseModel):
    """Sync start response model"""
    message: str = Field(description="Success message")
    sync_id: int = Field(description="Sync operation ID")
    estimated_duration_minutes: int = Field(description="Estimated duration in minutes")


class SyncHistoryResponse(BaseModel):
    """Sync history response model"""
    sync_logs: list[SyncLog] = Field(description="List of sync operations")
    total_count: int = Field(description="Total number of sync operations")


# Internal sync state management
class SyncState(BaseModel):
    """Internal sync state tracking"""
    is_running: bool = False
    current_sync_id: Optional[int] = None
    current_page: int = 0
    total_pages: int = 0
    processed_records: int = 0
    total_records: int = 0
    start_time: Optional[datetime] = None
    last_update: Optional[datetime] = None

    def update_progress(self, current_page: int, total_pages: int, processed_records: int) -> None:
        """Update sync progress"""
        self.current_page = current_page
        self.total_pages = total_pages
        self.processed_records = processed_records
        self.last_update = datetime.now()

    def get_percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_records == 0:
            return 0.0
        return (self.processed_records / self.total_records) * 100

    def get_estimated_remaining_seconds(self) -> Optional[int]:
        """Estimate remaining time in seconds"""
        if not self.start_time or self.processed_records == 0:
            return None

        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed == 0:
            return None

        rate = self.processed_records / elapsed
        if rate == 0:
            return None

        remaining_records = self.total_records - self.processed_records
        return int(remaining_records / rate)


# Global sync state instance
_sync_state = SyncState()


def get_sync_state() -> SyncState:
    """Get global sync state"""
    return _sync_state


def set_sync_state(state: SyncState) -> None:
    """Set global sync state"""
    global _sync_state
    _sync_state = state