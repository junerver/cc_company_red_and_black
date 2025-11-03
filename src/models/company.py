"""
Company data models for Company Data Synchronization System
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CompanyBase(BaseModel):
    """Base company model with common fields"""
    company_name: str = Field(..., min_length=1, max_length=255, description="Company name")
    owner: Optional[str] = Field(None, max_length=100, description="Legal representative or owner")
    company_desc: Optional[str] = Field(None, max_length=5000, description="Company description")
    address: Optional[str] = Field(None, max_length=500, description="Office address")
    create_time: Optional[datetime] = Field(None, description="Company creation time")
    update_time: Optional[datetime] = Field(None, description="Last update time")
    code: Optional[str] = Field(None, max_length=50, description="Company code")
    uuid: Optional[str] = Field(None, max_length=100, description="Unique identifier")


class CompanyCreate(CompanyBase):
    """Model for creating new companies"""
    id: Optional[int] = None  # Include id for syncing from external API


class CompanyUpdate(BaseModel):
    """Model for updating existing companies"""
    company_name: Optional[str] = Field(None, min_length=1, max_length=255)
    owner: Optional[str] = Field(None, max_length=100)
    company_desc: Optional[str] = Field(None, max_length=2000)
    address: Optional[str] = Field(None, max_length=500)
    update_time: Optional[datetime] = None


class Company(CompanyBase):
    """Complete company model with database fields"""
    id: int = Field(..., description="Company ID")
    last_sync_at: datetime = Field(default_factory=datetime.now, description="Last sync timestamp")
    is_active: bool = Field(True, description="Whether company is active")

    class Config:
        from_attributes = True


class CompanyInDB(Company):
    """Company model as stored in database"""
    pass


# API Response Models
class CompanyResponse(BaseModel):
    """Company model for API responses (minimal fields)"""
    id: int
    company_name: str
    owner: Optional[str] = None
    address: Optional[str] = None
    update_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class CompanyDetailResponse(CompanyResponse):
    """Detailed company model for API responses"""
    company_desc: Optional[str] = None
    create_time: Optional[datetime] = None
    code: Optional[str] = None
    uuid: Optional[str] = None
    last_sync_at: datetime

    class Config:
        from_attributes = True


# External API Models
class ExternalCompany(BaseModel):
    """Model for company data from external API"""
    model_config = ConfigDict(populate_by_name=True)

    id: int
    company_name: str = Field(..., alias="companyName")
    owner: Optional[str] = None
    company_desc: Optional[str] = Field(None, alias="companyDesc")
    adress: Optional[str] = None  # Note: API uses "adress" not "address", can be None
    create_time: str = Field(..., alias="createTime")
    update_time: Optional[str] = Field(None, alias="updateTime")
    code: Optional[str] = None
    uuid: Optional[str] = None

    def to_internal(self) -> CompanyCreate:
        """Convert external API model to internal model"""
        return CompanyCreate(
            id=self.id,
            company_name=self.company_name,
            owner=self.owner,
            company_desc=self.company_desc,
            address=self.adress if self.adress else "",  # Map adress to address, default to empty string
            create_time=datetime.fromisoformat(self.create_time) if self.create_time else None,
            update_time=datetime.fromisoformat(self.update_time) if self.update_time else None,
            code=self.code,
            uuid=self.uuid
        )


class ExternalCompanyResponse(BaseModel):
    """External API response wrapper"""
    code: int
    msg: str
    data: "ExternalData"


class ExternalData(BaseModel):
    """External API data wrapper"""
    model_config = ConfigDict(populate_by_name=True)

    total_page: int = Field(..., alias="totalPage")
    total: int
    rows: list[ExternalCompany]