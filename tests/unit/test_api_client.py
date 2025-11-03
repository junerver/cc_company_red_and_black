"""
Unit tests for API client
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.api_client import APIClient
from src.models.company import ExternalCompany, ExternalData, ExternalCompanyResponse
from src.utils.exceptions import APIException


class TestAPIClient:
    """Unit tests for API client"""

    @pytest.fixture
    async def api_client(self):
        """API client fixture"""
        client = APIClient()
        await client.initialize()
        yield client
        await client.close()

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test client initialization"""
        client = APIClient()
        await client.initialize()

        assert client.client is not None
        assert client.endpoints is not None

        await client.close()

    @pytest.mark.asyncio
    async def test_get_companies_page_success(self, api_client: APIClient):
        """Test successful page retrieval"""
        # Mock successful response
        mock_response_data = {
            "code": 200,
            "msg": "success",
            "data": {
                "total_page": 1,
                "total": 1,
                "rows": [
                    {
                        "id": 1,
                        "company_name": "Test Company",
                        "owner": "Test Owner",
                        "company_desc": "Test Description",
                        "adress": "Test Address",
                        "create_time": "2023-01-01 00:00:00",
                        "update_time": "2023-01-02 00:00:00",
                        "code": "TEST001",
                        "uuid": "test-uuid"
                    }
                ]
            }
        }

        with patch.object(api_client, '_request', return_value=mock_response_data):
            result = await api_client.get_companies_page(1, 50)

            assert isinstance(result, ExternalData)
            assert result.total == 1
            assert len(result.rows) == 1
            assert result.rows[0].company_name == "Test Company"
            assert result.rows[0].adress == "Test Address"  # Note: API uses "adress"

    @pytest.mark.asyncio
    async def test_get_companies_page_http_error(self, api_client: APIClient):
        """Test handling of HTTP errors"""
        with patch.object(api_client, '_request', side_effect=APIException("HTTP error")):
            with pytest.raises(APIException):
                await api_client.get_companies_page(1, 50)

    @pytest.mark.asyncio
    async def test_get_total_pages(self, api_client: APIClient):
        """Test getting total pages"""
        mock_response_data = {
            "code": 200,
            "msg": "success",
            "data": {
                "total_page": 5,
                "total": 250,
                "rows": []
            }
        }

        with patch.object(api_client, 'get_companies_page', return_value=ExternalData(**mock_response_data["data"])):
            total_pages = await api_client.get_total_pages(50)

            assert total_pages == 5

    @pytest.mark.asyncio
    async def test_get_all_companies(self, api_client: APIClient):
        """Test getting all companies with parallel requests"""
        mock_response_data = {
            "code": 200,
            "msg": "success",
            "data": {
                "total_page": 2,
                "total": 100,
                "rows": [
                    {
                        "id": 1,
                        "company_name": "Company 1",
                        "owner": "Owner 1",
                        "company_desc": None,
                        "adress": "Address 1",
                        "create_time": "2023-01-01 00:00:00",
                        "update_time": None,
                        "code": None,
                        "uuid": None
                    }
                ]
            }
        }

        with patch.object(api_client, 'get_total_pages', return_value=2):
            with patch.object(api_client, 'get_companies_page', return_value=ExternalData(**mock_response_data["data"])):
                companies = await api_client.get_all_companies(50)

                assert len(companies) == 2  # 2 pages, 1 company each
                assert companies[0].company_name == "Company 1"

    @pytest.mark.asyncio
    async def test_health_check_success(self, api_client: APIClient):
        """Test successful health check"""
        with patch.object(api_client, 'get_companies_page', return_value=ExternalData(total=0, total_page=0, rows=[])):
            result = await api_client.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, api_client: APIClient):
        """Test health check failure"""
        with patch.object(api_client, 'get_companies_page', side_effect=APIException("API error")):
            result = await api_client.health_check()
            assert result is False


class TestExternalCompany:
    """Unit tests for ExternalCompany model"""

    def test_to_internal_conversion(self):
        """Test conversion from external to internal model"""
        external = ExternalCompany(
            id=1,
            company_name="Test Company",
            owner="Test Owner",
            company_desc="Test Description",
            adress="Test Address",  # Note: API uses "adress"
            create_time="2023-01-01 00:00:00",
            update_time="2023-01-02 00:00:00",
            code="TEST001",
            uuid="test-uuid"
        )

        internal = external.to_internal()

        assert internal.company_name == "Test Company"
        assert internal.owner == "Test Owner"
        assert internal.company_desc == "Test Description"
        assert internal.address == "Test Address"  # Should be mapped from "adress"
        assert internal.code == "TEST001"
        assert internal.uuid == "test-uuid"