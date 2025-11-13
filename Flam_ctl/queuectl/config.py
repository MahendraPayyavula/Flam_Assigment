"""
Configuration management for queuectl
"""
import json
import os
from pathlib import Path
from typing import Any, Optional


class Config:
    """Manages queuectl configuration

    Supports passing an alternate config directory or file at construction time
    so tests and callers can isolate configuration from the user's home folder.
    """

    # Backwards-compatible class-level paths (existing tests may reference these)
    CONFIG_DIR = Path.home() / ".queuectl"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    DB_FILE = CONFIG_DIR / "jobs.db"

    # Default configuration values
    DEFAULTS = {
        "max_retries": 3,
        "backoff_base": 2,
        "worker_timeout": 300,  # 5 minutes
    }

    def __init__(self, config_dir: Optional[Path] = None, config_file: Optional[Path] = None):
        """Initialize configuration

        Args:
            config_dir: optional Path to directory where config is stored. If
                provided, it takes precedence over the default (~/.queuectl).
            config_file: optional Path to explicit config file. If provided,
                it takes precedence over config_dir / 'config.json'.
        """
        # Determine config directory and file (instance-level)
        default_dir = Path.home() / ".queuectl"
        self.config_dir = Path(config_dir) if config_dir is not None else default_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)

        if config_file is not None:
            self.config_file = Path(config_file)
        else:
            self.config_file = Path(config_dir) / "config.json" if config_dir is not None else self.config_dir / "config.json"

        # Database file path (instance-level)
        self.db_file = self.config_dir / "jobs.db"

        # Mirror backwards-compatible attributes on the instance so callers/tests
        # that assign to Config.CONFIG_FILE or Config.DB_FILE will continue to work
        # when they set them on the instance.
        self.CONFIG_DIR = self.config_dir
        self.CONFIG_FILE = self.config_file
        self.DB_FILE = self.db_file

        # Lazy-load configuration to respect any instance attribute changes
        # (e.g., tests may assign to config.CONFIG_FILE after construction).
        self._config = None

    def _ensure_loaded(self) -> None:
        """Ensure configuration is loaded into memory"""
        if self._config is None:
            self._config = self._load_config()
    
    def _load_config(self) -> dict:
        """Load configuration from file or return defaults"""
        # Respect instance attribute CONFIG_FILE if present (tests may set it)
        cfg_path = getattr(self, "CONFIG_FILE", self.config_file)
        if Path(cfg_path).exists():
            try:
                with open(cfg_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return self.DEFAULTS.copy()
        return self.DEFAULTS.copy()
    
    def _save_config(self) -> None:
        """Save configuration to file"""
        cfg_path = getattr(self, "CONFIG_FILE", self.config_file)
        with open(cfg_path, "w") as f:
            json.dump(self._config, f, indent=2)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        self._ensure_loaded()
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        self._ensure_loaded()
        self._config[key] = value
        self._save_config()
    
    def get_all(self) -> dict:
        """Get all configuration"""
        self._ensure_loaded()
        return self._config.copy()
    
    def reset(self) -> None:
        """Reset configuration to defaults"""
        self._config = self.DEFAULTS.copy()
        self._save_config()


# Global config instance
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """Get or create global config instance (uses default location)"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
