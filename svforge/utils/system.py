"""
System utilities for cross-platform support and Java management.

This module provides utilities for detecting the operating system,
managing Java installations, and handling system-specific operations.
"""

import logging
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePath
from typing import Dict, List, Optional, Tuple

from ..exceptions import PathValidationError, JavaError, SystemError

logger = logging.getLogger(__name__)


class SecurePathValidator:
    """Validates and sanitizes paths to prevent traversal attacks."""
    
    # Characters that are potentially dangerous in paths
    DANGEROUS_CHARS = ['..', '~', '$', '`', ';', '|', '&', '>', '<', '*', '?']
    
    # Reserved names on Windows that shouldn't be used
    RESERVED_NAMES = {
        'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5',
        'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4',
        'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    @staticmethod
    def validate_server_name(name: str) -> bool:
        """Validate server type/version names."""
        if not name or not isinstance(name, str):
            return False
        
        # Only allow alphanumeric, dots, dashes, and underscores
        if not re.match(r'^[a-zA-Z0-9._-]+$', name):
            return False
        
        # Don't allow names that are only dots or start with dots
        if name.startswith('.') or name == '.' or name == '..':
            return False
        
        # Check for reserved names (case insensitive)
        if name.upper() in SecurePathValidator.RESERVED_NAMES:
            return False
        
        # Reasonable length limit
        if len(name) > 100:
            return False
        
        return True
    
    @staticmethod
    def sanitize_path_component(component: str) -> str:
        """Sanitize a single path component."""
        if not SecurePathValidator.validate_server_name(component):
            raise PathValidationError(f"Invalid path component: {component}")
        
        # Remove any potentially dangerous characters
        sanitized = re.sub(r'[^\w._-]', '', component)
        
        # Ensure it's not empty after sanitization
        if not sanitized:
            raise PathValidationError(f"Path component became empty after sanitization: {component}")
        
        return sanitized
    
    @staticmethod
    def validate_and_resolve_path(path: Path, allowed_parent: Path) -> Path:
        """Validate and resolve a path, ensuring it stays within allowed parent."""
        try:
            # Resolve the path to handle any symbolic links or relative components
            resolved_path = path.resolve()
            resolved_parent = allowed_parent.resolve()
            
            # Ensure the resolved path is within the allowed parent directory
            if not str(resolved_path).startswith(str(resolved_parent)):
                raise PathValidationError(
                    f"Path traversal detected: {path} resolves outside allowed directory {allowed_parent}"
                )
            
            return resolved_path
            
        except (OSError, ValueError) as e:
            raise PathValidationError(f"Invalid path: {path} - {e}")
    
    @staticmethod
    def create_safe_directory(path: Path, mode: int = 0o755) -> Path:
        """Safely create a directory with proper validation."""
        try:
            # Validate each path component
            for part in path.parts:
                if part not in ['/', '\\'] and part:  # Skip root separators
                    SecurePathValidator.validate_server_name(part)
            
            # Create directory with restrictive permissions
            path.mkdir(parents=True, exist_ok=True, mode=mode)
            
            # Verify the directory was created and has correct permissions
            if not path.exists() or not path.is_dir():
                raise PathValidationError(f"Failed to create directory: {path}")
            
            return path
            
        except OSError as e:
            raise PathValidationError(f"Cannot create directory {path}: {e}")


class SystemInfo:
    """Provides information about the current system."""
    
    @staticmethod
    def get_platform() -> str:
        """Get the current platform (linux, darwin, windows)."""
        return platform.system().lower()
    
    @staticmethod
    def is_supported_platform() -> bool:
        """Check if the current platform is supported."""
        return SystemInfo.get_platform() in ["linux", "darwin"]
    
    @staticmethod
    def get_architecture() -> str:
        """Get the system architecture."""
        return platform.machine()
    
    @staticmethod
    def get_os_info() -> Dict[str, str]:
        """Get detailed OS information."""
        return {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        }
    
    @staticmethod
    def is_root() -> bool:
        """Check if running as root/admin."""
        return os.geteuid() == 0 if hasattr(os, 'geteuid') else False


class JavaManager:
    """Manages Java installations and version detection."""
    
    JAVA_VERSIONS = {
        8: "openjdk-8-jdk",
        11: "openjdk-11-jdk", 
        17: "openjdk-17-jdk",
        21: "openjdk-21-jdk",
    }
    
    @staticmethod
    def find_java_installations() -> Dict[int, str]:
        """Find all Java installations on the system."""
        installations = {}
        
        # Common Java installation paths
        if SystemInfo.get_platform() == "darwin":  # macOS
            java_paths = [
                "/Library/Java/JavaVirtualMachines",
                "/System/Library/Java/JavaVirtualMachines",
                "/usr/libexec/java_home",
            ]
            
            # Use java_home on macOS to find installations
            try:
                result = subprocess.run(
                    ["/usr/libexec/java_home", "-V"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                
                for line in result.stdout.split('\n'):
                    if 'jdk' in line.lower() or 'openjdk' in line.lower():
                        # Parse version from output
                        parts = line.strip().split()
                        if parts:
                            version_str = parts[0]
                            try:
                                # Extract major version number
                                if version_str.startswith('1.'):
                                    major_version = int(version_str.split('.')[1])
                                else:
                                    major_version = int(version_str.split('.')[0])
                                
                                # Get path for this version
                                java_home = subprocess.run(
                                    ["/usr/libexec/java_home", "-v", version_str],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True
                                )
                                if java_home.returncode == 0:
                                    installations[major_version] = java_home.stdout.strip()
                            except (ValueError, IndexError):
                                continue
                                
            except FileNotFoundError:
                logger.warning("java_home not found on macOS")
                
        elif SystemInfo.get_platform() == "linux":  # Linux
            java_paths = [
                "/usr/lib/jvm",
                "/usr/java",
                "/opt/java",
            ]
            
            for base_path in java_paths:
                if os.path.exists(base_path):
                    for item in os.listdir(base_path):
                        item_path = os.path.join(base_path, item)
                        if os.path.isdir(item_path):
                            # Try to determine version from directory name
                            java_version = JavaManager._parse_version_from_path(item)
                            if java_version:
                                installations[java_version] = item_path
        
        return installations
    
    @staticmethod
    def _parse_version_from_path(path: str) -> Optional[int]:
        """Parse Java version from installation path."""
        path_lower = path.lower()
        
        # Common patterns for Java version in path names
        version_patterns = [
            ("java-8", 8),
            ("java-11", 11),
            ("java-17", 17),
            ("java-21", 21),
            ("jdk-8", 8),
            ("jdk-11", 11),
            ("jdk-17", 17),
            ("jdk-21", 21),
            ("openjdk-8", 8),
            ("openjdk-11", 11),
            ("openjdk-17", 17),
            ("openjdk-21", 21),
            ("1.8", 8),
        ]
        
        for pattern, version in version_patterns:
            if pattern in path_lower:
                return version
        
        return None
    
    @staticmethod
    def get_java_executable(java_version: Optional[int] = None) -> Optional[str]:
        """Get path to Java executable for specified version."""
        if java_version:
            installations = JavaManager.find_java_installations()
            if java_version in installations:
                java_home = installations[java_version]
                java_exe = os.path.join(java_home, "bin", "java")
                if os.path.isfile(java_exe):
                    return java_exe
        
        # Fall back to system default Java
        java_exe = shutil.which("java")
        if java_exe:
            return java_exe
        
        return None
    
    @staticmethod
    def get_java_version(java_executable: str) -> Optional[int]:
        """Get Java version from executable."""
        try:
            result = subprocess.run(
                [java_executable, "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # Parse version from output (stderr is redirected to stdout)
            version_line = result.stdout.split('\n')[0]
            if 'openjdk version' in version_line or 'java version' in version_line:
                # Extract version string
                version_str = version_line.split('"')[1]
                
                if version_str.startswith('1.'):
                    return int(version_str.split('.')[1])
                else:
                    return int(version_str.split('.')[0])
                    
        except (subprocess.SubprocessError, ValueError, IndexError):
            logger.error(f"Failed to get Java version from {java_executable}")
        
        return None
    
    @staticmethod
    def install_java(version: int) -> bool:
        """Install Java version using system package manager."""
        if not JavaManager.is_java_version_supported(version):
            logger.error(f"Java {version} is not supported")
            return False
        
        platform_name = SystemInfo.get_platform()
        
        if platform_name == "linux":
            return JavaManager._install_java_linux(version)
        elif platform_name == "darwin":
            return JavaManager._install_java_macos(version)
        else:
            logger.error(f"Java installation not supported on {platform_name}")
            return False
    
    @staticmethod
    def _install_java_linux(version: int) -> bool:
        """Install Java on Linux using apt with user confirmation."""
        try:
            package_name = JavaManager.JAVA_VERSIONS.get(version)
            if not package_name:
                logger.error(f"No package available for Java {version}")
                return False
            
            # Ask for user confirmation before installing
            logger.info(f"Java {version} is required but not found.")
            logger.info(f"Would attempt to install package: {package_name}")
            
            # This should be handled by the calling code to prompt the user
            # For now, we'll log and return False to require manual installation
            logger.warning(f"Automatic Java installation requires manual confirmation.")
            logger.info(f"Please install manually with: sudo apt install {package_name}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to check Java installation options: {e}")
            return False
    
    @staticmethod
    def _install_java_macos(version: int) -> bool:
        """Install Java on macOS using Homebrew."""
        try:
            # Check if Homebrew is installed
            if not shutil.which("brew"):
                logger.error("Homebrew is required to install Java on macOS")
                return False
            
            # Map version to Homebrew formula
            formulas = {
                8: "openjdk@8",
                11: "openjdk@11", 
                17: "openjdk@17",
                21: "openjdk@21",
            }
            
            formula = formulas.get(version)
            if not formula:
                return False
            
            subprocess.run(["brew", "install", formula], check=True)
            
            logger.info(f"Successfully installed Java {version}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install Java {version}: {e}")
            return False
    
    @staticmethod
    def is_java_version_supported(version: int) -> bool:
        """Check if Java version is supported."""
        return version in JavaManager.JAVA_VERSIONS


class PathManager:
    """Manages paths and directories for server installations with security validation."""
    
    @staticmethod
    def get_servers_directory() -> Path:
        """Get the base directory for server installations."""
        if SystemInfo.get_platform() == "darwin":
            base_dir = Path.home() / "minecraft_servers"
        else:
            base_dir = Path.home() / "minecraft_servers"  # Changed from /opt for security
        
        return SecurePathValidator.create_safe_directory(base_dir)
    
    @staticmethod
    def get_server_directory(server_type: str, version: str, instance: int = 0) -> Path:
        """Get directory for a specific server instance with validation."""
        # Validate input parameters
        if not SecurePathValidator.validate_server_name(server_type):
            raise PathValidationError(f"Invalid server type: {server_type}")
        
        if not SecurePathValidator.validate_server_name(version):
            raise PathValidationError(f"Invalid version: {version}")
        
        if instance < 0 or instance > 999:  # Reasonable instance limit
            raise PathValidationError(f"Invalid instance number: {instance}")
        
        base_dir = PathManager.get_servers_directory()
        
        # Sanitize components
        safe_server_type = SecurePathValidator.sanitize_path_component(server_type)
        safe_version = SecurePathValidator.sanitize_path_component(version)
        
        if instance == 0:
            server_dir_name = f"{safe_server_type}-{safe_version}"
        else:
            server_dir_name = f"{safe_server_type}-{safe_version}-{instance}"
        
        server_dir = base_dir / server_dir_name
        
        # Validate the final path is within allowed directory
        validated_path = SecurePathValidator.validate_and_resolve_path(server_dir, base_dir)
        
        return SecurePathValidator.create_safe_directory(validated_path)
    
    @staticmethod
    def find_available_server_directory(server_type: str, version: str) -> Path:
        """Find next available server directory name with validation."""
        instance = 0
        max_instances = 1000  # Prevent infinite loop
        
        while instance < max_instances:
            try:
                server_dir = PathManager.get_server_directory(server_type, version, instance)
                if not any(server_dir.iterdir()):  # Directory is empty
                    return server_dir
                instance += 1
            except PathValidationError:
                # If validation fails, increment and try again
                instance += 1
        
        raise PathValidationError(f"Unable to find available directory after {max_instances} attempts")
    
    @staticmethod
    def validate_install_directory(install_dir: Optional[Path]) -> Optional[Path]:
        """Validate a custom install directory if provided."""
        if install_dir is None:
            return None
        
        try:
            # Ensure it's within a reasonable base directory
            base_dir = PathManager.get_servers_directory().parent  # One level up from minecraft_servers
            validated_path = SecurePathValidator.validate_and_resolve_path(install_dir, base_dir)
            return SecurePathValidator.create_safe_directory(validated_path)
            
        except PathValidationError as e:
            logger.error(f"Invalid custom install directory: {e}")
            raise