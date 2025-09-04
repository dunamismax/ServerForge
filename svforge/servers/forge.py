"""
Forge Minecraft server implementation.

This module provides the ForgeServer class for installing and managing
Minecraft Forge servers.
"""

import asyncio
import logging
import re
import subprocess
from pathlib import Path
from typing import List, Optional
import httpx

from .base import BaseServer
from ..constants import FORGE_SUPPORTED_VERSIONS

logger = logging.getLogger(__name__)


class ForgeServer(BaseServer):
    """Minecraft Forge server implementation."""
    
    FORGE_MAVEN_URL = "https://maven.minecraftforge.net/net/minecraftforge/forge"
    FORGE_FILES_URL = "https://files.minecraftforge.net/net/minecraftforge/forge"
    
    def __init__(self, version: str, forge_version: Optional[str] = None, **kwargs):
        super().__init__(version, **kwargs)
        self.forge_version = forge_version
        # Validate version support now that server_type is defined
        self._validate_version_support()
    
    @property
    def server_type(self) -> str:
        return "forge"
    
    @property
    def supported_versions(self) -> List[str]:
        """Forge supports versions 1.7.10 and higher."""
        return FORGE_SUPPORTED_VERSIONS.copy()
    
    @property
    def forge_installer_path(self) -> Path:
        """Get path to Forge installer jar."""
        if self.forge_version:
            return self.install_directory / f"forge-{self.version}-{self.forge_version}-installer.jar"
        return self.install_directory / f"forge-{self.version}-installer.jar"
    
    def get_jar_filename(self) -> str:
        if self.forge_version:
            return f"forge-{self.version}-{self.forge_version}.jar"
        return f"forge-{self.version}.jar"
    
    async def get_available_forge_versions(self) -> List[str]:
        """Get available Forge versions for the Minecraft version."""
        try:
            async with httpx.AsyncClient() as client:
                # Try to scrape Forge files website
                response = await client.get(f"{self.FORGE_FILES_URL}/index_{self.version}.html")
                if response.status_code == 200:
                    # Parse HTML to extract version numbers
                    content = response.text
                    # This is a simplified regex - in practice you'd need proper HTML parsing
                    versions = re.findall(
                        rf'{self.version}-(\d+\.\d+\.\d+(?:\.\d+)?)',
                        content
                    )
                    return list(set(versions))  # Remove duplicates
                
        except Exception as e:
            logger.warning(f"Failed to fetch Forge versions: {e}")
        
        return []
    
    async def get_latest_forge_version(self) -> Optional[str]:
        """Get the latest Forge version for the Minecraft version."""
        versions = await self.get_available_forge_versions()
        if versions:
            # Sort versions and return the latest
            from packaging import version
            try:
                sorted_versions = sorted(versions, key=lambda x: version.parse(x), reverse=True)
                return sorted_versions[0]
            except Exception:
                return versions[-1]  # Fallback to last in list
        return None
    
    async def ensure_forge_version_selected(self) -> bool:
        """Ensure a Forge version is selected, defaulting to latest if not specified."""
        if self.forge_version is None:
            latest_version = await self.get_latest_forge_version()
            if latest_version is None:
                logger.error(f"No Forge versions found for Minecraft {self.version}")
                return False
            self.forge_version = latest_version
            logger.info(f"Selected latest Forge version {self.forge_version} for Minecraft {self.version}")
        
        return True
    
    def get_forge_installer_url(self) -> str:
        """Get the download URL for Forge installer."""
        if self.forge_version:
            return (
                f"{self.FORGE_MAVEN_URL}/{self.version}-{self.forge_version}/"
                f"forge-{self.version}-{self.forge_version}-installer.jar"
            )
        else:
            # This shouldn't happen if ensure_forge_version_selected is called first
            return f"{self.FORGE_MAVEN_URL}/{self.version}/forge-{self.version}-installer.jar"
    
    async def download_forge_installer(self, progress_callback: Optional[callable] = None) -> bool:
        """Download Forge installer."""
        try:
            if not await self.ensure_forge_version_selected():
                return False
            
            download_url = self.get_forge_installer_url()
            logger.info(f"Downloading Forge installer {self.version}-{self.forge_version}...")
            
            success = await self._download_manager.download_file(
                download_url,
                str(self.forge_installer_path),
                progress_callback
            )
            
            if success:
                logger.info("Successfully downloaded Forge installer")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to download Forge installer: {e}")
            return False
    
    async def install_forge_server(self) -> bool:
        """Install Forge server using the installer."""
        try:
            from ..utils.system import JavaManager
            
            java_exe = JavaManager.get_java_executable()
            if not java_exe:
                logger.error("Java is required to install Forge server")
                return False
            
            logger.info("Installing Forge server...")
            
            # Run Forge installer
            process = await asyncio.create_subprocess_exec(
                java_exe, "-jar", str(self.forge_installer_path), "--installServer",
                cwd=str(self.install_directory),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            
            # Stream output
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                logger.info(line.decode().strip())
            
            await process.wait()
            
            if process.returncode == 0:
                logger.info("Successfully installed Forge server")
                
                # Find the generated server jar
                server_jars = list(self.install_directory.glob("forge-*.jar"))
                server_jars = [jar for jar in server_jars if "installer" not in jar.name]
                
                if server_jars:
                    # Rename to expected filename
                    expected_path = self.server_jar_path
                    if server_jars[0] != expected_path:
                        server_jars[0].rename(expected_path)
                    return True
                else:
                    logger.error("Forge server jar not found after installation")
                    return False
            else:
                logger.error(f"Forge installer failed with return code {process.returncode}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to install Forge server: {e}")
            return False
    
    async def download_server_jar(self, progress_callback: Optional[callable] = None) -> bool:
        """Download and install Forge server."""
        try:
            # Download installer
            if not await self.download_forge_installer(progress_callback):
                return False
            
            # Install server
            if not await self.install_forge_server():
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to obtain Forge server {self.version}: {e}")
            return False
    
    def create_start_script(self) -> bool:
        """Create startup script for Forge server with special considerations."""
        try:
            from ..utils.system import JavaManager
            
            required_java = self.get_required_java_version()
            java_exe = JavaManager.get_java_executable(required_java)
            
            if not java_exe:
                java_exe = "java"
            
            # For newer Forge versions, we need to use run.sh or run.bat
            run_script = self.install_directory / "run.sh"
            if run_script.exists():
                # Forge provides its own run script, modify it using Python instead of sed
                try:
                    # Read the original run script
                    with open(run_script, 'r') as f:
                        run_script_content = f.read()
                    
                    # Use Python regex to safely replace memory allocation
                    import re
                    modified_content = re.sub(
                        r'-Xmx\d+[mMgG]',
                        f'-Xmx{self.ram_allocation}M',
                        run_script_content
                    )
                    
                    # Write back the modified content
                    with open(run_script, 'w') as f:
                        f.write(modified_content)
                    
                    script_content = f"""#!/bin/bash
# Minecraft Forge Server Start Script (Modified)
# Generated by Minecraft Server Installer

cd "$(dirname "$0")"

echo "Starting Forge server version {self.version}-{self.forge_version}..."
echo "Allocating {self.ram_allocation}MB of RAM"
echo "Press Ctrl+A then D to detach from console"

screen -S "svforge-forge-{self.version}" ./run.sh
"""
                except Exception as e:
                    logger.warning(f"Could not modify run.sh, using fallback: {e}")
                    # Fall back to traditional method if modification fails
                    script_content = f"""#!/bin/bash
# Minecraft Forge Server Start Script (Fallback)
# Generated by Minecraft Server Installer

cd "$(dirname "$0")"

echo "Starting Forge server version {self.version}-{self.forge_version}..."
echo "Allocating {self.ram_allocation}MB of RAM"
echo "Press Ctrl+A then D to detach from console"

screen -S "svforge-forge-{self.version}" {java_exe} -Xmx{self.ram_allocation}M -Xms512M -jar {self.get_jar_filename()} nogui
"""
            else:
                # Fallback to traditional method
                script_content = f"""#!/bin/bash
# Minecraft Forge Server Start Script
# Generated by Minecraft Server Installer

cd "$(dirname "$0")"

echo "Starting Forge server version {self.version}-{self.forge_version}..."
echo "Allocating {self.ram_allocation}MB of RAM"
echo "Press Ctrl+A then D to detach from console"

screen -S "svforge-forge-{self.version}" {java_exe} -Xmx{self.ram_allocation}M -Xms512M -jar {self.get_jar_filename()} nogui
"""
            
            with open(self.start_script_path, 'w') as f:
                f.write(script_content)
            
            # Make script executable
            import os
            import stat
            os.chmod(self.start_script_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
            
            logger.info(f"Created Forge start script: {self.start_script_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create Forge start script: {e}")
            return False
    
    def get_installation_info(self) -> dict:
        """Get information about the Forge server installation."""
        info = super().get_installation_info()
        info["forge_version"] = self.forge_version
        return info