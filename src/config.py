from pathlib import Path

import yaml


def load_config(path: str | Path | None) -> dict:
    """Load an optional YAML configuration file as a mapping."""
    if path is None:
        return {}
    config_path = Path(path)
    with config_path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    if not isinstance(config, dict):
        raise ValueError("Configuration root must be a YAML mapping")
    return config


def config_value(config: dict, section: str, key: str, default=None):
    values = config.get(section, {})
    if not isinstance(values, dict):
        raise ValueError(f"Configuration section '{section}' must be a mapping")
    return values.get(key, default)
