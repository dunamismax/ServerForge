"""
API utilities for fetching Minecraft server information and downloads.

This module provides async and sync methods for interacting with various
Minecraft server APIs including Mojang, Paper, Spigot, Forge, and Leaf.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from packaging import version
import httpx
import requests

from ..exceptions import APIError, DownloadError
from .base_api import BaseDownloadClient, MinecraftServerAPI, ProgressCallback
from ..constants import (
    MOJANG_MANIFEST_URL, PAPER_API_URL, LEAF_API_URL,
    DEFAULT_TIMEOUT_SECONDS, DOWNLOAD_TIMEOUT_SECONDS
)

logger = logging.getLogger(__name__)


class PaperAPI(MinecraftServerAPI):
    """API client for Paper server."""
    
    def __init__(self) -> None:
        super().__init__(PAPER_API_URL, DEFAULT_TIMEOUT_SECONDS)
    
    def get_available_versions(self) -> List[str]:
        """Get available Paper versions."""
        try:
            data = self.get_json(self.build_url("projects/paper"))
            return data.get("versions", [])
        except Exception as e:
            logger.error(f"Failed to fetch Paper versions: {e}")
            return []
    
    async def get_available_versions_async(self) -> List[str]:
        """Get available Paper versions asynchronously."""
        try:
            data = await self.get_json_async(self.build_url("projects/paper"))
            return data.get("versions", [])
        except Exception as e:
            logger.error(f"Failed to fetch Paper versions: {e}")
            return []
    
    def get_builds(self, version: str) -> List[int]:
        """Get available builds for a Paper version."""
        try:
            data = self.get_json(self.build_url(f"projects/paper/versions/{version}"))
            return data.get("builds", [])
        except Exception as e:
            logger.error(f"Failed to fetch Paper builds for {version}: {e}")
            return []
    
    async def get_builds_async(self, version: str) -> List[int]:
        """Get available builds for a Paper version asynchronously."""
        try:
            data = await self.get_json_async(self.build_url(f"projects/paper/versions/{version}"))
            return data.get("builds", [])
        except Exception as e:
            logger.error(f"Failed to fetch Paper builds for {version}: {e}")
            return []
    
    def _fetch_version_info(self, version: str) -> Optional[Dict[str, Any]]:
        """Fetch Paper version info."""
        try:
            return self.get_json(self.build_url(f"projects/paper/versions/{version}"))
        except Exception:
            return None
    
    def _build_download_url(self, version: str, build: int = None, **kwargs: Any) -> Optional[str]:
        """Build Paper download URL."""
        if build is None:
            builds = self.get_builds(version)
            if not builds:
                return None
            build = max(builds)
        
        return self.build_url(
            f"projects/paper/versions/{version}/builds/{build}/downloads/paper-{version}-{build}.jar"
        )


class LeafAPI(MinecraftServerAPI):
    """API client for Leaf server."""
    
    def __init__(self) -> None:
        super().__init__(LEAF_API_URL, DEFAULT_TIMEOUT_SECONDS)
    
    def get_available_versions(self) -> List[str]:
        """Get available Leaf versions."""
        try:
            data = self.get_json(self.build_url("projects/leaf"))
            return data.get("versions", [])
        except Exception as e:
            logger.error(f"Failed to fetch Leaf versions: {e}")
            return []
    
    async def get_available_versions_async(self) -> List[str]:
        """Get available Leaf versions asynchronously."""
        try:
            data = await self.get_json_async(self.build_url("projects/leaf"))
            return data.get("versions", [])
        except Exception as e:
            logger.error(f"Failed to fetch Leaf versions: {e}")
            return []
    
    def get_builds(self, version: str) -> List[int]:
        """Get available builds for a Leaf version."""
        try:
            data = self.get_json(self.build_url(f"projects/leaf/versions/{version}"))
            return data.get("builds", [])
        except Exception as e:
            logger.error(f"Failed to fetch Leaf builds for {version}: {e}")
            return []
    
    async def get_builds_async(self, version: str) -> List[int]:
        """Get available builds for a Leaf version asynchronously."""
        try:
            data = await self.get_json_async(self.build_url(f"projects/leaf/versions/{version}"))
            return data.get("builds", [])
        except Exception as e:
            logger.error(f"Failed to fetch Leaf builds for {version}: {e}")
            return []
    
    def _fetch_version_info(self, version: str) -> Optional[Dict[str, Any]]:
        """Fetch Leaf version info."""
        try:
            return self.get_json(self.build_url(f"projects/leaf/versions/{version}"))
        except Exception:
            return None
    
    def _build_download_url(self, version: str, build: int = None, **kwargs: Any) -> Optional[str]:
        """Build Leaf download URL."""
        if build is None:
            builds = self.get_builds(version)
            if not builds:
                return None
            build = max(builds)
        
        return self.build_url(
            f"projects/leaf/versions/{version}/builds/{build}/downloads/leaf-{version}-{build}.jar"
        )


class MinecraftVersionAPI(MinecraftServerAPI):
    """Handles interaction with Minecraft version APIs."""
    
    def __init__(self) -> None:
        super().__init__(MOJANG_MANIFEST_URL, DEFAULT_TIMEOUT_SECONDS)
        self._paper_api = PaperAPI()
        self._leaf_api = LeafAPI()
    
    def get_available_versions(self) -> List[str]:
        """Get available vanilla versions."""
        return self.get_vanilla_versions()
    
    async def get_available_versions_async(self) -> List[str]:
        """Get available vanilla versions asynchronously."""
        return self.get_vanilla_versions()
    
    def _fetch_version_info(self, version: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed version info from Mojang API."""
        try:
            manifest = self.get_json(MOJANG_MANIFEST_URL)
            versions = manifest["versions"]
            
            target_version = version.parse(version)
            
            for version_info in filter(lambda x: x["type"] == "release", versions):
                if version.parse(version_info["id"]) == target_version:
                    # Fetch detailed version info
                    detail_data = self.get_json(version_info["url"])
                    return detail_data
            
            logger.warning(f"Version {version} not found")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get version info for {version}: {e}")
            return None
    
    def _build_download_url(self, version: str, **kwargs: Any) -> Optional[str]:
        """Get server jar download URL for vanilla version."""
        version_info = self.get_version_info(version)
        if version_info and "downloads" in version_info and "server" in version_info["downloads"]:
            return version_info["downloads"]["server"]["url"]
        return None
    
    def get_vanilla_versions(self) -> List[str]:
        """Get list of available Minecraft vanilla versions."""
        try:
            response = requests.get(self.MOJANG_MANIFEST_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return [
                v["id"] for v in data["versions"] 
                if v["type"] == "release"
            ]
        except Exception as e:
            logger.error(f"Failed to fetch vanilla versions: {e}")
            return []
    
    def get_version_info(self, version_str: str) -> Optional[Dict]:
        """Get detailed version information from Mojang API."""
        try:
            if version_str in self._version_cache:
                return self._version_cache[version_str]
            
            response = requests.get(self.MOJANG_MANIFEST_URL, timeout=10)
            response.raise_for_status()
            versions = response.json()["versions"]
            
            target_version = version.parse(version_str)
            
            for version_info in filter(lambda x: x["type"] == "release", versions):
                if version.parse(version_info["id"]) == target_version:
                    # Fetch detailed version info
                    detail_response = requests.get(version_info["url"], timeout=10)
                    detail_response.raise_for_status()
                    detail_data = detail_response.json()
                    
                    self._version_cache[version_str] = detail_data
                    return detail_data
            
            logger.warning(f"Version {version_str} not found")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get version info for {version_str}: {e}")
            return None
    
    def get_java_version(self, minecraft_version: str) -> Optional[int]:
        """Get required Java version for a Minecraft version."""
        version_info = self.get_version_info(minecraft_version)
        if version_info and "javaVersion" in version_info:
            return version_info["javaVersion"]["majorVersion"]
        
        # Fallback logic for older versions
        try:
            ver = version.parse(minecraft_version)
            if ver >= version.parse("1.20.5"):
                return 21
            elif ver >= version.parse("1.17"):
                return 17  
            elif ver >= version.parse("1.12"):
                return 8
            else:
                return 8
        except:
            return 8
    
    def get_server_jar_url(self, minecraft_version: str) -> Optional[str]:
        """Get download URL for vanilla server jar."""
        version_info = self.get_version_info(minecraft_version)
        if version_info and "downloads" in version_info and "server" in version_info["downloads"]:
            return version_info["downloads"]["server"]["url"]
        return None
    
    async def get_paper_versions(self) -> List[str]:
        """Get available Paper versions."""
        try:
            response = await self._client.get(f"{self.PAPER_API_URL}/projects/paper")
            response.raise_for_status()
            data = response.json()
            return data.get("versions", [])
        except Exception as e:
            logger.error(f"Failed to fetch Paper versions: {e}")
            return []
    
    async def get_paper_builds(self, minecraft_version: str) -> List[int]:
        """Get available Paper builds for a specific version."""
        try:
            response = await self._client.get(
                f"{self.PAPER_API_URL}/projects/paper/versions/{minecraft_version}"
            )
            response.raise_for_status()
            data = response.json()
            return data.get("builds", [])
        except Exception as e:
            logger.error(f"Failed to fetch Paper builds for {minecraft_version}: {e}")
            return []
    
    def get_paper_download_url(self, minecraft_version: str, build: int) -> str:
        """Get Paper download URL for specific version and build."""
        return (
            f"{self.PAPER_API_URL}/projects/paper/versions/{minecraft_version}/"
            f"builds/{build}/downloads/paper-{minecraft_version}-{build}.jar"
        )
    
    async def get_leaf_versions(self) -> List[str]:
        """Get available Leaf versions."""
        try:
            response = await self._client.get(f"{self.LEAF_API_URL}/projects/leaf")
            response.raise_for_status()
            data = response.json()
            return data.get("versions", [])
        except Exception as e:
            logger.error(f"Failed to fetch Leaf versions: {e}")
            return []
    
    async def get_leaf_builds(self, minecraft_version: str) -> List[int]:
        """Get available Leaf builds for a specific version."""
        try:
            response = await self._client.get(
                f"{self.LEAF_API_URL}/projects/leaf/versions/{minecraft_version}"
            )
            response.raise_for_status()
            data = response.json()
            return data.get("builds", [])
        except Exception as e:
            logger.error(f"Failed to fetch Leaf builds for {minecraft_version}: {e}")
            return []
    
    def get_leaf_download_url(self, minecraft_version: str, build: int) -> str:
        """Get Leaf download URL for specific version and build."""
        return (
            f"{self.LEAF_API_URL}/projects/leaf/versions/{minecraft_version}/"
            f"builds/{build}/downloads/leaf-{minecraft_version}-{build}.jar"
        )


class DownloadManager(BaseDownloadClient):
    """Handles file downloads with progress tracking."""
    
    def __init__(self) -> None:
        super().__init__(DOWNLOAD_TIMEOUT_SECONDS)


# Convenience functions for backwards compatibility
def find_version_info(version_str: str) -> Optional[Dict]:
    """Find version info for a given Minecraft version."""
    api = MinecraftVersionAPI()
    return api.get_version_info(version_str)


def get_java_version(version_str: str) -> Optional[int]:
    """Get required Java version for Minecraft version."""
    api = MinecraftVersionAPI()
    return api.get_java_version(version_str)


def get_server_url(version_str: str) -> Optional[str]:
    """Get server jar download URL for Minecraft version."""
    api = MinecraftVersionAPI()
    return api.get_server_jar_url(version_str)