# iso8583sim/cli/config.py
import json
from pathlib import Path

import typer
from pydantic import BaseModel


class CLIConfig(BaseModel):
    """CLI Configuration Model"""

    default_version: str = "1987"
    output_directory: str = "./output"
    templates_directory: str = "./templates"
    log_level: str = "INFO"
    color_output: bool = True
    save_history: bool = True
    history_file: str = "~/.iso8583sim_history"
    default_currency: str = "840"
    default_terminal_id: str = "TEST1234"
    default_merchant_id: str = "MERCHANT123456789"


class ConfigManager:
    def __init__(self):
        self.app_dir = typer.get_app_dir("iso8583sim")
        self.config_file = Path(self.app_dir) / "config.json"
        self.config = self._load_config()

    def _load_config(self) -> CLIConfig:
        """Load configuration from file or create default"""
        try:
            if self.config_file.exists():
                config_data = json.loads(self.config_file.read_text())
                return CLIConfig(**config_data)
            else:
                return self._create_default_config()
        except Exception as e:
            print(f"Error loading config: {e}. Using defaults.")
            return CLIConfig()

    def _create_default_config(self) -> CLIConfig:
        """Create default configuration file"""
        config = CLIConfig()
        self._save_config(config)
        return config

    def _save_config(self, config: CLIConfig):
        """Save configuration to file"""
        try:
            Path(self.app_dir).mkdir(parents=True, exist_ok=True)
            self.config_file.write_text(config.model_dump_json(indent=2))
        except Exception as e:
            print(f"Error saving config: {e}")

    def update_config(self, **kwargs):
        """Update configuration with new values"""
        config_data = self.config.model_dump()
        config_data.update(kwargs)
        self.config = CLIConfig(**config_data)
        self._save_config(self.config)

    def get_config(self) -> CLIConfig:
        """Get current configuration"""
        return self.config
