"""
Configuration management for svforge.

This module handles configuration loading, validation, and management
using YAML files and environment variables.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from platformdirs import user_config_dir, user_data_dir

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for svforge."""
    
    def __init__(self) -> None:
        self.app_name = "serverforge"
        self.config_dir = Path(user_config_dir(self.app_name))
        self.data_dir = Path(user_data_dir(self.app_name))
        self.config_file = self.config_dir / "config.yaml"
        
        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Default configuration
        self._defaults = {
            "servers": {
                "default_ram": 2048,
                "default_port": 25565,
                "install_directory": str(self.data_dir / "servers"),
                "java_auto_install": True,
                "cache_enabled": True,
                "cache_directory": str(self.data_dir / "cache"),
            },
            "downloads": {
                "timeout": 300,
                "chunk_size": 8192,
                "max_retries": 3,
                "verify_ssl": True,
            },
            "logging": {
                "level": "INFO",
                "file_logging": True,
                "log_file": str(self.data_dir / "logs" / "svforge.log"),
                "max_log_size": "10MB",
                "backup_count": 5,
            },
            "ui": {
                "progress_bar": True,
                "colored_output": True,
                "confirmation_prompts": True,
            }
        }
        
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = yaml.safe_load(f) or {}
                
                # Merge with defaults
                merged_config = self._merge_configs(self._defaults, config)
                
                logger.info(f"Loaded configuration from {self.config_file}")
                return merged_config
                
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}. Using defaults.")
                return self._defaults.copy()
        else:
            # Create default config file
            self.save_config(self._defaults)
            return self._defaults.copy()
    
    def _merge_configs(self, defaults: Dict, user_config: Dict) -> Dict:
        """Recursively merge user config with defaults."""
        result = defaults.copy()
        
        for key, value in user_config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation."""
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation."""
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save_config(self, config: Optional[Dict] = None) -> bool:
        """Save configuration to file."""
        try:
            config_to_save = config or self._config
            
            with open(self.config_file, 'w') as f:
                yaml.dump(config_to_save, f, default_flow_style=False, indent=2)
            
            logger.info(f"Configuration saved to {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults."""
        self._config = self._defaults.copy()
        self.save_config()
        logger.info("Configuration reset to defaults")
    
    def get_servers_directory(self) -> Path:
        """Get the servers installation directory."""
        servers_dir = Path(self.get("servers.install_directory"))
        servers_dir.mkdir(parents=True, exist_ok=True)
        return servers_dir
    
    def get_cache_directory(self) -> Path:
        """Get the cache directory."""
        cache_dir = Path(self.get("servers.cache_directory"))
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    
    def get_log_directory(self) -> Path:
        """Get the log directory."""
        log_file = Path(self.get("logging.log_file"))
        log_dir = log_file.parent
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir


# Global configuration instance
config = Config()