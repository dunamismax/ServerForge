"""
Spigot Minecraft server implementation.

This module provides the SpigotServer class for installing and managing
Spigot Minecraft servers using BuildTools.
"""

import asyncio
import logging
import os
import subprocess
from pathlib import Path
from typing import List, Optional

from .base import BaseServer
from ..utils.system import JavaManager
from ..constants import SPIGOT_SUPPORTED_VERSIONS

logger = logging.getLogger(__name__)


class SpigotServer(BaseServer):
    """Spigot Minecraft server implementation using BuildTools."""
    
    BUILDTOOLS_URL = "https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar"
    
    def __init__(self, version: str, **kwargs):
        super().__init__(version, **kwargs)
        # Validate version support now that server_type is defined
        self._validate_version_support()
    
    @property
    def server_type(self) -> str:
        return "spigot"
    
    @property
    def supported_versions(self) -> List[str]:
        """Spigot supports versions 1.8.x and higher."""
        return SPIGOT_SUPPORTED_VERSIONS.copy()
    
    @property
    def build_directory(self) -> Path:
        """Get the build directory for Spigot compilation."""
        return self.install_directory / "build"
    
    @property
    def buildtools_path(self) -> Path:
        """Get path to BuildTools.jar."""
        return self.build_directory / "BuildTools.jar"
    
    @property
    def compiled_jar_path(self) -> Path:
        """Get path to the compiled Spigot jar."""
        return self.build_directory / f"spigot-{self.version}.jar"
    
    def get_jar_filename(self) -> str:
        return f"spigot-{self.version}.jar"
    
    async def download_buildtools(self) -> bool:
        """Download BuildTools.jar."""
        try:
            self.build_directory.mkdir(parents=True, exist_ok=True)
            
            logger.info("Downloading BuildTools.jar...")
            
            success = await self._download_manager.download_file(
                self.BUILDTOOLS_URL,
                str(self.buildtools_path)
            )
            
            if success:
                logger.info("Successfully downloaded BuildTools.jar")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to download BuildTools.jar: {e}")
            return False
    
    def check_spigot_cache(self) -> bool:
        """Check if Spigot jar is already cached."""
        cache_dir = Path.home() / ".minecraft_server_cache" / "spigot"
        cached_jar = cache_dir / f"spigot-{self.version}.jar"
        
        if cached_jar.exists():
            logger.info(f"Found cached Spigot {self.version}")
            try:
                # Copy from cache to installation directory
                import shutil
                shutil.copy2(cached_jar, self.server_jar_path)
                logger.info("Copied Spigot jar from cache")
                return True
            except Exception as e:
                logger.warning(f"Failed to copy from cache: {e}")
        
        return False
    
    def cache_spigot_jar(self) -> None:
        """Cache the compiled Spigot jar for future use."""
        try:
            cache_dir = Path.home() / ".minecraft_server_cache" / "spigot"
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            cached_jar = cache_dir / f"spigot-{self.version}.jar"
            
            import shutil
            shutil.copy2(self.server_jar_path, cached_jar)
            logger.info(f"Cached Spigot {self.version} for future use")
            
        except Exception as e:
            logger.warning(f"Failed to cache Spigot jar: {e}")
    
    async def compile_spigot(self) -> bool:
        """Compile Spigot using BuildTools."""
        try:
            java_exe = JavaManager.get_java_executable(8)  # BuildTools needs Java 8+
            if not java_exe:
                logger.error("Java is required to compile Spigot")
                return False
            
            logger.info(f"Compiling Spigot {self.version}... This may take several minutes.")
            
            # Change to build directory
            original_cwd = os.getcwd()
            os.chdir(self.build_directory)
            
            try:
                # Run BuildTools
                process = await asyncio.create_subprocess_exec(
                    java_exe, "-jar", "BuildTools.jar", "--rev", self.version,
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
                    # Move compiled jar to installation directory
                    if self.compiled_jar_path.exists():
                        import shutil
                        shutil.move(self.compiled_jar_path, self.server_jar_path)
                        logger.info(f"Successfully compiled Spigot {self.version}")
                        return True
                    else:
                        logger.error("Compiled Spigot jar not found")
                        return False
                else:
                    logger.error(f"BuildTools failed with return code {process.returncode}")
                    return False
                    
            finally:
                os.chdir(original_cwd)
                
        except Exception as e:
            logger.error(f"Failed to compile Spigot {self.version}: {e}")
            return False
    
    async def download_server_jar(self, progress_callback: Optional[callable] = None) -> bool:
        """Download/compile Spigot server jar."""
        try:
            # Check cache first
            if self.check_spigot_cache():
                return True
            
            # Download BuildTools
            if not await self.download_buildtools():
                return False
            
            # Compile Spigot
            if not await self.compile_spigot():
                return False
            
            # Cache the compiled jar
            self.cache_spigot_jar()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to obtain Spigot {self.version}: {e}")
            return False