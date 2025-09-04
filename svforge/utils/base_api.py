"""
Base API classes with common functionality.

This module provides base classes for API clients to reduce code duplication
and provide consistent interfaces.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, TypeVar, Union

import httpx
import requests

from ..constants import DEFAULT_TIMEOUT_SECONDS, DOWNLOAD_TIMEOUT_SECONDS
from ..exceptions import APIError, DownloadError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ProgressCallback(Protocol):
    """Protocol for progress callback functions."""
    
    def __call__(self, downloaded: int, total: int) -> None:
        """Called with download progress information."""
        ...


class BaseHTTPClient(ABC):
    """Base class for HTTP clients with common functionality."""
    
    def __init__(self, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        """
        Initialize the HTTP client.
        
        Args:
            timeout: Default timeout for requests in seconds
        """
        self.timeout = timeout
        self._session: Optional[requests.Session] = None
        self._async_client: Optional[httpx.AsyncClient] = None
    
    @property
    def session(self) -> requests.Session:
        """Get or create synchronous HTTP session."""
        if self._session is None:
            self._session = requests.Session()
            self._session.timeout = self.timeout
        return self._session
    
    @property
    def async_client(self) -> httpx.AsyncClient:
        """Get or create asynchronous HTTP client."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(timeout=self.timeout)
        return self._async_client
    
    def get_json(self, url: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Perform synchronous GET request and return JSON response.
        
        Args:
            url: URL to request
            **kwargs: Additional arguments passed to requests.get
            
        Returns:
            JSON response as dictionary
            
        Raises:
            APIError: If request fails or returns non-JSON response
        """
        try:
            response = self.session.get(url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"HTTP request failed for {url}: {e}")
            raise APIError(f"Failed to fetch data from {url}: {e}") from e
        except ValueError as e:
            logger.error(f"Invalid JSON response from {url}: {e}")
            raise APIError(f"Invalid JSON response from {url}") from e
    
    async def get_json_async(self, url: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Perform asynchronous GET request and return JSON response.
        
        Args:
            url: URL to request
            **kwargs: Additional arguments passed to httpx.get
            
        Returns:
            JSON response as dictionary
            
        Raises:
            APIError: If request fails or returns non-JSON response
        """
        try:
            response = await self.async_client.get(url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            logger.error(f"HTTP request failed for {url}: {e}")
            raise APIError(f"Failed to fetch data from {url}: {e}") from e
        except ValueError as e:
            logger.error(f"Invalid JSON response from {url}: {e}")
            raise APIError(f"Invalid JSON response from {url}") from e
    
    def close(self) -> None:
        """Close HTTP connections."""
        if self._session:
            self._session.close()
            self._session = None
    
    async def aclose(self) -> None:
        """Close async HTTP connections."""
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None
    
    def __enter__(self) -> 'BaseHTTPClient':
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
    
    async def __aenter__(self) -> 'BaseHTTPClient':
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.aclose()


class BaseVersionAPI(BaseHTTPClient):
    """Base class for version-fetching APIs."""
    
    def __init__(self, base_url: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        """
        Initialize the version API client.
        
        Args:
            base_url: Base URL for the API
            timeout: Request timeout in seconds
        """
        super().__init__(timeout)
        self.base_url = base_url.rstrip('/')
    
    @abstractmethod
    def get_available_versions(self) -> List[str]:
        """Get list of available versions."""
        pass
    
    @abstractmethod
    async def get_available_versions_async(self) -> List[str]:
        """Get list of available versions asynchronously."""
        pass
    
    def build_url(self, endpoint: str) -> str:
        """
        Build full URL from endpoint.
        
        Args:
            endpoint: API endpoint (without leading slash)
            
        Returns:
            Full URL
        """
        return f"{self.base_url}/{endpoint.lstrip('/')}"


class BaseDownloadClient(BaseHTTPClient):
    """Base class for download clients with progress tracking."""
    
    def __init__(self, timeout: float = DOWNLOAD_TIMEOUT_SECONDS) -> None:
        """
        Initialize the download client.
        
        Args:
            timeout: Download timeout in seconds
        """
        super().__init__(timeout)
    
    async def download_file(
        self,
        url: str,
        destination: str,
        progress_callback: Optional[ProgressCallback] = None,
        chunk_size: int = 8192
    ) -> bool:
        """
        Download file with optional progress tracking.
        
        Args:
            url: URL to download from
            destination: Local file path to save to
            progress_callback: Optional callback for progress updates
            chunk_size: Size of chunks to read at once
            
        Returns:
            True if download successful, False otherwise
            
        Raises:
            DownloadError: If download fails
        """
        try:
            async with self.async_client.stream("GET", url) as response:
                response.raise_for_status()
                
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0
                
                with open(destination, "wb") as file:
                    async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                        file.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)
                
                logger.info(f"Successfully downloaded {url} to {destination}")
                return True
                
        except httpx.RequestError as e:
            logger.error(f"Failed to download {url}: {e}")
            raise DownloadError(f"Failed to download {url}: {e}") from e
        except IOError as e:
            logger.error(f"Failed to write file {destination}: {e}")
            raise DownloadError(f"Failed to write file {destination}: {e}") from e


class CachedAPIClient(BaseHTTPClient):
    """Base API client with simple response caching."""
    
    def __init__(self, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        """Initialize cached API client."""
        super().__init__(timeout)
        self._cache: Dict[str, Any] = {}
    
    def get_cached_or_fetch(
        self, 
        cache_key: str, 
        fetch_func: callable, 
        *args: Any, 
        **kwargs: Any
    ) -> Any:
        """
        Get data from cache or fetch if not cached.
        
        Args:
            cache_key: Key for caching
            fetch_func: Function to call if not in cache
            *args: Arguments for fetch function
            **kwargs: Keyword arguments for fetch function
            
        Returns:
            Cached or fetched data
        """
        if cache_key not in self._cache:
            try:
                self._cache[cache_key] = fetch_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Failed to fetch data for cache key {cache_key}: {e}")
                return None
        
        return self._cache[cache_key]
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
    
    def remove_from_cache(self, cache_key: str) -> None:
        """Remove specific item from cache."""
        self._cache.pop(cache_key, None)


class MinecraftServerAPI(BaseVersionAPI, CachedAPIClient):
    """Base class for Minecraft server APIs with common patterns."""
    
    def __init__(self, base_url: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        """Initialize Minecraft server API client."""
        BaseVersionAPI.__init__(self, base_url, timeout)
        CachedAPIClient.__init__(self, timeout)
    
    def get_version_info(self, version: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific version.
        
        Args:
            version: Version to get info for
            
        Returns:
            Version info dictionary or None if not found
        """
        cache_key = f"version_info_{version}"
        return self.get_cached_or_fetch(
            cache_key, 
            self._fetch_version_info, 
            version
        )
    
    @abstractmethod
    def _fetch_version_info(self, version: str) -> Optional[Dict[str, Any]]:
        """Fetch version info from API (to be implemented by subclasses)."""
        pass
    
    def get_download_url(self, version: str, **kwargs: Any) -> Optional[str]:
        """
        Get download URL for a version.
        
        Args:
            version: Version to get URL for
            **kwargs: Additional parameters (build number, etc.)
            
        Returns:
            Download URL or None if not available
        """
        return self._build_download_url(version, **kwargs)
    
    @abstractmethod
    def _build_download_url(self, version: str, **kwargs: Any) -> Optional[str]:
        """Build download URL (to be implemented by subclasses)."""
        pass