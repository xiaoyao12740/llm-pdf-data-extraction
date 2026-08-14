import pytest

from src.config import load_config
from src.pipeline import run


def test_yaml_config_drives_pipeline_paths(tmp_path):
    raw = tmp_path / "incoming"
    output = tmp_path / "results"
    raw.mkdir()
    config = tmp_path / "config.yaml"
    config.write_text(
        f"paths:\n  raw: {raw.as_posix()}\n  processed: {output.as_posix()}\n"
        "validation:\n  rate_tolerance: 0.01\n"
        "database:\n  enabled: false\n"
        "llm:\n  enabled: false\n",
        encoding="utf-8",
    )

    assert run(config_path=config) == []
    assert (output / "structured_records.json").exists()


def test_yaml_config_requires_mapping_root(tmp_path):
    config = tmp_path / "invalid.yaml"
    config.write_text("- not\n- a\n- mapping\n", encoding="utf-8")
    with pytest.raises(ValueError, match="root must be"):
        load_config(config)
