"""
Leaf Minecraft server implementation.

This module provides the LeafServer class for installing and managing
Leaf Minecraft servers (fork of Paper).
"""

import asyncio
import logging
from typing import List, Optional

from .base import BaseServer

logger = logging.getLogger(__name__)


class LeafServer(BaseServer):
    """Leaf Minecraft server implementation."""
    
    def __init__(self, version: str, build: Optional[int] = None, **kwargs):
        super().__init__(version, **kwargs)
        self.build = build
        # Validate version support now that server_type is defined
        self._validate_version_support()
    
    @property
    def server_type(self) -> str:
        return "leaf"
    
    @property
    def supported_versions(self) -> List[str]:
        """Get supported Leaf versions from Leaf API."""
        if not hasattr(self, '_cached_versions'):
            try:
                loop = asyncio.get_event_loop()
                self._cached_versions = loop.run_until_complete(
                    self._api.get_leaf_versions()
                )
            except RuntimeError:
                # If no event loop is running, create a new one
                self._cached_versions = asyncio.run(self._api.get_leaf_versions())
                
            # Fallback list if API fails - use recent versions that Leaf typically supports
            if not self._cached_versions:
                from ..constants import DEFAULT_MINECRAFT_VERSIONS
                # Filter to recent versions that Leaf typically supports
                self._cached_versions = [v for v in DEFAULT_MINECRAFT_VERSIONS 
                                       if v.startswith(('1.19.', '1.20.', '1.21.'))]
        return self._cached_versions
    
    def get_jar_filename(self) -> str:
        if self.build:
            return f"leaf-{self.version}-{self.build}.jar"
        return f"leaf-{self.version}-latest.jar"
    
    async def get_available_builds(self) -> List[int]:
        """Get available builds for the Leaf version."""
        return await self._api.get_leaf_builds(self.version)
    
    async def get_latest_build(self) -> Optional[int]:
        """Get the latest build number for the Leaf version."""
        builds = await self.get_available_builds()
        return max(builds) if builds else None
    
    async def ensure_build_selected(self) -> bool:
        """Ensure a build is selected, defaulting to latest if not specified."""
        if self.build is None:
            latest_build = await self.get_latest_build()
            if latest_build is None:
                logger.error(f"No builds found for Leaf {self.version}")
                return False
            self.build = latest_build
            logger.info(f"Selected latest build {self.build} for Leaf {self.version}")
        
        return True
    
    def is_direct_download_version(self) -> bool:
        """Check if this version has direct download (older versions) or requires build selection."""
        from packaging import version
        try:
            # Versions 1.21.4+ generally have build selection
            return version.parse(self.version) < version.parse("1.21.4")
        except:
            return False
    
    def get_direct_download_url(self) -> str:
        """Get direct download URL for versions that don't use build selection."""
        return f"https://api.leafmc.one/v2/projects/leaf/versions/{self.version}/builds/latest/downloads/leaf-{self.version}.jar"
    
    async def download_server_jar(self, progress_callback: Optional[callable] = None) -> bool:
        """Download Leaf server jar from Leaf API."""
        try:
            # Check if this version uses direct download or build selection
            if self.is_direct_download_version():
                download_url = self.get_direct_download_url()
                logger.info(f"Downloading Leaf {self.version} (direct download)...")
            else:
                if not await self.ensure_build_selected():
                    return False
                
                download_url = self._api.get_leaf_download_url(self.version, self.build)
                logger.info(f"Downloading Leaf {self.version} build {self.build}...")
            
            success = await self._download_manager.download_file(
                download_url,
                str(self.server_jar_path),
                progress_callback
            )
            
            if success:
                if self.build:
                    logger.info(f"Successfully downloaded Leaf {self.version} build {self.build}")
                else:
                    logger.info(f"Successfully downloaded Leaf {self.version}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to download Leaf {self.version}: {e}")
            return False
    
    def create_server_properties(self) -> bool:
        """Create server.properties file with Leaf-specific optimizations."""
        try:
            properties_path = self.install_directory / "server.properties"
            
            properties_content = f"""# Minecraft server properties
# Generated by Minecraft Server Installer for Leaf
server-port={self.server_port}
max-players=20
online-mode=true
white-list=false
level-name=world
gamemode=survival
difficulty=easy
spawn-protection=16
max-world-size=29999984
level-type=minecraft:normal
enable-command-block=false
spawn-monsters=true
spawn-animals=true
spawn-npcs=true
pvp=true
hardcore=false
view-distance=10
simulation-distance=10
resource-pack=
resource-pack-sha1=
allow-flight=false
allow-nether=true
server-name=A Minecraft Server powered by Leaf
motd=A Minecraft Server powered by Leaf
"""
            
            with open(properties_path, 'w') as f:
                f.write(properties_content)
            
            logger.info("Created server.properties for Leaf")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create server.properties: {e}")
            return False
    
    def get_installation_info(self) -> dict:
        """Get information about the Leaf server installation."""
        info = super().get_installation_info()
        info["build"] = self.build
        info["direct_download"] = self.is_direct_download_version()
        return info