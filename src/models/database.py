"""
Database connection and management for Company Data Synchronization System
"""

import asyncio
import aiosqlite
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from ..utils.config import get_settings
from ..utils.exceptions import DatabaseException
from ..utils.logging import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Database connection manager with connection pooling"""

    def __init__(self):
        self.settings = get_settings()
        self.db_path = str(self.settings.database_path)
        self._connection_pool: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """Initialize database connection and run migrations"""
        try:
            # Create connection with optimal settings
            self._connection_pool = await aiosqlite.connect(self.db_path)

            # Configure SQLite for performance
            await self._configure_connection()

            # Run database schema
            await self._run_schema()

            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseException(f"Database initialization failed: {e}", operation="initialize")

    async def _configure_connection(self) -> None:
        """Configure connection settings for optimal performance"""
        if not self._connection_pool:
            raise DatabaseException("No database connection available", operation="configure")

        # Enable WAL mode for better concurrency
        await self._connection_pool.execute("PRAGMA journal_mode=WAL")
        await self._connection_pool.execute("PRAGMA synchronous=NORMAL")
        await self._connection_pool.execute("PRAGMA cache_size=10000")
        await self._connection_pool.execute("PRAGMA temp_store=memory")
        await self._connection_pool.execute("PRAGMA mmap_size=268435456")  # 256MB
        await self._connection_pool.execute("PRAGMA foreign_keys=ON")

    async def _run_schema(self) -> None:
        """Run database schema creation"""
        if not self._connection_pool:
            raise DatabaseException("No database connection available", operation="schema")

        schema_sql = """
        -- Create companies table if not exists
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY,
            company_name TEXT NOT NULL,
            owner TEXT,
            company_desc TEXT,
            address TEXT,
            create_time DATETIME,
            update_time DATETIME,
            code TEXT,
            uuid TEXT,
            last_sync_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        );

        -- Create indexes for companies table
        CREATE INDEX IF NOT EXISTS idx_company_name ON companies(company_name);
        CREATE INDEX IF NOT EXISTS idx_owner ON companies(owner);
        CREATE INDEX IF NOT EXISTS idx_update_time ON companies(update_time);
        CREATE INDEX IF NOT EXISTS idx_last_sync ON companies(last_sync_at);
        CREATE INDEX IF NOT EXISTS idx_active ON companies(is_active);

        -- Create full-text search virtual table
        CREATE VIRTUAL TABLE IF NOT EXISTS companies_fts USING fts5(
            company_name,
            owner,
            address,
            content='companies',
            content_rowid='id'
        );

        -- Create triggers to maintain FTS index
        CREATE TRIGGER IF NOT EXISTS companies_fts_insert
        AFTER INSERT ON companies BEGIN
            INSERT INTO companies_fts(rowid, company_name, owner, address)
            VALUES (new.id, new.company_name, new.owner, new.address);
        END;

        CREATE TRIGGER IF NOT EXISTS companies_fts_delete
        AFTER DELETE ON companies BEGIN
            INSERT INTO companies_fts(companies_fts, rowid, company_name, owner, address)
            VALUES ('delete', old.id, old.company_name, old.owner, old.address);
        END;

        CREATE TRIGGER IF NOT EXISTS companies_fts_update
        AFTER UPDATE ON companies BEGIN
            INSERT INTO companies_fts(companies_fts, rowid, company_name, owner, address)
            VALUES ('delete', old.id, old.company_name, old.owner, old.address);
            INSERT INTO companies_fts(rowid, company_name, owner, address)
            VALUES (new.id, new.company_name, new.owner, new.address);
        END;

        -- Create sync_logs table
        CREATE TABLE IF NOT EXISTS sync_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time DATETIME NOT NULL,
            end_time DATETIME,
            status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
            total_records INTEGER DEFAULT 0,
            success_records INTEGER DEFAULT 0,
            failed_records INTEGER DEFAULT 0,
            error_message TEXT,
            duration_ms INTEGER
        );

        -- Create indexes for sync_logs table
        CREATE INDEX IF NOT EXISTS idx_start_time ON sync_logs(start_time);
        CREATE INDEX IF NOT EXISTS idx_status ON sync_logs(status);

        -- Create search_queries table
        CREATE TABLE IF NOT EXISTS search_queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            result_count INTEGER DEFAULT 0,
            user_agent TEXT
        );

        -- Create indexes for search_queries table
        CREATE INDEX IF NOT EXISTS idx_timestamp ON search_queries(timestamp);
        CREATE INDEX IF NOT EXISTS idx_query ON search_queries(query);
        """

        await self._connection_pool.executescript(schema_sql)
        logger.debug("Database schema executed successfully")

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Get a database connection from the pool"""
        if not self._connection_pool:
            raise DatabaseException("Database not initialized", operation="get_connection")

        try:
            yield self._connection_pool
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise DatabaseException(f"Database operation failed: {e}")

    async def execute_query(self, query: str, params: tuple = ()) -> list[dict]:
        """Execute a SELECT query and return results as list of dictionaries"""
        async with self.get_connection() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected row count"""
        async with self.get_connection() as conn:
            cursor = await conn.execute(query, params)
            await conn.commit()
            return cursor.rowcount

    async def execute_many(self, query: str, params_list: list[tuple]) -> int:
        """Execute multiple INSERT/UPDATE/DELETE operations"""
        async with self.get_connection() as conn:
            cursor = await conn.executemany(query, params_list)
            await conn.commit()
            return cursor.rowcount

    async def close(self) -> None:
        """Close database connection"""
        if self._connection_pool:
            await self._connection_pool.close()
            self._connection_pool = None
            logger.info("Database connection closed")

    async def health_check(self) -> dict[str, bool]:
        """Perform database health check"""
        try:
            async with self.get_connection() as conn:
                await conn.execute("SELECT 1")
                return {"database": True, "readable": True, "writable": True}
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"database": False, "readable": False, "writable": False, "error": str(e)}


# Global database manager instance
db_manager = DatabaseManager()


async def get_database() -> DatabaseManager:
    """Get the global database manager instance"""
    if not db_manager._connection_pool:
        await db_manager.initialize()
    return db_manager


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Context manager for getting database connection"""
    db = await get_database()
    async with db.get_connection() as conn:
        yield conn