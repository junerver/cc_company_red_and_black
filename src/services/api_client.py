"""
External API client for Company Data Synchronization System
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

from ..models.company import ExternalCompany, ExternalCompanyResponse, ExternalData
from ..utils.config import get_settings
from ..utils.exceptions import APIException
from ..utils.logging import get_logger

logger = get_logger(__name__)


class APIClient:
    """Async HTTP client for external API interactions"""

    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[httpx.AsyncClient] = None
        self.endpoints = self.settings.external_api_endpoints

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def initialize(self) -> None:
        """Initialize HTTP client with optimal settings"""
        if self.client:
            return

        # Configure HTTP client limits for high concurrency
        limits = httpx.Limits(
            max_keepalive_connections=self.settings.external_api_max_concurrent // 2,
            max_connections=self.settings.external_api_max_concurrent,
            keepalive_expiry=30.0
        )

        # Configure timeout settings
        timeout = httpx.Timeout(
            connect=self.settings.external_api_timeout // 3,
            read=self.settings.external_api_timeout,
            write=self.settings.external_api_timeout,
            pool=self.settings.external_api_timeout
        )

        self.client = httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            headers={
                "User-Agent": self.settings.external_api_user_agent,
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        )

        logger.info("API client initialized")

    async def close(self) -> None:
        """Close HTTP client"""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info("API client closed")

    async def _request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling and retries"""
        if not self.client:
            await self.initialize()

        last_exception = None

        for attempt in range(self.settings.sync_retry_attempts + 1):
            try:
                response = await self.client.request(method, url, **kwargs)
                response.raise_for_status()

                # Parse JSON response
                try:
                    return response.json()
                except Exception as e:
                    raise APIException(f"Failed to parse JSON response: {e}")

            except httpx.HTTPStatusError as e:
                last_exception = APIException(
                    f"HTTP error {e.response.status_code}: {e.response.text}",
                    status_code=e.response.status_code,
                    response_data=e.response.text
                )

                # Don't retry client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    raise last_exception

                logger.warning(f"Request failed (attempt {attempt + 1}): {last_exception}")

            except httpx.RequestError as e:
                last_exception = APIException(f"Request failed: {e}")
                logger.warning(f"Request failed (attempt {attempt + 1}): {last_exception}")

            # Wait before retry (except for last attempt)
            if attempt < self.settings.sync_retry_attempts:
                delay = self.settings.sync_retry_delay * (2 ** attempt)  # Exponential backoff
                await asyncio.sleep(delay)

        # All attempts failed
        raise last_exception

    async def get_companies_page(self, page_num: int, page_size: int = 50) -> ExternalData:
        """Get a page of companies from the external API"""
        url = f"{self.endpoints['companies']}"
        params = {
            "pageNum": page_num,
            "pageSize": page_size
        }

        logger.debug(f"Fetching companies page {page_num} with size {page_size}")

        try:
            response_data = await self._request("GET", url, params=params)

            # Parse response using Pydantic models
            external_response = ExternalCompanyResponse(**response_data)

            logger.debug(f"Retrieved {len(external_response.data.rows)} companies from page {page_num}")
            return external_response.data

        except Exception as e:
            logger.error(f"Failed to fetch companies page {page_num}: {e}")
            raise

    async def get_total_pages(self, page_size: int = 50) -> int:
        """Get total number of pages by fetching first page"""
        try:
            first_page = await self.get_companies_page(1, page_size)
            total_records = first_page.total
            pages_needed = (total_records + page_size - 1) // page_size
            logger.info(f"Total records: {total_records}, pages needed: {pages_needed}")
            return pages_needed
        except Exception as e:
            logger.error(f"Failed to get total pages: {e}")
            raise

    async def get_all_companies(self, page_size: int = 50) -> List[ExternalCompany]:
        """Get all companies from all pages with parallel requests"""
        try:
            # Get total pages first
            total_pages = await self.get_total_pages(page_size)
            logger.info(f"Fetching {total_pages} pages of companies")

            # Execute all requests in parallel with controlled concurrency
            semaphore = asyncio.Semaphore(self.settings.external_api_max_concurrent)

            async def get_page_with_semaphore(page_num: int) -> List[ExternalCompany]:
                async with semaphore:
                    page_data = await self.get_companies_page(page_num, page_size)
                    return page_data.rows

            # Create and execute all tasks
            tasks = [get_page_with_semaphore(page_num) for page_num in range(1, total_pages + 1)]
            results = await asyncio.gather(*tasks)

            # Flatten results
            all_companies = []
            for page_companies in results:
                all_companies.extend(page_companies)

            logger.info(f"Successfully retrieved {len(all_companies)} companies")
            return all_companies

        except Exception as e:
            logger.error(f"Failed to get all companies: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if external API is accessible"""
        try:
            # Try to fetch a small page as health check
            await self.get_companies_page(1, 1)
            return True
        except Exception as e:
            logger.warning(f"API health check failed: {e}")
            return False


# Convenience function for creating API client
async def create_api_client() -> APIClient:
    """Create and initialize API client"""
    client = APIClient()
    await client.initialize()
    return client