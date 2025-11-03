"""
Unit tests for company detail service functionality
"""

import pytest
from datetime import datetime

from src.services.company_service import CompanyService
from src.models.company import Company
from src.models.database import db_manager


@pytest.fixture
async def service():
    """Company service fixture"""
    return CompanyService()


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
                (3, 'Technology Company', 'Tech Owner', 'Technology company specializing in software development', 'Tech Address',
                 '2023-01-05 00:00:00', '2023-01-06 00:00:00', 'TECH003', 'uuid-3', datetime('now'), 1)
        """)
        await conn.commit()

    yield
    await db_manager.close()


class TestCompanyDetailService:
    """Unit tests for company detail service functionality"""

    @pytest.mark.asyncio
    async def test_get_company_by_id_success(self, service: CompanyService, setup_database):
        """Test successful company retrieval by ID"""
        company = await service.get_company_by_id(1)

        assert company is not None
        assert company.id == 1
        assert company.company_name == "Test Company 1"
        assert company.owner == "Owner 1"
        assert company.address == "Test Address 1"
        assert company.company_desc == "Test Description 1"
        assert company.code == "CODE001"

    @pytest.mark.asyncio
    async def test_get_company_by_id_not_found(self, service: CompanyService, setup_database):
        """Test company retrieval for non-existent ID"""
        company = await service.get_company_by_id(999)

        assert company is None

    @pytest.mark.asyncio
    async def test_get_company_by_id_invalid_id(self, service: CompanyService, setup_database):
        """Test company retrieval with invalid ID"""
        with pytest.raises(ValueError, match="Company ID must be positive"):
            await service.get_company_by_id(0)

        with pytest.raises(ValueError, match="Company ID must be positive"):
            await service.get_company_by_id(-1)

    @pytest.mark.asyncio
    async def test_get_company_by_id_database_error(self, service: CompanyService, setup_database):
        """Test company retrieval with database error"""
        # Force database error by closing connection
        await db_manager.close()

        with pytest.raises(Exception):
            await service.get_company_by_id(1)

        # Reinitialize for cleanup
        await db_manager.initialize()

    @pytest.mark.asyncio
    async def test_row_to_company_detail_conversion(self, service: CompanyService):
        """Test database row to company detail response conversion"""
        # Mock database row tuple
        # (id, company_name, owner, company_desc, address, create_time, update_time, code, uuid, last_sync_at)
        row = (
            1,
            "Test Company",
            "Test Owner",
            "Test Description",
            "Test Address",
            "2023-01-01 00:00:00",
            "2023-01-02 00:00:00",
            "TEST001",
            "test-uuid",
            "2023-01-03 00:00:00"
        )

        company_detail = service._row_to_company_detail(row)

        assert company_detail.id == 1
        assert company_detail.company_name == "Test Company"
        assert company_detail.owner == "Test Owner"
        assert company_detail.company_desc == "Test Description"
        assert company_detail.address == "Test Address"
        assert company_detail.create_time == "2023-01-01 00:00:00"
        assert company_detail.update_time == "2023-01-02 00:00:00"
        assert company_detail.code == "TEST001"
        assert company_detail.uuid == "test-uuid"
        assert company_detail.last_sync_at == "2023-01-03 00:00:00"

    @pytest.mark.asyncio
    async def test_get_company_detail_with_empty_fields(self, service: CompanyService, setup_database):
        """Test company retrieval with empty optional fields"""
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

        company = await service.get_company_by_id(4)

        assert company is not None
        assert company.id == 4
        assert company.company_name == "Minimal Company"
        assert company.owner == ""
        assert company.address == ""
        assert company.company_desc == ""

    @pytest.mark.asyncio
    async def test_get_company_detail_with_null_fields(self, service: CompanyService, setup_database):
        """Test company retrieval with NULL optional fields"""
        # Insert company with NULL optional fields
        async with db_manager.get_connection() as conn:
            await conn.execute("""
                INSERT INTO companies (
                    id, company_name, owner, company_desc, address,
                    create_time, update_time, last_sync_at, is_active
                ) VALUES
                    (5, 'Null Company', NULL, NULL, NULL,
                     '2023-01-09 00:00:00', '2023-01-10 00:00:00', datetime('now'), 1)
            """)
            await conn.commit()

        company = await service.get_company_by_id(5)

        assert company is not None
        assert company.id == 5
        assert company.company_name == "Null Company"
        assert company.owner is None
        assert company.address is None
        assert company.company_desc is None

    @pytest.mark.asyncio
    async def test_get_company_detail_inactive_company(self, service: CompanyService, setup_database):
        """Test that inactive companies are not returned"""
        # Insert inactive company
        async with db_manager.get_connection() as conn:
            await conn.execute("""
                INSERT INTO companies (
                    id, company_name, owner, company_desc, address,
                    create_time, update_time, last_sync_at, is_active
                ) VALUES
                    (6, 'Inactive Company', 'Owner 6', 'Description 6', 'Address 6',
                     '2023-01-11 00:00:00', '2023-01-12 00:00:00', datetime('now'), 0)
            """)
            await conn.commit()

        company = await service.get_company_by_id(6)

        # Should not find inactive company
        assert company is None