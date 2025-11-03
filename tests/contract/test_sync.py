"""
Contract tests for sync API endpoints
"""

import pytest
import asyncio
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
    """Setup test database"""
    await db_manager.initialize()
    yield
    await db_manager.close()


class TestSyncAPI:
    """Contract tests for sync API endpoints"""

    @pytest.mark.asyncio
    async def test_start_sync_endpoint(self, client: AsyncClient, setup_database):
        """Test POST /api/sync endpoint"""
        response = await client.post("/api/sync")

        assert response.status_code == 202
        data = response.json()

        assert "message" in data
        assert "sync_id" in data
        assert "estimated_duration_minutes" in data
        assert isinstance(data["sync_id"], int)
        assert isinstance(data["estimated_duration_minutes"], int)

    @pytest.mark.asyncio
    async def test_start_sync_already_running(self, client: AsyncClient, setup_database):
        """Test POST /api/sync when sync is already running"""
        # Start first sync
        response1 = await client.post("/api/sync")
        assert response1.status_code == 202

        # Try to start second sync
        response2 = await client.post("/api/sync")
        assert response2.status_code == 409
        data = response2.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_get_sync_status(self, client: AsyncClient, setup_database):
        """Test GET /api/sync/status endpoint"""
        response = await client.get("/api/sync/status")

        assert response.status_code == 200
        data = response.json()

        # Should contain sync status information
        assert "id" in data or data == {}  # Empty response if no sync history

    @pytest.mark.asyncio
    async def test_get_sync_progress_no_active_sync(self, client: AsyncClient, setup_database):
        """Test GET /api/sync/progress when no sync is active"""
        response = await client.get("/api/sync/progress")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_cancel_sync_no_active_sync(self, client: AsyncClient, setup_database):
        """Test POST /api/sync/cancel when no sync is active"""
        response = await client.post("/api/sync/cancel")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient, setup_database):
        """Test GET /api/health endpoint"""
        response = await client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "database" in data
        assert "timestamp" in data
        assert data["status"] == "healthy"
        assert "database" in data["database"]