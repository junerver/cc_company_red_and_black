"""
Companies API endpoints for Company Data Synchronization System
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from ...models.company import CompanyResponse, CompanyDetailResponse
from ...models.search import SearchResult
from ...services.company_service import get_company_service
from ...utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Routes order: / -> /search -> /detail/{company_id} (specific paths before parameterized)


@router.get("/", response_model=SearchResult)
async def get_companies(
    query: str = Query("", description="Search query for company name, owner, or address"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    search_type: str = Query("auto", regex="^(auto|fts|like)$", description="Type of search to perform")
):
    """Get companies with pagination and search"""
    try:
        company_service = await get_company_service()
        result = await company_service.get_companies(
            query=query,
            page=page,
            page_size=page_size,
            search_type=search_type
        )
        return result

    except ValueError as e:
        logger.warning(f"Invalid parameters: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting companies: {e}")
        raise HTTPException(status_code=500, detail="Failed to get companies")


@router.get("/search")
async def search_companies(
    query: str = Query(..., min_length=1, max_length=100, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    search_type: str = Query("auto", regex="^(auto|fts|like)$", description="Search strategy")
):
    """Search companies (alias for GET /companies with query parameter)"""
    try:
        company_service = await get_company_service()
        result = await company_service.get_companies(
            query=query,
            page=page,
            page_size=page_size,
            search_type=search_type
        )
        return result

    except ValueError as e:
        logger.warning(f"Invalid search parameters: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error searching companies: {e}")
        raise HTTPException(status_code=500, detail="Failed to search companies")


@router.get("/detail/{company_id}", response_model=CompanyDetailResponse)
async def get_company_detail(company_id: int):
    """Get detailed information for a specific company"""
    try:
        if company_id < 1:
            raise HTTPException(status_code=422, detail="Company ID must be positive")

        company_service = await get_company_service()
        company = await company_service.get_company_by_id(company_id)

        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        return company

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting company detail for ID {company_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get company detail")