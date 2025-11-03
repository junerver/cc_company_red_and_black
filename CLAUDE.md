# CC Company Red and Black - Claude Context

**Last updated**: 2025-11-03

## Project Overview

This is a Python-based data synchronization application that crawls company information from external APIs and provides a web interface for data management and search.

## Active Technologies

- Python 3.13 + FastAPI + httpx + aiosqlite + Pydantic + uvicorn (1-company-data-sync)
- SQLite (1-company-data-sync)

## Recent Changes

- 1-company-data-sync: Added Python 3.13 + FastAPI + httpx + aiosqlite + Pydantic + uvicorn
- 1-company-data-sync: Added SQLite

## Project Structure

```
src/
├── api/
│   ├── main.py           # FastAPI application entry
│   ├── routes/
│   │   ├── sync.py      # Sync endpoints
│   │   └── companies.py # Company CRUD endpoints
│   └── middleware/
│       └── __init__.py
├── models/
│   ├── company.py       # Company data models
│   ├── sync.py          # Sync operation models
│   └── database.py      # Database connection and setup
├── services/
│   ├── sync_service.py  # Core sync logic
│   ├── company_service.py # Company business logic
│   └── api_client.py    # External API client
├── utils/
│   ├── __init__.py
│   ├── logging.py       # Logging configuration
│   └── validation.py    # Data validation utilities
└── static/              # Frontend static files
    ├── css/
    ├── js/
    └── index.html

tests/
├── contract/
│   ├── test_api.py      # API contract tests
│   └── test_sync.py     # Sync contract tests
├── integration/
│   ├── test_full_sync.py # Full sync integration tests
│   └── test_search.py   # Search integration tests
└── unit/
    ├── test_models.py   # Model unit tests
    ├── test_services.py # Service unit tests
    └── test_utils.py    # Utility unit tests
```

## Key Commands

- uv run pytest
- ruff check .

## Development Guidelines

### Constitutional Requirements

**CRITICAL**: This project follows strict constitutional principles that must be adhered to:

1. **UV-First 依赖管理**: All Python package operations must use `uv` commands. NEVER use `pip` or `python -m pip`.
   - Install: `uv add package-name`
   - Remove: `uv remove package-name`
   - Run: `uv run python script.py`

2. **API-First 数据设计**: Data structures must be based on external API contracts. All data models must align with interface documentation and use Pydantic for validation.

3. **SQLite 本地缓存优先**: All data from interfaces must be cached to local SQLite first. Ensure offline access capability with timestamps and sync status.

4. **FastAPI 异步优先**: All API endpoints must use async/await. Database operations must use async connection pools. HTTP clients must use async libraries.

5. **测试驱动开发 (NON-NEGOTIABLE)**: TDD is mandatory. Unit test coverage must be ≥90%. Integration tests must cover key flows. Use pytest and pytest-asyncio.

### Technology Stack

- **Package Manager**: uv (required, no exceptions)
- **Web Framework**: FastAPI with async/await
- **HTTP Client**: httpx for async requests
- **Database**: aiosqlite for async SQLite operations
- **Data Validation**: Pydantic models
- **Testing**: pytest + pytest-asyncio
- **Server**: uvicorn

### Code Patterns

**Async Patterns**:
```python
# Always use async/await for API endpoints
@app.get("/api/companies")
async def get_companies():
    async with aiosqlite.connect(db_path) as db:
        result = await db.execute("SELECT * FROM companies")
        return await result.fetchall()

# Always use async HTTP clients
async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

**Database Patterns**:
```python
# Use connection pooling and transactions
async def batch_insert_companies(companies: List[Company]):
    async with aiosqlite.connect(db_path) as db:
        await db.execute("BEGIN TRANSACTION")
        try:
            for company in companies:
                await db.execute(
                    "INSERT INTO companies (...) VALUES (...)",
                    company.dict()
                )
            await db.commit()
        except Exception:
            await db.rollback()
            raise
```

### External API Integration

**Base URL**: `https://kaifazhe.fun/prod-api`
**Endpoint**: `/system/softwareCompany/list`
**Pagination**: `pageNum` (1-based), `pageSize` (default 50)
**Rate Limiting**: Max 200 concurrent connections
**Timeout**: 30 seconds total, 10 seconds connect

### Data Models

Key entities follow Pydantic models with strict validation:
- **Company**: Core company data with sync tracking
- **SyncLog**: Synchronization operation records
- **SearchQuery**: Search query tracking

### Performance Requirements

- Data sync: 1000 records in ≤30 seconds
- Search: 5000 records results in ≤1 second
- Concurrent users: 100 simultaneous users
- Incremental sync: 100 changes in ≤5 seconds

### Testing Strategy

- **Unit Tests**: All business logic, ≥90% coverage
- **Integration Tests**: API endpoints and sync workflows
- **Contract Tests**: External API integration
- **Async Tests**: Use pytest-asyncio for all async code

### Error Handling

- Implement exponential backoff for API retries
- Use structured logging with correlation IDs
- Provide user-friendly error messages
- Log all sync operations with timing

## Development Workflow

1. **Setup**: Use `uv sync` to install dependencies
2. **Development**: Use `uv run uvicorn src.api.main:app --reload`
3. **Testing**: Use `uv run pytest` for all tests
4. **Database**: SQLite file in `data/` directory
5. **Static Files**: Frontend served from `src/static/`

## Important Notes

- Never use `pip` - always use `uv` commands
- All I/O operations must be async
- Database operations must use transactions
- API responses must include proper error handling
- Frontend is static files (no build process required)
- Tests must be written before implementation (TDD)