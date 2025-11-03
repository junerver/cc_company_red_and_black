#!/usr/bin/env python3
"""
Database initialization script for Company Data Synchronization System
"""

import asyncio
import aiosqlite
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logging import setup_logger

logger = setup_logger(__name__)


async def create_database_schema(db_path: str) -> None:
    """Create database schema with all tables, indexes, and triggers"""

    # Ensure data directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    async with aiosqlite.connect(db_path) as db:
        # Enable WAL mode for better concurrency
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")
        await db.execute("PRAGMA cache_size=10000")
        await db.execute("PRAGMA temp_store=memory")
        await db.execute("PRAGMA mmap_size=268435456")  # 256MB

        # Create companies table
        await db.execute("""
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
            )
        """)

        # Create indexes for companies table
        await db.execute("CREATE INDEX IF NOT EXISTS idx_company_name ON companies(company_name)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_owner ON companies(owner)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_update_time ON companies(update_time)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_last_sync ON companies(last_sync_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_active ON companies(is_active)")

        # Create full-text search virtual table
        await db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS companies_fts USING fts5(
                company_name,
                owner,
                address,
                content='companies',
                content_rowid='id'
            )
        """)

        # Create triggers to maintain FTS index
        await db.execute("""
            CREATE TRIGGER IF NOT EXISTS companies_fts_insert
            AFTER INSERT ON companies BEGIN
                INSERT INTO companies_fts(rowid, company_name, owner, address)
                VALUES (new.id, new.company_name, new.owner, new.address);
            END
        """)

        await db.execute("""
            CREATE TRIGGER IF NOT EXISTS companies_fts_delete
            AFTER DELETE ON companies BEGIN
                INSERT INTO companies_fts(companies_fts, rowid, company_name, owner, address)
                VALUES ('delete', old.id, old.company_name, old.owner, old.address);
            END
        """)

        await db.execute("""
            CREATE TRIGGER IF NOT EXISTS companies_fts_update
            AFTER UPDATE ON companies BEGIN
                INSERT INTO companies_fts(companies_fts, rowid, company_name, owner, address)
                VALUES ('delete', old.id, old.company_name, old.owner, old.address);
                INSERT INTO companies_fts(rowid, company_name, owner, address)
                VALUES (new.id, new.company_name, new.owner, new.address);
            END
        """)

        # Create sync_logs table
        await db.execute("""
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
            )
        """)

        # Create indexes for sync_logs table
        await db.execute("CREATE INDEX IF NOT EXISTS idx_start_time ON sync_logs(start_time)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_status ON sync_logs(status)")

        # Create search_queries table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS search_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                result_count INTEGER DEFAULT 0,
                user_agent TEXT
            )
        """)

        # Create indexes for search_queries table
        await db.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON search_queries(timestamp)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_query ON search_queries(query)")

        await db.commit()
        logger.info("Database schema created successfully")


async def check_database_exists(db_path: str) -> bool:
    """Check if database file exists and has tables"""
    if not os.path.exists(db_path):
        return False

    try:
        async with aiosqlite.connect(db_path) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in await cursor.fetchall()]
            required_tables = ['companies', 'sync_logs', 'search_queries', 'companies_fts']

            return all(table in tables for table in required_tables)
    except Exception as e:
        logger.error(f"Error checking database: {e}")
        return False


async def main():
    """Main initialization function"""
    # Get database path from environment or use default
    db_path = os.getenv("DATABASE_URL", "sqlite:///./data/companies.db")
    if db_path.startswith("sqlite:///"):
        db_path = db_path[10:]  # Remove sqlite:///

    logger.info(f"Initializing database at: {db_path}")

    try:
        if await check_database_exists(db_path):
            logger.info("Database already exists and is properly initialized")
        else:
            await create_database_schema(db_path)
            logger.info("Database initialized successfully")

        # Test database connection
        async with aiosqlite.connect(db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM companies")
            count = await cursor.fetchone()
            logger.info(f"Database ready. Current company count: {count[0]}")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())