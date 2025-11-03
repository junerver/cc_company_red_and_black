"""
Sync API endpoints for Company Data Synchronization System
"""

import asyncio
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks

from ...models.sync import SyncStartResponse, SyncStatusResponse, SyncProgressResponse, SyncLogUpdate
from ...services.sync_service import get_sync_service
from ...services.api_client import create_api_client, APIClient
from ...utils.logging import get_logger
from ...utils.exceptions import SyncInProgressException

logger = get_logger(__name__)
router = APIRouter()


@router.post("/sync", response_model=SyncStartResponse, status_code=202)
async def start_sync():
    """Start data synchronization from external API"""
    try:
        sync_service = await get_sync_service()
        sync_log = await sync_service.start_sync()

        # Start sync in background using asyncio.create_task
        # Keep reference to task to prevent garbage collection
        logger.info(f"Creating background task for sync_log_id: {sync_log.id}")
        task = asyncio.create_task(run_sync_background(sync_log.id))

        # Add callback to log task completion/errors
        def task_done_callback(t):
            try:
                if t.exception():
                    logger.error(f"Background task failed with exception: {t.exception()}")
                else:
                    logger.info(f"Background task completed successfully")
            except Exception as e:
                logger.error(f"Error in task_done_callback: {e}")

        task.add_done_callback(task_done_callback)
        logger.info(f"Background task created and callback registered")

        return SyncStartResponse(
            message="Synchronization started successfully",
            sync_id=sync_log.id,
            estimated_duration_minutes=5
        )

    except SyncInProgressException as e:
        logger.warning(f"Sync start failed: {e}")
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error starting sync: {e}")
        raise HTTPException(status_code=500, detail="Failed to start synchronization")


@router.get("/sync/status", response_model=SyncStatusResponse)
async def get_sync_status():
    """Get current synchronization status"""
    try:
        sync_service = await get_sync_service()
        status = await sync_service.get_sync_status()

        if not status:
            raise HTTPException(status_code=404, detail="No synchronization history found")

        return SyncStatusResponse(**status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sync status")


@router.get("/sync/progress", response_model=SyncProgressResponse)
async def get_sync_progress():
    """Get real-time synchronization progress"""
    try:
        sync_service = await get_sync_service()
        progress = await sync_service.get_sync_progress()

        # Return progress even when not running so frontend can detect completion
        return SyncProgressResponse(**progress)

    except Exception as e:
        logger.error(f"Error getting sync progress: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sync progress")


@router.post("/sync/cancel")
async def cancel_sync():
    """Cancel ongoing synchronization"""
    try:
        sync_service = await get_sync_service()
        success = await sync_service.cancel_sync()

        if not success:
            raise HTTPException(status_code=404, detail="No active synchronization to cancel")

        return {"message": "Synchronization cancelled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling sync: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel synchronization")


async def run_sync_background(sync_log_id: int):
    """Background task to run synchronization"""
    logger.info(f"Starting background sync task for sync_log_id: {sync_log_id}")

    try:
        sync_service = await get_sync_service()

        # Create API client using APIClient context manager
        async with APIClient() as api_client:
            # Perform synchronization
            result = await sync_service.perform_sync(api_client, sync_log_id)

            logger.info(f"Background sync completed: {result}")

    except Exception as e:
        logger.error(f"Background sync failed: {e}")

        # Update sync log with error
        try:
            sync_service = await get_sync_service()
            await sync_service._update_sync_log(
                sync_log_id,
                SyncLogUpdate(
                    end_time=datetime.now(),
                    status="failed",
                    error_message=str(e),
                    duration_ms=None
                )
            )
        except Exception as log_error:
            logger.error(f"Failed to update sync log with error: {log_error}")


@router.get("/sync/history")
async def get_sync_history(limit: int = 10, status: str = None):
    """Get synchronization history"""
    try:
        sync_service = await get_sync_service()

        # This would need to be implemented in sync service
        # For now, return empty history
        return {
            "sync_logs": [],
            "total_count": 0
        }

    except Exception as e:
        logger.error(f"Error getting sync history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sync history")