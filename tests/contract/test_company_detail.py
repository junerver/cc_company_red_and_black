"""
Contract tests for company detail API endpoint
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
                create_time, update_time, code, uuid, last_sync_at, is_active
            ) VALUES
                (1, 'Test Company 1', 'Owner 1', 'Test Description 1', 'Test Address 1',
                 '2023-01-01 00:00:00', '2023-01-02 00:00:00', 'CODE001', 'uuid-1', datetime('now'), 1),
                (2, 'Test Company 2', 'Owner 2', 'Test Description 2', 'Test Address 2',
                 '2023-01-03 00:00:00', '2023-01-04 00:00:00', 'CODE002', 'uuid-2', datetime('now'), 1),
                (3, 'Technology Company', 'Tech Owner', 'Technology company specializing in software development and IT consulting services. We provide comprehensive solutions for businesses of all sizes.', 'Tech Address',
                 '2023-01-05 00:00:00', '2023-01-06 00:00:00', 'TECH003', 'uuid-3', datetime('now'), 1)
        """)
        await conn.commit()

    yield
    await db_manager.close()


class TestCompanyDetailAPI:
    """Contract tests for company detail API endpoint"""

    @pytest.mark.asyncio
    async def test_get_company_detail_success(self, client: AsyncClient, setup_database):
        """Test GET /api/companies/{id} for existing company"""
        response = await client.get("/api/companies/1")

        assert response.status_code == 200
        company = response.json()

        # Verify all expected fields are present
        assert "id" in company
        assert "company_name" in company
        assert "owner" in company
        assert "address" in company
        assert "company_desc" in company
        assert "create_time" in company
        assert "update_time" in company
        assert "code" in company
        assert "uuid" in company
        assert "last_sync_at" in company

        # Verify field values
        assert company["id"] == 1
        assert company["company_name"] == "Test Company 1"
        assert company["owner"] == "Owner 1"
        assert company["address"] == "Test Address 1"
        assert company["company_desc"] == "Test Description 1"
        assert company["code"] == "CODE001"

    @pytest.mark.asyncio
    async def test_get_company_detail_not_found(self, client: AsyncClient, setup_database):
        """Test GET /api/companies/{id} for non-existent company"""
        response = await client.get("/api/companies/999")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Company not found"

    @pytest.mark.asyncio
    async def test_get_company_detail_invalid_id(self, client: AsyncClient, setup_database):
        """Test GET /api/companies/{id} with invalid ID"""
        response = await client.get("/api/companies/invalid")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_company_detail_zero_id(self, client: AsyncClient, setup_database):
        """Test GET /api/companies/{id} with zero ID"""
        response = await client.get("/api/companies/0")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_company_detail_negative_id(self, client: AsyncClient, setup_database):
        """Test GET /api/companies/{id} with negative ID"""
        response = await client.get("/api/companies/-1")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_company_detail_long_description(self, client: AsyncClient, setup_database):
        """Test GET /api/companies/{id} with long company description"""
        response = await client.get("/api/companies/3")

        assert response.status_code == 200
        company = response.json()

        # Verify long description is handled properly
        assert company["company_name"] == "Technology Company"
        assert company["company_desc"] == "Technology company specializing in software development and IT consulting services. We provide comprehensive solutions for businesses of all sizes."

    @pytest.mark.asyncio
    async def test_get_company_detail_empty_fields(self, client: AsyncClient, setup_database):
        """Test GET /api/companies/{id} with company having empty optional fields"""
        # Insert company with empty optional fields
        async with db_manager.get_connection() as conn:
            await conn.execute("""
                INSERT INTO companies (
                    id, company_name, owner, company_desc, address,
                    create_time, update_time, last_sync_at, is_active
                ) VALUES
                    (4, 'Minimal Company', '', '', '',
                     '2023-01-07 00:00:00', '2023-01-08 00:00:00', datetime('now'), 1)
            """)
            await conn.commit()

        response = await client.get("/api/companies/4")

        assert response.status_code == 200
        company = response.json()

        assert company["id"] == 4
        assert company["company_name"] == "Minimal Company"
        assert company["owner"] == ""
        assert company["address"] == ""
        assert company["company_desc"] == ""