from __future__ import annotations

import importlib.util
import sys
import textwrap
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "validate_prometheus_config.py"
)
spec = importlib.util.spec_from_file_location(
    "validate_prometheus_config", MODULE_PATH
)
assert spec is not None and spec.loader is not None
validator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validator
spec.loader.exec_module(validator)


def _write_configmap(tmp_path, content: str) -> None:
    (tmp_path / "configmap.yaml").write_text(
        textwrap.dedent(content).strip() + "\n"
    )


def test_extract_prometheus_config_reads_embedded_yaml(
    tmp_path, monkeypatch
) -> None:
    _write_configmap(
        tmp_path,
        """
        apiVersion: v1
        kind: ConfigMap
        data:
          prometheus.yml: |
            global:
              scrape_interval: 15s
    """,
    )

    monkeypatch.setattr(
        validator, "CONFIGMAP_PATH", tmp_path / "configmap.yaml"
    )

    config_text = validator.extract_prometheus_config()

    assert "global:" in config_text
    assert config_text.endswith("\n")


def test_extract_prometheus_config_errors_on_empty(
    tmp_path, monkeypatch
) -> None:
    _write_configmap(
        tmp_path,
        """
        apiVersion: v1
        kind: ConfigMap
        data:
          prometheus.yml: |
    """,
    )

    monkeypatch.setattr(
        validator, "CONFIGMAP_PATH", tmp_path / "configmap.yaml"
    )

    with pytest.raises(SystemExit, match="Failed to extract"):
        validator.extract_prometheus_config()


def test_extract_rule_files_returns_yaml_entries(tmp_path, monkeypatch) -> None:
    _write_configmap(
        tmp_path,
        """
        apiVersion: v1
        kind: ConfigMap
        data:
          critical-alerts.yaml: |
            groups:
              - name: demo
          ignored.txt: |
            should be filtered
    """,
    )

    monkeypatch.setattr(
        validator, "RULES_CONFIGMAP_PATH", tmp_path / "configmap.yaml"
    )

    rule_files = validator.extract_rule_files()

    assert list(rule_files) == ["critical-alerts.yaml"]
    assert "groups:" in rule_files["critical-alerts.yaml"]


def test_extract_rule_files_errors_when_missing_yaml(
    tmp_path, monkeypatch
) -> None:
    _write_configmap(
        tmp_path,
        """
        apiVersion: v1
        kind: ConfigMap
        data:
          README: |
            not yaml
    """,
    )

    monkeypatch.setattr(
        validator, "RULES_CONFIGMAP_PATH", tmp_path / "configmap.yaml"
    )

    with pytest.raises(SystemExit, match="No rule files"):
        validator.extract_rule_files()
