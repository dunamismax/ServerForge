"""
Common validation utilities for svforge.

This module provides shared validation functions to reduce code duplication
across the application and enforce consistent validation patterns.
"""

import re
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ..constants import (
    MIN_RAM_MB, MAX_RAM_MB, MIN_PORT, MAX_PORT,
    MAX_BUILD_NUMBER, MAX_FORGE_VERSION_LENGTH, MAX_VERSION_LENGTH,
    VALID_VERSION_CHARS, FORBIDDEN_SYSTEM_PATHS
)
from ..exceptions import ValidationError


class BaseValidator:
    """Base validator class with common validation methods."""
    
    @staticmethod
    def validate_non_empty_string(value: Any, field_name: str) -> str:
        """Validate that value is a non-empty string."""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")
        
        stripped = value.strip()
        if not stripped:
            raise ValidationError(f"{field_name} cannot be empty")
        
        return stripped
    
    @staticmethod
    def validate_integer_range(
        value: Any, 
        field_name: str, 
        min_value: int, 
        max_value: int
    ) -> int:
        """Validate that value is an integer within the specified range."""
        if not isinstance(value, int):
            raise ValidationError(f"{field_name} must be an integer")
        
        if value < min_value or value > max_value:
            raise ValidationError(
                f"{field_name} must be between {min_value} and {max_value}"
            )
        
        return value
    
    @staticmethod
    def validate_string_length(
        value: str, 
        field_name: str, 
        max_length: int,
        min_length: int = 1
    ) -> str:
        """Validate string length constraints."""
        if len(value) < min_length:
            raise ValidationError(f"{field_name} must be at least {min_length} characters")
        
        if len(value) > max_length:
            raise ValidationError(f"{field_name} must be no more than {max_length} characters")
        
        return value
    
    @staticmethod
    def validate_regex_pattern(
        value: str, 
        field_name: str, 
        pattern: str, 
        pattern_description: str = "valid format"
    ) -> str:
        """Validate that value matches the given regex pattern."""
        if not re.match(pattern, value):
            raise ValidationError(f"{field_name} must have {pattern_description}")
        
        return value


class ServerValidator(BaseValidator):
    """Validator for server-specific inputs."""
    
    @staticmethod
    def validate_ram_allocation(ram: Any) -> int:
        """Validate RAM allocation input."""
        return ServerValidator.validate_integer_range(
            ram, "RAM allocation", MIN_RAM_MB, MAX_RAM_MB
        )
    
    @staticmethod
    def validate_port(port: Any) -> int:
        """Validate server port input."""
        return ServerValidator.validate_integer_range(
            port, "Server port", MIN_PORT, MAX_PORT
        )
    
    @staticmethod
    def validate_version(version: Any) -> str:
        """Validate Minecraft version string."""
        version_str = ServerValidator.validate_non_empty_string(version, "Version")
        
        # Validate length
        version_str = ServerValidator.validate_string_length(
            version_str, "Version", MAX_VERSION_LENGTH
        )
        
        # Validate format
        version_str = ServerValidator.validate_regex_pattern(
            version_str, 
            "Version", 
            VALID_VERSION_CHARS,
            "valid characters (alphanumeric, dots, dashes, underscores, plus signs only)"
        )
        
        return version_str
    
    @staticmethod
    def validate_build_number(build: Any) -> int:
        """Validate build number for server types that support it."""
        return ServerValidator.validate_integer_range(
            build, "Build number", 1, MAX_BUILD_NUMBER
        )
    
    @staticmethod
    def validate_forge_version(forge_version: Any) -> str:
        """Validate Forge version string."""
        forge_str = ServerValidator.validate_non_empty_string(forge_version, "Forge version")
        
        return ServerValidator.validate_string_length(
            forge_str, "Forge version", MAX_FORGE_VERSION_LENGTH
        )
    
    @staticmethod
    def validate_server_directory(directory: Any) -> Path:
        """Validate custom server directory path."""
        if not isinstance(directory, (str, Path)):
            raise ValidationError("Directory must be a string or Path")
        
        try:
            directory_path = Path(directory).resolve()
        except Exception as e:
            raise ValidationError(f"Invalid directory path: {e}")
        
        # Check if it's within forbidden system paths
        path_str = str(directory_path)
        for forbidden_path in FORBIDDEN_SYSTEM_PATHS:
            if path_str.startswith(forbidden_path):
                raise ValidationError("Cannot install to system directories")
        
        return directory_path


class InstallationValidator(BaseValidator):
    """Validator for installation-specific inputs."""
    
    @staticmethod
    def validate_installation_params(
        server_type: str,
        version: str,
        ram: int,
        port: int,
        build: Optional[int] = None,
        forge_version: Optional[str] = None,
        directory: Optional[Union[str, Path]] = None
    ) -> Dict[str, Any]:
        """
        Validate all installation parameters and return cleaned values.
        
        Args:
            server_type: Type of server (vanilla, paper, forge, etc.)
            version: Minecraft version
            ram: RAM allocation in MB
            port: Server port
            build: Optional build number (for Paper/Leaf)
            forge_version: Optional Forge version (for Forge servers)
            directory: Optional custom installation directory
            
        Returns:
            Dict with validated parameters
        """
        validated = {}
        
        # Basic validations
        validated['server_type'] = ServerValidator.validate_non_empty_string(
            server_type, "Server type"
        ).lower()
        validated['version'] = ServerValidator.validate_version(version)
        validated['ram'] = ServerValidator.validate_ram_allocation(ram)
        validated['port'] = ServerValidator.validate_port(port)
        
        # Optional validations
        if build is not None:
            validated['build'] = ServerValidator.validate_build_number(build)
        
        if forge_version is not None:
            validated['forge_version'] = ServerValidator.validate_forge_version(forge_version)
        
        if directory is not None:
            validated['directory'] = ServerValidator.validate_server_directory(directory)
        
        return validated


class APIValidator(BaseValidator):
    """Validator for API-related inputs."""
    
    @staticmethod
    def validate_url(url: Any, field_name: str = "URL") -> str:
        """Validate URL format."""
        url_str = APIValidator.validate_non_empty_string(url, field_name)
        
        # Basic URL validation
        if not (url_str.startswith('http://') or url_str.startswith('https://')):
            raise ValidationError(f"{field_name} must start with http:// or https://")
        
        return url_str
    
    @staticmethod
    def validate_timeout(timeout: Any) -> float:
        """Validate timeout value."""
        if not isinstance(timeout, (int, float)):
            raise ValidationError("Timeout must be a number")
        
        if timeout <= 0:
            raise ValidationError("Timeout must be positive")
        
        if timeout > 3600:  # 1 hour max
            raise ValidationError("Timeout cannot exceed 3600 seconds")
        
        return float(timeout)


def validate_server_installation_input(
    server_type: str,
    version: str,
    ram: int = 2048,
    port: int = 25565,
    build: Optional[int] = None,
    forge_version: Optional[str] = None,
    directory: Optional[Union[str, Path]] = None,
    force: bool = False
) -> Dict[str, Any]:
    """
    Comprehensive validation for server installation inputs.
    
    This is the main validation function used by the CLI and other interfaces.
    
    Args:
        server_type: Type of server to install
        version: Minecraft version
        ram: RAM allocation in MB
        port: Server port
        build: Optional build number (Paper/Leaf)
        forge_version: Optional Forge version (Forge servers)
        directory: Optional custom directory
        force: Whether to force installation
        
    Returns:
        Dict with all validated parameters
        
    Raises:
        ValidationError: If any validation fails
    """
    # Validate all parameters
    params = InstallationValidator.validate_installation_params(
        server_type=server_type,
        version=version,
        ram=ram,
        port=port,
        build=build,
        forge_version=forge_version,
        directory=directory
    )
    
    # Add force flag (no validation needed)
    params['force'] = bool(force)
    
    return params