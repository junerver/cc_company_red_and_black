"""
Search models for Company Data Synchronization System
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING, List

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .company import CompanyResponse
else:
    from .company import CompanyResponse


class SearchQueryBase(BaseModel):
    """Base search query model"""
    query: str = Field(..., min_length=1, max_length=100, description="Search query")


class SearchQueryCreate(SearchQueryBase):
    """Model for creating search queries"""
    result_count: int = Field(0, ge=0, description="Number of results")
    user_agent: Optional[str] = Field(None, description="User agent string")


class SearchQuery(SearchQueryBase):
    """Complete search query model"""
    id: int
    timestamp: datetime = Field(default_factory=datetime.now)
    result_count: int
    user_agent: Optional[str] = None

    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    """Search request model"""
    query: str = Field(..., min_length=1, max_length=100, description="Search query")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=200, description="Items per page")
    search_type: str = Field("auto", pattern=r"^(auto|fts|like)$", description="Search strategy")


class SearchResult(BaseModel):
    """Search result model"""
    companies: List[CompanyResponse] = Field(description="Company results")
    total_count: int = Field(description="Total number of matching companies")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    total_pages: int = Field(description="Total number of pages")
    query: str = Field(description="Search query used")
    search_type: str = Field(description="Type of search performed")
    processing_time_ms: float = Field(description="Processing time in milliseconds")

    @classmethod
    def create_empty(cls, query: str, page: int = 1, page_size: int = 50) -> "SearchResult":
        """Create empty search result"""
        return cls(
            companies=[],
            total_count=0,
            page=page,
            page_size=page_size,
            total_pages=0,
            query=query,
            search_type="auto",
            processing_time_ms=0.0
        )


# CompanyResponse imported above with TYPE_CHECKING to avoid circular imports