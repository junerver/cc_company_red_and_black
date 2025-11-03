"""
Main FastAPI application for Company Data Synchronization System
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime

from ..models.database import db_manager
from ..utils.config import get_settings
from ..utils.logging import get_logger
from .middleware.cors import setup_cors
from .middleware.error_handler import ErrorHandlerMiddleware, setup_error_handlers
from .routes import sync
from .routes import companies

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Company Data Synchronization System")

    # Initialize database
    await db_manager.initialize()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down Company Data Synchronization System")
    await db_manager.close()


# Create FastAPI application
app = FastAPI(
    title="Company Data Synchronization System",
    description="API for synchronizing and searching company data from external sources",
    version="1.0.0",
    lifespan=lifespan
)

# Setup middleware
setup_error_handlers(app)
app.add_middleware(ErrorHandlerMiddleware)
setup_cors(app)

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="src/static"), name="static")
except RuntimeError:
    logger.warning("Static files directory not found, continuing without static file serving")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page"""
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>公司数据同步系统</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            .loading {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                z-index: 9999;
                justify-content: center;
                align-items: center;
            }
            .progress-container {
                background: white;
                padding: 2rem;
                border-radius: 10px;
                text-align: center;
                min-width: 300px;
            }
            .sync-btn {
                min-width: 150px;
            }
            .search-container {
                margin-bottom: 1rem;
            }
            .table-responsive {
                max-height: 70vh;
                overflow-y: auto;
            }
            .modal-body {
                max-height: 60vh;
                overflow-y: auto;
            }
        </style>
    </head>
    <body>
        <div class="container-fluid py-4">
            <header class="mb-4">
                <h1 class="text-center">
                    <i class="fas fa-building"></i>
                    公司数据同步系统
                </h1>
                <p class="text-center text-muted">自动同步、搜索和管理公司信息</p>
            </header>

            <main>
                <!-- Sync Controls -->
                <section class="row mb-4">
                    <div class="col-12 text-center">
                        <button id="syncBtn" class="btn btn-primary btn-lg sync-btn" onclick="startSync()">
                            <i class="fas fa-sync"></i>
                            开始同步
                        </button>
                        <button id="cancelBtn" class="btn btn-warning btn-lg sync-btn d-none" onclick="cancelSync()">
                            <i class="fas fa-stop"></i>
                            取消同步
                        </button>
                    </div>
                </section>

                <!-- Sync Status -->
                <section id="syncStatus" class="row mb-4 d-none">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-header">
                                <h5 class="mb-0">
                                    <i class="fas fa-info-circle"></i>
                                    同步状态
                                </h5>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-6">
                                        <p><strong>状态:</strong> <span id="syncStatusText">准备就绪</span></p>
                                        <p><strong>进度:</strong> <span id="syncProgress">0%</span></p>
                                    </div>
                                    <div class="col-md-6">
                                        <p><strong>已处理:</strong> <span id="processedRecords">0</span> / <span id="totalRecords">0</span></p>
                                        <p><strong>当前页面:</strong> <span id="currentPage">0</span> / <span id="totalPages">0</span></p>
                                    </div>
                                </div>
                                <div class="progress mb-3">
                                    <div id="syncProgressBar" class="progress-bar" role="progressbar" style="width: 0%"></div>
                                </div>
                                <p class="mb-0"><small class="text-muted" id="syncMessage">点击"开始同步"按钮开始数据同步</small></p>
                            </div>
                        </div>
                    </div>
                </section>

                <!-- Search -->
                <section class="row mb-4">
                    <div class="col-12">
                        <div class="search-container">
                            <div class="input-group">
                                <input type="text" id="searchInput" class="form-control" placeholder="搜索公司名称、法人或地址...">
                                <button class="btn btn-outline-secondary" type="button" onclick="searchCompanies()">
                                    <i class="fas fa-search"></i>
                                    搜索
                                </button>
                                <button class="btn btn-outline-secondary" type="button" onclick="clearSearch()">
                                    <i class="fas fa-times"></i>
                                    清除
                                </button>
                            </div>
                        </div>
                    </div>
                </section>

                <!-- Companies Table -->
                <section class="row">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-header d-flex justify-content-between align-items-center">
                                <h5 class="mb-0">
                                    <i class="fas fa-list"></i>
                                    公司列表
                                </h5>
                                <span class="badge bg-primary" id="totalCount">0 条记录</span>
                            </div>
                            <div class="card-body">
                                <div class="table-responsive">
                                    <table class="table table-striped table-hover">
                                        <thead class="table-dark">
                                            <tr>
                                                <th>ID</th>
                                                <th>公司名称</th>
                                                <th>法人</th>
                                                <th>地址</th>
                                                <th>更新时间</th>
                                                <th>操作</th>
                                            </tr>
                                        </thead>
                                        <tbody id="companiesTableBody">
                                            <tr>
                                                <td colspan="6" class="text-center text-muted">
                                                    暂无数据，请先同步数据
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>

                                <!-- Pagination -->
                                <nav aria-label="Page navigation" class="mt-3">
                                    <ul class="pagination justify-content-center" id="pagination">
                                        <!-- Pagination will be generated here -->
                                    </ul>
                                </nav>
                            </div>
                        </div>
                    </div>
                </section>
            </main>
        </div>

        <!-- Loading Overlay -->
        <div id="loadingOverlay" class="loading">
            <div class="progress-container">
                <div class="spinner-border text-primary mb-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p id="loadingText">处理中...</p>
                <div class="progress" style="width: 200px;">
                    <div id="loadingProgress" class="progress-bar" role="progressbar" style="width: 0%"></div>
                </div>
            </div>
        </div>

        <!-- Company Detail Modal -->
        <div class="modal fade" id="companyDetailModal" tabindex="-1" aria-labelledby="companyDetailModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="companyDetailModalLabel">公司详情</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body" id="companyDetailBody">
                        <!-- Company details will be loaded here -->
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                    </div>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            let currentPage = 1;
            let currentSearch = '';
            let syncInProgress = false;

            // Show/hide loading overlay
            function showLoading(text = '处理中...') {
                document.getElementById('loadingText').textContent = text;
                document.getElementById('loadingOverlay').style.display = 'flex';
            }

            function hideLoading() {
                document.getElementById('loadingOverlay').style.display = 'none';
            }

            // Sync functions
            async function startSync() {
                if (syncInProgress) return;

                try {
                    syncInProgress = true;
                    document.getElementById('syncBtn').classList.add('d-none');
                    document.getElementById('cancelBtn').classList.remove('d-none');
                    document.getElementById('syncStatus').classList.remove('d-none');

                    updateSyncStatus('running', '开始同步数据...');

                    const response = await fetch('/api/sync', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        }
                    });

                    if (response.ok) {
                        const result = await response.json();
                        console.log('Sync started:', result);
                        pollSyncProgress();
                    } else {
                        throw new Error('Failed to start sync');
                    }
                } catch (error) {
                    console.error('Sync error:', error);
                    updateSyncStatus('failed', '同步失败: ' + error.message);
                    resetSyncButtons();
                }
            }

            async function cancelSync() {
                try {
                    const response = await fetch('/api/sync/cancel', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        }
                    });

                    if (response.ok) {
                        updateSyncStatus('cancelled', '同步已取消');
                    }
                } catch (error) {
                    console.error('Cancel error:', error);
                }

                resetSyncButtons();
            }

            async function pollSyncProgress() {
                if (!syncInProgress) return;

                try {
                    const response = await fetch('/api/sync/progress');
                    if (response.ok) {
                        const progress = await response.json();
                        updateSyncProgress(progress);

                        if (progress.is_running) {
                            setTimeout(pollSyncProgress, 1000); // Poll every second
                        } else {
                            updateSyncStatus('completed', '同步完成！');
                            setTimeout(() => {
                                loadCompanies();
                                resetSyncButtons();
                            }, 2000);
                        }
                    }
                } catch (error) {
                    console.error('Progress poll error:', error);
                    setTimeout(pollSyncProgress, 2000); // Retry after 2 seconds
                }
            }

            function updateSyncProgress(progress) {
                document.getElementById('syncProgressBar').style.width = progress.percentage + '%';
                document.getElementById('syncProgress').textContent = progress.percentage.toFixed(1) + '%';
                document.getElementById('processedRecords').textContent = progress.processed_records;
                document.getElementById('totalRecords').textContent = progress.total_records;
                document.getElementById('currentPage').textContent = progress.current_page;
                document.getElementById('totalPages').textContent = progress.total_pages;

                if (progress.current_operation) {
                    updateSyncStatus('running', progress.current_operation);
                }
            }

            function updateSyncStatus(status, message) {
                const statusText = document.getElementById('syncStatusText');
                const statusMessage = document.getElementById('syncMessage');
                const progressBar = document.getElementById('syncProgressBar');

                statusText.textContent = status;
                statusMessage.textContent = message;

                // Update progress bar color based on status
                progressBar.className = 'progress-bar';
                if (status === 'completed') {
                    progressBar.classList.add('bg-success');
                } else if (status === 'failed') {
                    progressBar.classList.add('bg-danger');
                } else if (status === 'cancelled') {
                    progressBar.classList.add('bg-warning');
                }
            }

            function resetSyncButtons() {
                syncInProgress = false;
                document.getElementById('syncBtn').classList.remove('d-none');
                document.getElementById('cancelBtn').classList.add('d-none');

                setTimeout(() => {
                    document.getElementById('syncStatus').classList.add('d-none');
                }, 3000);
            }

            // Search functions
            async function searchCompanies() {
                currentSearch = document.getElementById('searchInput').value.trim();
                currentPage = 1;
                await loadCompanies();
            }

            function clearSearch() {
                document.getElementById('searchInput').value = '';
                currentSearch = '';
                currentPage = 1;
                loadCompanies();
            }

            // Load companies
            async function loadCompanies() {
                console.log('[DEBUG] Starting loadCompanies');
                showLoading('加载公司数据...');
                console.log('[DEBUG] Loading overlay shown');

                const timeoutId = setTimeout(() => {
                    console.error('[DEBUG] Loading timeout - forcing hide loading');
                    const overlay = document.getElementById('loadingOverlay');
                    if (overlay) overlay.style.display = 'none';
                }, 15000); // 15 second timeout for slow database queries

                try {
                    const params = new URLSearchParams({
                        page: currentPage,
                        page_size: 50
                    });

                    if (currentSearch) {
                        params.append('query', currentSearch);
                    }

                    console.log('[DEBUG] Fetching from /api/companies?' + params.toString());

                    const response = await fetch(`/api/companies?${params}`, {
                        cache: 'no-store',
                        headers: {
                            'Cache-Control': 'no-cache',
                            'Cache-Control': 'no-cache, no-store, must-revalidate'
                        }
                    });

                    clearTimeout(timeoutId);
                    console.log('[DEBUG] Response received, status:', response.status);

                    if (response.ok) {
                        const data = await response.json();
                        console.log('[DEBUG] Data parsed:', data);
                        renderCompaniesTable(data);
                        updatePagination(data);
                    } else {
                        throw new Error(`HTTP ${response.status}: Failed to load companies`);
                    }
                } catch (error) {
                    console.error('[DEBUG] Load companies error:', error);
                    // Show error in table instead of alert
                    const tbody = document.getElementById('companiesTableBody');
                    if (tbody) {
                        tbody.innerHTML = `
                            <tr>
                                <td colspan="6" class="text-center text-danger">
                                    加载失败: ${error.message}
                                </td>
                            </tr>
                        `;
                    }
                } finally {
                    console.log('[DEBUG] Hiding loading overlay');
                    const overlay = document.getElementById('loadingOverlay');
                    if (overlay) overlay.style.display = 'none';
                    hideLoading();
                    console.log('[DEBUG] Loading overlay hidden');
                }
            }

            function renderCompaniesTable(data) {
                const tbody = document.getElementById('companiesTableBody');
                const totalCount = document.getElementById('totalCount');

                totalCount.textContent = `${data.total_count} 条记录`;

                if (data.companies.length === 0) {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="6" class="text-center text-muted">
                                ${currentSearch ? '未找到匹配的公司' : '暂无数据，请先同步数据'}
                            </td>
                        </tr>
                    `;
                    return;
                }

                tbody.innerHTML = data.companies.map(company => `
                    <tr>
                        <td>${company.id}</td>
                        <td>${company.company_name}</td>
                        <td>${company.owner || '-'}</td>
                        <td>${company.address || '-'}</td>
                        <td>${company.update_time ? new Date(company.update_time).toLocaleString() : '-'}</td>
                        <td>
                            <button class="btn btn-sm btn-outline-primary" onclick="showCompanyDetail(${company.id})">
                                <i class="fas fa-eye"></i>
                                详情
                            </button>
                        </td>
                    </tr>
                `).join('');
            }

            function updatePagination(data) {
                const pagination = document.getElementById('pagination');

                if (data.total_pages <= 1) {
                    pagination.innerHTML = '';
                    return;
                }

                let paginationHTML = '';

                // Previous button
                paginationHTML += `
                    <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                        <a class="page-link" href="#" onclick="changePage(${currentPage - 1})">上一页</a>
                    </li>
                `;

                // Page numbers
                const startPage = Math.max(1, currentPage - 2);
                const endPage = Math.min(data.total_pages, currentPage + 2);

                for (let i = startPage; i <= endPage; i++) {
                    paginationHTML += `
                        <li class="page-item ${i === currentPage ? 'active' : ''}">
                            <a class="page-link" href="#" onclick="changePage(${i})">${i}</a>
                        </li>
                    `;
                }

                // Next button
                paginationHTML += `
                    <li class="page-item ${currentPage === data.total_pages ? 'disabled' : ''}">
                        <a class="page-link" href="#" onclick="changePage(${currentPage + 1})">下一页</a>
                    </li>
                `;

                pagination.innerHTML = paginationHTML;
            }

            function changePage(page) {
                currentPage = page;
                loadCompanies();
            }

            // Company detail
            async function showCompanyDetail(companyId) {
                showLoading('加载公司详情...');

                try {
                    const response = await fetch(`/api/companies/detail/${companyId}`);

                    if (response.ok) {
                        const company = await response.json();
                        renderCompanyDetail(company);

                        const modal = new bootstrap.Modal(document.getElementById('companyDetailModal'));
                        modal.show();
                    } else {
                        throw new Error('Failed to load company details');
                    }
                } catch (error) {
                    console.error('Load company detail error:', error);
                    alert('加载公司详情失败: ' + error.message);
                } finally {
                    hideLoading();
                }
            }

            function renderCompanyDetail(company) {
                const detailBody = document.getElementById('companyDetailBody');
                const modalTitle = document.getElementById('companyDetailModalLabel');

                modalTitle.textContent = company.company_name;

                detailBody.innerHTML = `
                    <div class="row">
                        <div class="col-md-6">
                            <p><strong>ID:</strong> ${company.id}</p>
                            <p><strong>公司名称:</strong> ${company.company_name}</p>
                            <p><strong>法人:</strong> ${company.owner || '-'}</p>
                            <p><strong>地址:</strong> ${company.address || '-'}</p>
                        </div>
                        <div class="col-md-6">
                            <p><strong>创建时间:</strong> ${company.create_time ? new Date(company.create_time).toLocaleString() : '-'}</p>
                            <p><strong>更新时间:</strong> ${company.update_time ? new Date(company.update_time).toLocaleString() : '-'}</p>
                            <p><strong>最后同步:</strong> ${new Date(company.last_sync_at).toLocaleString()}</p>
                            <p><strong>公司代码:</strong> ${company.code || '-'}</p>
                        </div>
                    </div>
                    ${company.company_desc ? `
                        <div class="row mt-3">
                            <div class="col-12">
                                <h6>公司描述:</h6>
                                <p class="text-muted">${company.company_desc}</p>
                            </div>
                        </div>
                    ` : ''}
                `;
            }

            // Global error handlers to ensure loading is always hidden
            window.addEventListener('error', function(e) {
                console.error('[DEBUG] Global error:', e.error);
                const overlay = document.getElementById('loadingOverlay');
                if (overlay) overlay.style.display = 'none';
            });

            window.addEventListener('unhandledrejection', function(e) {
                console.error('[DEBUG] Unhandled promise rejection:', e.reason);
                const overlay = document.getElementById('loadingOverlay');
                if (overlay) overlay.style.display = 'none';
            });

            // Initialize
            document.addEventListener('DOMContentLoaded', function() {
                console.log('[DEBUG] DOMContentLoaded event fired');
                // Set up search input enter key
                const searchInput = document.getElementById('searchInput');
                if (searchInput) {
                    searchInput.addEventListener('keypress', function(e) {
                        if (e.key === 'Enter') {
                            searchCompanies();
                        }
                    });
                }

                // Load initial data without showing loading for first load
                console.log('[DEBUG] Calling loadCompanies from DOMContentLoaded');
                loadCompaniesWithoutLoading();
            });

            // Load companies without loading overlay (for initial page load)
            async function loadCompaniesWithoutLoading() {
                console.log('[DEBUG] Starting loadCompaniesWithoutLoading');
                try {
                    const params = new URLSearchParams({
                        page: currentPage,
                        page_size: 50
                    });

                    if (currentSearch) {
                        params.append('query', currentSearch);
                    }

                    console.log('[DEBUG] Fetching from /api/companies?' + params.toString());

                    const response = await fetch(`/api/companies?${params}`, {
                        cache: 'no-store',
                        headers: {
                            'Cache-Control': 'no-cache, no-store, must-revalidate'
                        }
                    });

                    console.log('[DEBUG] Response received, status:', response.status);

                    if (response.ok) {
                        const data = await response.json();
                        console.log('[DEBUG] Data parsed:', data);
                        renderCompaniesTable(data);
                        updatePagination(data);
                    } else {
                        throw new Error(`HTTP ${response.status}: Failed to load companies`);
                    }
                } catch (error) {
                    console.error('[DEBUG] Load companies error:', error);
                    const tbody = document.getElementById('companiesTableBody');
                    if (tbody) {
                        tbody.innerHTML = `
                            <tr>
                                <td colspan="6" class="text-center text-danger">
                                    加载失败: ${error.message}
                                </td>
                            </tr>
                        `;
                    }
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    db_health = await db_manager.health_check()
    return {
        "status": "healthy",
        "database": db_health,
        "timestamp": datetime.now().isoformat()
    }


# Include routers
app.include_router(companies.router, prefix="/api/companies", tags=["Companies"])
app.include_router(sync.router, prefix="/api", tags=["Synchronization"])


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on {settings.app_host}:{settings.app_port}")
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.reload,
        log_level=settings.app_log_level.lower()
    )