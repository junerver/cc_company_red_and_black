"""
Unit tests for sync service
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from src.services.sync_service import SyncService
from src.models.company import CompanyCreate
from src.models.sync import SyncLog, SyncState
from src.utils.exceptions import DatabaseException, SyncInProgressException


class TestSyncService:
    """Unit tests for sync service"""

    @pytest.fixture
    async def sync_service(self):
        """Sync service fixture"""
        with patch('src.services.sync_service.get_database') as mock_db:
            service = SyncService()
            service.db = AsyncMock()
            mock_db.return_value = service.db
            yield service

    @pytest.fixture
    def sample_external_companies(self):
        """Sample external company data"""
        return [
            {
                "id": 1,
                "company_name": "Company 1",
                "owner": "Owner 1",
                "company_desc": "Description 1",
                "adress": "Address 1",
                "create_time": "2023-01-01 00:00:00",
                "update_time": "2023-01-02 00:00:00",
                "code": "CODE001",
                "uuid": "uuid-1"
            },
            {
                "id": 2,
                "company_name": "Company 2",
                "owner": "Owner 2",
                "company_desc": None,
                "adress": "Address 2",
                "create_time": "2023-01-03 00:00:00",
                "update_time": None,
                "code": None,
                "uuid": None
            }
        ]

    @pytest.mark.asyncio
    async def test_start_sync_success(self, sync_service: SyncService):
        """Test successful sync start"""
        with patch('src.services.sync_service.get_sync_state') as mock_state:
            mock_state.return_value = SyncState(is_running=False)

            with patch.object(sync_service, '_create_sync_log', return_value=SyncLog(id=1, start_time=datetime.now(), status="running")):
                result = await sync_service.start_sync()

                assert isinstance(result, SyncLog)
                assert result.status == "running"
                assert result.id == 1

    @pytest.mark.asyncio
    async def test_start_sync_already_running(self, sync_service: SyncService):
        """Test sync start when already running"""
        with patch('src.services.sync_service.get_sync_state') as mock_state:
            mock_state.return_value = SyncState(is_running=True)

            with pytest.raises(SyncInProgressException):
                await sync_service.start_sync()

    @pytest.mark.asyncio
    async def test_perform_sync(self, sync_service: SyncService, sample_external_companies):
        """Test sync execution"""
        with patch('src.services.sync_service.create_api_client') as mock_client_creator:
            mock_client = AsyncMock()
            mock_client_creator.return_value.__aenter__.return_value = mock_client
            mock_client.get_all_companies.return_value = sample_external_companies

            # Mock database operations
            sync_service.db.execute_query.return_value = []  # No existing companies
            sync_service.db.execute_many.return_value = 2  # 2 companies inserted

            result = await sync_service.perform_sync(mock_client, sync_log_id=1)

            assert result["total_records"] == 2
            assert result["success_records"] == 2
            assert result["failed_records"] == 0
            assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_perform_sync_with_existing_data(self, sync_service: SyncService, sample_external_companies):
        """Test sync with existing data (incremental update)"""
        # Mock existing company
        existing_company = {
            "id": 1,
            "company_name": "Company 1",  # Same as in sample
            "update_time": "2023-01-01 00:00:00"  # Older than sample
        }

        with patch('src.services.sync_service.create_api_client') as mock_client_creator:
            mock_client = AsyncMock()
            mock_client_creator.return_value.__aenter__.return_value = mock_client
            mock_client.get_all_companies.return_value = sample_external_companies

            # Mock database operations
            sync_service.db.execute_query.return_value = [existing_company]
            sync_service.db.execute_update.return_value = 1  # 1 company updated
            sync_service.db.execute_many.return_value = 1  # 1 company inserted

            result = await sync_service.perform_sync(mock_client, sync_log_id=1)

            assert result["total_records"] == 2
            assert result["success_records"] == 2
            assert result["failed_records"] == 0

    @pytest.mark.asyncio
    async def test_cancel_sync(self, sync_service: SyncService):
        """Test sync cancellation"""
        with patch('src.services.sync_service.get_sync_state') as mock_state:
            mock_state.return_value = SyncState(is_running=True)

            result = await sync_service.cancel_sync()

            assert result is True

    @pytest.mark.asyncio
    async def test_cancel_sync_not_running(self, sync_service: SyncService):
        """Test cancel sync when not running"""
        with patch('src.services.sync_service.get_sync_state') as mock_state:
            mock_state.return_value = SyncState(is_running=False)

            result = await sync_service.cancel_sync()

            assert result is False

    @pytest.mark.asyncio
    async def test_get_sync_progress(self, sync_service: SyncService):
        """Test getting sync progress"""
        with patch('src.services.sync_service.get_sync_state') as mock_state:
            mock_state.return_value = SyncState(
                is_running=True,
                current_page=3,
                total_pages=10,
                processed_records=150,
                total_records=500,
                start_time=datetime.now()
            )

            result = await sync_service.get_sync_progress()

            assert result["is_running"] is True
            assert result["current_page"] == 3
            assert result["total_pages"] == 10
            assert result["processed_records"] == 150
            assert result["total_records"] == 500
            assert result["percentage"] == 30.0

    @pytest.mark.asyncio
    async def test_get_sync_status(self, sync_service: SyncService):
        """Test getting sync status"""
        mock_sync_log = SyncLog(
            id=1,
            start_time=datetime.now(),
            status="completed",
            total_records=100,
            success_records=95,
            failed_records=5,
            duration_ms=30000
        )

        sync_service.db.execute_query.return_value = [mock_sync_log]

        result = await sync_service.get_sync_status()

        assert result["id"] == 1
        assert result["status"] == "completed"
        assert result["total_records"] == 100
        assert result["success_records"] == 95
        assert result["failed_records"] == 5
        assert result["duration_ms"] == 30000

    @pytest.mark.asyncio
    async def test_get_sync_status_no_history(self, sync_service: SyncService):
        """Test getting sync status with no history"""
        sync_service.db.execute_query.return_value = []

        result = await sync_service.get_sync_status()

        assert result == {}