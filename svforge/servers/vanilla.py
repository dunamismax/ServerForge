"""
Vanilla Minecraft server implementation.

This module provides the VanillaServer class for installing and managing
vanilla Minecraft servers.
"""

import logging
from typing import List, Optional

from .base import BaseServer
from ..utils.api import MinecraftVersionAPI
from ..constants import DEFAULT_MINECRAFT_VERSIONS
from ..exceptions import ServerInstallationError

logger = logging.getLogger(__name__)


class VanillaServer(BaseServer):
    """Vanilla Minecraft server implementation."""
    
    def __init__(self, version: str, **kwargs):
        super().__init__(version, **kwargs)
        # Validate version support now that server_type is defined
        self._validate_version_support()
    
    @property
    def server_type(self) -> str:
        return "vanilla"
    
    @property
    def supported_versions(self) -> List[str]:
        """Get supported vanilla versions from Mojang API."""
        if not hasattr(self, '_cached_versions'):
            if self._api:
                self._cached_versions = self._api.get_vanilla_versions()
                # Use fallback if API fails
                if not self._cached_versions:
                    self._cached_versions = DEFAULT_MINECRAFT_VERSIONS.copy()
            else:
                # Use shared constants when API is not available
                self._cached_versions = DEFAULT_MINECRAFT_VERSIONS.copy()
        return self._cached_versions
    
    def get_jar_filename(self) -> str:
        return f"minecraft_server.{self.version}.jar"
    
    async def download_server_jar(self, progress_callback: Optional[callable] = None) -> bool:
        """Download vanilla server jar from Mojang."""
        try:
            if not self._api:
                raise ServerInstallationError("API client not initialized - server must be used as async context manager")
            
            download_url = self._api.get_server_jar_url(self.version)
            if not download_url:
                logger.error(f"No download URL found for vanilla {self.version}")
                return False
            
            logger.info(f"Downloading vanilla server {self.version}...")
            
            success = await self._download_manager.download_file(
                download_url,
                str(self.server_jar_path),
                progress_callback
            )
            
            if success:
                logger.info(f"Successfully downloaded vanilla server {self.version}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to download vanilla server {self.version}: {e}")
            return False