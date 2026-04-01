"""Configuration management for Pixibox UE5 Bridge."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """Configuration manager for UE5 bridge settings.

    Stores configuration at ~/.pixibox/ue5-bridge.json with defaults for
    Pixibox API URL, UE5 Remote Control endpoint, and auto-import settings.
    """

    DEFAULT_CONFIG_DIR = Path.home() / ".pixibox"
    DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "ue5-bridge.json"

    DEFAULT_SETTINGS = {
        "api_url": "https://api.pixibox.ai",
        "api_token": "",
        "ue5_host": "localhost",
        "ue5_port": 30010,
        "auto_import": {
            "enabled": False,
            "poll_interval": 30,
            "content_path": "/Game/Pixibox/Models",
            "spawn_actors": True,
        },
    }

    def __init__(self, config_file: Optional[Path] = None) -> None:
        """Initialize configuration.

        Args:
            config_file: Path to config file. Defaults to ~/.pixibox/ue5-bridge.json
        """
        self.config_file = config_file or self.DEFAULT_CONFIG_FILE
        self.config: Dict[str, Any] = self.DEFAULT_SETTINGS.copy()
        self._load()

    def _load(self) -> None:
        """Load configuration from file if it exists."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    loaded = json.load(f)
                    # Merge with defaults
                    self.config.update(loaded)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load config: {e}. Using defaults.")

    def save(self) -> None:
        """Save configuration to file."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            key: Configuration key (supports dot notation for nested keys)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        if "." in key:
            # Handle nested keys like "auto_import.enabled"
            keys = key.split(".")
            value = self.config
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                else:
                    return default
            return value if value is not None else default

        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.

        Args:
            key: Configuration key (supports dot notation for nested keys)
            value: Value to set
        """
        if "." in key:
            # Handle nested keys like "auto_import.enabled"
            keys = key.split(".")
            config = self.config
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            config[keys[-1]] = value
        else:
            self.config[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary.

        Returns:
            Configuration dictionary
        """
        return self.config.copy()

    def __repr__(self) -> str:
        """String representation of configuration."""
        return f"Config(file={self.config_file})"
