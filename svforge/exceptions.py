"""
Custom exception classes for ServerForge.

This module defines the exception hierarchy used throughout the application
for consistent error handling and reporting.
"""

from typing import Optional


class ServerForgeError(Exception):
    """Base exception class for all ServerForge errors."""
    
    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.cause = cause
    
    def __str__(self) -> str:
        if self.cause:
            return f"{self.message} (caused by: {self.cause})"
        return self.message


class ValidationError(ServerForgeError):
    """Raised when input validation fails."""
    pass


class PathValidationError(ValidationError):
    """Raised when path validation fails."""
    pass


class ServerInstallationError(ServerForgeError):
    """Raised when server installation fails."""
    pass


class DownloadError(ServerForgeError):
    """Raised when file download fails."""
    pass


class SystemError(ServerForgeError):
    """Raised when system-level operations fail."""
    pass


class JavaError(SystemError):
    """Raised when Java-related operations fail."""
    pass


class APIError(ServerForgeError):
    """Raised when API calls fail."""
    pass


class ConfigurationError(ServerForgeError):
    """Raised when configuration is invalid or missing."""
    pass


class UnsupportedVersionError(ValidationError):
    """Raised when an unsupported Minecraft version is specified."""
    pass