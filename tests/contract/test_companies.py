"""
Contract tests for companies API endpoints
"""

import pytest
from httpx import AsyncClient

from src.api.main import app
from src.models.database import db_manager


@pytest.fixture
async def client():
    """Test client fixture"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def setup_database():
    """Setup test database with sample data"""
    await db_manager.initialize()

    # Insert sample companies for testing
    async with db_manager.get_connection() as conn:
        await conn.execute("""
            INSERT INTO companies (
                id, company_name, owner, company_desc, address,
                create_time, update_time, last_sync_at, is_active
            ) VALUES
                (1, 'Test Company 1', 'Owner 1', 'Description 1', 'Address 1',
                 '2023-01-01 00:00:00', '2023-01-02 00:00:00', datetime('now'), 1),
                (2, 'Test Company 2', 'Owner 2', 'Description 2', 'Address 2',
                 '2023-01-03 00:00:00', '2023-01-04 00:00:00', datetime('now'), 1),
                (3, 'Technology Company', 'Tech Owner', 'Tech Description', 'Tech Address',
                 '2023-01-05 00:00:00', '2023-01-06 00:00:00', datetime('now'), 1)
        """)
        await conn.commit()

    yield
    await db_manager.close()


class TestCompaniesAPI:
    """Contract tests for companies API endpoints"""

    @pytest.mark.asyncio
    async def test_get_companies_no_search(self, client: AsyncClient, setup_database):
        """Test GET /api/companies without search parameters"""
        response = await client.get("/api/companies")

        assert response.status_code == 200
        data = response.json()

        assert "companies" in data
        assert "total_count" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert "query" in data
        assert "search_type" in data
        assert "processing_time_ms" in data

        assert data["total_count"] == 3
        assert len(data["companies"]) == 3
        assert data["page"] == 1
        assert data["page_size"] == 50

    @pytest.mark.asyncio
    async def test_get_companies_with_search(self, client: AsyncClient, setup_database):
        """Test GET /api/companies with search query"""
        response = await client.get("/api/companies?query=Technology")

        assert response.status_code == 200
        data = response.json()

        assert len(data["companies"]) == 1
        assert data["companies"][0]["company_name"] == "Technology Company"
        assert data["query"] == "Technology"
        assert data["total_count"] == 1

    @pytest.mark.asyncio
    async def test_get_companies_pagination(self, client: AsyncClient, setup_database):
        """Test GET /api/companies with pagination"""
        response = await client.get("/api/companies?page=1&page_size=2")

        assert response.status_code == 200
        data = response.json()

        assert len(data["companies"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total_pages"] == 2
        assert data["total_count"] == 3

    @pytest.mark.asyncio
    async def test_get_companies_invalid_page(self, client: AsyncClient, setup_database):
        """Test GET /api/companies with invalid page number"""
        response = await client.get("/api/companies?page=0")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_companies_invalid_page_size(self, client: AsyncClient, setup_database):
        """Test GET /api/companies with invalid page size"""
        response = await client.get("/api/companies?page_size=0")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_companies_page_size_too_large(self, client: AsyncClient, setup_database):
        """Test GET /api/companies with page size too large"""
        response = await client.get("/api/companies?page_size=300")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_companies_search_type_invalid(self, client: AsyncClient, setup_database):
        """Test GET /api/companies with invalid search type"""
        response = await client.get("/api/companies?search_type=invalid")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_companies_empty_database(self, client: AsyncClient):
        """Test GET /api/companies with empty database"""
        # Don't setup database for this test
        response = await client.get("/api/companies")

        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 0
        assert len(data["companies"]) == 0

    @pytest.mark.asyncio
    async def test_get_company_detail_success(self, client: AsyncClient, setup_database):
        """Test GET /api/companies/{id} for existing company"""
        response = await client.get("/api/companies/1")

        assert response.status_code == 200
        company = response.json()

        assert company["id"] == 1
        assert company["company_name"] == "Test Company 1"
        assert company["owner"] == "Owner 1"
        assert "company_desc" in company
        assert "create_time" in company
        assert "last_sync_at" in company

    @pytest.mark.asyncio
    async def test_get_company_detail_not_found(self, client: AsyncClient, setup_database):
        """Test GET /api/companies/{id} for non-existent company"""
        response = await client.get("/api/companies/999")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_get_company_detail_invalid_id(self, client: AsyncClient, setup_database):
        """Test GET /api/companies/{id} with invalid ID"""
        response = await client.get("/api/companies/invalid")

        assert response.status_code == 422  # Validation error