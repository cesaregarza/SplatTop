#!/usr/bin/env python3
"""Validate embedded Prometheus configuration and rules using promtool."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

CONFIGMAP_PATH = Path("k8s/monitoring/prometheus/configmap.yaml")
RULES_CONFIGMAP_PATH = Path("k8s/monitoring/prometheus/rules.yaml")
PROMTOOL_IMAGE = "prom/prometheus:v2.52.0"
INDENT = "  "


def extract_configmap_entries(path: Path) -> dict[str, str]:
    """Return ConfigMap data entries keyed by filename."""

    lines = path.read_text().splitlines()
    entries: dict[str, str] = {}
    in_data_section = False
    data_indent = 0
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())

        if not in_data_section:
            if stripped == "data:":
                in_data_section = True
                data_indent = indent
            i += 1
            continue

        if indent <= data_indent:
            break

        if stripped.endswith(": |"):
            key = stripped[:-3]
            value_indent = indent + len(INDENT)
            value_lines: list[str] = []
            i += 1

            while i < len(lines):
                value_line = lines[i]
                if not value_line.strip():
                    value_lines.append("")
                    i += 1
                    continue

                current_indent = len(value_line) - len(value_line.lstrip())
                if current_indent < value_indent:
                    break

                value_lines.append(value_line[value_indent:])
                i += 1

            entries[key] = "\n".join(value_lines).rstrip() + "\n"
            continue

        i += 1

    if not entries:
        raise SystemExit(f"No ConfigMap data entries discovered in {path}")

    return entries


def extract_prometheus_config() -> str:
    entries = extract_configmap_entries(CONFIGMAP_PATH)
    try:
        config_text = entries["prometheus.yml"]
    except KeyError as exc:  # pragma: no cover - misconfigured configmap
        raise SystemExit("prometheus.yml entry not found in configmap") from exc

    if not config_text.strip():
        raise SystemExit("Failed to extract prometheus.yml contents from configmap")

    return config_text


def extract_rule_files() -> dict[str, str]:
    entries = extract_configmap_entries(RULES_CONFIGMAP_PATH)
    filtered = {name: contents for name, contents in entries.items() if name.endswith(".yaml")}

    if not filtered:
        raise SystemExit("No rule files discovered in rules ConfigMap")

    return filtered


def run_promtool_config(config_text: str) -> None:
    with tempfile.TemporaryDirectory() as tempdir:
        cfg_dir = Path(tempdir)
        config_path = cfg_dir / "prometheus.yml"
        config_path.write_text(config_text)

        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{cfg_dir}:/etc/prometheus/conf:ro",
                PROMTOOL_IMAGE,
                "promtool",
                "check",
                "config",
                "/etc/prometheus/conf/prometheus.yml",
            ],
            check=True,
        )


def run_promtool_rules(rule_files: dict[str, str]) -> None:
    with tempfile.TemporaryDirectory() as tempdir:
        rules_dir = Path(tempdir)
        for name, contents in rule_files.items():
            safe_name = Path(name).name
            (rules_dir / safe_name).write_text(contents)

        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{rules_dir}:/etc/prometheus/rules:ro",
                PROMTOOL_IMAGE,
                "promtool",
                "check",
                "rules",
                "/etc/prometheus/rules",
            ],
            check=True,
        )


def main() -> None:
    try:
        config_text = extract_prometheus_config()
        run_promtool_config(config_text)
        rule_files = extract_rule_files()
        run_promtool_rules(rule_files)
    except SystemExit:
        raise
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
    except Exception as exc:  # pragma: no cover - unexpected failure
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
