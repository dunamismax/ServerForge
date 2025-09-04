"""
Constants used throughout ServerForge.

This module contains all hardcoded values used across the application
for easy maintenance and configuration.
"""

from typing import Dict, List, Set

# Version constraints
MIN_RAM_MB: int = 512
MAX_RAM_MB: int = 32768
DEFAULT_RAM_MB: int = 2048

MIN_PORT: int = 1024
MAX_PORT: int = 65535
DEFAULT_PORT: int = 25565

# Limits
MAX_BUILD_NUMBER: int = 9999
MAX_VERSION_LENGTH: int = 100
MAX_FORGE_VERSION_LENGTH: int = 50
MAX_DIRECTORY_INSTANCES: int = 1000

# Network settings
DEFAULT_TIMEOUT_SECONDS: float = 30.0
DOWNLOAD_TIMEOUT_SECONDS: float = 300.0
DOWNLOAD_CHUNK_SIZE: int = 8192

# File permissions
DEFAULT_DIR_MODE: int = 0o755
SCRIPT_EXECUTABLE_MODE: int = 0o755

# Java version mappings
JAVA_VERSION_MAP: Dict[str, int] = {
    "1.7": 8,
    "1.8": 8,
    "1.9": 8,
    "1.10": 8,
    "1.11": 8,
    "1.12": 8,
    "1.13": 8,
    "1.14": 8,
    "1.15": 8,
    "1.16": 8,
    "1.17": 17,
    "1.18": 17,
    "1.19": 17,
    "1.20.0": 17,
    "1.20.1": 17,
    "1.20.2": 17,
    "1.20.3": 17,
    "1.20.4": 17,
    "1.20.5": 21,
    "1.21": 21,
}

DEFAULT_JAVA_VERSION: int = 8

# Supported Java versions for installation
SUPPORTED_JAVA_VERSIONS: Set[int] = {8, 11, 17, 21}

# Linux package names for Java versions
LINUX_JAVA_PACKAGES: Dict[int, str] = {
    8: "openjdk-8-jdk",
    11: "openjdk-11-jdk", 
    17: "openjdk-17-jdk",
    21: "openjdk-21-jdk",
}

# macOS Homebrew formulas for Java versions
MACOS_JAVA_FORMULAS: Dict[int, str] = {
    8: "openjdk@8",
    11: "openjdk@11", 
    17: "openjdk@17",
    21: "openjdk@21",
}

# API URLs
MOJANG_MANIFEST_URL: str = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
PAPER_API_URL: str = "https://api.papermc.io/v2"
FORGE_MAVEN_URL: str = "https://maven.minecraftforge.net/net/minecraftforge/forge"
FORGE_FILES_URL: str = "https://files.minecraftforge.net/net/minecraftforge/forge"
LEAF_API_URL: str = "https://api.leafmc.one"
SPIGOT_BUILDTOOLS_URL: str = "https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar"

# Path validation
FORBIDDEN_SYSTEM_PATHS: List[str] = ['/etc', '/usr', '/var', '/boot', '/sys', '/proc', '/dev']
VALID_PATH_CHARS: str = r'^[a-zA-Z0-9._-]+$'
DANGEROUS_PATH_CHARS: List[str] = ['..', '~', '$', '`', ';', '|', '&', '>', '<', '*', '?']

# Reserved names (Windows compatibility)
RESERVED_PATH_NAMES: Set[str] = {
    'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5',
    'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4',
    'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
}

# Version validation
VALID_VERSION_CHARS: str = r'^[a-zA-Z0-9._+\-]+$'

# Default supported Minecraft versions (fallback when API is unavailable)
DEFAULT_MINECRAFT_VERSIONS: List[str] = [
    "1.7.2", "1.7.4", "1.7.5", "1.7.6", "1.7.7", "1.7.8", "1.7.9", "1.7.10",
    "1.8", "1.8.1", "1.8.2", "1.8.3", "1.8.4", "1.8.5", "1.8.6", "1.8.7", "1.8.8", "1.8.9",
    "1.9", "1.9.1", "1.9.2", "1.9.3", "1.9.4",
    "1.10", "1.10.1", "1.10.2",
    "1.11", "1.11.1", "1.11.2",
    "1.12", "1.12.1", "1.12.2",
    "1.13", "1.13.1", "1.13.2",
    "1.14", "1.14.1", "1.14.2", "1.14.3", "1.14.4",
    "1.15", "1.15.1", "1.15.2",
    "1.16", "1.16.1", "1.16.2", "1.16.3", "1.16.4", "1.16.5",
    "1.17", "1.17.1",
    "1.18", "1.18.1", "1.18.2",
    "1.19", "1.19.1", "1.19.2", "1.19.3", "1.19.4",
    "1.20", "1.20.1", "1.20.2", "1.20.3", "1.20.4", "1.20.5", "1.20.6",
    "1.21", "1.21.1", "1.21.2", "1.21.3", "1.21.4", "1.21.5", "1.21.6", "1.21.7", "1.21.8"
]

# Forge supported versions
FORGE_SUPPORTED_VERSIONS: List[str] = [
    "1.7.10",
    "1.8", "1.8.9",
    "1.9", "1.9.4",
    "1.10", "1.10.2",
    "1.11", "1.11.2",
    "1.12", "1.12.1", "1.12.2",
    "1.13", "1.13.2",
    "1.14", "1.14.1", "1.14.2", "1.14.3", "1.14.4",
    "1.15", "1.15.1", "1.15.2",
    "1.16", "1.16.1", "1.16.2", "1.16.3", "1.16.4", "1.16.5",
    "1.17", "1.17.1",
    "1.18", "1.18.1", "1.18.2",
    "1.19", "1.19.1", "1.19.2", "1.19.3", "1.19.4",
    "1.20", "1.20.1", "1.20.2", "1.20.3", "1.20.4", "1.20.5", "1.20.6",
    "1.21", "1.21.1", "1.21.2", "1.21.3", "1.21.4", "1.21.5", "1.21.6", "1.21.7", "1.21.8"
]

# Spigot supported versions (BuildTools)
SPIGOT_SUPPORTED_VERSIONS: List[str] = [
    "1.8", "1.8.3", "1.8.7", "1.8.8",
    "1.9", "1.9.2", "1.9.4",
    "1.10", "1.10.2",
    "1.11", "1.11.2",
    "1.12", "1.12.1", "1.12.2",
    "1.13", "1.13.1", "1.13.2",
    "1.14", "1.14.1", "1.14.2", "1.14.3", "1.14.4",
    "1.15", "1.15.1", "1.15.2",
    "1.16", "1.16.1", "1.16.2", "1.16.3", "1.16.4", "1.16.5",
    "1.17", "1.17.1",
    "1.18", "1.18.1", "1.18.2",
    "1.19", "1.19.1", "1.19.2", "1.19.3", "1.19.4",
    "1.20", "1.20.1", "1.20.2", "1.20.3", "1.20.4", "1.20.5", "1.20.6",
    "1.21", "1.21.1", "1.21.2", "1.21.3", "1.21.4", "1.21.5", "1.21.6", "1.21.7", "1.21.8"
]