"""
Company service for Company Data Synchronization System
"""

from typing import Dict, List, Optional

from ..models.company import Company, CompanyResponse, CompanyDetailResponse
from ..models.search import SearchQuery, SearchQueryCreate, SearchRequest, SearchResult
from ..models.database import get_db_connection
from ..utils.exceptions import DatabaseException
from ..utils.logging import get_logger

logger = get_logger(__name__)


class CompanyService:
    """Service for managing company data operations"""

    def __init__(self):
        self.db = None

    async def get_companies(
        self,
        query: str = "",
        page: int = 1,
        page_size: int = 50,
        search_type: str = "auto"
    ) -> SearchResult:
        """Get companies with pagination and search"""
        if page < 1:
            raise ValueError("Page must be >= 1")
        if page_size < 1 or page_size > 200:
            raise ValueError("Page size must be between 1 and 200")
        if search_type not in ["auto", "fts", "like"]:
            raise ValueError("Search type must be 'auto', 'fts', or 'like'")

        try:
            async with get_db_connection() as conn:
                # Count total results
                total_count = await self._count_companies(conn, query, search_type)

                # Get paginated results
                companies = await self._search_companies(
                    conn, query, search_type, page, page_size
                )

                # Log search query
                if query:
                    await self._log_search_query(query, len(companies))

                # Calculate pagination
                total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

                return SearchResult(
                    companies=[self._company_to_response(comp) for comp in companies],
                    total_count=total_count,
                    page=page,
                    page_size=page_size,
                    total_pages=total_pages,
                    query=query,
                    search_type=search_type,
                    processing_time_ms=0.0  # TODO: Add timing
                )

        except Exception as e:
            logger.error(f"Error getting companies: {e}")
            raise DatabaseException(f"Failed to get companies: {e}")

    async def get_company_by_id(self, company_id: int) -> Optional[CompanyDetailResponse]:
        """Get company details by ID"""
        if company_id < 1:
            raise ValueError("Company ID must be positive")

        try:
            async with get_db_connection() as conn:
                cursor = await conn.execute(
                    """
                    SELECT id, company_name, owner, company_desc, address,
                           create_time, update_time, code, uuid, last_sync_at, is_active
                    FROM companies
                    WHERE id = ? AND is_active = 1
                    """,
                    (company_id,)
                )

                row = await cursor.fetchone()
                if row:
                    return self._row_to_company_detail(row)
                else:
                    return None

        except Exception as e:
            logger.error(f"Error getting company {company_id}: {e}")
            raise DatabaseException(f"Failed to get company: {e}")

    def _company_to_response(self, company: Company) -> CompanyResponse:
        """Convert Company model to response model"""
        return CompanyResponse(
            id=company.id,
            company_name=company.company_name,
            owner=company.owner,
            address=company.address,
            update_time=company.update_time
        )

    def _row_to_company_detail(self, row) -> CompanyDetailResponse:
        """Convert database row to company detail response"""
        return CompanyDetailResponse(
            id=row[0],
            company_name=row[1],
            owner=row[2],
            address=row[4],
            update_time=row[6],
            company_desc=row[3],
            create_time=row[5],
            code=row[7],
            uuid=row[8],
            last_sync_at=row[9]
        )

    async def _count_companies(self, conn, query: str, search_type: str) -> int:
        """Count total companies matching search criteria"""
        if not query:
            cursor = await conn.execute("SELECT COUNT(*) FROM companies WHERE is_active = 1")
            result = await cursor.fetchone()
            return result[0] if result else 0
        else:
            # Use appropriate search method
            if search_type == "fts":
                # Full-text search
                cursor = await conn.execute("""
                    SELECT COUNT(DISTINCT c.id)
                    FROM companies c
                    JOIN companies_fts fts ON c.id = fts.rowid
                    WHERE companies_fts MATCH ? AND c.is_active = 1
                """, (query,))
                result = await cursor.fetchone()
                return result[0] if result else 0
            else:
                # LIKE search (fallback)
                cursor = await conn.execute("""
                    SELECT COUNT(*) FROM companies
                    WHERE is_active = 1 AND (
                        company_name LIKE ? OR
                        owner LIKE ? OR
                        address LIKE ?
                    )
                """, (f"%{query}%", f"%{query}%", f"%{query}%"))
                result = await cursor.fetchone()
                return result[0] if result else 0

    async def _search_companies(
        self, conn, query: str, search_type: str, page: int, page_size: int
    ) -> List[Company]:
        """Search companies with pagination"""
        offset = (page - 1) * page_size

        if not query:
            # Get all companies
            cursor = await conn.execute("""
                SELECT id, company_name, owner, company_desc, address,
                       create_time, update_time, code, uuid, last_sync_at, is_active
                FROM companies
                WHERE is_active = 1
                ORDER BY company_name
                LIMIT ? OFFSET ?
            """, (page_size, offset))

        else:
            # Use appropriate search method
            if search_type == "fts":
                # Full-text search
                cursor = await conn.execute("""
                    SELECT DISTINCT c.id, c.company_name, c.owner, c.company_desc, c.address,
                           c.create_time, c.update_time, c.code, c.uuid, c.last_sync_at, c.is_active
                    FROM companies c
                    JOIN companies_fts fts ON c.id = fts.rowid
                    WHERE companies_fts MATCH ? AND c.is_active = 1
                    ORDER BY c.company_name
                    LIMIT ? OFFSET ?
                """, (query, page_size, offset))
            else:
                # LIKE search (fallback)
                cursor = await conn.execute("""
                    SELECT id, company_name, owner, company_desc, address,
                           create_time, update_time, code, uuid, last_sync_at, is_active
                    FROM companies
                    WHERE is_active = 1 AND (
                        company_name LIKE ? OR
                        owner LIKE ? OR
                        address LIKE ?
                    )
                    ORDER BY company_name
                    LIMIT ? OFFSET ?
                """, (f"%{query}%", f"%{query}%", f"%{query}%", page_size, offset))

        rows = await cursor.fetchall()
        return [
            Company(
                id=row[0],
                company_name=row[1],
                owner=row[2],
                company_desc=row[3],
                address=row[4],
                create_time=row[5],
                update_time=row[6],
                code=row[7],
                uuid=row[8],
                last_sync_at=row[9],
                is_active=row[10]
            )
            for row in rows
        ]

    async def _log_search_query(self, query: str, result_count: int) -> None:
        """Log search query for analytics"""
        try:
            async with get_db_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO search_queries (query, result_count, user_agent)
                    VALUES (?, ?, ?)
                    """,
                    (query, result_count, "web-interface")
                )
                await conn.commit()
        except Exception as e:
            logger.warning(f"Failed to log search query: {e}")


# Global company service instance
company_service = CompanyService()


async def get_company_service() -> CompanyService:
    """Get company service instance"""
    return company_service