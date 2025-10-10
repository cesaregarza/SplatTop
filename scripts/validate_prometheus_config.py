#!/usr/bin/env python3
"""Validate embedded Prometheus configuration using promtool."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

CONFIGMAP_PATH = Path("k8s/monitoring/prometheus/configmap.yaml")
PROMTOOL_IMAGE = "prom/prometheus:v2.52.0"
CONFIG_KEY = "prometheus.yml: |"
INDENT = "    "

def extract_prometheus_config() -> str:
    lines = CONFIGMAP_PATH.read_text().splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == CONFIG_KEY) + 1
    except StopIteration as exc:  # pragma: no cover - misconfigured configmap
        raise SystemExit("prometheus.yml entry not found in configmap") from exc

    extracted: list[str] = []
    for line in lines[start:]:
        if line.startswith(INDENT):
            extracted.append(line[len(INDENT) :])
            continue
        if not line.strip():
            extracted.append("")
            continue
        break

    if not any(fragment.strip() for fragment in extracted):
        raise SystemExit("Failed to extract prometheus.yml contents from configmap")

    return "\n".join(extracted).rstrip() + "\n"

def run_promtool(config_text: str) -> None:
    with tempfile.NamedTemporaryFile("w", delete=False) as handle:
        handle.write(config_text)
        temp_path = Path(handle.name)

    try:
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{temp_path}:/etc/prometheus/prometheus.yml",
                PROMTOOL_IMAGE,
                "promtool",
                "check",
                "config",
                "/etc/prometheus/prometheus.yml",
            ],
            check=True,
        )
    finally:
        temp_path.unlink(missing_ok=True)

def main() -> None:
    try:
        config_text = extract_prometheus_config()
        run_promtool(config_text)
    except SystemExit:
        raise
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
    except Exception as exc:  # pragma: no cover - unexpected failure
        raise SystemExit(str(exc)) from exc

if __name__ == "__main__":
    main()
