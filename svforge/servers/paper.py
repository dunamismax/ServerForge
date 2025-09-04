"""
Paper Minecraft server implementation.

This module provides the PaperServer class for installing and managing
Paper Minecraft servers with build selection.
"""

import asyncio
import logging
from typing import List, Optional

from .base import BaseServer

logger = logging.getLogger(__name__)


class PaperServer(BaseServer):
    """Paper Minecraft server implementation."""
    
    def __init__(self, version: str, build: Optional[int] = None, **kwargs):
        super().__init__(version, **kwargs)
        self.build = build
        # Validate version support now that server_type is defined
        self._validate_version_support()
    
    @property
    def server_type(self) -> str:
        return "paper"
    
    @property
    def supported_versions(self) -> List[str]:
        """Get supported Paper versions from Paper API."""
        if not hasattr(self, '_cached_versions'):
            try:
                loop = asyncio.get_event_loop()
                self._cached_versions = loop.run_until_complete(
                    self._api.get_paper_versions()
                )
            except RuntimeError:
                # If no event loop is running, create a new one
                self._cached_versions = asyncio.run(self._api.get_paper_versions())
        return self._cached_versions
    
    def get_jar_filename(self) -> str:
        if self.build:
            return f"paper-{self.version}-{self.build}.jar"
        return f"paper-{self.version}-latest.jar"
    
    async def get_available_builds(self) -> List[int]:
        """Get available builds for the Paper version."""
        return await self._api.get_paper_builds(self.version)
    
    async def get_latest_build(self) -> Optional[int]:
        """Get the latest build number for the Paper version."""
        builds = await self.get_available_builds()
        return max(builds) if builds else None
    
    async def ensure_build_selected(self) -> bool:
        """Ensure a build is selected, defaulting to latest if not specified."""
        if self.build is None:
            latest_build = await self.get_latest_build()
            if latest_build is None:
                logger.error(f"No builds found for Paper {self.version}")
                return False
            self.build = latest_build
            logger.info(f"Selected latest build {self.build} for Paper {self.version}")
        
        return True
    
    async def download_server_jar(self, progress_callback: Optional[callable] = None) -> bool:
        """Download Paper server jar from Paper API."""
        try:
            if not await self.ensure_build_selected():
                return False
            
            download_url = self._api.get_paper_download_url(self.version, self.build)
            logger.info(f"Downloading Paper {self.version} build {self.build}...")
            
            success = await self._download_manager.download_file(
                download_url,
                str(self.server_jar_path),
                progress_callback
            )
            
            if success:
                logger.info(f"Successfully downloaded Paper {self.version} build {self.build}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to download Paper {self.version}: {e}")
            return False
    
    def get_installation_info(self) -> dict:
        """Get information about the Paper server installation."""
        info = super().get_installation_info()
        info["build"] = self.build
        return info