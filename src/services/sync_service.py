"""
Sync service for Company Data Synchronization System
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from ..models.company import Company, CompanyCreate
from ..models.sync import SyncLog, SyncLogCreate, SyncLogUpdate, SyncState, get_sync_state, set_sync_state
from ..models.database import get_db_connection
from ..utils.exceptions import DatabaseException, SyncInProgressException
from ..utils.logging import get_logger

logger = get_logger(__name__)


class SyncService:
    """Service for managing company data synchronization"""

    def __init__(self):
        self.db = None

    async def start_sync(self) -> SyncLog:
        """Start a new synchronization process"""
        current_state = get_sync_state()
        if current_state.is_running:
            raise SyncInProgressException("Synchronization is already in progress")

        # Create sync log
        sync_log = await self._create_sync_log()

        # Update state
        new_state = SyncState(
            is_running=True,
            current_sync_id=sync_log.id,
            current_page=0,
            total_pages=0,
            processed_records=0,
            total_records=0,
            start_time=datetime.now()
        )
        set_sync_state(new_state)

        logger.info(f"Started sync process with ID: {sync_log.id}")
        return sync_log

    async def perform_sync(self, api_client, sync_log_id: int) -> Dict[str, int]:
        """Perform the actual synchronization"""
        start_time = datetime.now()
        state = get_sync_state()

        try:
            logger.info("Starting data synchronization from external API")

            # Get total pages and records first to update progress immediately
            total_pages = await api_client.get_total_pages(page_size=50)
            first_page = await api_client.get_companies_page(1, page_size=50)
            total_records = first_page.total

            # Update state with total records so frontend can show progress
            state.total_records = total_records
            state.total_pages = total_pages
            logger.info(f"Total records to sync: {total_records} ({total_pages} pages)")

            # Get all companies from external API
            external_companies = await api_client.get_all_companies()
            logger.info(f"Retrieved {len(external_companies)} companies from external API")

            # Get existing companies from database
            existing_companies = await self._get_existing_companies()
            existing_by_id = {comp["id"]: comp for comp in existing_companies}

            logger.info(f"Found {len(existing_by_id)} existing companies in database")

            # Process companies
            success_count = 0
            failed_count = 0

            # Batch processing
            batch_size = 100
            for i in range(0, len(external_companies), batch_size):
                batch = external_companies[i:i + batch_size]

                # Update progress
                current_page = (i // batch_size) + 1
                total_pages = (len(external_companies) + batch_size - 1) // batch_size
                processed_records = min(i + batch_size, len(external_companies))

                state.update_progress(current_page, total_pages, processed_records)

                batch_success, batch_failed = await self._process_batch(
                    batch, existing_by_id
                )

                success_count += batch_success
                failed_count += batch_failed

                logger.info(f"Processed batch {current_page}/{total_pages}: {batch_success} success, {batch_failed} failed")

            # Update sync log
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            await self._update_sync_log(
                sync_log_id,
                SyncLogUpdate(
                    end_time=datetime.now(),
                    status="completed",
                    total_records=total_records,
                    success_records=success_count,
                    failed_records=failed_count,
                    duration_ms=duration_ms
                )
            )

            # Update state
            state.is_running = False
            set_sync_state(state)

            logger.info(f"Sync completed: {success_count} success, {failed_count} failed")

            return {
                "total_records": total_records,
                "success_records": success_count,
                "failed_records": failed_count,
                "status": "completed"
            }

        except Exception as e:
            logger.error(f"Sync failed: {e}")

            # Update sync log with error
            await self._update_sync_log(
                sync_log_id,
                SyncLogUpdate(
                    end_time=datetime.now(),
                    status="failed",
                    error_message=str(e),
                    duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                )
            )

            # Update state
            state.is_running = False
            set_sync_state(state)

            raise

    async def cancel_sync(self) -> bool:
        """Cancel ongoing synchronization"""
        state = get_sync_state()

        if not state.is_running:
            return False

        # Update sync log
        if state.current_sync_id:
            await self._update_sync_log(
                state.current_sync_id,
                SyncLogUpdate(
                    end_time=datetime.now(),
                    status="cancelled"
                )
            )

        # Update state
        state.is_running = False
        set_sync_state(state)

        logger.info("Sync cancelled by user")
        return True

    async def get_sync_progress(self) -> Dict:
        """Get current sync progress"""
        state = get_sync_state()

        if not state.is_running:
            return {
                "is_running": False,
                "current_page": 0,
                "total_pages": 0,
                "processed_records": 0,
                "total_records": 0,
                "percentage": 0.0,
                "estimated_remaining_seconds": None
            }

        return {
            "is_running": True,
            "current_page": state.current_page,
            "total_pages": state.total_pages,
            "processed_records": state.processed_records,
            "total_records": state.total_records,
            "percentage": state.get_percentage(),
            "estimated_remaining_seconds": state.get_estimated_remaining_seconds(),
            "current_operation": f"Processing page {state.current_page} of {state.total_pages}"
        }

    async def get_sync_status(self) -> Dict:
        """Get latest sync status"""
        async with get_db_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT id, start_time, end_time, status, total_records,
                       success_records, failed_records, error_message, duration_ms
                FROM sync_logs
                ORDER BY id DESC
                LIMIT 1
                """
            )
            row = await cursor.fetchone()

            if row:
                return {
                    "id": row[0],
                    "start_time": row[1],
                    "end_time": row[2],
                    "status": row[3],
                    "total_records": row[4],
                    "success_records": row[5],
                    "failed_records": row[6],
                    "error_message": row[7],
                    "duration_ms": row[8]
                }
            else:
                return {}

    async def _create_sync_log(self) -> SyncLog:
        """Create a new sync log entry"""
        sync_log = SyncLogCreate(start_time=datetime.now(), status="running")

        async with get_db_connection() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO sync_logs (start_time, status, total_records, success_records, failed_records)
                VALUES (?, ?, 0, 0, 0)
                """,
                (sync_log.start_time, sync_log.status)
            )

            sync_log_id = cursor.lastrowid
            await conn.commit()

            return SyncLog(
                id=sync_log_id,
                start_time=sync_log.start_time,
                status=sync_log.status,
                total_records=0,
                success_records=0,
                failed_records=0
            )

    async def _update_sync_log(self, sync_log_id: int, update: SyncLogUpdate) -> None:
        """Update sync log entry"""
        async with get_db_connection() as conn:
            await conn.execute(
                """
                UPDATE sync_logs
                SET end_time = ?, status = ?, total_records = ?,
                    success_records = ?, failed_records = ?, error_message = ?, duration_ms = ?
                WHERE id = ?
                """,
                (
                    update.end_time, update.status, update.total_records,
                    update.success_records, update.failed_records, update.error_message,
                    update.duration_ms, sync_log_id
                )
            )
            await conn.commit()

    async def _get_existing_companies(self) -> List[Dict]:
        """Get existing companies from database"""
        async with get_db_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT id, company_name, owner, company_desc, address,
                       create_time, update_time, code, uuid, last_sync_at, is_active
                FROM companies
                WHERE is_active = 1
                """
            )
            rows = await cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "company_name": row[1],
                    "owner": row[2],
                    "company_desc": row[3],
                    "address": row[4],
                    "create_time": row[5],
                    "update_time": row[6],
                    "code": row[7],
                    "uuid": row[8],
                    "last_sync_at": row[9],
                    "is_active": row[10]
                }
                for row in rows
            ]

    async def _process_batch(self, batch: List, existing_by_id: Dict) -> tuple[int, int]:
        """Process a batch of companies"""
        success_count = 0
        failed_count = 0

        to_insert = []
        to_update = []

        for external_company in batch:
            try:
                internal_company = external_company.to_internal()

                if external_company.id in existing_by_id:
                    # Check if update is needed
                    existing = existing_by_id[external_company.id]
                    if self._needs_update(existing, internal_company, external_company):
                        to_update.append(internal_company)
                else:
                    to_insert.append(internal_company)

            except Exception as e:
                logger.error(f"Failed to process company {external_company.id}: {e}")
                failed_count += 1

        # Insert new companies
        if to_insert:
            insert_success = await self._insert_companies(to_insert)
            success_count += insert_success
            failed_count += len(to_insert) - insert_success

        # Update existing companies
        if to_update:
            update_success = await self._update_companies(to_update)
            success_count += update_success
            failed_count += len(to_update) - update_success

        return success_count, failed_count

    def _needs_update(self, existing: Dict, internal: CompanyCreate, external) -> bool:
        """Check if company needs to be updated"""
        # Compare update times if available
        if external.update_time and existing["update_time"]:
            try:
                external_time = datetime.fromisoformat(external.update_time)
                existing_time = datetime.fromisoformat(existing["update_time"]) if existing["update_time"] else None

                if existing_time and external_time <= existing_time:
                    return False  # No update needed
            except ValueError:
                pass  # If time parsing fails, assume update needed

        # Always update if we can't determine timestamps
        return True

    async def _insert_companies(self, companies: List[CompanyCreate]) -> int:
        """Insert new companies into database"""
        if not companies:
            return 0

        try:
            async with get_db_connection() as conn:
                # Begin transaction
                await conn.execute("BEGIN TRANSACTION")

                # Insert companies
                values = []
                for company in companies:
                    values.append((
                        company.id,
                        company.company_name,
                        company.owner,
                        company.company_desc,
                        company.address,
                        company.create_time,
                        company.update_time,
                        company.code,
                        company.uuid,
                        datetime.now()  # last_sync_at
                    ))

                await conn.executemany(
                    """
                    INSERT INTO companies (
                        id, company_name, owner, company_desc, address,
                        create_time, update_time, code, uuid, last_sync_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values
                )

                await conn.commit()
                logger.debug(f"Inserted {len(companies)} new companies")
                return len(companies)

        except Exception as e:
            logger.error(f"Failed to insert companies: {e}")
            raise DatabaseException(f"Insert operation failed: {e}", operation="insert")

    async def _update_companies(self, companies: List[CompanyCreate]) -> int:
        """Update existing companies in database"""
        if not companies:
            return 0

        try:
            async with get_db_connection() as conn:
                # Begin transaction
                await conn.execute("BEGIN TRANSACTION")

                # Update companies
                for company in companies:
                    await conn.execute(
                        """
                        UPDATE companies
                        SET company_name = ?, owner = ?, company_desc = ?, address = ?,
                            update_time = ?, code = ?, uuid = ?, last_sync_at = ?
                        WHERE id = ?
                        """,
                        (
                            company.company_name,
                            company.owner,
                            company.company_desc,
                            company.address,
                            company.update_time,
                            company.code,
                            company.uuid,
                            datetime.now(),
                            company.id
                        )
                    )

                await conn.commit()
                logger.debug(f"Updated {len(companies)} companies")
                return len(companies)

        except Exception as e:
            logger.error(f"Failed to update companies: {e}")
            raise DatabaseException(f"Update operation failed: {e}", operation="update")


# Global sync service instance
sync_service = SyncService()


async def get_sync_service() -> SyncService:
    """Get sync service instance"""
    return sync_service