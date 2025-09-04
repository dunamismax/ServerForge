"""
Base server classes for Minecraft server management.

This module provides the abstract base class and common functionality
for all Minecraft server types.
"""

import asyncio
import logging
import os
import stat
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..utils.api import DownloadManager, MinecraftVersionAPI
from ..utils.system import JavaManager, PathManager
from ..exceptions import PathValidationError, ServerInstallationError, ValidationError, UnsupportedVersionError
from ..constants import MIN_RAM_MB, MAX_RAM_MB, DEFAULT_RAM_MB, MIN_PORT, MAX_PORT, DEFAULT_PORT, DEFAULT_JAVA_VERSION

logger = logging.getLogger(__name__)


class BaseServer(ABC):
    """Abstract base class for Minecraft servers."""
    
    def __init__(
        self,
        version: str,
        ram_allocation: int = DEFAULT_RAM_MB,
        server_port: int = DEFAULT_PORT,
        install_directory: Optional[Path] = None,
    ) -> None:
        # Validate inputs before setting attributes
        if not isinstance(version, str) or not version.strip():
            raise ValidationError("Version must be a non-empty string")
        
        if not isinstance(ram_allocation, int) or ram_allocation < MIN_RAM_MB or ram_allocation > MAX_RAM_MB:
            raise ValidationError(f"RAM allocation must be between {MIN_RAM_MB}MB and {MAX_RAM_MB}MB")
        
        if not isinstance(server_port, int) or server_port < MIN_PORT or server_port > MAX_PORT:
            raise ValidationError(f"Server port must be between {MIN_PORT} and {MAX_PORT}")
        
        self.version = version.strip()
        self.ram_allocation = ram_allocation
        self.server_port = server_port
        
        # Validate and set install directory if provided
        try:
            self._install_directory = PathManager.validate_install_directory(install_directory)
        except PathValidationError as e:
            raise ValidationError(f"Invalid install directory: {e}")
        
        self._api = None
        self._download_manager = None
        
        # Validate version after setting server_type (which is available after subclass init)
        # This will be checked by calling _validate_version_support() in subclass __init__
    
    def _validate_version_support(self) -> None:
        """Validate that the version is supported by this server type."""
        if not self.is_version_supported(self.version):
            raise UnsupportedVersionError(f"Version {self.version} is not supported for {self.server_type}")
        logger.debug(f"Version {self.version} is supported for {self.server_type}")
    
    async def __aenter__(self) -> 'BaseServer':
        """Async context manager entry."""
        self._api = MinecraftVersionAPI()
        self._download_manager = DownloadManager()
        await self._api.__aenter__()
        await self._download_manager.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._api:
            await self._api.__aexit__(exc_type, exc_val, exc_tb)
        if self._download_manager:
            await self._download_manager.__aexit__(exc_type, exc_val, exc_tb)
    
    @property
    @abstractmethod
    def server_type(self) -> str:
        """Return the server type name."""
        pass
    
    @property
    @abstractmethod
    def supported_versions(self) -> List[str]:
        """Return list of supported Minecraft versions."""
        pass
    
    @property
    def install_directory(self) -> Path:
        """Get the installation directory for this server."""
        if self._install_directory is None:
            try:
                self._install_directory = PathManager.find_available_server_directory(
                    self.server_type, self.version
                )
            except PathValidationError as e:
                raise ServerInstallationError(f"Cannot create install directory: {e}")
        return self._install_directory
    
    @property
    def server_jar_path(self) -> Path:
        """Get path to the server jar file."""
        return self.install_directory / self.get_jar_filename()
    
    @property
    def start_script_path(self) -> Path:
        """Get path to the start script."""
        return self.install_directory / "start.sh"
    
    @abstractmethod
    def get_jar_filename(self) -> str:
        """Get the expected jar filename for this server type."""
        pass
    
    @abstractmethod
    async def download_server_jar(
        self, 
        progress_callback: Optional[callable] = None
    ) -> bool:
        """Download the server jar file."""
        pass
    
    def is_version_supported(self, version: str) -> bool:
        """Check if a version is supported by this server type."""
        return version in self.supported_versions
    
    def get_required_java_version(self) -> int:
        """Get the required Java version for this server."""
        if self._api:
            return self._api.get_java_version(self.version) or DEFAULT_JAVA_VERSION
        
        # Fallback logic when API is not initialized
        from packaging import version
        try:
            ver = version.parse(self.version)
            if ver >= version.parse("1.20.5"):
                return 21
            elif ver >= version.parse("1.17"):
                return 17  
            elif ver >= version.parse("1.12"):
                return 8
            else:
                return DEFAULT_JAVA_VERSION
        except:
            return DEFAULT_JAVA_VERSION
    
    def ensure_java_installation(self) -> bool:
        """Ensure the required Java version is installed."""
        required_version = self.get_required_java_version()
        java_exe = JavaManager.get_java_executable(required_version)
        
        if java_exe is None:
            logger.info(f"Installing Java {required_version}...")
            if not JavaManager.install_java(required_version):
                logger.error(f"Failed to install Java {required_version}")
                return False
            java_exe = JavaManager.get_java_executable(required_version)
        
        if java_exe is None:
            logger.error(f"Java {required_version} is still not available after installation")
            return False
        
        logger.info(f"Using Java {required_version} at {java_exe}")
        return True
    
    def create_server_properties(self) -> bool:
        """Create server.properties file with basic configuration."""
        try:
            properties_path = self.install_directory / "server.properties"
            
            properties_content = f"""# Minecraft server properties
# Generated by Minecraft Server Installer
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
resource-pack=
resource-pack-sha1=
allow-flight=false
allow-nether=true
server-name=A Minecraft Server
"""
            
            with open(properties_path, 'w') as f:
                f.write(properties_content)
            
            logger.info("Created server.properties")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create server.properties: {e}")
            return False
    
    def create_start_script(self) -> bool:
        """Create startup script for the server."""
        try:
            required_java = self.get_required_java_version()
            java_exe = JavaManager.get_java_executable(required_java)
            
            if not java_exe:
                java_exe = "java"  # Fallback to system java
            
            script_content = f"""#!/bin/bash
# Minecraft Server Start Script
# Generated by Minecraft Server Installer
# Server Type: {self.server_type}
# Minecraft Version: {self.version}
# Required Java Version: {required_java}

cd "$(dirname "$0")"

# Check Java version
JAVA_VERSION=$({java_exe} -version 2>&1 | awk -F '"' '/version/ {{print $2}}' | cut -d'.' -f1-2)
REQUIRED_JAVA={required_java}

echo "Detected Java version: $JAVA_VERSION"
echo "Required Java version: $REQUIRED_JAVA"

# Start server with screen session
echo "Starting {self.server_type} server version {self.version}..."
echo "Allocating {self.ram_allocation}MB of RAM"
echo "Press Ctrl+A then D to detach from console"

screen -S "svforge-{self.server_type}-{self.version}" {java_exe} -Xmx{self.ram_allocation}M -Xms512M -jar {self.get_jar_filename()} nogui
"""
            
            with open(self.start_script_path, 'w') as f:
                f.write(script_content)
            
            # Make script executable
            os.chmod(self.start_script_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
            
            logger.info(f"Created start script: {self.start_script_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create start script: {e}")
            return False
    
    def create_eula_file(self) -> bool:
        """Create EULA file with acceptance."""
        try:
            eula_path = self.install_directory / "eula.txt"
            
            eula_content = """# By changing the setting below to TRUE you are indicating your agreement to our EULA (https://account.mojang.com/documents/minecraft_eula).
# Generated by Minecraft Server Installer
eula=true
"""
            
            with open(eula_path, 'w') as f:
                f.write(eula_content)
            
            logger.info("Created EULA file")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create EULA file: {e}")
            return False
    
    async def install(self, progress_callback: Optional[callable] = None) -> bool:
        """Install the server with all necessary files."""
        install_steps = [
            ("Java installation", self._ensure_java_step),
            ("Server jar download", self._download_jar_step),
            ("Server properties creation", self._create_properties_step),
            ("Start script creation", self._create_script_step),
            ("EULA file creation", self._create_eula_step),
        ]
        
        try:
            logger.info(f"Installing {self.server_type} {self.version} to {self.install_directory}")
            
            for step_name, step_func in install_steps:
                try:
                    logger.debug(f"Starting step: {step_name}")
                    if asyncio.iscoroutinefunction(step_func):
                        success = await step_func(progress_callback)
                    else:
                        success = step_func()
                    
                    if not success:
                        error_msg = f"Installation failed at step '{step_name}'"
                        logger.error(error_msg)
                        raise ServerInstallationError(error_msg)
                    
                    logger.debug(f"Completed step: {step_name}")
                    
                except Exception as e:
                    error_msg = f"Installation failed at step '{step_name}': {str(e)}"
                    logger.error(error_msg)
                    raise ServerInstallationError(error_msg) from e
            
            logger.info(f"Successfully installed {self.server_type} {self.version}")
            return True
            
        except ServerInstallationError:
            # Re-raise server installation errors as-is
            raise
        except Exception as e:
            error_msg = f"Unexpected error during server installation: {str(e)}"
            logger.error(error_msg)
            raise ServerInstallationError(error_msg) from e
    
    def _ensure_java_step(self) -> bool:
        """Ensure Java installation step."""
        return self.ensure_java_installation()
    
    async def _download_jar_step(self, progress_callback: Optional[callable] = None) -> bool:
        """Download server jar step."""
        if not self._download_manager:
            raise ServerInstallationError("Download manager not initialized")
        return await self.download_server_jar(progress_callback)
    
    def _create_properties_step(self) -> bool:
        """Create server properties step."""
        return self.create_server_properties()
    
    def _create_script_step(self) -> bool:
        """Create start script step."""
        return self.create_start_script()
    
    def _create_eula_step(self) -> bool:
        """Create EULA file step."""
        return self.create_eula_file()
    
    def is_installed(self) -> bool:
        """Check if the server is already installed."""
        return (
            self.server_jar_path.exists() and
            self.start_script_path.exists() and
            (self.install_directory / "eula.txt").exists()
        )
    
    def get_installation_info(self) -> Dict[str, Union[str, int, bool]]:
        """Get information about the server installation."""
        return {
            "server_type": self.server_type,
            "version": self.version,
            "install_directory": str(self.install_directory),
            "ram_allocation": self.ram_allocation,
            "server_port": self.server_port,
            "java_version": self.get_required_java_version(),
            "installed": self.is_installed(),
            "jar_file": self.get_jar_filename(),
        }